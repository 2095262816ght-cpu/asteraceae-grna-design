#!/usr/bin/env python
# RNAfold CLI shim for native Windows, backed by the ViennaRNA Python bindings
# (pip package "viennarna" 2.7.2, site-package RNA module).
# Supports the subset of RNAfold CLI behaviour used by CRISPRon:
#   RNAfold --version
#   echo ">id\nSEQ" | RNAfold --noPS   ->  id / seq / "dotbracket ( mfe)"
import sys

import RNA

if "--version" in sys.argv:
    print("RNAfold 2.7.2 (win-shim via ViennaRNA python bindings)")
    sys.exit(0)

data = sys.stdin.read().splitlines()

records = []
rid = None
seq_lines = []
for line in data:
    line = line.strip()
    if not line:
        continue
    if line.startswith(">"):
        if seq_lines:
            records.append((rid, "".join(seq_lines)))
        rid = line[1:]
        seq_lines = []
    elif line.startswith("@"):
        # RNAfold structure constraint lines: ignore (not used by CRISPRon)
        continue
    else:
        seq_lines.append(line.upper().replace("T", "U"))
if seq_lines:
    records.append((rid, "".join(seq_lines)))

for rid, seq in records:
    if not seq:
        continue
    fc = RNA.fold_compound(seq)
    struct, mfe = fc.mfe()
    if rid:
        print(">" + rid)
    print(seq)
    # mimic RNAfold default output: structure ( mfe ) right-aligned
    print("%s (%6.2f)" % (struct, mfe))
