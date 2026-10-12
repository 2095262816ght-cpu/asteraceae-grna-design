import logging
from pathlib import Path
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Gene, TargetCandidate, GeneExpression
from backend.app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

TISSUES = {"Root": "根", "Stem": "茎", "Leaf": "叶", "Flower": "花", "Seed": "种子"}
TISSUE_ORDER = ["Root", "Stem", "Leaf", "Flower", "Seed"]


def calc_tau(tpm_series: pd.Series) -> float:
    """计算组织特异性指数 tau (Yanai et al., 2005)"""
    mx = float(tpm_series.max())
    if mx <= 0:
        return 0.0
    return float((1.0 - tpm_series / mx).sum() / (len(tpm_series) - 1))


def build_expression_record(
    gid: str, xw: dict, expr_df, missing_crosswalk_reason: str
) -> GeneExpression:
    """crosswalk × 5 组织表达矩阵 -> GeneExpression；表达证据缺失如实标注，不编造 TPM。"""
    lsa_primary = xw.get("lsa_primary")
    tier_val = int(xw["tier"]) if pd.notna(xw.get("tier")) else None
    vote_frac = float(xw["lsa_vote_frac"]) if pd.notna(xw.get("lsa_vote_frac")) else None
    resolved_frac = float(xw["lsa_resolved_frac"]) if pd.notna(xw.get("lsa_resolved_frac")) else None
    n_cluster_val = int(xw.get("n_cluster", 1)) if pd.notna(xw.get("n_cluster", 1)) else 1
    lsa_cluster_val = str(xw.get("lsa_cluster")) if pd.notna(xw.get("lsa_cluster")) else None
    scaffold_ev = str(xw.get("scaffold_evidence")) if pd.notna(xw.get("scaffold_evidence")) else None

    is_map = False
    unmap_reason = None
    tpm_root = tpm_stem = tpm_leaf = tpm_flower = tpm_seed = None
    top_tiss = None
    top_tpm_val = None
    tau_val = None

    if not xw:
        unmap_reason = missing_crosswalk_reason
    elif pd.isna(lsa_primary):
        unmap_reason = (
            f"该基因座在莴苣 v1.1c 表达矩阵中无对应注释（crosswalk tier {tier_val or 4}，"
            f"guide 解析占比 {((resolved_frac or 0)*100):.1f}%）：序列在 v1.1c 中缺失/高度分歧，"
            f"或序列共线但存在注释缺口，故不展示假定表达值。"
        )
    elif expr_df is not None and lsa_primary in expr_df.index:
        is_map = True
        tpm_s = expr_df.loc[lsa_primary, TISSUE_ORDER].astype(float)
        tpm_root = float(tpm_s["Root"])
        tpm_stem = float(tpm_s["Stem"])
        tpm_leaf = float(tpm_s["Leaf"])
        tpm_flower = float(tpm_s["Flower"])
        tpm_seed = float(tpm_s["Seed"])
        top_key = tpm_s.idxmax()
        top_tiss = TISSUES.get(top_key, top_key)
        top_tpm_val = float(tpm_s.max())
        tau_val = calc_tau(tpm_s)
    else:
        unmap_reason = f"crosswalk 映射基因 {lsa_primary} 未收录于 5 组织表达矩阵中。"

    return GeneExpression(
        gene_id=gid,
        lsa_id=str(lsa_primary) if pd.notna(lsa_primary) else None,
        tier=tier_val,
        lsa_vote_frac=vote_frac,
        lsa_resolved_frac=resolved_frac,
        is_mappable=is_map,
        unmappable_reason=unmap_reason,
        tpm_root=tpm_root,
        tpm_stem=tpm_stem,
        tpm_leaf=tpm_leaf,
        tpm_flower=tpm_flower,
        tpm_seed=tpm_seed,
        top_tissue=top_tiss,
        top_tpm=top_tpm_val,
        tau=tau_val,
        n_cluster=n_cluster_val,
        lsa_cluster=lsa_cluster_val,
        scaffold_evidence=scaffold_ev,
    )


