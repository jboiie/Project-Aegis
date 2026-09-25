import math
def wilson_ci(x, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, center - margin), min(1.0, center + margin))

pairs = [
    ("recall lost (test)", 56, 1193),
    ("sec_ed b1-2 FPR after", 11, 18),
    ("sec_ed b3 FPR after", 14, 100),
    ("sec_ed combined FPR after", 25, 118),
]
for label, x, n in pairs:
    lo, hi = wilson_ci(x, n)
    print(f"{label}: {x}/{n} = {x/n:.1%}  [{lo:.1%}, {hi:.1%}]")
