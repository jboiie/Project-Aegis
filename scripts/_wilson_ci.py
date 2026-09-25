import sys
import math

def wilson_ci(x, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, center - margin), min(1.0, center + margin))

for x, n in [(2, 20), (0, 20), (0, 28), (0, 60)]:
    lo, hi = wilson_ci(x, n)
    print(f"{x}/{n} = {x/n:.1%}  95% Wilson CI: [{lo:.3f}, {hi:.3f}]")
