# -*- coding: utf-8 -*-
"""
Убирает кавычки \" вокруг запрещённых фраз в input (чтобы модель не училась на подсказке)
и в output убирает обрамляющие кавычки у фраз.
"""
import json
import os

DIR = os.path.dirname(os.path.abspath(__file__))


def get_phrases_from_output(out_obj):
    """Из output извлекаем список текстов фраз (для number_char — из объектов с ключом phrase)."""
    phrases = out_obj.get("extremist_phrases") or []
    result = []
    for p in phrases:
        if isinstance(p, dict):
            result.append(p.get("phrase", ""))
        else:
            result.append(str(p))
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
            inp = obj["input"]
            out_str = obj["output"]
            try:
                out_obj = json.loads(out_str)
            except json.JSONDecodeError:
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                n += 1
                continue

            phrases = get_phrases_from_output(out_obj)
            # Убираем в input обёртку "фраза" -> фраза (чтобы не подсказывать модели)
            for phrase in phrases:
                stripped = phrase.strip('"')
                if not stripped:
                    continue
                pattern = '"' + stripped + '"'
                if pattern in inp:
                    inp = inp.replace(pattern, stripped)
            obj["input"] = inp

            # В output храним фразу без обрамляющих кавычек
            new_phrases = []
            for p in out_obj.get("extremist_phrases") or []:
                if isinstance(p, dict):
                    new_p = dict(p)
                    new_p["phrase"] = p.get("phrase", "").strip('"')
                    new_phrases.append(new_p)
                else:
                    new_phrases.append(p.strip('"') if isinstance(p, str) else p)
            out_obj["extremist_phrases"] = new_phrases
            obj["output"] = json.dumps(out_obj, ensure_ascii=False)

            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    return n


if __name__ == "__main__":
    train_path = os.path.join(DIR, "train_dataset.jsonl")
    test_path = os.path.join(DIR, "test_dataset.jsonl")
    n_train = process(train_path)
    n_test = process(test_path)
    print("Убраны кавычки вокруг фраз в input и в output (phrase без обёртки).")
    print("train_dataset.jsonl:", n_train, "строк")
    print("test_dataset.jsonl:", n_test, "строк")
