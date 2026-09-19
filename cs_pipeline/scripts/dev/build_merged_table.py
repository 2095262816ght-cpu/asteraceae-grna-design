# -*- coding: utf-8 -*-
"""
build_merged_table.py — 将旧表与新表合并为一个完整数据集
输入:
  - data/1_Hi-results-12-20260913.xlsx (旧主表, 491行)
  - data/1_Hi-results-13-NEWdata-20260918.xlsx (新批次表, 877行)
输出:
  - data/1_Hi-results-13-merged-20260918.xlsx (合并全量表, 1368行)
原有两张表均原样保留不变。
"""
import os
import shutil
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = r'd:\lifesciencechallenge\cs_pipeline'
OLD_PATH = os.path.join(BASE_DIR, 'data', '1_Hi-results-12-20260913.xlsx')
NEW_PATH = os.path.join(BASE_DIR, 'data', '1_Hi-results-13-NEWdata-20260918.xlsx')
OUT_PATH = os.path.join(BASE_DIR, 'data', '1_Hi-results-13-merged-20260918.xlsx')
BACKUP_PATH = os.path.join(BASE_DIR, 'data', '1_Hi-results-13-merged-20260918_backup_817rows.xlsx')

def main():
    # 1. 备份现存的旧版 817 行合并表（如果存在且未备份）
    if os.path.exists(OUT_PATH) and not os.path.exists(BACKUP_PATH):
        print(f"备份旧版合并表到: {BACKUP_PATH}")
        shutil.copy2(OUT_PATH, BACKUP_PATH)

    # 2. 读取旧表与新表
    assert os.path.exists(OLD_PATH), f"旧表不存在: {OLD_PATH}"
    assert os.path.exists(NEW_PATH), f"新表不存在: {NEW_PATH}"
    
    print(f"读取旧表: {OLD_PATH}")
    df_old = pd.read_excel(OLD_PATH, sheet_name='Sheet1')
    print(f"读取新表: {NEW_PATH}")
    df_new = pd.read_excel(NEW_PATH, sheet_name='Sheet1')
    
    print(f"旧表行数: {len(df_old)}, 新表行数: {len(df_new)}")
    assert list(df_old.columns) == list(df_new.columns), "列结构不一致！"

    # 3. 检查并确认 guide-id 连续性
    print(f"旧表 guide-id: {df_old['guide-id'].iloc[0]} .. {df_old['guide-id'].iloc[-1]}")
    print(f"新表 guide-id: {df_new['guide-id'].iloc[0]} .. {df_new['guide-id'].iloc[-1]}")
    
    # 4. 合并数据
    df_merged = pd.concat([df_old, df_new], ignore_index=True)
    expected_rows = len(df_old) + len(df_new)
    assert len(df_merged) == expected_rows, f"合并行数异常: 期望 {expected_rows}, 实际 {len(df_merged)}"
    
    # guide-id 唯一性检查
    assert df_merged['guide-id'].is_unique, "合并后 guide-id 存在重复！"
    print(f"合并后总行数: {len(df_merged)} (唯一 guide-id: {df_merged['guide-id'].iloc[0]} .. {df_merged['guide-id'].iloc[-1]})")
    
    # 批次分布
    print("\n各批次分布:")
    print(df_merged['batch'].value_counts().to_string())

    # 5. 读取新表的补充 Sheet (guide候选 与 说明)
    xls_new = pd.ExcelFile(NEW_PATH)
    sheets_dict = {'Sheet1': df_merged}
    if 'guide候选' in xls_new.sheet_names:
        sheets_dict['guide候选'] = pd.read_excel(NEW_PATH, sheet_name='guide候选')
    
    doc_text = [
        '本表为 1_Hi-results-12-20260913.xlsx (旧主表 491 行) 与 1_Hi-results-13-NEWdata-20260918.xlsx (新批次表 877 行) 的全量合并版',
        f'生成时间: 2026-09-18, 合并总行数: {len(df_merged)} 行, 涵盖全部 24 个批次',
        f'旧主表 7 批次 (491 行): USR-4411, USR-5712, USR-5713, USR-8145, USR-23709, USR-25902, USR-26162',
        f'新纳入 17 批次 (877 行): 包含 NEWdata 的 12 个批次以及追加纳入的 5 个批次 (USR-4811/6137/6444/6883/7342)',
        '列名、列序及各字段口径均与主表完全保持一致，两张源表格均完整保留。'
    ]
    sheets_dict['说明'] = pd.DataFrame({'说明': doc_text})

    # 6. 写出到 Excel
    with pd.ExcelWriter(OUT_PATH, engine='openpyxl') as writer:
        for sname, sdata in sheets_dict.items():
            sdata.to_excel(writer, sheet_name=sname, index=False)
            
    print(f"\n合并完成，成功写入: {OUT_PATH}")
    print(f"原旧表保留: {OLD_PATH}")
    print(f"原新表保留: {NEW_PATH}")

if __name__ == '__main__':
    main()