async def seed_genome_wide(base_dir: Path, session: AsyncSession) -> int:
    """路径 C：灌入莴苣全基因组基因目录 + 每基因 Top100 候选（已预计算 efficiency_score）。

    数据源（存在才灌，否则返回 0）：
    - cs_pipeline/results/lettuce_all_genes_catalog.csv
    - cs_pipeline/results/lettuce_all_genes_top100_candidates.csv
    全量 1090 万分片在 results/scored_genome/，库内只保留交互用 Top100，避免灌库过久。
    前置条件：调用方已清空 genes/gene_expressions/target_candidates。
    """
    catalog_file = base_dir / "cs_pipeline" / "results" / "lettuce_all_genes_catalog.csv"
    top_file = base_dir / "cs_pipeline" / "results" / "lettuce_all_genes_top100_candidates.csv"
    if not catalog_file.exists() or not top_file.exists():
        return 0

    logger.info("路径C：加载全基因组目录 %s", catalog_file)
    genes_df = pd.read_csv(catalog_file)

    # 第一遍：分块统计每基因候选数（Top100 大表约 868MB，不整读，避免灌库内存尖峰）
    cand_counts: dict[str, int] = {}
    total_rows = 0
    logger.info("路径C：分块统计 Top100 候选 %s", top_file)
    for chunk in pd.read_csv(top_file, usecols=["gene_id"], chunksize=200_000):
        for gid, n in chunk["gene_id"].value_counts().items():
            gid = str(gid)
            cand_counts[gid] = cand_counts.get(gid, 0) + int(n)
        total_rows += len(chunk)

    chrom_col = "g_chrom_norm" if "g_chrom_norm" in genes_df.columns else "g_chrom"

    gene_records = []
    for _, row in genes_df.iterrows():
        gid = str(row["gene_id"])
        gene_records.append(
            Gene(
                gene_id=gid,
                chrom=str(row[chrom_col]),
                start=int(row["g_start"]),
                end=int(row["g_end"]),
                strand=str(row["g_strand"]),
                nlr_type="protein-coding",
                candidate_count=int(cand_counts.get(gid, row.get("candidate_count", 0))),
            )
        )
    session.add_all(gene_records)
    await session.flush()

    # crosswalk × 5 组织表达矩阵真实表达证据（18 号批量定位引擎产物）；
    # crosswalk 缺失或基因不可映射时如实标缺失，不编造 TPM
    xwalk_file = base_dir / "cs_pipeline" / "results" / "crosswalk_lsa_t2t_genome.csv"
    expr_file = base_dir / "cs_pipeline" / "data" / "expression" / "1-3_lettuce_5tissue_expression_matrix.csv"
    xwalk_map = {}
    if xwalk_file.exists():
        xwalk_map = pd.read_csv(xwalk_file).set_index("gene_id").to_dict(orient="index")
    else:
        logger.warning("未找到全基因组 crosswalk: %s，表达证据将如实标为缺失", xwalk_file)
    expr_df = pd.read_csv(expr_file).set_index("GeneID") if expr_file.exists() else None
    missing_reason = (
        "全基因组扩表后尚未建立 LsT2T↔LSA crosswalk；"
        "该基因仅有序列与效率预计算分，组织表达证据缺失。"
    )
    expr_records = [
        build_expression_record(str(gid), xwalk_map.get(str(gid), {}), expr_df, missing_reason)
        for gid in genes_df["gene_id"]
    ]
    session.add_all(expr_records)
    await session.flush()

    # 第二遍：分块构建并灌入候选（每块 20 万行构建 → 5000/批落库）
    batch_size = 5000
    n_done = 0
    logger.info("路径C：分块灌入 Top100 候选 %s", top_file)
    for data_df in pd.read_csv(top_file, chunksize=200_000):
        candidate_mappings = []
        for row in data_df.itertuples(index=False):
            region = str(row.region_type).lower()
            gc_pct = float(row.gc_total) * 100.0 if pd.notna(row.gc_total) else 50.0
            candidate_mappings.append(
                {
                    "guide_id": str(row.guide_id),
                    "gene_id": str(row.gene_id),
                    "chrom": str(row.chrom),
                    "start": int(row.start),
                    "end": int(row.end),
                    "strand": str(row.strand),
                    "seq30": str(row.seq30),
                    "seq20": str(row.seq20),
                    "pam": str(row.pam),
                    "region_type": str(row.region_type),
                    "is_centromere": False,
                    "is_exon": "exon" in region or "cds" in region,
                    "gc_pct": float(gc_pct),
                    "tm_c": float(row.tm) if pd.notna(row.tm) else 60.0,
                    "offtarget_count_mis3": None,  # 未计算；导出时按需补算，不以 0 冒充"已验证无脱靶"
                    "deepspcas9_score": float(row.deepspcas9_score) if pd.notna(row.deepspcas9_score) else None,
                    "crispron_score": float(row.crispron_score) if pd.notna(row.crispron_score) else None,
                    "efficiency_score": float(row.efficiency_score) if pd.notna(row.efficiency_score) else None,
                }
            )
        for i in range(0, len(candidate_mappings), batch_size):
            part = candidate_mappings[i : i + batch_size]
            await session.run_sync(lambda s: s.bulk_insert_mappings(TargetCandidate, part))
        n_done += len(candidate_mappings)
        logger.info("路径C：候选灌库进度 %d / %d", n_done, total_rows)

    logger.info(
        "路径C完成：基因 %d、表达占位 %d、候选 %d（全量分片仍在 scored_genome，未删除）",
        len(gene_records), len(expr_records), n_done,
    )
    return n_done


