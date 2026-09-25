import json

for path in ["data/cmp_qwen_template.jsonl", "data/cmp_qwen_encoding.jsonl", "data/cmp_qwen_pair.jsonl",
             "data/cmp_gptoss120b_template.jsonl", "data/cmp_gptoss120b_encoding.jsonl", "data/cmp_gptoss120b_pair.jsonl"]:
    n_with_think = 0
    n_total = 0
    for l in open(path, encoding="utf-8"):
        r = json.loads(l)
        n_total += 1
        if "<think>" in r["response"]:
            n_with_think += 1
    print(f"{path}: {n_with_think}/{n_total} responses contain <think>")
