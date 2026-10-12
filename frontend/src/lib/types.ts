// 领域类型单一来源：基因 / 表达 / 脱靶位点 / 方法与版本。
// 候选条目与查询编码类型仍在 candidateQuery.ts（查询深度模块）。

export interface GeneInfo {
  gene_id: string
  chrom: string
  start: number
  end: number
  strand: string
  nlr_type?: string
  candidate_count: number
}

export interface GeneExpressionData {
  gene_id: string
  lsa_id?: string
  tier?: number
  lsa_vote_frac?: number
  lsa_resolved_frac?: number
  is_mappable: boolean
  unmappable_reason?: string
  tpm_root?: number
  tpm_stem?: number
  tpm_leaf?: number
  tpm_flower?: number
  tpm_seed?: number
  top_tissue?: string
  top_tpm?: number
  tau?: number
  n_cluster: number
  lsa_cluster?: string
  scaffold_evidence?: string
  tpm_dict: Record<string, number>
}

// ============ 脱靶位点明细 API（教师反馈 #1） ============
export interface OfftargetSite {
  chrom: string
  start: number
  end: number
  strand: string
  protospacer20: string
  pam: string
  mismatch_count: number
  mismatch_positions: number[]
  cfd_score: number
  mit_hit_score: number
  region_type?: string | null
  region_label?: string | null
  gene_id?: string | null
  risk_level: string
  risk_note: string
  is_ontarget: boolean
}

export interface OfftargetSitesResponse {
  seq20: string
  bundle_id: string
  bundle_name: string
  genome_note: string
  profile: { exact: number; mis1: number; mis2: number; mis3: number }
  sites: OfftargetSite[]
  sites_truncated: boolean
  specificity: {
    n_offtarget_sites_scored: number
    mit_hit_sum: number
    mit_specificity: number
    cfd_hit_sum: number
    cfd_specificity: number
    on_target_excluded: boolean
  }
  method_note: string
}

// ============ 方法与版本说明 API（教师反馈 #4/#5） ============
export interface MethodsInfo {
  efficiency_model: {
    name: string
    kind: string
    components: string[]
    validation: string
    model_card: string
    lineage_note: string
  }
  offtarget: {
    search: string
    params: { pam: string; gRNA_length: string; max_mismatches: number; strands: string }
    site_scores: string[]
    guide_specificity: string
    risk_note: string
  }
  expression_fitness: { poly_t: string; five_prime_g: string; mfe: string; gc: string }
  gene_structure: { source: string; protein_domains: string }
  reference_genomes: Array<{
    id: string
    display_name: string
    fasta_available: boolean
    gff_available: boolean
  }>
  disclaimer: string
}