async def seed_demo_nlr(base_dir: Path, session: AsyncSession) -> int:
    """demo 路径：49 个 NLR 代表基因 + crosswalk 表达证据 + 组织优先/脱靶危害候选。

    与 seed_genome_wide 共存灌库（两套基因 ID 命名空间不同，互不冲突）。
    前置条件：调用方已清空 genes/gene_expressions/target_candidates。
    """
    genes_file = base_dir / "cs_pipeline" / "demo" / "app_genes.csv"
    data_file = base_dir / "cs_pipeline" / "demo" / "app_data.csv"
    prio_file = base_dir / "cs_pipeline" / "demo" / "app_data_tissue_priority.csv"
    haz_file = base_dir / "cs_pipeline" / "results" / "offtarget_functional_hazard_0923.csv"
    xwalk_file = base_dir / "cs_pipeline" / "results" / "crosswalk_lsa_t2t_0923.csv"
    expr_file = base_dir / "cs_pipeline" / "data" / "expression" / "1-3_lettuce_5tissue_expression_matrix.csv"

    if not genes_file.exists() or not data_file.exists():
        logger.warning("未找到待导入的 demo CSV 数据文件: %s, %s", genes_file, data_file)
        return 0

    logger.info("正在从 %s 解析 49 个代表基因...", genes_file)
    genes_df = pd.read_csv(genes_file)

    logger.info("正在从 %s 解析全量候选靶点...", data_file)
    data_df = pd.read_csv(data_file)

    # 合并方案3：组织特异性优先推荐指数与表达证据
    if prio_file.exists():
        logger.info("正在合并组织特异性优先指数 (%s)...", prio_file)
        prio_df = pd.read_csv(prio_file)
        keep_cols = ["guide_id"] + [
            c for c in prio_df.columns
            if c.startswith("priority_score_") or c in ("expression_status", "lsa_id")
        ]
        data_df = data_df.merge(prio_df[keep_cols], on="guide_id", how="left")

    # 合并方案5：功能性脱靶危害指数
    if haz_file.exists():
        logger.info("正在合并功能性脱靶危害指数 (%s)...", haz_file)
        haz_df = pd.read_csv(haz_file)
        keep_cols = ["guide_id"] + [
            c for c in haz_df.columns
            if c.startswith("hazard_") or c == "n_intra_panel_sites"
        ]
        data_df = data_df.merge(haz_df[keep_cols], on="guide_id", how="left")

    # 加载 crosswalk 与 5 组织表达矩阵
    xwalk_map = {}
    if xwalk_file.exists():
        xwalk_df = pd.read_csv(xwalk_file).set_index("gene_id")
        xwalk_map = xwalk_df.to_dict(orient="index")

    expr_df = None
    if expr_file.exists():
        expr_df = pd.read_csv(expr_file).set_index("GeneID")
    else:
        logger.warning("表达矩阵缺失: %s，49 个 NLR 基因将无 TPM 表达证据", expr_file)

    # 统计每个基因关联的候选数量
    cand_counts = data_df["gene_id"].value_counts().to_dict()

    # 1. 批量插入基因
    gene_records = []
    for _, row in genes_df.iterrows():
        gid = str(row["gene_id"])
        gene_records.append(
            Gene(
                gene_id=gid,
                chrom=str(row["g_chrom"]),
                start=int(row["g_start"]),
                end=int(row["g_end"]),
                strand=str(row["g_strand"]),
                nlr_type=str(row.get("nlr_type", "NLR")),
                candidate_count=cand_counts.get(gid, 0),
            )
        )
    session.add_all(gene_records)
    await session.flush()

    # 2. 批量插入多组织表达看板元数据 (GeneExpression)
    expr_records = [
        build_expression_record(
            str(row["gene_id"]), xwalk_map.get(str(row["gene_id"]), {}), expr_df,
            "该基因不在 crosswalk 表中。")
        for _, row in genes_df.iterrows()
    ]
    session.add_all(expr_records)
    await session.flush()

    # 3. 批量插入候选靶点 (包含组织特异性优先推荐指数与脱靶危害)
    candidate_mappings = []
    for _, row in data_df.iterrows():
        eff_score = None
        for col in ("efficiency_score_v21_nob879", "efficiency_score_full_0916", "efficiency_score"):
            if col in row and pd.notna(row[col]):
                eff_score = float(row[col])
                break

        region = str(row.get("region_type", "exon")).lower()
        is_exon_val = "cds" in region or "exon" in region

        candidate_mappings.append(
            {
                "guide_id": str(row["guide_id"]),
                "gene_id": str(row["gene_id"]),
                "chrom": str(row["chrom"]),
                "start": int(row["start"]),
                "end": int(row["end"]),
                "strand": str(row["strand"]),
                "seq30": str(row["seq30"]),
                "seq20": str(row["seq20"]),
                "pam": str(row["pam"]),
                "region_type": str(row.get("region_type", "exon")),
                "is_centromere": bool(row.get("in_centromere", False)),
                "is_exon": is_exon_val,
                "gc_pct": float(row.get("gc_pct", 50.0)),
                "tm_c": float(row.get("tm_c", 60.0)),
                "offtarget_count_mis3": int(row.get("offtarget_count_mis3", 0)) if pd.notna(row.get("offtarget_count_mis3")) else 0,
                "deepspcas9_score": float(row["deepspcas9_score"]) if pd.notna(row.get("deepspcas9_score")) else None,
                "crispron_score": float(row["crispron_score"]) if pd.notna(row.get("crispron_score")) else None,
                "efficiency_score": eff_score,
                # 组织特异性优先指数
                "priority_score_root": float(row["priority_score_root"]) if "priority_score_root" in row and pd.notna(row["priority_score_root"]) else None,
                "priority_score_stem": float(row["priority_score_stem"]) if "priority_score_stem" in row and pd.notna(row["priority_score_stem"]) else None,
                "priority_score_leaf": float(row["priority_score_leaf"]) if "priority_score_leaf" in row and pd.notna(row["priority_score_leaf"]) else None,
                "priority_score_flower": float(row["priority_score_flower"]) if "priority_score_flower" in row and pd.notna(row["priority_score_flower"]) else None,
                "priority_score_seed": float(row["priority_score_seed"]) if "priority_score_seed" in row and pd.notna(row["priority_score_seed"]) else None,
                # 功能性脱靶危害
                "hazard_root": float(row["hazard_root"]) if "hazard_root" in row and pd.notna(row["hazard_root"]) else None,
                "hazard_stem": float(row["hazard_stem"]) if "hazard_stem" in row and pd.notna(row["hazard_stem"]) else None,
                "hazard_leaf": float(row["hazard_leaf"]) if "hazard_leaf" in row and pd.notna(row["hazard_leaf"]) else None,
                "hazard_flower": float(row["hazard_flower"]) if "hazard_flower" in row and pd.notna(row["hazard_flower"]) else None,
                "hazard_seed": float(row["hazard_seed"]) if "hazard_seed" in row and pd.notna(row["hazard_seed"]) else None,
                # 表达证据与面板内位点数
                "expression_status": str(row["expression_status"]) if "expression_status" in row and pd.notna(row["expression_status"]) else None,
                "n_intra_panel_sites": int(row["n_intra_panel_sites"]) if "n_intra_panel_sites" in row and pd.notna(row["n_intra_panel_sites"]) else 0,
                "lsa_id": str(row["lsa_id"]) if "lsa_id" in row and pd.notna(row["lsa_id"]) else None,
            }
        )

    # 分批插入以保证 SQLite / Postgres 性能
    batch_size = 2000
    for i in range(0, len(candidate_mappings), batch_size):
        chunk = candidate_mappings[i : i + batch_size]
        await session.run_sync(
            lambda s: s.bulk_insert_mappings(TargetCandidate, chunk)
        )

    logger.info(
        "demo 路径完成：%d 个 NLR 代表基因、%d 条组织表达记录与 %d 条候选 gRNA 靶点。",
        len(gene_records), len(expr_records), len(candidate_mappings)
    )
    return len(candidate_mappings)


