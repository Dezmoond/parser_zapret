# -*- coding: utf-8 -*-
"""
Восстанавливает метки start_char и end_char для каждой экстремистской фразы в датасете.
Использует текущие поля: input (текст) и output.extremist_phrases (список строк).
Для каждой фразы ищет её первое вхождение в input и записывает start_char, end_char.
Формат output.extremist_phrases после обработки: [{"text": "...", "start_char": int, "end_char": int}, ...]
Резервные копии: train_dataset.jsonl.bak, test_dataset.jsonl.bak.
Запуск: python restore_phrase_spans.py
"""
import json
import os
import re

DIR = os.path.dirname(os.path.abspath(__file__))


def normalize_for_search(s: str) -> str:
    """Сворачиваем множественные пробелы для более гибкого поиска."""
    return re.sub(r"\s+", " ", s.strip())


def find_phrase_span(text: str, phrase: str):
    """
    Ищет первое вхождение phrase в text. Возвращает (start_char, end_char) или (None, None).
    Сначала точное совпадение; если не найдено — поиск с игнорированием множественных пробелов.
    """
    if not phrase or not text:
        return None, None
    pos = text.find(phrase)
    if pos != -1:
        return pos, pos + len(phrase)
    phrase_norm = normalize_for_search(phrase)
    if not phrase_norm:
        return None, None
    # Сопоставление: p_idx по phrase_norm, t_idx по text; в text пропускаем лишние пробелы
    for t_start in range(len(text)):
        p_idx = 0
        t_idx = t_start
        while p_idx < len(phrase_norm) and t_idx < len(text):
            pc = phrase_norm[p_idx]
            tc = text[t_idx]
            if pc == " ":
                if re.match(r"\s", tc):
                    p_idx += 1
                    while t_idx < len(text) and re.match(r"\s", text[t_idx]):
                        t_idx += 1
                    continue
                break
            if pc != tc:
                break
            p_idx += 1
            t_idx += 1
        if p_idx == len(phrase_norm):
            return t_start, t_idx
    return None, None


def process(path: str, backup: bool = True) -> tuple[int, int]:
    """
    Обрабатывает jsonl-файл: для каждой строки восстанавливает start_char/end_char у фраз.
    Возвращает (число строк, число фраз без найденной позиции).
    """
    if backup and os.path.isfile(path):
        bak = path + ".bak"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(bak, "w", encoding="utf-8") as f:
            f.write(content)
    tmp = path + ".tmp"
    n_lines = 0
    n_missed = 0
    with open(path, "r", encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as out:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            inp = obj.get("input", "")
            out_str = obj.get("output", "{}")
            try:
                out_obj = json.loads(out_str)
            except json.JSONDecodeError:
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                n_lines += 1
                continue

            phrases_raw = out_obj.get("extremist_phrases") or []
            new_phrases = []
            for p in phrases_raw:
                if isinstance(p, dict):
                    text = p.get("text") or p.get("phrase") or ""
                else:
                    text = str(p).strip()
                start_char, end_char = find_phrase_span(inp, text)
                if start_char is None:
                    n_missed += 1
                new_phrases.append({
                    "text": text,
                    "start_char": start_char,
                    "end_char": end_char,
                })
            out_obj["extremist_phrases"] = new_phrases
            obj["output"] = json.dumps(out_obj, ensure_ascii=False)
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n_lines += 1
    os.replace(tmp, path)
    return n_lines, n_missed


if __name__ == "__main__":
    train_path = os.path.join(DIR, "train_dataset.jsonl")
    test_path = os.path.join(DIR, "test_dataset.jsonl")
    total_missed = 0
    for name, path in [("train_dataset.jsonl", train_path), ("test_dataset.jsonl", test_path)]:
        if not os.path.isfile(path):
            print("Пропуск (нет файла):", path)
            continue
        n_lines, n_missed = process(path, backup=True)
        total_missed += n_missed
        print(f"{name}: обработано строк {n_lines}, фраз без позиции: {n_missed}")
    print("Готово. В output.extremist_phrases теперь объекты с полями text, start_char, end_char.")
    print("Резервные копии: train_dataset.jsonl.bak, test_dataset.jsonl.bak")
