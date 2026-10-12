# -*- coding: utf-8 -*-
"""features_common.py — noB879 / train969 队列装载与 10 维标准特征的向量化适配器。

特征语义（seq30 布局、9 维派生特征、Tm/GC 口径）单点定义在 core.sequence_spec；
本模块负责队列口径、装载、结构防呆与落盘。

背景（P2 工程债）
----------------
这段逻辑此前在 `scripts/15:61-73`（生产模型训练）与 `scripts/17:183-192`（方案2 消融）
各存一份**逐行相同**的副本。方案2 的阴性结论依赖两份副本严格同构——否则比较的就不是
"加/不加表达特征"，而是"同时换了序列特征"——但此前没有任何机制防止二者漂移。
本模块消除该重复，并把标准特征矩阵落盘为可审计产物：

    results/feature_matrix_nob879_0921.csv    879 行 × 20 列

**四条路径共用 `seq_features()`**（训练与推理不再各存副本）：
    load_cohort()                          scripts/15 生产训练 + scripts/17 方案2 消融
    scripts/predict.py                     单序列交互推理（demo Tab2）
    demo/rescore_demo_v21_nob879.py        demo 候选库 19,839 条批量重打分
此前这四处各存一份特征构建副本（其中训练与消融两份逐行相同），`gc_seed` 的种子区切片这类
细节一旦改动就会让训练与推理静默分家，且无任何机制报警；现已全部收敛到单点定义。

运行（在 cs_pipeline/ 下，crispr 环境；不需 torch，约 20 秒）：
    python scripts/features_common.py

口径定义（源：data/1_Hi-results-16.1-efficiency-20260921.xlsx）
--------------------------------------------------------------
noB879    「全部打分」sheet 中 `处理状态=="保留" 且 等级!="B"` → 879 行 / 16 基因组。
          剔除的 90 行 B 级为"多候选竞争未经设计表确认"样本，其 guide-id ↔ 序列的对应
          关系不可信（同 CHANGELOG_0927.md 第 6 款"编号地雷"），特征属伪特征。
          **这是生产口径**，`scripts/15` 只用它。
train969  「训练集」sheet 全部行 → 969 行 / 17 基因组，是 noB879 的严格超集
          （差集恰为那 90 行 B 级；其中 LG01.6862 仅 2 条 guide 且全为 B 级，整基因消失，
          故 LOGO 折数 17→16）。仅供 `scripts/17` 做敏感性分析，**不落盘**。

防呆（针对 0918 编号地雷事故）
------------------------------
1. `guide_id` 强制 str + 行数硬断言 + 唯一性断言；
2. 矩阵**行内自带 seq20/seq30/pam**，可脱离 guide_id 独立核验，不需要跨表 join；
3. 10 维列名与顺序由 `FEATURE_COLS` 单点定义，`assert_feature_schema` 在两个消费脚本
   入口各跑一次，检查列齐全、形状、无 NaN、PAM one-hot 划分与取值区间；
4. PAM one-hot 缺列**显式补 0.0**而非静默少列——旧表 `feature_matrix_full_0916.csv`
   就因该子集无 G 起始 PAM 而只有 3 个 pam_n 列（28 列），与 0918 表的 29 列不一致，
   按固定列数读取的下游会随机崩，且崩不崩取决于数据而非代码。
"""
from pathlib import Path
import sys

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 特征语义（seq30 布局切片、9 维派生特征取值定义、PAM one-hot 列名）单点定义在
# core.sequence_spec；本模块只是其向量化适配器 + 队列装载器，不再自持第二份定义。
from core.sequence_spec import (  # noqa: E402
    GUIDE_SLICE,
    PAM_N_SLICE,
    PAM_ONEHOT,
    SEED_SLICE,
    SEQ_FEATURE_COLS,
    seq_feature_dict,
)
XLSX_161 = BASE_DIR / "data" / "1_Hi-results-16.1-efficiency-20260921.xlsx"
SEQ30_CSV = BASE_DIR / "data" / "hitom" / "hitom_seq30_merged_0918.csv"
DSS_CSV = BASE_DIR / "results" / "scores_deepspcas9_merged_0918.csv"
CRISPON_CSV = BASE_DIR / "results" / "scores_crispron_merged_0918.csv"
READS_CSV = BASE_DIR / "data" / "hitom" / "hitom_reads_depth_0921.csv"

FEATURE_MATRIX_CSV = BASE_DIR / "results" / "feature_matrix_nob879_0921.csv"

