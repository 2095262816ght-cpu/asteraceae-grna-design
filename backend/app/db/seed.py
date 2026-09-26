import logging
from pathlib import Path
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Gene, TargetCandidate
from backend.app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def seed_candidates_if_empty(base_dir: Path | None = None) -> int:
    """如果数据库为空，自动从现存的 demo 数据中灌入 49 个 NLR 基因与候选靶点数据。"""
    if base_dir is None:
        # 当前根目录 d:\lifesciencechallenge\
        base_dir = Path(__file__).resolve().parent.parent.parent.parent

    async with AsyncSessionLocal() as session:
        # 检查是否已有基因数据
        existing_genes = await session.execute(select(func.count(Gene.gene_id)))
        if (existing_genes.scalar() or 0) > 0:
            logger.info("数据库已包含基因与候选靶点数据，跳过 Seed。")
            return 0

        genes_file = base_dir / "cs_pipeline" / "demo" / "app_genes.csv"
        data_file = base_dir / "cs_pipeline" / "demo" / "app_data.csv"

        if not genes_file.exists() or not data_file.exists():
            logger.warning("未找到待导入的 demo CSV 数据文件: %s, %s", genes_file, data_file)
            return 0

        logger.info("正在从 %s 解析 49 个代表基因...", genes_file)
        genes_df = pd.read_csv(genes_file)
        
        logger.info("正在从 %s 解析全量候选靶点...", data_file)
        data_df = pd.read_csv(data_file)

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

        # 2. 批量插入候选靶点
        candidate_mappings = []
        for _, row in data_df.iterrows():
            # 效率分自适应取值 (优先 v21_nob879 -> full_0916 -> efficiency_score -> None)
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
                }
            )

        # 分批插入以保证 SQLite / Postgres 性能
        batch_size = 2000
        for i in range(0, len(candidate_mappings), batch_size):
            chunk = candidate_mappings[i : i + batch_size]
            await session.run_sync(
                lambda s: s.bulk_insert_mappings(TargetCandidate, chunk)
            )

        await session.commit()
        logger.info("已成功自动灌入 %d 个基因与 %d 条候选 gRNA 靶点！", len(gene_records), len(candidate_mappings))
        return len(candidate_mappings)
