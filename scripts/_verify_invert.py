import math
EPS = 1e-6
def logit(p):
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))
def sigmoid(z):
    return 1 / (1 + math.exp(-z))
T_old = 0.66
for orig_conf in (0.02, 0.35, 0.8, 0.99):
    s_raw = sigmoid(logit(1 - orig_conf) * T_old)
    reproduced = 1 - sigmoid(logit(s_raw) / T_old)
    print(orig_conf, "->", reproduced, "match", abs(orig_conf - reproduced) < 1e-9)
