"""
Утилита для записи данных в CSV
"""
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any


class CSVWriter:
    """Класс для записи данных в CSV файлы"""
    
    def __init__(self, output_file: str):
        """
        Инициализация CSV writer
        
        Args:
            output_file: Путь к выходному CSV файлу
        """
        self.output_file = output_file
        self.logger = logging.getLogger(__name__)
        
        # Создание директории для выходных файлов
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def write(self, data: List[Dict[str, Any]], fieldnames: List[str] = None) -> None:
        """
        Запись данных в CSV файл
        
        Args:
            data: Список словарей с данными
            fieldnames: Список имен колонок (если None, будут определены автоматически)
        """
        if not data:
            self.logger.warning("Нет данных для записи")
            return
        
        # Определяем имена колонок
        if fieldnames is None:
            fieldnames = set()
            for record in data:
                fieldnames.update(record.keys())
            fieldnames = sorted(list(fieldnames))
        
        # Записываем данные
        with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in data:
                # Заполняем отсутствующие поля пустыми значениями
                row = {field: record.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        self.logger.info(f"Записано {len(data)} записей в {self.output_file}")
    
    def append(self, data: List[Dict[str, Any]], fieldnames: List[str] = None) -> None:
        """
        Добавление данных в существующий CSV файл
        
        Args:
            data: Список словарей с данными
            fieldnames: Список имен колонок
        """
        if not data:
            return
        
        file_exists = Path(self.output_file).exists()
        
        # Определяем имена колонок
        if fieldnames is None:
            fieldnames = set()
            for record in data:
                fieldnames.update(record.keys())
            fieldnames = sorted(list(fieldnames))
        
        # Если файл существует, читаем существующие fieldnames
        if file_exists:
            with open(self.output_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                existing_fieldnames = reader.fieldnames or []
                fieldnames = sorted(list(set(fieldnames) | set(existing_fieldnames)))
        
        # Записываем данные
        mode = 'a' if file_exists else 'w'
        with open(self.output_file, mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            for record in data:
                row = {field: record.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        self.logger.info(f"Добавлено {len(data)} записей в {self.output_file}")


