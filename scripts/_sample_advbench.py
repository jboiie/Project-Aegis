import csv
import random

random.seed(42)
with open("C:/Programming/Projects/aegis/data/advbench_harmful_behaviors.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    goals = [row["goal"] for row in reader]

print(f"Total AdvBench behaviors: {len(goals)}")
sample = random.sample(goals, 30)
with open("C:/Programming/Projects/aegis/data/advbench_sample_30.txt", "w", encoding="utf-8") as f:
    for g in sample:
        f.write(g + "\n")
for g in sample:
    print(repr(g))
