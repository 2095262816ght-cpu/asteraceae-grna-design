"""表达证据状态派生：候选级 expression_status 缺失时，从基因级 crosswalk 元数据派生。

判定优先级（export_service 与 candidates API 共用，保证 Excel 与界面口径一致）：
1. 候选级 expression_status 已填（demo 路径）→ 直接使用；
2. 基因级 GeneExpression 存在且 is_mappable → 按 tier 映射四态；
3. 基因级存在但不可映射 → unmappable（表达证据缺失），理由取 unmappable_reason；
4. 全无 → unassessed（未评估）。
"""
from typing import Optional, Tuple

from backend.app.db.models import GeneExpression

TIER_STATUS = {1: "mapped", 2: "mapped_cluster", 3: "mapped_scaffold"}

STATUS_DISPLAY = {
    "mapped": "已映射",
    "mapped_cluster": "已映射（串联簇）",
    "mapped_scaffold": "已映射（未挂载 scaffold）",
    "unmappable": "表达证据缺失",
    "unassessed": "未评估",
}

DEFAULT_UNMAPPABLE_REASON = "表达证据缺失：未取得该基因的 LSA 映射或组织表达值，不展示假定表达值。"
UNASSESSED_REASON = "未评估：未找到该基因的 crosswalk 映射或表达图谱记录。"


def _mappable_note(expr: GeneExpression) -> str:
    note = f"LSA 主映射 {expr.lsa_id}（tier {expr.tier}）"
    if expr.n_cluster and expr.n_cluster > 1:
        note += f"；串联簇 {expr.lsa_cluster or 'n_cluster=' + str(expr.n_cluster)}"
    if expr.scaffold_evidence:
        note += f"；scaffold 证据 {expr.scaffold_evidence}"
    return note


def derive_expression_evidence(
    candidate_status: Optional[str],
    expr: Optional[GeneExpression],
) -> Tuple[str, str, str]:
    """返回 (状态码, 中文展示, 证据说明)。"""
    if candidate_status:
        display = STATUS_DISPLAY.get(candidate_status, candidate_status)
        if candidate_status == "unmappable":
            note = (expr.unmappable_reason if expr and expr.unmappable_reason else DEFAULT_UNMAPPABLE_REASON)
        elif expr is not None and expr.is_mappable:
            note = _mappable_note(expr)
        else:
            note = "候选级表达证据已标注。"
        return candidate_status, display, note

    if expr is None:
        return "unassessed", STATUS_DISPLAY["unassessed"], UNASSESSED_REASON

    if expr.is_mappable:
        code = TIER_STATUS.get(expr.tier or 1, "mapped")
        return code, STATUS_DISPLAY[code], _mappable_note(expr)

    return (
        "unmappable",
        STATUS_DISPLAY["unmappable"],
        expr.unmappable_reason or DEFAULT_UNMAPPABLE_REASON,
    )
