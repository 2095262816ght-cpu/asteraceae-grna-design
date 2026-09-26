import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Gene(Base):
    """目标靶基因元数据实体。"""
    __tablename__ = "genes"

    gene_id = Column(String(64), primary_key=True, index=True, doc="基因唯一识别号，如 LsaT2T01G023690")
    chrom = Column(String(32), nullable=False, index=True, doc="染色体编号，如 Chr01")
    start = Column(Integer, nullable=False, doc="起始坐标")
    end = Column(Integer, nullable=False, doc="终止坐标")
    strand = Column(String(4), nullable=False, doc="正负链方向 (+ / -)")
    nlr_type = Column(String(64), nullable=True, doc="NLR 分类亚型，如 NLR-LRR")
    candidate_count = Column(Integer, default=0, doc="关联的候选 gRNA 靶点总数")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    candidates = relationship("TargetCandidate", back_populates="gene", cascade="all, delete-orphan")


class TargetCandidate(Base):
    """候选 gRNA 靶位点领域实体。"""
    __tablename__ = "target_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guide_id = Column(String(64), nullable=False, index=True, doc="引导序列识别号，如 Lsat_675191")
    gene_id = Column(String(64), ForeignKey("genes.gene_id"), nullable=False, index=True)
    chrom = Column(String(32), nullable=False, index=True)
    start = Column(Integer, nullable=False)
    end = Column(Integer, nullable=False)
    strand = Column(String(4), nullable=False)
    seq30 = Column(String(32), nullable=False, doc="30bp 全长靶位点序列 (4nt + 20nt guide + 3nt PAM + 3nt)")
    seq20 = Column(String(24), nullable=False, doc="20nt 间隔识别序列")
    pam = Column(String(8), nullable=False, doc="PAM 基序 (NGG)")
    region_type = Column(String(32), nullable=False, default="exon", doc="基因结构区域 (CDS/exon/promoter/intron)")
    is_centromere = Column(Boolean, default=False, index=True, doc="是否位于着丝粒不稳定区")
    is_exon = Column(Boolean, default=False, index=True, doc="是否位于外显子/编码区")
    gc_pct = Column(Float, nullable=False, doc="GC 含量百分比 (0-100)")
    tm_c = Column(Float, nullable=False, doc="解链温度 Tm")
    offtarget_count_mis3 = Column(Integer, default=0, doc="错配数<=3的潜在脱靶位点计数")
    deepspcas9_score = Column(Float, nullable=True, doc="DeepSpCas9 模型预测活性分")
    crispron_score = Column(Float, nullable=True, doc="CRISPRon 模型预测活性分")
    efficiency_score = Column(Float, nullable=True, index=True, doc="形态二分层选择性 GLMM 终版相对排序分")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    gene = relationship("Gene", back_populates="candidates")

    __table_args__ = (
        Index("ix_target_candidates_gene_eff", "gene_id", "efficiency_score"),
    )


class ScoringJob(Base):
    """打分任务实体。"""
    __tablename__ = "scoring_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(128), nullable=False, default="单序列打分任务")
    job_type = Column(String(32), default="single")  # "single" | "batch"
    status = Column(String(32), default="completed", index=True)  # "pending", "running", "completed", "failed"
    total_sequences = Column(Integer, default=1)
    processed_sequences = Column(Integer, default=1)
    duration_seconds = Column(Float, default=0.0)
    crispron_source = Column(String(32), nullable=True)  # "wsl_real" | "approximated"
    warning_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime, nullable=True)

    items = relationship("ScoringJobItem", back_populates="job", cascade="all, delete-orphan")


class ScoringJobItem(Base):
    """打分作业单条序列明细实体。"""
    __tablename__ = "scoring_job_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("scoring_jobs.id"), nullable=False, index=True)
    custom_id = Column(String(128), nullable=True, doc="用户上传的样本编号/自定义ID")
    seq30 = Column(String(64), nullable=False)
    flank_5p = Column(String(8), nullable=True)
    guide_seq = Column(String(24), nullable=True)
    pam = Column(String(8), nullable=True)
    flank_3p = Column(String(8), nullable=True)
    gc_pct = Column(Float, nullable=True)
    tm_c = Column(Float, nullable=True)
    deepspcas9_score = Column(Float, nullable=True)
    crispron_source = Column(String(32), nullable=True)
    efficiency_score = Column(Float, nullable=True)
    is_valid = Column(Boolean, default=True, doc="序列格式是否合法")
    error_message = Column(Text, nullable=True, doc="单条序列错误提示")

    job = relationship("ScoringJob", back_populates="items")