# LG01.6995 / 6999 为同源对，合并成一个 LOGO 组：否则"留出 6995 做测试"时其同源伙伴
# 仍留在训练集里，模型等于提前见过答案。
HOMOLOG = {
    "EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
    "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999",
}

# 10 维标准特征。顺序即模型输入顺序，改动等于换模型，须全队会签。
FEATURE_COLS = [
    "deepspcas9_score", "crispron_score", "gc_total", "gc_seed",
    "tm", "poly_t", "pam_n_A", "pam_n_C", "pam_n_G", "pam_n_T",
]

EXPECTED_ROWS = {"noB879": 879, "train969": 969}
EXPECTED_GROUPS = {"noB879": 16, "train969": 17}

# 落盘列。前 10 列让这张表自证：guide_id 对应哪条序列、标签与测序深度是多少，
# 10 维特征都能由行内 seq20/seq30/pam 独立重算核验，不依赖任何跨表 join。
# 注意：**不要**把 reads 表的 non_wt_reads 加进来当"标签可核验"的证据——实测
# indel_pct ≠ non_wt_reads/total_reads（naive 比值 ~0.53 vs 标签 0.056，r=0.68，
# 879 行中仅 229 行相等）。indel_pct 是生科侧口径的 curated 标签，二者不同源；
# 放进来只会诱导错误的核验。该列在全项目无任何消费者，故 merge 时也不取。
META_COLS = [
    "guide_id", "gene_id", "gene_group", "batch", "rep",
    "seq20", "seq30", "pam", "indel_pct", "total_reads",
]


def seq_features(seq30):
    """从 30bp 序列构建 9 个序列派生特征，返回与 seq30 同索引的 DataFrame。

    **core.sequence_spec.seq_feature_dict 的向量化适配器**：特征语义（哪个切片算哪个
    特征、Tm/GC 取值口径、PAM one-hot 划分）在 SequenceSpec 单点定义，本函数只负责
    逐行套用 + 拼表。训练与推理四条路径（load_cohort、scripts/predict.py、
    demo/rescore_demo_v21_nob879.py、批量打分）共用本函数，不再各存副本。

    一律以 seq30 为唯一原语（不用源表存储的 seq20/pam 列）：实测在 noB879（879 行）、
    train969（969 行）与 demo app_data（19,839 行）上，存储列 seq20 == seq30[4:24]、
    pam == seq30[24:27] 全部逐行成立。

    PAM one-hot 显式产出 4 列 float（不用 pd.get_dummies）：get_dummies 只产出数据中
    出现过的碱基列，会让特征矩阵的列数随子集变化——旧表 feature_matrix_full_0916.csv
    就因该子集无 G 起始 PAM 而只有 3 列（28 列 vs 0918 表的 29 列），且写出的是
    True/False 而非数值。
    """
    seq30 = seq30.astype(str)
    if len(seq30) == 0:
        return pd.DataFrame(columns=SEQ_FEATURE_COLS, index=seq30.index)
    out = pd.DataFrame.from_records(
        [seq_feature_dict(s) for s in seq30], index=seq30.index
    )
    return out[SEQ_FEATURE_COLS]


def cohort_ids(kind):
    """返回该口径的 guide-id 集合（全部为 str）。"""
    if kind == "noB879":
        a = pd.read_excel(XLSX_161, sheet_name="全部打分")
        gid = a["guide-id"].astype(str)
        pop = set(gid[(a["处理状态"] == "保留") & (a["等级"] != "B")])
    elif kind == "train969":
        t = pd.read_excel(XLSX_161, sheet_name="训练集")
        pop = set(t["guide-id"].astype(str))
    else:
        raise ValueError(f"未知口径 {kind!r}，可选 {sorted(EXPECTED_ROWS)}")
    assert len(pop) == EXPECTED_ROWS[kind], \
        f"{kind} 人群期望 {EXPECTED_ROWS[kind]} 行，实际 {len(pop)} 行"
    return pop


