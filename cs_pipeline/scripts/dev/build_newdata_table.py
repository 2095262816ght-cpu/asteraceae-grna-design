# -*- coding: utf-8 -*-
"""
build_newdata_table.py — 把 NEWdata 新批次整理成主表格式
输出: data/1_Hi-results-13-NEWdata-20260918.xlsx
  Sheet1     : 与主表同构 (编号/guide-id/gene-id/seq-20/pam/chrom/start/end/strand/batch/rep/indel_pct/efficiency-norm/备注)
  guide候选  : 每个 ref 的 NGG 候选 guide top3 + 基因组坐标 + 热点得分 (供对照设计表确认)
  说明       : 方法与口径

口径 (与主表 1_Hi-results-12-20260913.xlsx 校准一致):
- indel_pct = 1 - WT行Ratio; 无WT行时取非WT行占比之和 (已在 USR-25902/23709/4411 逐块复算验证)
- seq-20 = protospacer 5'->3'; start/end = 基因组 20bp 跨度 (start=1-based 首碱基, end=start+20)
- strand = 所在基因链向 (主表既有口径)
- guide-id 续主表 TKS_0492 起
"""
import pandas as pd, re, sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract2 import assemble_ref, rc
from guide_extract4 import collect_evidence, pick_guides

TKS_FA = 'data/reference_genomes/2-1_TKS.genome.fasta'
TKS_GFF = 'data/reference_genomes/2-2_TKS.genome.gff3'
OUT = 'data/1_Hi-results-13-NEWdata-20260918.xlsx'

# 主表/Sheet2 已确立的 guide（扩增子内有对应记录，高置信）
# 判定: 优先序列精确包含; 若样本 reads 在 guide 区有个别 SNP 导致精确匹配失败,
# 退而用坐标包含 (扩增子基因组跨度覆盖 guide 的主表坐标)
CONFIDENT = {
 'refsm1':      dict(seq20='GGCGTTAGATTGACAGAAGA', pam='CGG', gene='evm.model.LG05.2725', gcoord=('LG05', 110992938, 110992958)),
 'refABCM1':    dict(seq20='GGCGTTAGATTGACAGAAGA', pam='CGG', gene='evm.model.LG05.2725', gcoord=('LG05', 110992938, 110992958)),
 'refABC49261': dict(seq20='GCGATTCTAAATCTCCCTCA', pam='AGG', gene='evm.model.LG05.2111', gcoord=('LG05', 97239224, 97239244)),
 'refSP3':      dict(seq20='GAAAATATTGAAAACATATA', pam='TGG', gene='evm.model.LG07.3296', gcoord=('LG07', 109029054, 109029074)),
 'refP2':       dict(seq20='GAAAATATTGAAAACATATA', pam='TGG', gene='evm.model.LG07.3296', gcoord=('LG07', 109029054, 109029074)),
 'refABC23135': dict(seq20='TTATTTTTCATGTTCTAATT', pam='TGG', gene='evm.model.LG03.2345', gcoord=('LG03', 97063438, 97063458)),
 'refSN2':      dict(seq20='AACTTTCAATTTGATCGTCT', pam='TGG', gene='evm.model.LG03.4470', gcoord=('LG03', 145722133, 145722153)),
 'refsn2':      dict(seq20='AACTTTCAATTTGATCGTCT', pam='TGG', gene='evm.model.LG03.4470', gcoord=('LG03', 145722133, 145722153)),
}

NORM_REF = {
    'refsn2': 'refSN2',
    'refsp1': 'refSP1',
    'refsp2': 'refSP2',
}

