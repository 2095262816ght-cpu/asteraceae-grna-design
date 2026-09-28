import numpy as np
import pandas as pd

real = pd.read_csv("results/real_crispron_top100_0927.csv")
rmap = dict(zip(real["seq30"].astype(str), real["crispron_score"].astype(float)))
print("real scores loaded:", len(rmap), flush=True)

a_list, b_list = [], []
seen = set()
for chunk in pd.read_csv(
    "results/lettuce_all_genes_top100_candidates.csv",
    usecols=["seq30", "crispron_score"],
    chunksize=500000,
):
    for s, ap in zip(chunk["seq30"].astype(str), chunk["crispron_score"].astype(float)):
        if s in rmap and s not in seen:
            seen.add(s)
            a_list.append(ap)
            b_list.append(rmap[s])
    print("chunk done, matched:", len(seen), flush=True)

a = np.asarray(a_list, dtype=float)
b = np.asarray(b_list, dtype=float)
ra = np.argsort(np.argsort(a)).astype(float)
rb = np.argsort(np.argsort(b)).astype(float)
rho = np.corrcoef(ra, rb)[0, 1]
r = np.corrcoef(a, b)[0, 1]
d = b - a
ad = np.abs(d)
print("sample n =", len(a))
print("Spearman rho = %.4f" % rho)
print("Pearson  r   = %.4f" % r)
print("bias(real-approx): mean=%+.2f median=%+.2f std=%.2f" % (d.mean(), np.median(d), d.std()))
print("abs error: mean=%.2f P95=%.2f max=%.2f" % (ad.mean(), np.quantile(ad, 0.95), ad.max()))
