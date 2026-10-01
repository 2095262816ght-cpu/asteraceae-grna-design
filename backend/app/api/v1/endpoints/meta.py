"""透明性端点（教师反馈 #4/#5）：算法、版本、参数与参考基因组口径说明。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.services.reference_bundle_service import list_bundles
from cs_pipeline.core.ranking_semantics import (
    hazard_formula_text,
    priority_atac_formula_text,
    priority_formula_text,
)

router = APIRouter()

METHODS_INFO = {
    "efficiency_model": {
        "name": "自研 Stacking 元模型（效率分 v2.1 / noB879）",
        "kind": "自研（非 Rule Set 2/3、非 DeepCRISPR、非 DeepHF）",
        "components": [
            "DeepSpCas9 深度学习模型 on-target 活性分",
            "CRISPRon 深度学习模型 on-target 活性分",
            "10 维序列特征（GC 总量、种子区 GC、Tm、poly-T 等）",
            "分层选择性 Beta-Binomial GLMM 聚合",
        ],
        "validation": "留出验证 Spearman ρ=0.464 / 0.342（如实标注，不同测试集）",
        "model_card": "cs_pipeline/results/model_card_hier_bb_nob879_0921.md",
        "lineage_note": (
            "业界常用效率模型谱系：Doench 2016（Rule Set 2）、Moreno-Mateos 2016、"
            "Doench 2022 Rule Set 3（47,000 条 gRNA 实验数据训练）、深度学习 DeepHF/CRISPRon。"
            "本平台效率分以 DeepSpCas9+CRISPRon 为成分、自训练 GLMM 聚合，不直接套用上述单一模型。"
        ),
    },
    "offtarget": {
        "search": "Cas-OFFinder 式全基因组扫描（鸽笼原理种子筛 + Hamming 验证）",
        "params": {
            "pam": "NGG（SpCas9）",
            "gRNA_length": "20nt",
            "max_mismatches": 3,
            "strands": "正负链分行计数（同一基因组位点双链均合格计两行）",
        },
        "site_scores": [
            "CFD（Cutting Frequency Determination，Doench et al. 2016）：错配位置×碱基对类型罚分连乘×PAM 罚分；本口径仅扫 NGG 故 PAM 罚分恒为 1",
            "MIT/Hsu 单位点 hit score（Hsu et al. 2013）：位置权重罚分×错配间距因子×错配数因子，0–100",
        ],
        "guide_specificity": "CRISPOR 口径：MIT Sguide=100/(100+ΣhitScore)×100；CFD 特异性=100/Σcfd_site",
        "risk_note": "0 错配脱靶（除在靶外完全匹配）致命、1 错配高危、2–3 错配相对可接受",
    },
    "expression_fitness": {
        "poly_t": "含 TTTT 的 spacer 在候选枚举阶段硬过滤（U6 为 RNA Pol III 启动子，遇 TTTT 提前终止转录）",
        "five_prime_g": "5' 端为 G 提高 U6 转录效率（加分标记，不作硬过滤）",
        "mfe": (
            "spacer 二级结构：仅 20nt spacer 自折叠最小自由能（本地 ViennaRNA RNAfold，不含 scaffold 骨架）；"
            "风险阈值 ΔG < -5 kcal/mol（gRNA 文库筛选数据荟萃分析）。MFE 为参考维度，非绝对判据，"
            "需与 GC、脱靶、染色质开放状态综合判断"
        ),
        "gc": "GC 含量建议 40%–70%（参考区间，软提示不拦截）",
    },
    "gene_structure": {
        "source": "参考包 GFF 注释（gene/mRNA/exon/CDS 层级解析，TSS 链感知取转录起始位点）",
        "protein_domains": (
            "蛋白功能域（CC/TIR/NBS/LRR）来自离线注释 NLR-Annotator v2.1b（Steuernagel et al. 2020），"
            "GFF 不含结构域信息；未覆盖基因如实标注缺失"
        ),
    },
    "disclaimer": (
        "所有预测指标为计算估计值，非实验测量。效率分与脱靶风险互相独立，需综合评价；"
        "MFE 阈值为参考维度非绝对判据；各指标口径详见用户手册「参数设置详解」与导出 Excel《指标方法说明》sheet。"
    ),
}


@router.get("/meta/methods", summary="算法与版本说明（透明性声明）")
async def get_methods(db: AsyncSession = Depends(get_db)) -> dict:
    bundles = await list_bundles(db)
    return {
        **METHODS_INFO,
        "reference_genomes": [
            {
                "id": b["id"],
                "display_name": b["display_name"],
                "fasta_available": b["fasta_available"],
                "gff_available": b["gff_available"],
            }
            for b in bundles
        ],
    }


def sort_help_items(tissue_name: str) -> list:
    """排序选项方法学条目：公式行取自 ranking_semantics 单点定义，前端不再复述公式。"""
    return [
        {
            "key": "efficiency_score",
            "title": "on-target 效率分 (v2.1 推荐排序) · 系统默认",
            "direction": "降序（分数高者优先）",
            "lines": [
                "含义：自训练 Stacking 元模型（分层 Beta-Binomial GLMM，v2.1）预测的 on-target 在靶切割活性综合分，0–100。",
                "排名方式：按分数降序；分数由 score = 100/(1+exp(−(β₀+Σβⱼ·zⱼ))) 给出，10 维入模特征 = DeepSpCas9 分、CRISPRon 分、全长 GC、种子区 GC、Tm、polyT 信号、PAM 首碱基 one-hot。",
                "适用：通用排序，与导出表「实验优选推荐序」一致；为同基因内相对排序参考，非绝对效率承诺。",
            ],
        },
        {
            "key": "priority_score",
            "title": f"组织优先指数（{tissue_name}）· 方案3",
            "direction": "降序（指数高者优先）",
            "lines": [
                "含义：面向目标组织的综合择优指数，随「目标组织」切换联动。",
                f"排名方式：{priority_formula_text()}。",
                "适用：已确定目标组织时择优；无表达证据时表达项记 0（不加分也不倒扣）。",
            ],
        },
        {
            "key": "priority_score_atac",
            "title": f"组织优先指数+ATAC（{tissue_name}）· 表观可及性折中变体",
            "direction": "降序（指数高者优先）",
            "lines": [
                "含义：在方案3 基础上引入染色质开放状态的折中指数（demo 专属选项）。",
                f"排名方式：{priority_atac_formula_text()}。",
            ],
        },
        {
            "key": "hazard_score",
            "title": f"功能性脱靶危害（{tissue_name}）· 方案5",
            "direction": "升序（数值越小越安全）",
            "lines": [
                "含义：脱靶命中对目标组织的潜在功能危害。",
                f"排名方式：{hazard_formula_text()}；命中 = 49 个 NLR demo 基因座 ±20kb 内 PAM=NGG 且 ≤3 错配的链特异行，自身 on-target 行不计。",
                "适用：安全性优先筛选，可与组织优先指数配合使用。",
            ],
        },
        {
            "key": "start",
            "title": "基因物理起始坐标",
            "direction": "升序 = 基因组顺序（可切换）",
            "lines": [
                "含义：按候选在参考基因组上的物理位置浏览。",
                "排名方式：按基因组起始坐标排序；坐标口径为 20nt guide + 3nt PAM 共 23nt 区间，1-based 闭区间。",
            ],
        },
        {
            "key": "offtarget_count_mis3",
            "title": "潜在脱靶位点数",
            "direction": "升序优先（位点越少越干净）",
            "lines": [
                "含义：全基因组潜在脱靶位点计数（错配 1–3 累计，不含完全匹配行）。",
                "排名方式：按计数升序；计数来自 Cas-OFFinder 口径全基因组扫描（PAM=NGG、正负链分行计数）。注意：这是不加权位点计数，不是 MIT/CFD 评分。",
                "适用：快速比较「谁最干净」；如需组织层面的危害评估请用功能性脱靶危害（方案5）。",
            ],
        },
        {
            "key": "gc_pct",
            "title": "GC 含量 (%)",
            "direction": "无推荐方向（按需切换升降序）",
            "lines": [
                "含义：20nt guide 的 GC 百分比 = GC 碱基数 / 20 × 100，不含侧翼与 PAM。",
                "适用：实验合成偏好参考，常用偏好区间约 40–70%。",
            ],
        },
    ]


@router.get("/meta/sort-help", summary="排序选项方法学帮助条目（前端排序帮助共用来源）")
async def get_sort_help(
    tissue_name: str = Query("叶", description="目标组织展示名（如 叶/根/茎）"),
) -> dict:
    return {"items": sort_help_items(tissue_name)}