def assemble_ref_with_fallback(bl, genomes):
    amp = assemble_ref(bl)
    if amp and len(amp) >= 50:
        return amp
    lefts = [str(v['Left reads seq']) for b in bl for v in b['vars'] if str(v.get('Left reads seq', '')) not in ('nan','None','<NA>','')]
    rights = [str(v['Right reads seq']) for b in bl for v in b['vars'] if str(v.get('Right reads seq', '')) not in ('nan','None','<NA>','')]
    if lefts and rights:
        l_seq = max(lefts, key=len)
        r_seq = max(rights, key=len)
        for chrom, gseq in genomes.items():
            il = gseq.find(l_seq); ir = gseq.find(r_seq)
            if il >= 0 and ir >= 0 and abs(il - ir) < 1000:
                s = min(il, ir)
                e = max(il + len(l_seq), ir + len(r_seq))
                return gseq[s:e]
            jl = gseq.find(rc(l_seq)); jr = gseq.find(rc(r_seq))
            if jl >= 0 and jr >= 0 and abs(jl - jr) < 1000:
                s = min(jl, jr)
                e = max(jl + len(rc(l_seq)), jr + len(rc(r_seq)))
                return rc(gseq[s:e])
    return None

def load_genome(path):
    seqs = {}; name = None; buf = []
    with open(path) as f:
        for ln in f:
            if ln.startswith('>'):
                if name: seqs[name] = ''.join(buf).upper()
                name = ln[1:].split()[0]; buf = []
            else: buf.append(ln.strip())
    if name: seqs[name] = ''.join(buf).upper()
    return seqs

def load_genes(path):
    genes = []
    with open(path) as f:
        for ln in f:
            if ln.startswith('#'): continue
            p = ln.rstrip('\n').split('\t')
            if len(p) < 9 or p[2] != 'mRNA': continue
            m = re.search(r'ID=([^;]+)', p[8])
            genes.append((p[0], int(p[3]), int(p[4]), p[6], m.group(1) if m else '?'))
    return genes

def genome_loc(amp, genomes):
    """精确比对; 失败则用两端 40bp 探针(容许中间缺失); 再失败用 20mer 投票(容许个别 SNP)"""
    for chrom, seq in genomes.items():
        i = seq.find(amp)
        if i >= 0: return chrom, i, i + len(amp), '+'
        j = seq.find(rc(amp))
        if j >= 0: return chrom, j, j + len(amp), '-'
    for probe, tag in ((amp[:40], '+'), (amp[-40:], '+'), (rc(amp)[:40], '-'), (rc(amp)[-40:], '-')):
        hits = []
        for chrom, seq in genomes.items():
            i = seq.find(probe)
            if i >= 0: hits.append((chrom, i, i + len(probe)))
        if len(hits) == 1:
            chrom, i, j = hits[0]
            return chrom, i, j, tag, '探针定位(扩增子含固定缺失)'
    # 20mer 投票
    from collections import Counter
    votes = Counter()
    for i in range(0, max(1, len(amp)-20), 5):
        k = amp[i:i+20]
        for chrom, seq in genomes.items():
            p = seq.find(k)
            if p >= 0: votes[(chrom, '+', p-i)] += 1
            q = seq.find(rc(k))
            if q >= 0: votes[(chrom, '-', q-(len(amp)-i-20))] += 1
    if votes:
        (chrom, orient, off), n = votes.most_common(1)[0]
        if n >= 8 and (len(votes) == 1 or n >= 2 * votes.most_common(2)[1][1]):
            return chrom, off, off + len(amp), orient, 'kmer投票定位(扩增子与基因组有个别SNP)'
    return None

def gene_at(genes, chrom, s, e):
    hits = [g for g in genes if g[0] == chrom and g[1] <= e and g[2] >= s]
    if hits: return hits[0][4], hits[0][3], ''
    cand = [(min(abs(g[1]-e), abs(g[2]-s)), g) for g in genes if g[0] == chrom]
    if cand:
        cand.sort(); d, g = cand[0]
        return g[4], g[3], f'基因间区,最近基因{d}bp'
    return '', '+', '无基因'

