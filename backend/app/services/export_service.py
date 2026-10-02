import io
import json
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ExportBatch, GeneExpression, ScoringJob, TargetCandidate
from backend.app.services.expression_evidence import derive_expression_evidence
from backend.app.services.multiomics_service import penalty_from_profile
from backend.app.services import offtarget_service, reference_bundle_service as rb_service
from cs_pipeline.core.ranking_semantics import (
    hazard_formula_text,
    priority_formula_text,
    priority_score,
    within_gene_percentiles,
)
from cs_pipeline.scripts.crispron_scorer import approx_formula_text


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符。"""
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', name.strip())
    return cleaned or "export_batch"


def build_reference_data_template_frame() -> pd.DataFrame:
    """数据需求模板 sheet：参考基因组/表达矩阵等数据的格式要求（D4 缺啥写啥）。"""
    rows = [
        ("参考基因组 FASTA（必需，用于基因组回贴/脱靶/基因内百分位）",
         "多序列 FASTA（.fa/.fasta），建议为该物种组装版本",
         "放到服务端 cs_pipeline/data/reference_genomes/ 后在 Tab 2「导入参考包」填路径注册；"
         "≤50MB 小文件可直传；.fai 索引缺失时自动构建（免 samtools）",
         "未导入时：脱靶计数、基因组回贴、基因内效率百分位均不可计算，导出表逐行标注缺失原因与所需数据"),
        ("基因注释 GFF3（可选，用于基因定位）",
         "标准 GFF3，含 gene 特征行（ID=基因编号）",
         "注册参考包时一并填路径",
         "未导入时：可回贴坐标但无法定位基因，表达证据与基因内百分位不可用，如实标注"),
        ("表达矩阵 CSV/XLSX（可选，用于优先指数表达项）",
         "首列为基因 ID（需与 GFF 基因 ID 同体系），其余列为各组织表达量（TPM 或定量值）",
         "注册时填路径 + 「组织列映射」（组织名→矩阵列名）",
         "未导入时：优先指数表达项按 0（无证据即无加分），导出标注「表达证据缺失」与所需数据"),
        ("基因 ID 匹配规则",
         "same：GFF 与矩阵基因 ID 直接一致；evm_tu_to_model：evm.TU.X ↔ evm.model.X 规则映射（橡胶草体系）",
         "注册时选择",
         "错配规则会导致表达证据缺失——系统只做映射规则变换，不跨体系猜 ID"),
        ("贴入集合（批量提交的同批序列）",
         "同批多条 30bp 序列一起提交即构成贴入集合",
         "批量上传 CSV/Excel（自带模板可下载）",
         "未锚定序列的百分位只有批内排名口径（导出「百分位口径」列逐行标注），非基因内排名；单条无集合不排名"),
    ]
    return pd.DataFrame(rows, columns=["数据项", "格式要求", "提供方式", "缺失时的如实行为"])


def build_methodology_frame() -> pd.DataFrame:
    """sheet2 逐列方法说明：覆盖导出表全部数据列，歧义口径单独备注。"""
    rows = [
        ("【总览】导出表结构", "Sheet1 为数据表，本 sheet 为逐列方法说明",
         "—", "如对任一列的含义或算法有疑问，可先在本表定位口径"),
        ("【关键约定】“未计算”", "该指标尚未算出或计算资源不可用",
         "—", "“未计算”≠ 0，也不代表“已验证无脱靶/无危害”；一律如实标注，不以 0 冒充"),
        ("【关键约定】分数尺度", "各模型分均为模型内部相对尺度",
         "—", "DeepSpCas9/CRISPRon/综合排序效率分均为 0–100 模型分，不是实测编辑率（indel%）；"
              "用途是候选相对排序与择优，不构成绝对效率承诺"),
        ("【关键约定】坐标口径", "基因组起始/终止 = 20nt guide + 3nt PAM 共 23nt 的区间",
         "1-based 闭区间（与基因目录同源）",
         "30bp 完整靶位点 = 该区间 + 上游 4nt + 下游 3nt 侧翼；负链靶点的起止仍按正链坐标递增方向给出"),
        ("实验优选推荐序", "导出批次内的推荐顺序", "按“综合排序效率分”降序",
         "仅批次内排序，跨批次不可比；排序参考非绝对效率承诺"),
        ("靶点唯一ID", "候选靶点主键", "—", "数据库自增 ID，可用于回查"),
        ("目标基因", "候选所属目标基因", "—", "基因命名空间 LsT2T（莴苣 T2T 全基因组目录）"),
        ("染色体", "候选所在染色体", "—", "LsT2T 参考基因组"),
        ("基因组起始 / 基因组终止", "见【关键约定】坐标口径", "guide+PAM 23nt 区间", "1-based 闭区间"),
        ("链向", "靶位点所在链", "+：guide 与正链同向；−：guide 与负链同向",
         "负链靶点给出的序列已是其自身 5'→3' 方向"),
        ("30bp完整靶位点", "用于模型打分的完整序列", "4nt 上游 + 20nt guide + 3nt PAM + 3nt 下游",
         "自参考基因组按坐标提取"),
        ("20bp_Guide序列", "sgRNA 间隔识别区", "与靶位点（除 PAM）互补配对的 20nt",
         "实验合成 guide 的靶向识别骨架即此序列"),
        ("3bp_PAM", "PAM 基序", "恒为 NGG（gRNA 链方向）",
         "歧义备注：负链靶点在基因组正链上读作 CCN——表内给的是 gRNA 链方向的 NGG 写法，不是正链读序"),
        ("GC含量(%)", "20nt guide 的 GC 百分比", "GC 碱基数 / 20 × 100",
         "仅 guide 区，不含侧翼与 PAM；建议区间 40%–70%（软提示参考，不拦截）"),
        ("Poly-T 硬过滤", "含 TTTT 的候选不进入候选列表",
         "U6 启动子（RNA Pol III）遇 TTTT 提前终止转录，gRNA 无法完整表达，"
         "故在候选枚举阶段硬过滤（非扣分）；被过滤数量在界面提示",
         "模型特征表中的 poly_t 系数（β = −0.1617）为过滤后剩余候选的统计扣分，双保险"),
        ("5'G 标记", "5' 端是否为 G", "U6 转录起始偏好 G，5' 为 G 可提高表达",
         "加分标记，不作硬过滤"),
        ("spacer MFE (kcal/mol)", "20nt spacer 自折叠最小自由能",
         "本地 ViennaRNA RNAfold 预测（仅 spacer 20nt 自身折叠，不含 scaffold 骨架序列）",
         "风险警示线 ΔG < −5 kcal/mol（gRNA 文库筛选数据荟萃分析）：负值越大自折叠越稳定，"
         "可能抑制靶向活性；MFE 为参考维度非绝对判据，需与 GC、脱靶、染色质开放状态综合判断"),
        ("解链温度_Tm(C)", "20nt guide 双链解链温度", "最近邻法（Nearest-Neighbor）热力学计算",
         "计算值非实测值"),
        ("综合排序效率分", "综合活性预测分（0–100）",
         "自训练 Stacking 元模型输出：score = 100 / (1 + exp(−(β0 + Σ βj·zj)))，"
         "β0 = −0.5096，zj 为标准化后的 10 维入模特征（见下方特征系数表）",
         "模型 = 分层选择性 Beta-Binomial GLMM（形态二 / v2.1，meta_model_hier_bb_nob879_0921），"
         "训练集为橡胶草 Hi-TOM 扩增子实测 indel 数据 879 行（纯 A 级金标准）；"
         "性能：留出测试集 Spearman ρ=+0.342，低混杂核心折 ρ=+0.464"),
        ("综合排序效率分·与两个活性分的关系", "回答“与 DeepSpCas9/CRISPRon 是否有关、权重多少”",
         "二者是 10 维入模特征中的 2 维（见下方系数表）；模型并非固定百分比加权，"
         "其“权重”即下表的标准化系数 β",
         "DeepSpCas9 与 CRISPRon 两项 |β| 合计约占全部特征 |β| 总量的 13.4%（0.4427/3.3148）；"
         "两分在测试集上高度相关（ρ≈0.998），共线性使二者系数偏小且呈负号"
         "（已知 artifact，不代表“活性分越低越好”），故以系数表为准，不宜给 50%/50% 式百分比权重"),
        ("│特征系数 deepspcas9_score", "DeepSpCas9 模型打分（0–100）", "标准化系数 β = −0.2112",
         "genet 0.17.2 实现的 DeepSpCas9 预训练深度模型"),
        ("│特征系数 crispron_score", "CRISPRon 模型打分（0–100）", "标准化系数 β = −0.2315",
         "CRISPRon 预训练模型"),
        ("│特征系数 gc_total", "20nt guide 全长 GC 含量 [0,1]", "标准化系数 β = −0.6411",
         "序列派生特征"),
        ("│特征系数 gc_seed", "PAM 近端 6nt 种子区 GC 含量 [0,1]", "标准化系数 β = +0.2438",
         "序列派生特征"),
        ("│特征系数 tm", "20nt guide 最近邻解链温度", "标准化系数 β = +0.8453",
         "序列派生特征"),
        ("│特征系数 poly_t", "是否含 TTTT 早期转录终止信号（0/1）", "标准化系数 β = −0.1617",
         "序列派生特征"),
        ("│特征系数 pam_n_A", "PAM 5' 侧首位碱基为 A 的 one-hot", "标准化系数 β = +0.4246",
         "序列派生特征"),
        ("│特征系数 pam_n_C", "PAM 5' 侧首位碱基为 C 的 one-hot", "标准化系数 β = −0.3057",
         "序列派生特征"),
        ("│特征系数 pam_n_G", "PAM 5' 侧首位碱基为 G 的 one-hot", "标准化系数 β = +0.1092",
         "序列派生特征"),
        ("│特征系数 pam_n_T", "PAM 5' 侧首位碱基为 T 的 one-hot", "标准化系数 β = −0.1407",
         "序列派生特征"),
        ("DeepSpCas9活性分", "DeepSpCas9 预训练模型预测活性（0–100）", "genet 0.17.2 离线推理",
         "模型内部分数非实测值；同时作为综合排序效率分的输入特征之一"),
        ("CRISPRon活性分", "CRISPRon 预训练模型预测活性（0–100）",
         f"经 WSL 原生 CRISPRon 实跑（与训练集同一取值约定）；个别无法实跑的序列"
         f"降级为经验近似式 {approx_formula_text()}",
         "进库候选已批量实跑回填（cs_pipeline/scripts/28–29），失败序列保留近似值并在源数据 "
         "crispron_source 列逐条标注（wsl_real=实跑 / approximated=近似式），本导出表未携带该标记；"
         "同为综合排序效率分的输入特征之一"),
        ("潜在脱靶位点数(<=3)", "全基因组潜在脱靶位点计数",
         "自建 Cas-OFFinder 口径全基因组扫描：20nt guide 对 LsT2T 参考基因组正负链逐窗口比对，"
         "要求 PAM=NGG、允许 1–3 错配；本列 = 错配 1–3 的位点累计数；完全匹配行单独计数不计入本列；"
         "正负链命中分别计行",
         "歧义备注：本列不是 MIT 特异性评分、也不是 CFD 评分——MIT/CFD 是按错配位置与类型加权的"
         "切割频率评分，本列为不加权位点计数（口径更保守透明）；实现为 5-mer 鸽笼种子过滤 + 汉明距"
         "校验 + PAM 预筛，与 Cas-OFFinder 金标准比对偏差 ±1；界面点击脱靶数可查看位点明细"
         "（坐标、错配位置、CFD 评分——Doench 2016、MIT 单位点评分——Hsu 2013、所在基因区域）"),
        ("面板内位点数(49NLR面板)", "落入 49 个 NLR demo 基因座 ±20kb 的脱靶命中行数",
         "与“潜在脱靶位点数”同口径扫描后按面板窗口统计；guide 自身 on-target 行不计",
         "面板仅覆盖 49 个 NLR 基因座，是功能性危害评估的范围限定，不代表全基因组功能区"),
        ("组织优先指数(叶) / (根)", "组织特异性择优指数（方案3）",
         priority_formula_text(),
         "TPM_t 取该基因在对应组织（叶/根）的表达量；无表达证据时表达项记 0"
         "（无证据不加分，也不倒扣）；公式同 cs_pipeline/scripts/21（0923 修订版），"
         "百分位口径为基因内（同基因择优用途）"),
        ("功能性脱靶危害(叶) / (根)", "组织特异性脱靶危害分（方案5）",
         hazard_formula_text(),
         "命中 = 49NLR 面板 ±20kb 内 PAM=NGG 且 ≤3 错配的链特异行，guide 自身 on-target 行不计；"
         "数值越小越安全；ω 为错配档位权重（近似 CFD 思想但非 CFD 评分）；"
         "公式同 cs_pipeline/scripts/22 轻量版"),
        ("表达证据状态", "表达证据可用性",
         "由 LsT2T↔LSA crosswalk 映射层级派生：tier1=已映射；tier2=已映射（串联簇）；"
         "tier3=已映射（未挂载 scaffold）；tier4/不可映射=表达证据缺失；无记录=未评估",
         "不编造表达值；组织优先指数的表达项随之取 0"),
        ("表达证据说明", "映射对象与缺失理由",
         "已映射给出 LSA 主映射与 tier/簇/scaffold 证据；缺失给出具体原因",
         "与界面展示同口径"),
        ("是否外显子", "候选是否落在外显子/编码区", "按候选区域注释（CDS/exon）判定",
         "布尔标记，供实验设计过滤参考"),
        ("是否着丝粒区", "候选是否落在着丝粒不稳定区", "按着丝粒注释区间判定",
         "建议避开，但不自动剔除"),
        ("百分位口径", "组织优先指数中效率百分位的计算口径标签",
         "库内该基因预计算候选分布 rank(pct=True)（基因内排名）",
         "Tab 2 自定义序列另有「现场枚举同基因候选分布」与「贴入集合（批内排名）」两种口径，"
         "各导出表逐行标注，口径不同的百分位不可直接互比"),
        ("所用参考包", "多组学指标所用的参考基因组与证据来源", "莴苣 (LsT2T) 预置参考包",
         "Tab 2 可导入自定义参考包（参考基因组+GFF+表达矩阵），届时导出逐行标注实际所用参考包"),
        ("缺失原因", "该行多组学指标缺失的具体原因", "逐行派生",
         "与界面展示同口径；“—”表示无缺失"),
        ("所需数据", "补齐该行缺失指标所需的数据", "逐行派生（见「数据需求模板」sheet）",
         "不以 0 冒充未计算值；补齐数据后重新导出即按需计算"),
    ]
    return pd.DataFrame(rows, columns=["主题 / 数据列", "含义", "计算方法与公式", "来源与口径备注"])


async def create_export_batch(
    name: str,
    format: str,
    candidate_ids: List[int],
    gene_id: Optional[str] = None,
    db: AsyncSession = None,
) -> ExportBatch:
    """创建并保存实验设计导出批次。"""
    if not candidate_ids:
        raise HTTPException(status_code=400, detail="导出批次必须至少包含一个候选靶点")

    fmt = format.lower()
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="仅支持 csv 或 xlsx 格式导出")

    # 查重或校验候选靶点在数据库中是否存在
    stmt = select(TargetCandidate.id).where(TargetCandidate.id.in_(candidate_ids))
    res = await db.execute(stmt)
    found_ids = list(res.scalars().all())

    if not found_ids:
        raise HTTPException(status_code=404, detail="指定的候选靶点在数据库中均不存在")

    batch_id = str(uuid.uuid4())
    batch_name = name.strip() if name and name.strip() else f"gRNA优选批次_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    batch = ExportBatch(
        id=batch_id,
        name=batch_name,
        format=fmt,
        gene_id=gene_id,
        candidate_count=len(found_ids),
        candidate_ids=json.dumps(found_ids),
        created_at=datetime.now(timezone.utc),
    )

    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


async def generate_batch_export_bytes(
    batch_id: str,
    db: AsyncSession,
) -> Tuple[bytes, str, str]:
    """生成符合湿实验下单规范的标准 CSV 或 Excel 表格字节流。"""
    batch = await db.get(ExportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"未找到 ID 为 '{batch_id}' 的导出批次")

    try:
        cand_ids = json.loads(batch.candidate_ids)
    except Exception:
        cand_ids = [int(x.strip()) for x in batch.candidate_ids.split(",") if x.strip().isdigit()]

    stmt = (
        select(TargetCandidate)
        .where(TargetCandidate.id.in_(cand_ids))
        .order_by(TargetCandidate.efficiency_score.desc())
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    if not candidates:
        raise HTTPException(status_code=404, detail="该批次对应的候选靶点数据不存在")

    # 快下载：不在下载请求里做全基因组按需计算（脱靶扫描 ~100 秒/条，下载要等数分钟）。
    # 脱靶分档/优先指数/面板危害由交互页"按需脱靶计算"显式触发（同口径 fill_missing_multiomics
    # 计算并回填持久化），本导出只读已算好的值；缺的逐行标"未计算"（缺失原因/所需数据），不编造数值

    # 基因级表达证据（crosswalk × 表达矩阵），候选级缺失时派生状态与说明
    gene_ids = {c.gene_id for c in candidates}
    res = await db.execute(select(GeneExpression).where(GeneExpression.gene_id.in_(gene_ids)))
    expr_map = {e.gene_id: e for e in res.scalars().all()}

    records = []
    for rank, c in enumerate(candidates, start=1):
        expr_row = expr_map.get(c.gene_id)
        _, expr_display, expr_note = derive_expression_evidence(c.expression_status, expr_row)

        # D4 缺啥写啥：逐行标注缺失原因与所需数据，不以 0 冒充
        need_parts = []
        if c.offtarget_count_mis3 is None:
            need_parts.append("参考基因组 FASTA（含 .fai）用于脱靶扫描")
        if c.priority_score_leaf is None:
            need_parts.append("可定义的效率百分位分布与脱靶谱")
        if expr_row is None or not expr_row.is_mappable:
            need_parts.append("该基因 crosswalk 映射与 5 组织表达矩阵记录（表达项）")
        records.append({
            "实验优选推荐序": rank,
            "靶点唯一ID": c.id,
            "目标基因": c.gene_id,
            "染色体": c.chrom,
            "基因组起始": c.start,
            "基因组终止": c.end,
            "链向": c.strand,
            "30bp完整靶位点": c.seq30,
            "20bp_Guide序列": c.seq20,
            "3bp_PAM(gRNA链方向，恒为NGG；负链靶点在基因组正链读作CCN)": c.pam,
            "GC含量(%)": c.gc_pct,
            "解链温度_Tm(C)": c.tm_c,
            "综合排序效率分": c.efficiency_score,
            "组织优先指数(叶)": c.priority_score_leaf if c.priority_score_leaf is not None else "未计算",
            "组织优先指数(根)": c.priority_score_root if c.priority_score_root is not None else "未计算",
            "功能性脱靶危害(叶)": c.hazard_leaf if c.hazard_leaf is not None else "未计算",
            "功能性脱靶危害(根)": c.hazard_root if c.hazard_root is not None else "未计算",
            "表达证据状态": expr_display,
            "表达证据说明": expr_note,
            "百分位口径": "库内该基因预计算候选分布（rank(pct=True) Tab 1 同口径）",
            "所用参考包": "莴苣 (LsT2T)（3-1_LsT2T.genome.fa，库内 genes/expression 证据）",
            "所需数据": "；".join(need_parts) if need_parts else "—",
            "缺失原因": "—",
            "面板内位点数(49NLR面板)": c.n_intra_panel_sites if c.n_intra_panel_sites is not None else "未计算",
            "DeepSpCas9活性分": c.deepspcas9_score,
            "CRISPRon活性分": c.crispron_score,
            "潜在脱靶位点数(<=3)": c.offtarget_count_mis3 if c.offtarget_count_mis3 is not None else "未计算",
            "是否外显子": "是" if c.is_exon else "否",
            "是否着丝粒区": "是" if c.is_centromere else "否",
        })

    df = pd.DataFrame(records)
    clean_name = sanitize_filename(batch.name)

    if batch.format == "xlsx":
        from openpyxl.styles import Alignment

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="gRNA实验设计优选清单", index=False)
            meth = build_methodology_frame()
            meth.to_excel(writer, sheet_name="指标方法说明", index=False)
            build_reference_data_template_frame().to_excel(writer, sheet_name="数据需求模板", index=False)
            ws = writer.sheets["指标方法说明"]
            for col, width in zip("ABCD", (28, 32, 56, 62)):
                ws.column_dimensions[col].width = width
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
            ws.freeze_panes = "A2"
            ws2 = writer.sheets["数据需求模板"]
            for col, width in zip("ABCD", (34, 40, 46, 56)):
                ws2.column_dimensions[col].width = width
            for row in ws2.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
            ws2.freeze_panes = "A2"
        content = buf.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{clean_name}_{batch.id[:8]}.xlsx"
    else:
        content = df.to_csv(index=False).encode("utf-8-sig")
        media_type = "text/csv"
        filename = f"{clean_name}_{batch.id[:8]}.csv"

    return content, media_type, filename


def _write_sheets(buf: io.BytesIO, df: pd.DataFrame, fmt: str, extra_sheets: Optional[dict] = None) -> bytes:
    """写数据表 + 指标方法说明 + 数据需求模板（xlsx 多 sheet；csv 仅数据表）。"""
    if fmt == "xlsx":
        from openpyxl.styles import Alignment

        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="数据表", index=False)
            meth = build_methodology_frame()
            meth.to_excel(writer, sheet_name="指标方法说明", index=False)
            for name, frame in (extra_sheets or {}).items():
                frame.to_excel(writer, sheet_name=name, index=False)
            build_reference_data_template_frame().to_excel(writer, sheet_name="数据需求模板", index=False)
            for sheet_name in writer.sheets:
                ws = writer.sheets[sheet_name]
                for col_cells in ws.iter_cols(min_row=1, max_row=1):
                    ws.column_dimensions[col_cells[0].column_letter].width = 30
                for row in ws.iter_rows(min_row=2):
                    for cell in row:
                        cell.alignment = Alignment(wrap_text=True, vertical="top")
                ws.freeze_panes = "A2"
        return buf.getvalue()
    return df.to_csv(index=False).encode("utf-8-sig")


async def generate_scoring_job_export_bytes(
    job_id: str,
    db: AsyncSession,
    bundle_id: Optional[str] = None,
    fmt: str = "xlsx",
) -> Tuple[bytes, str, str]:
    """打分任务结果导出（D4 缺啥写啥）：三态多组学注释 + 缺失原因/所需数据/所用参考包/百分位口径。

    口径纪律：未计算/不适用逐行如实标注，绝不以 0 冒充；百分位口径逐行标注
    （库内基因分布 / 贴入集合批内排名 / 不适用）。bundle_id 缺省沿用任务记录的参考包。
    """
    job = (
        await db.execute(
            select(ScoringJob).options(selectinload(ScoringJob.items)).where(ScoringJob.id == job_id)
        )
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail=f"未找到 ID 为 '{job_id}' 的打分任务")
    bundle_id = bundle_id or job.bundle_id or "lettuce"

    items = sorted(job.items, key=lambda x: x.id) if job.items else []
    valid = [it for it in items if it.is_valid and it.efficiency_score is not None]
    ordered = sorted(valid, key=lambda x: float(x.efficiency_score), reverse=True)

    # 档③贴入集合百分位（批内排名口径）；key 与 ordered 同序
    pct_rows = [("paste_set", i, float(it.efficiency_score)) for i, it in enumerate(ordered)]
    pct_by_idx = within_gene_percentiles(pct_rows) if len(ordered) >= 2 else {}
    pct_map = {it.id: pct_by_idx.get(i) for i, it in enumerate(ordered)}
    paste_basis = (
        f"贴入集合百分位（批内排名口径，同批 {len(ordered)} 条，非基因内排名）"
        if len(ordered) >= 2
        else "单条/有效分数不足，无贴入集合可排名：百分位不适用"
    )

    # 预计算命中（同源复用）
    seqs = [it.seq30.strip().upper() for it in valid]
    cand_map = {}
    if seqs:
        res = await db.execute(select(TargetCandidate).where(TargetCandidate.seq30.in_(set(seqs))))
        cand_map = {c.seq30: c for c in res.scalars().all()}

    try:
        bundle = await rb_service.resolve_bundle(db, bundle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    bundle_label = f"{bundle.display_name}（{bundle.id}）"

    # 快导出：不做现场全基因组扫描（回贴一次 ~1 分钟、脱靶 ~100 秒/条，无法即时返回）。
    # 复用已按需算过的结果：先读本进程缓存，再读持久化表（"计算脱靶+优先指数"落库产物，重启不丢），
    # 未算的行按"缺啥写啥"如实标注缺失原因/所需数据，计算留在显式"按需计算"流程
    to_peek = [s for s in dict.fromkeys(seqs) if s not in cand_map]
    profiles = {}
    if bundle.fasta is not None and to_peek:
        seq20s = [s[4:24] for s in to_peek]
        profiles = offtarget_service.peek_profiles(seq20s, bundle.fasta)
        missed = [s for s in seq20s if s not in profiles]
        if missed:
            profiles.update(await offtarget_service.load_persisted_profiles(db, bundle.fasta, missed))

    # 表达证据（库内基因）
    gene_ids = {c.gene_id for c in cand_map.values()}
    expr_map = {}
    if gene_ids:
        res = await db.execute(select(GeneExpression).where(GeneExpression.gene_id.in_(gene_ids)))
        expr_map = {e.gene_id: e for e in res.scalars().all()}

    rows = []
    invalid_items = [it for it in items if not it.is_valid or it.efficiency_score is None]
    rank = 0
    for it in ordered + invalid_items:
        s = it.seq30.strip().upper() if it.seq30 else ""
        cand = cand_map.get(s)
        prof = profiles.get(s[4:24]) if len(s) == 30 else None
        pct = pct_map.get(it.id)

        if not it.is_valid:
            state_display = "序列不合法（未计算）"
            pct_val, basis = "不适用", f"不适用（{it.error_message or '序列不合法'}）"
            prio_val, off_val = "不适用", "不适用"
            expr_status, expr_note = "不适用", "不适用"
            missing = it.error_message or "序列不合法"
            need = "合规 30bp 序列（4+20+NGG+3 布局）"
        elif cand is not None:
            rank += 1
            state_display = "命中预计算候选（与 Tab 1 同源复用）"
            pct_val, basis = "见多组学列", "库内该基因预计算候选分布（rank(pct=True) Tab 1 同口径）"
            prio_val = cand.priority_score_leaf if cand.priority_score_leaf is not None else "未计算"
            off_val = cand.offtarget_count_mis3 if cand.offtarget_count_mis3 is not None else "未计算"
            _, expr_status, expr_note = derive_expression_evidence(cand.expression_status, expr_map.get(cand.gene_id))
            missing = "—"
            need = "—"
        else:
            rank += 1
            if prof is not None:
                state_display = "脱靶已按需计算（复用已算结果，未现场基因组回贴）"
                missing = "—"
            else:
                state_display = "未命中预计算候选库（未计算：快照导出不做现场全基因组扫描）"
                missing = (
                    "该序列未命中预计算候选表；快照导出为即时下载，"
                    "未现场执行基因组回贴与全基因组脱靶扫描"
                )
            off_val = prof.mis3 if prof is not None else "未计算"
            if pct is not None and prof is not None:
                pct_val = round(pct, 4)
                basis = f"{paste_basis}（非基因内口径）"
                prio_val = round(priority_score(pct, penalty_from_profile(prof), 0.0), 6)  # 表达项 0
            else:
                pct_val = round(pct, 4) if pct is not None else "未计算"
                basis = paste_basis
                prio_val = "未计算"
            expr_status, expr_note = (
                "表达证据缺失",
                "未锚定基因座，表达证据不适用；提供基因组回贴+该物种表达矩阵后可计算",
            )
            need_parts = []
            if prof is None:
                need_parts.append(
                    "参考基因组回贴（锚定基因座）+ FASTA（含 .fai）脱靶扫描（约 100 秒/条，可在交互页按需计算后导出）"
                )
            if bundle.expression_layout != "tissue_tpm" or bundle.expression_path is None:
                need_parts.append("表达矩阵+组织列映射（表达项）")
            need = "；".join(need_parts) if need_parts else "—"

        rows.append({
            "实验优选推荐序": rank if it.is_valid else "不适用",
            "样本编号": it.custom_id,
            "30bp完整靶位点": it.seq30,
            "20bp_Guide序列": it.guide_seq or "—",
            "3bp_PAM(gRNA链方向)": it.pam or "—",
            "GC含量(%)": it.gc_pct if it.gc_pct is not None else "—",
            "解链温度_Tm(C)": it.tm_c if it.tm_c is not None else "—",
            "DeepSpCas9活性分": it.deepspcas9_score if it.deepspcas9_score is not None else "未计算",
            "CRISPRon模型来源": it.crispron_source or "未计算",
            "综合排序效率分": it.efficiency_score if it.efficiency_score is not None else "未计算",
            "效率百分位": pct_val,
            "百分位口径": basis,
            "多组学证据状态": state_display,
            "潜在脱靶位点数(<=3)": off_val,
            "组织优先指数(叶)": prio_val,
            "表达证据状态": expr_status,
            "表达证据说明": expr_note,
            "缺失原因": missing,
            "所需数据": need,
            "所用参考包": bundle_label,
        })

    df = pd.DataFrame(rows)
    clean_name = sanitize_filename(job.title or "scoring_job")
    buf = io.BytesIO()
    content = _write_sheets(buf, df, "xlsx" if fmt == "xlsx" else "csv")
    if fmt == "xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{clean_name}_{job.id[:8]}.xlsx"
    else:
        media_type = "text/csv"
        filename = f"{clean_name}_{job.id[:8]}.csv"
    return content, media_type, filename
