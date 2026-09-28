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
    expression = relationship("GeneExpression", back_populates="gene", uselist=False, cascade="all, delete-orphan")


class GeneExpression(Base):
    """目标靶基因在各组织中的表达图谱与 crosswalk 映射元数据。"""
    __tablename__ = "gene_expressions"

    gene_id = Column(String(64), ForeignKey("genes.gene_id"), primary_key=True, index=True)
    lsa_id = Column(String(32), nullable=True, doc="莴苣 v1.1c 主映射基因座")
    tier = Column(Integer, nullable=True, doc="crosswalk 映射置信度层级 1-4")
    lsa_vote_frac = Column(Float, nullable=True, doc="guide 投票主映射占比")
    lsa_resolved_frac = Column(Float, nullable=True, doc="guide 成功解析至 v1.1c 占比")
    is_mappable = Column(Boolean, default=False, doc="是否具备有效表达映射")
    unmappable_reason = Column(Text, nullable=True, doc="无法映射原因说明")
    tpm_root = Column(Float, nullable=True, doc="根部表达量 TPM")
    tpm_stem = Column(Float, nullable=True, doc="茎部表达量 TPM")
    tpm_leaf = Column(Float, nullable=True, doc="叶部表达量 TPM")
    tpm_flower = Column(Float, nullable=True, doc="花部表达量 TPM")
    tpm_seed = Column(Float, nullable=True, doc="种子表达量 TPM")
    top_tissue = Column(String(32), nullable=True, doc="最高表达组织")
    top_tpm = Column(Float, nullable=True, doc="最高表达量 TPM")
    tau = Column(Float, nullable=True, doc="组织特异性指数 tau")
    n_cluster = Column(Integer, default=1, doc="串联基因簇成员数")
    lsa_cluster = Column(String(256), nullable=True, doc="串联基因簇成员ID")
    scaffold_evidence = Column(String(64), nullable=True, doc="未挂载 scaffold 证据")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    gene = relationship("Gene", back_populates="expression")


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
    offtarget_count_mis3 = Column(Integer, nullable=True, default=None, doc="错配数1-3的潜在脱靶位点计数（不含完全匹配；None=未计算）")
    deepspcas9_score = Column(Float, nullable=True, doc="DeepSpCas9 模型预测活性分")
    crispron_score = Column(Float, nullable=True, doc="CRISPRon 模型预测活性分")
    efficiency_score = Column(Float, nullable=True, index=True, doc="形态二分层选择性 GLMM 终版相对排序分")

    # 方案3：五组织特异性优先推荐指数 (PriorityScore = 0.5*Pct(Eff) - 0.25*OffPen + 0.25*Sig(Expr))
    priority_score_root = Column(Float, nullable=True, index=True, doc="根部组织优先推荐分")
    priority_score_stem = Column(Float, nullable=True, index=True, doc="茎部组织优先推荐分")
    priority_score_leaf = Column(Float, nullable=True, index=True, doc="叶部组织优先推荐分")
    priority_score_flower = Column(Float, nullable=True, index=True, doc="花部组织优先推荐分")
    priority_score_seed = Column(Float, nullable=True, index=True, doc="种子组织优先推荐分")

    # 方案5：五组织功能性脱靶危害指数 (Functional Off-target Hazard)
    hazard_root = Column(Float, nullable=True, doc="根部功能性脱靶危害分")
    hazard_stem = Column(Float, nullable=True, doc="茎部功能性脱靶危害分")
    hazard_leaf = Column(Float, nullable=True, doc="叶部功能性脱靶危害分")
    hazard_flower = Column(Float, nullable=True, doc="花部功能性脱靶危害分")
    hazard_seed = Column(Float, nullable=True, doc="种子功能性脱靶危害分")

    # 多组学表达证据与面板内位点数
    expression_status = Column(String(32), nullable=True, doc="表达证据状态 (mapped/mapped_cluster/mapped_scaffold/unmappable)")
    n_intra_panel_sites = Column(Integer, nullable=True, default=None, doc="面板内关键功能靶位点数（None=不适用/未计算，面板仅覆盖49个NLR基因）")
    lsa_id = Column(String(32), nullable=True, doc="关联的 LSA 基因编号")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    gene = relationship("Gene", back_populates="candidates")

    __table_args__ = (
        Index("ix_target_candidates_gene_eff", "gene_id", "efficiency_score"),
        Index("ix_target_candidates_gene_prio_leaf", "gene_id", "priority_score_leaf"),
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


class ExportBatch(Base):
    """实验设计导出批次实体。"""
    __tablename__ = "export_batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False, doc="导出批次名称")
    format = Column(String(16), default="csv", doc="文件格式: csv | xlsx")
    gene_id = Column(String(64), nullable=True, index=True, doc="关联的目标基因 ID")
    candidate_count = Column(Integer, default=0, doc="包含候选靶点数")
    candidate_ids = Column(Text, nullable=False, doc="包含的候选靶点主键列表 (逗号分隔或JSON)")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