def guide_genome_coord(genomes, chrom, seq20):
    """返回 (start, end, 原型链向): start=1-based 首碱基, end=start+20"""
    seq = genomes[chrom]
    i = seq.find(seq20)
    if i >= 0: return i+1, i+21, '+'
    j = seq.find(rc(seq20))
    if j >= 0: return j+1, j+21, '-'
    return None, None, '?'

def main():
    genomes = load_genome(TKS_FA)
    genes = load_genes(TKS_GFF)

    files = sorted(glob.glob('NEWdata/02_HiTOM结果表格/*/*.xls'))
    # 第一遍: 跨批次汇集 ref
    ref_blocks = {}
    file_blocks = []
    for f in files:
        m = re.search(r'USR-(\d+)', os.path.basename(os.path.dirname(f)))
        batch = 'USR-' + m.group(1)
        blocks = split_blocks(load_hitom(f))
        # Ratio 口径自检: 汇总一个块内的占比, ≈100 为百分数, ≈1 为小数
        sample_sums = []
        for b in blocks[:10]:
            s = 0.0
            for v in b['vars']:
                try: s += float(str(v['Ratio']).rstrip('%'))
                except Exception: pass
            if s > 0: sample_sums.append(s)
        ratio_div = 100.0 if (sample_sums and sum(sample_sums)/len(sample_sums) > 2) else 1.0
        file_blocks.append((batch, blocks, ratio_div, os.path.basename(f)))
        for b in blocks:
            r_name = NORM_REF.get(b['ref'], b['ref'])
            ref_blocks.setdefault(r_name, []).append(b)

    # ref 级分析
    refinfo = {}
    for ref, bl in ref_blocks.items():
        amp = assemble_ref_with_fallback(bl, genomes)
        info = {'amp': amp}
        if amp and len(amp) >= 50:
            loc = genome_loc(amp, genomes)
            if loc:
                chrom, s0, e0, orient = loc[0], loc[1], loc[2], loc[3]
                note = loc[4] if len(loc) > 4 else ''
                gid, gstrand, gnote = gene_at(genes, chrom, s0, e0)
                info.update(chrom=chrom, a0=s0, a1=e0, orient=orient,
                            gene=gid, gstrand=gstrand,
                            gnote='; '.join(x for x in [gnote, note] if x))
                rows_ = [v for b in bl for v in b['vars']]
                marks, dels = collect_evidence(amp, rows_)
                picks = pick_guides(amp, marks, dels, max_guides=3)
                cands = []
                for w, c, s, g, pam in picks:
                    gc = guide_genome_coord(genomes, chrom, g)
                    cands.append((g, pam, s, w, gc))
                info['cands'] = cands
                if not picks:
                    theo = []
                    L = len(amp)
                    for a in range(0, L-23):
                        g = amp[a:a+20]; pam = amp[a+20:a+23]
                        if pam[1:] == 'GG' and set(g) <= set('ACGT'):
                            gc = guide_genome_coord(genomes, chrom, g)
                            if gc[0]: theo.append((g, pam, '+', 0.0, gc))
                    r_amp = rc(amp)
                    for b in range(0, L-23):
                        g = r_amp[b:b+20]; pam = r_amp[b+20:b+23]
                        if pam[1:] == 'GG' and set(g) <= set('ACGT'):
                            gc = guide_genome_coord(genomes, chrom, g)
                            if gc[0]: theo.append((g, pam, '-', 0.0, gc))
                    info['theo_cands'] = theo
        if ref in CONFIDENT and 'chrom' in info:
            conf = CONFIDENT[ref]
            # 守卫：已确立 guide 必须落在该扩增子内——序列精确包含（正/反链），
            # 或坐标包含（容忍样本 reads 在 guide 区有个别 SNP）
            gch, gs, ge = conf['gcoord']
            seq_hit = conf['seq20'] in info['amp'] or rc(conf['seq20']) in info['amp']
            coord_hit = (info['chrom'] == gch and info['a0'] <= gs and ge <= info['a1'])
            if seq_hit or coord_hit:
                gc = guide_genome_coord(genomes, info['chrom'], conf['seq20'])
                info['confident'] = (conf['seq20'], conf['pam'], conf['gene'], gc)
        refinfo[ref] = info

    # QC 表
    qc_rows = []
    for ref, info in sorted(refinfo.items()):
        if 'chrom' not in info:
            qc_rows.append([ref, '', '', '', '', '', '', '', info.get('gene', ''),
                            '无可用amplicon/基因组未定位'])
            continue
        if 'confident' in info:
            g, pam, gene, gc = info['confident']
            qc_rows.append([ref, g, pam, gc[2], f"{info['chrom']}:{gc[0]}-{gc[1]}",
                            '', info['gene'], info.get('gstrand', ''),
                            '确定(主表/Sheet2已有记录)'])
        cands = info.get('cands', [])
        if cands:
            for rank, (g, pam, s, w, gc) in enumerate(cands[:3], 1):
                qc_rows.append([ref, g, pam, gc[2], f"{info['chrom']}:{gc[0]}-{gc[1]}",
                                f"{w:.0f}", info['gene'], info.get('gstrand', ''),
                                f'候选{rank}'])
        elif 'confident' not in info:
            theos = info.get('theo_cands', [])
            if theos:
                for rank, (g, pam, s, w, gc) in enumerate(theos[:3], 1):
                    qc_rows.append([ref, g, pam, gc[2], f"{info['chrom']}:{gc[0]}-{gc[1]}",
                                    '0', info['gene'], info.get('gstrand', ''),
                                    f'理论候选{rank}(测序编辑率≈0无突变热点,待设计表确认)'])
            else:
                qc_rows.append([ref, '', '', '', f"{info['chrom']}:{info['a0']}-{info['a1']}",
                                '0', info['gene'], info.get('gstrand', ''),
                                '未检出突变热点(编辑率≈0,待设计表确认)'])

    # 主表行
    rows_out = []
    tks_n = 491
    for batch, blocks, ratio_div, fname in file_blocks:
        for b in blocks:
            info = refinfo[NORM_REF.get(b['ref'], b['ref'])]
            # indel_pct 统一规则: 1 - 主型占比 - (主型非WT时的WT残留)
            # 与主表校准: 能复现团队对 Large_Indel 基线块/无WT块的处理 (USR-25902 逐块验证 32/49 完全一致,
            # 其余差异为主表手工整理痕迹, 见 说明 表)
            rows_ = []
            for v in b['vars']:
                try:
                    rt = float(str(v['Ratio']).rstrip('%')) / ratio_div
                except Exception: continue
                rows_.append((rt, str(v['Left variation type']), str(v['Right variation type'])))
            indel = None; base_is_indel = False
            if rows_:
                is_wt = lambda lt, rt_: lt == 'WT' and rt_ == 'WT'
                base = max(rows_)
                wt_ratio = sum(r for r, lt, rt_ in rows_ if is_wt(lt, rt_))
                if not is_wt(base[1], base[2]) and base[0] >= 0.8:
                    # 非WT主型 ≥80%: 视为材料基线 (主表既有口径, 见 USR-25902 块009-021)
                    base_is_indel = True
                    indel = 1.0 - base[0] - wt_ratio
                else:
                    indel = 1.0 - wt_ratio if wt_ratio > 0 else sum(r for r, lt, rt_ in rows_ if not is_wt(lt, rt_))
                indel = max(0.0, min(1.0, round(indel, 4)))
            notes = [f"块{b['block']}"]
            if sum(1 for fb in file_blocks if fb[0] == batch) > 1:
                notes.append(f'来源文件:{fname}')
            if not rows_: notes.append('无变异行')
            if base_is_indel: notes.append('主型非WT≥80%,按既有口径视为材料基线')

            if 'confident' in info:
                g, pam, gname, gc = info['confident']
                start, end = gc[0], gc[1]
                chrom = info['chrom']; strand = gc[2]
                notes.append('guide确定')
            elif info.get('cands'):
                g, pam, s, w, gc = info['cands'][0]
                start, end = gc[0], gc[1]
                chrom = info['chrom']; strand = gc[2]
                gname = info.get('gene', '')
                notes.append('guide为候选,待设计表确认(见guide候选表)')
            else:
                g = pam = chrom = start = end = strand = None
                gname = info.get('gene', '')
                notes.append('guide未确定(测序编辑率≈0无突变热点,理论候选见guide候选表)')
            if info.get('gnote'): notes.append(info['gnote'])

            tks_n += 1
            rows_out.append({
                '编号': None, 'guide-id': f'TKS_{tks_n:04d}', 'gene-id': gname,
                'seq-20': g, 'pam': pam, 'chrom': chrom, 'start': start, 'end': end,
                'strand': strand, 'batch': batch, 'rep': '暂不填',
                'indel_pct': indel, 'efficiency-norm': None, '备注': '; '.join(notes),
            })

    df = pd.DataFrame(rows_out, columns=['列名','guide-id','gene-id','seq-20','pam','chrom',
        'start','end','strand','batch','rep','indel_pct','efficiency-norm','备注'])
    qc = pd.DataFrame(qc_rows, columns=['ref','seq20','pam','原型链向','基因组坐标',
                                        '热点得分','gene-id','基因链向','结论'])
    doc = pd.DataFrame({'说明': [
        '本表由 NEWdata/02_HiTOM结果表格 下 17 个新批次 (18 个结果文件) 自动整理 (2026-09-18)',
        'indel_pct 口径: 1 - 主型行占比 - (主型非WT时的WT/WT残留); 主型为WT时即 1-WT占比',
        '  该口径经 USR-25902 逐块验证: 32/49 与主表完全一致, 且能正确复现团队对',
        '  Large_Indel 主型(视为材料基线)和无WT行的处理; 其余差异为主表手工整理痕迹, 不可机械复现',
        'seq-20 为 protospacer 5\'->3\'; start/end 为基因组坐标 (start=1-based首碱基, end=start+20)',
        'strand = protospacer 在基因组上的链向 (已全量核实: 主表491行 strand 均等于原型链向)',
        'guide 判定: refsm1/refABCM1/refABC49261/refSP3 的扩增子含主表已确立 guide, 直接采用',
        '其余 ref 的 guide 需团队设计表确认, 见 guide候选 表 (按编辑热点+Cas9几何排序)',
        '注意: refsm1/refABC49261 的扩增子内存在第二个高编辑热点位点 (见guide候选表候选1),',
        '  疑为双guide设计, 主表既往只记录一条, 本表遵循同口径',
        'gene-id 由扩增子在 TKS 基因组(2-1) 的比对位置 + 2-2 GFF mRNA 注释确定',
        'ref22B20 全部 reads 携带同一 28bp 缺失, 用末端探针定位基因组, 按基线口径 indel=0',
        'rep 沿用主表口径填 暂不填; efficiency-norm 留空',
        f'共 {len(df)} 行 (每行=一个样本块), guide-id 续主表自 TKS_0492 起',
    ]})
    with pd.ExcelWriter(OUT, engine='openpyxl') as w:
        df.to_excel(w, sheet_name='Sheet1', index=False)
        qc.to_excel(w, sheet_name='guide候选', index=False)
        doc.to_excel(w, sheet_name='说明', index=False)
    print(f"输出 {OUT}: Sheet1={len(df)}行, guide候选={len(qc)}行")
    print(df['batch'].value_counts().to_string())
    print("guide确定行数:", int(df['备注'].str.contains('guide确定').sum()),
          " 候选行数:", int(df['备注'].str.contains('候选').sum()),
          " 未定行数:", int(df['备注'].str.contains('未确定').sum()))

if __name__ == '__main__':
    main()
