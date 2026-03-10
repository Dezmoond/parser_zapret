# -*- coding: utf-8 -*-
"""
Преобразует все датасеты к формату:
- found_extremism -> found_dangerous
- extremist_phrases -> dangerous_phrases
- categories удаляются полностью
- instruction обновляется: found_dangerous, dangerous_phrases (без categories)

Запуск из корня проекта: python convert_to_dangerous_format.py
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
NEW_INSTRUCTION = "Определи в тексте наличие опасных высказываний: агрессия, оскорбления, дискриминация, экстремизм, ЛГБТ. Ответ — JSON: found_dangerous, dangerous_phrases."

FILES = [
    (os.path.join(ROOT, "extremism_detection_dataset", "train_dataset.jsonl"), False),
    (os.path.join(ROOT, "extremism_detection_dataset", "test_dataset.jsonl"), False),
    (os.path.join(ROOT, "extremism_detection_dataset_number_char", "train_dataset.jsonl"), True),
    (os.path.join(ROOT, "extremism_detection_dataset_number_char", "test_dataset.jsonl"), True),
]


def convert_file(path: str, is_number_char: bool, backup: bool = True) -> int:
    if not os.path.isfile(path):
        print("Пропуск (нет файла):", path)
        return 0
    if backup:
        bak = path + ".bak_before_dangerous"
        with open(path, "r", encoding="utf-8") as f, open(bak, "w", encoding="utf-8") as b:
            b.write(f.read())
        print("Бэкап:", bak)
    tmp = path + ".tmp"
    n = 0
    skipped = 0
    with open(path, "r", encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as out:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            obj["instruction"] = NEW_INSTRUCTION
            out_str = obj.get("output", "{}")
            try:
                out_obj = json.loads(out_str)
            except json.JSONDecodeError:
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                n += 1
                continue
            fe = out_obj.get("found_extremism", out_obj.get("found_dangerous", False))
            phrases_raw = out_obj.get("extremist_phrases", out_obj.get("dangerous_phrases", [])) or []
            if is_number_char:
                dangerous = []
                for p in phrases_raw:
                    if isinstance(p, dict):
                        dangerous.append({
                            "text": p.get("text") or p.get("phrase") or "",
                            "start_char": p.get("start_char"),
                            "end_char": p.get("end_char"),
                        })
                    else:
                        dangerous.append({"text": str(p), "start_char": None, "end_char": None})
            else:
                dangerous = []
                for p in phrases_raw:
                    if isinstance(p, dict):
                        dangerous.append(p.get("text") or p.get("phrase") or str(p))
                    else:
                        dangerous.append(str(p))
            obj["output"] = json.dumps({
                "found_dangerous": fe,
                "dangerous_phrases": dangerous,
            }, ensure_ascii=False)
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    print(path, "— обработано строк:", n, "пропущено:", skipped)
    return n


if __name__ == "__main__":
    total = 0
    for path, is_nc in FILES:
        total += convert_file(path, is_nc, backup=True)
    print("Готово. Всего строк:", total)
