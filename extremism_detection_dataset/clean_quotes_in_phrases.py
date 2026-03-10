# -*- coding: utf-8 -*-
"""Очищает фразы в output от \" и кавычек (как в number_char/simplify_output)."""
import json
import os

DIR = os.path.dirname(os.path.abspath(__file__))


def clean_phrase(s: str) -> str:
    s = s.strip()
    while s.startswith('"') or s.startswith('\\"'):
        s = s[2:] if s.startswith('\\"') else s[1:]
    while s.endswith('"') or s.endswith('\\"'):
        s = s[:-2] if s.endswith('\\"') else s[:-1]
    s = s.strip()
    return s.replace('\\"', '').replace('"', '').strip()


def process(path: str) -> int:
    tmp = path + ".tmp"
    n = 0
    with open(path, "r", encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as out:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            try:
                out_obj = json.loads(obj["output"])
            except json.JSONDecodeError:
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                n += 1
                continue
            phrases = out_obj.get("extremist_phrases") or []
            out_obj["extremist_phrases"] = [clean_phrase(str(p)) for p in phrases]
            obj["output"] = json.dumps(out_obj, ensure_ascii=False)
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    return n


if __name__ == "__main__":
    for name in ["train_dataset.jsonl", "test_dataset.jsonl"]:
        path = os.path.join(DIR, name)
        if os.path.isfile(path):
            cnt = process(path)
            print(name, cnt, "строк")