async def seed_candidates_if_empty(base_dir: Path | None = None, force_reseed: bool = False) -> int:
    """灌库入口：全基因组（路径 C）与 49 NLR（demo 路径）两路并存。

    两套基因 ID 命名空间不同（LsT2T1G* vs LsaT2T01G*），同库共存互不冲突；
    任一数据源缺失则跳过该路，两路都缺失时返回 0。
    """
    if base_dir is None:
        # 当前根目录（项目根）
        base_dir = Path(__file__).resolve().parent.parent.parent.parent

    async with AsyncSessionLocal() as session:
        # 检查是否已有基因数据与组织表达数据
        if not force_reseed:
            existing_genes = await session.execute(select(func.count(Gene.gene_id)))
            existing_expr = await session.execute(select(func.count(GeneExpression.gene_id)))
            if (existing_genes.scalar() or 0) > 0 and (existing_expr.scalar() or 0) > 0:
                logger.info("数据库已包含基因、候选靶点与组织表达数据，跳过 Seed。")
                return 0

        # 清除旧记录，避免主键与唯一键冲突（同时覆盖 force_reseed 重灌场景）
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(GeneExpression.__table__.delete())
        await session.execute(Gene.__table__.delete())
        await session.flush()

        n_wide = await seed_genome_wide(base_dir, session)
        n_demo = await seed_demo_nlr(base_dir, session)

        if n_wide == 0 and n_demo == 0:
            logger.warning("未找到任何可导入的 CSV 数据文件，Seed 跳过。")
            return 0

        await session.commit()
        logger.info(
            "灌库完成：全基因组候选 %d 条 + 49 NLR 候选 %d 条，共 %d 条。",
            n_wide, n_demo, n_wide + n_demo,
        )
        return n_wide + n_demo


if __name__ == "__main__":
    import asyncio
    import sys
    from backend.app.db.models import Base
    from backend.app.db.session import engine

    async def _main():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await seed_candidates_if_empty(force_reseed="--force" in sys.argv)

    asyncio.run(_main())