def assert_feature_schema(df, kind=None):
    """十维同序 + 区间合法性断言。任何一处增删列、改顺序、改类型都会在这里立刻报错，
    而不是静默改变模型输入。两个消费脚本入口各调一次。

    注意：本断言守的是"结构"（列在不在、顺序、形状、取值域），不守"语义"——它无法
    发现有人把 gc_seed 的切片从 [18:24] 改成 [17:23]。后者由**单一来源**本身防护：
    两个消费脚本 import 同一个 FEATURE_COLS 与同一个 load_cohort，结构上无从分家。
    """
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    assert not missing, f"特征列缺失 {missing}"
    x = df[FEATURE_COLS].astype(float)
    assert x.shape == (len(df), len(FEATURE_COLS)), \
        f"特征矩阵形状 {x.shape}，期望 ({len(df)}, {len(FEATURE_COLS)})"
    assert not x.isna().any().any(), "特征矩阵含 NaN"

    # pam_n_* 必须构成 one-hot 划分：每条 guide 的 PAM 首碱基恰好是四种之一。
    # 若上游 pam 列大小写或取值变化，get_dummies 会产出 pam_n_a 之类的列，
    # 而 pam_n_A 会被下面的补 0 逻辑静默填成全 0——模型就此无声丢掉一个特征。
    pam_sum = x[PAM_ONEHOT].sum(axis=1)
    assert (pam_sum == 1).all(), \
        f"PAM one-hot 每行须恰好一个 1，实际取值 {sorted(pam_sum.unique())}"
    # 区间合法性
    for col, lo, hi in (("gc_total", 0.0, 1.0), ("gc_seed", 0.0, 1.0)):
        assert x[col].between(lo, hi).all(), f"{col} 超出 [{lo}, {hi}]"
    assert x["poly_t"].isin([0.0, 1.0]).all(), "poly_t 必须是 0/1"
    assert (x["tm"] > 0).all(), "tm 必须为正"

    if kind is not None:
        n_grp = df["gene_group"].nunique()
        assert n_grp == EXPECTED_GROUPS[kind], \
            f"{kind} 期望 {EXPECTED_GROUPS[kind]} 个基因组（= LOGO 折数），实际 {n_grp}"


def load_cohort(kind):
    """装载队列并构建 10 维标准特征。scripts/15 与 scripts/17 的唯一入口。

    行序由 `base` 决定并经 isin 过滤后 reset_index，两个口径共用同一条路径，
    因此 noB879 的行序是 train969 行序的子序列——这对可复现的 LOGO 分组是必要的。
    """
    pop = cohort_ids(kind)

    base = pd.read_csv(SEQ30_CSV)
    base = base.merge(pd.read_csv(DSS_CSV), on="guide_id", validate="1:1")
    base = base.merge(pd.read_csv(CRISPON_CSV), on="guide_id", validate="1:1")
    reads = pd.read_csv(READS_CSV)
    base = base.merge(reads[["guide_id", "total_reads"]],
                      on="guide_id", validate="1:1")
    base["guide_id"] = base["guide_id"].astype(str)

    df = base[base.guide_id.isin(pop)].copy().reset_index(drop=True)
    assert len(df) == EXPECTED_ROWS[kind], \
        f"{kind} 期望 {EXPECTED_ROWS[kind]} 行，实际 {len(df)} 行"
    assert df["guide_id"].nunique() == len(df), f"{kind} guide_id 有重复"

    df["gene_group"] = df["gene_id"].replace(HOMOLOG)
    df = pd.concat([df, seq_features(df["seq30"])], axis=1)

    assert_feature_schema(df, kind)
    return df


def dump_feature_matrix(df=None, out=FEATURE_MATRIX_CSV):
    """落盘 noB879 标准特征矩阵。scripts/15 每次训练后调用，保证留档与生产模型同源。"""
    if df is None:
        df = load_cohort("noB879")
    cols = META_COLS + FEATURE_COLS
    missing = [c for c in cols if c not in df.columns]
    assert not missing, f"落盘列缺失 {missing}"
    out_df = df[cols].copy()
    out_df["guide_id"] = out_df["guide_id"].astype(str)
    assert len(out_df) == EXPECTED_ROWS["noB879"], \
        f"落盘行数 {len(out_df)}，期望 {EXPECTED_ROWS['noB879']}"
    assert out_df["guide_id"].nunique() == len(out_df), "guide_id 有重复，拒绝落盘"
    out_df.to_csv(out, index=False)
    return out_df


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    saved = dump_feature_matrix()
    print("已落盘 %d 行 × %d 列" % saved.shape)
    print("  路径：%s" % FEATURE_MATRIX_CSV.relative_to(BASE_DIR))
    print("  基因组数：%d（= LOGO 折数）" % saved["gene_group"].nunique())
    print("  PAM one-hot 非零列数：%d/4"
          % sum(int(saved[c].astype(float).sum() > 0) for c in PAM_ONEHOT))
