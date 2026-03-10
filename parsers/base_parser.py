"""
Базовый класс для всех парсеров
"""
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import requests
from pathlib import Path


class BaseParser(ABC):
    """Базовый класс для парсеров"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация парсера
        
        Args:
            config: Конфигурация парсера из config.json
        """
        self.name = config.get('name', 'Unknown Parser')
        self.urls = config.get('urls', [])
        self.output_file = config.get('output_file', 'output/data.csv')
        self.enabled = config.get('enabled', True)
        
        # Настройки из общего конфига
        self.timeout = config.get('timeout', 30)
        self.retry_count = config.get('retry_count', 3)
        self.delay_between_requests = config.get('delay_between_requests', 1)
        self.user_agent = config.get('user_agent', 'Mozilla/5.0')
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.name)
        
        # Создание директории для выходных файлов
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def fetch_url(self, url: str) -> requests.Response:
        """
        Получение данных по URL с повторными попытками
        
        Args:
            url: URL для запроса
            
        Returns:
            Response объект
            
        Raises:
            requests.RequestException: При ошибке запроса
        """
        headers = {
            'User-Agent': self.user_agent
        }
        
        for attempt in range(self.retry_count):
            try:
                self.logger.info(f"Запрос к {url} (попытка {attempt + 1}/{self.retry_count})")
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                self.logger.warning(f"Ошибка при запросе {url}: {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.delay_between_requests * (attempt + 1))
                else:
                    raise
        
        raise requests.RequestException(f"Не удалось получить данные с {url}")
    
    @abstractmethod
    def parse(self, response: requests.Response) -> List[Dict[str, Any]]:
        """
        Парсинг ответа от сервера
        
        Args:
            response: Response объект
            
        Returns:
            Список словарей с данными
        """
        pass
    
    def run(self) -> None:
        """
        Запуск парсера для всех URL из конфигурации
        """
        if not self.enabled:
            self.logger.info(f"Парсер {self.name} отключен в конфигурации")
            return
        
        self.logger.info(f"Запуск парсера {self.name}")
        all_data = []
        
        for url in self.urls:
            try:
                response = self.fetch_url(url)
                data = self.parse(response)
                all_data.extend(data)
                self.logger.info(f"Получено {len(data)} записей с {url}")
                
                # Задержка между запросами
                if url != self.urls[-1]:  # Не делать задержку после последнего запроса
                    time.sleep(self.delay_between_requests)
                    
            except Exception as e:
                self.logger.error(f"Ошибка при обработке {url}: {e}")
                continue
        
        if all_data:
            self.save_to_csv(all_data)
            self.logger.info(f"Парсер {self.name} завершил работу. Сохранено {len(all_data)} записей")
        else:
            self.logger.warning(f"Парсер {self.name} не собрал данных")
    
    def save_to_csv(self, data: List[Dict[str, Any]]) -> None:
        """
        Сохранение данных в CSV файл
        
        Args:
            data: Список словарей с данными
        """
        if not data:
            self.logger.warning("Нет данных для сохранения")
            return
        
        import csv
        
        # Получаем все уникальные ключи из всех записей
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        fieldnames = sorted(list(fieldnames))
        
        # Записываем данные в CSV
        with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        self.logger.info(f"Данные сохранены в {self.output_file}")


