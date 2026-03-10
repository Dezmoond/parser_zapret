# -*- coding: utf-8 -*-
"""
1. Очищает фразы от оставшихся \" и кавычек по краям.
2. Упрощает output: extremist_phrases — только список строк ["фраза1", "фраза2"],
   без start_char/end_char (для обучения этого достаточно).
"""
import json
import os
import re

DIR = os.path.dirname(os.path.abspath(__file__))


def clean_phrase(s: str) -> str:
    """Убираем кавычки по краям и все \" и \" внутри фразы."""
    s = s.strip()
    while s.startswith('"') or s.startswith('\\"'):
        s = s[2:] if s.startswith('\\"') else s[1:]
    while s.endswith('"') or s.endswith('\\"'):
        s = s[:-2] if s.endswith('\\"') else s[:-1]
    s = s.strip()
    # Убираем все оставшиеся \" и " внутри фразы (для обучения не нужны)
    return s.replace('\\"', '').replace('"', '').strip()


def get_phrase_strings(out_obj):
    """Из output получаем список строк фраз (уже очищенных)."""
    phrases = out_obj.get("extremist_phrases") or []
    result = []
    for p in phrases:
        if isinstance(p, dict):
            result.append(clean_phrase(p.get("phrase", "")))
        else:
            result.append(clean_phrase(str(p)))
    return result


def process(path: str) -> int:
    tmp = path + ".tmp"
    n = 0
    with open(path, "r", encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as out:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out_str = obj["output"]
            try:
                out_obj = json.loads(out_str)
            except json.JSONDecodeError:
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                n += 1
                continue

            # Упрощённый output: только found_extremism, extremist_phrases как список строк, categories
            phrase_strings = get_phrase_strings(out_obj)
            new_out = {
                "found_extremism": out_obj.get("found_extremism", False),
                "extremist_phrases": phrase_strings,
                "categories": out_obj.get("categories", []),
            }
            obj["output"] = json.dumps(new_out, ensure_ascii=False)
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    return n


if __name__ == "__main__":
    train_path = os.path.join(DIR, "train_dataset.jsonl")
    test_path = os.path.join(DIR, "test_dataset.jsonl")
    n_train = process(train_path)
    n_test = process(test_path)
    print("Output упрощён: extremist_phrases = [строка, ...], без start_char/end_char; фразы без \\\".")
    print("train_dataset.jsonl:", n_train, "строк")
    print("test_dataset.jsonl:", n_test, "строк")
