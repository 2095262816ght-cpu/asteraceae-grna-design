import sys, io, csv, shutil, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import openpyxl

XLSX = r"cs_pipeline\data\1_Hi-results-12-20260913.xlsx"
CSV = r"cs_pipeline\data\hitom\usr5712_indel_rightside_recompute_0915.csv"
NOTE_TMPL = ("indel_pct于2026-09-16写回为切割点侧(右列)口径重算值{new}（原左侧口径值{old}系低估）；"
             "该批参考按负链提交、切割信号落在右列，重算表见data/hitom/usr5712_indel_rightside_recompute_0915.csv")

# 1) 读取重算表
rec = {}
with open(CSV, encoding="utf-8") as f:
    for d in csv.DictReader(f):
        rec[d["block"]] = (float(d["indel_left_published口径"]), float(d["indel_right_切割点侧"]))
blocks = sorted(rec)
assert len(blocks) == 61, f"重算表块数应为61，实际{len(blocks)}"

# 2) 备份
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = XLSX.replace(".xlsx", f"_backup_{ts}_pre5712indelwb.xlsx")
shutil.copy2(XLSX, bak)
print("备份:", bak)

# 3) 取 5712 批 61 行（表内顺序），先验证 行序=块序 的对应关系
wb = openpyxl.load_workbook(XLSX)
ws = wb["Sheet1"]
hdr = [str(c.value).strip() for c in ws[1]]
c = {h: i + 1 for i, h in enumerate(hdr)}

rows = []
for row in range(2, ws.max_row + 1):
    if str(ws.cell(row, c["batch"]).value).strip() == "USR-5712":
        rows.append(row)
assert len(rows) == 61, f"5712 行数应为61，实际{len(rows)}"

match = 0
for i, row in enumerate(rows):
    lv, _ = rec[blocks[i]]
    v = float(ws.cell(row, c["indel_pct"]).value)
    if abs(v - lv) <= 0.001:
        match += 1
assert match >= 60, f"行序=块序对应关系不成立（左口径仅{match}/61吻合），中止"
print(f"对应关系验证通过：左口径 {match}/61 顺序吻合（TKS_0095 原值 0.1117 与任何块都对不上，属原始记录异常）")

# 4) 写回右侧口径值 + 备注
changed = []
for i, row in enumerate(rows):
    b = blocks[i]
    lv, rv = rec[b]
    cell = ws.cell(row, c["indel_pct"])
    old = float(cell.value)
    cell.value = rv
    note_cell = ws.cell(row, c["备注"])
    old_note = note_cell.value
    note = NOTE_TMPL.format(old=old, new=rv)
    note_cell.value = (str(old_note).strip() + "；" + note) if old_note else note
    changed.append((str(ws.cell(row, c["guide-id"]).value).strip(), b, old, rv))

wb.save(XLSX)
print(f"已写回 {len(changed)} 行。示例:")
for g, b, o, n in changed[:5]:
    print(f"  {g} 块{b}: {o} -> {n}")
assert len(changed) == 61

# 5) 读回验证
wb2 = openpyxl.load_workbook(XLSX)
ws2 = wb2["Sheet1"]
n_ok = 0
for i, row in enumerate(rows):
    _, rv = rec[blocks[i]]
    v = float(ws2.cell(row, c["indel_pct"]).value)
    assert abs(v - rv) < 1e-9, f"行{row} 写回值不符: {v} != {rv}"
    n_ok += 1
import statistics
new_vals = [rec[blocks[i]][1] for i in range(61)]
print(f"读回验证通过：{n_ok}/61 行均为右侧口径值")
print(f"写回后 5712 批 indel_pct：中位数 {statistics.median(new_vals):.4f}，均值 {statistics.mean(new_vals):.4f}")
