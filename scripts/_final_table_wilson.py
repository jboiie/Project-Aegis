import math
def wilson_ci(x, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, center - margin), min(1.0, center + margin))

rows = [
    ("current: b1-2", 11, 18), ("current: b3", 15, 100), ("current: combined", 26, 118),
    ("L2tune: b1-2", 11, 18), ("L2tune: b3", 14, 100), ("L2tune: combined", 25, 118),
    ("L1fix: b1-2", 4, 18), ("L1fix: b3", 7, 100), ("L1fix: combined", 11, 118),
    ("L1fix+LayaL2: b1-2", 1, 18), ("L1fix+LayaL2: b3", 0, 100), ("L1fix+LayaL2: combined", 1, 118),
    ("Laya-all: b1-2", 2, 18), ("Laya-all: b3", 0, 100), ("Laya-all: combined", 2, 118),
    ("recall L2tune", 56, 1193), ("recall L1fix", 0, 1193), ("recall L1fix+LayaL2 strict", 72, 1193),
    ("recall L1fix+LayaL2 eff", 71, 1193), ("recall Laya-all strict", 72, 1193), ("recall Laya-all eff", 71, 1193),
]
for label, x, n in rows:
    lo, hi = wilson_ci(x, n)
    print(f"{label}: {x}/{n} = {x/n:.1%}  [{lo:.1%}, {hi:.1%}]")
