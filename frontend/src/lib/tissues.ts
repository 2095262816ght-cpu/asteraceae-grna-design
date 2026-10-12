// 目标组织单一来源：命名、顺序与类型。UI 与查询编码共用。
export type TargetTissue = 'Leaf' | 'Root' | 'Stem' | 'Flower' | 'Seed'

export const TISSUE_NAMES: Record<TargetTissue, string> = {
  Leaf: '叶',
  Root: '根',
  Stem: '茎',
  Flower: '花',
  Seed: '种子',
}

export const TISSUE_ORDER: TargetTissue[] = ['Leaf', 'Root', 'Stem', 'Flower', 'Seed']
