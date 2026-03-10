"""
Парсер 7 - Скачивание перечня экстремистских материалов Минюста (CSV)
"""
import logging
import time
from pathlib import Path
from urllib.parse import urljoin
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

from .base_parser import BaseParser


# URL страницы с перечнем экстремистских материалов
PAGE_URL = "https://minjust.gov.ru/ru/extremist-materials/"
# Прямая ссылка на CSV (fallback, если не удастся найти на странице)
DEFAULT_CSV_URL = "https://minjust.gov.ru/uploaded/files/exportfsm.csv"


class Parser7(BaseParser):
    """Парсер 7 - скачивает CSV файл перечня экстремистских материалов с сайта Минюста"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Сайт Минюста отвечает медленно — таймаут 120 сек
        self.timeout = config.get("timeout", 120)

    def _get_csv_url(self) -> str:
        """
        Получает URL CSV-файла. Сначала пробует со страницы, при ошибке — прямой URL.
        """
        try:
            response = requests.get(
                PAGE_URL,
                headers={"User-Agent": self.user_agent},
                timeout=15,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            link = (
                soup.select_one('a[href*="exportfsm.csv"]')
                or soup.select_one("body > main > div:nth-child(2) > a:nth-child(12)")
            )
            if link and link.get("href"):
                return urljoin(PAGE_URL, link["href"].strip())
        except Exception as e:
            self.logger.info(f"Ссылка со страницы недоступна, используем прямой URL: {e}")
        return DEFAULT_CSV_URL

    def parse(self, response: requests.Response) -> List[Dict[str, Any]]:
        """
        Не используется — парсер сохраняет сырой CSV.
        Переопределён для совместимости с BaseParser.
        """
        return []

    def run(self) -> None:
        """
        Запуск парсера: получает ссылку на CSV, скачивает файл и сохраняет.
        При каждом запуске файл обновляется.
        """
        if not self.enabled:
            self.logger.info(f"Парсер {self.name} отключен в конфигурации")
            return

        self.logger.info(f"Запуск парсера {self.name}")

        csv_url = self._get_csv_url()
        self.logger.info(f"Скачивание CSV: {csv_url} (таймаут {self.timeout} сек)")

        headers = {
            "User-Agent": self.user_agent,
            "Referer": PAGE_URL,
            "Accept": "text/csv,application/csv,*/*",
        }
        content = None
        resp_headers = {}
        for attempt in range(self.retry_count):
            try:
                self.logger.info(f"Скачивание (попытка {attempt + 1}/{self.retry_count})")
                # stream=True + iter_content — помогает при медленном соединении
                with requests.get(
                    csv_url,
                    headers=headers,
                    timeout=(10, self.timeout),  # (connect, read)
                    stream=True,
                ) as r:
                    r.raise_for_status()
                    resp_headers = r.headers
                    content = b"".join(r.iter_content(chunk_size=65536))
                break
            except Exception as e:
                self.logger.warning(f"Ошибка: {e}")
                if attempt < self.retry_count - 1:
                    delay = self.delay_between_requests * (attempt + 1)
                    self.logger.info(f"Повтор через {delay} сек...")
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"Не удалось скачать CSV после {self.retry_count} попыток. "
                        f"Попробуйте вручную: {csv_url}"
                    )
                    return

        if content is None:
            return

        # Эмулируем response для дальнейшей обработки
        response = type("Resp", (), {"content": content, "headers": resp_headers})()

        # Создаём директорию для выходного файла
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Определяем кодировку: сайт Минюста отдаёт CSV в Windows-1251
        content_type = response.headers.get("Content-Type", "").lower()
        encoding = None
        if "charset=" in content_type:
            encoding = content_type.split("charset=")[-1].split(";")[0].strip()
        if not encoding:
            encoding = "cp1251"  # стандартная кодировка для российских госсайтов

        # Декодируем и сохраняем в UTF-8 (utf-8-sig для корректного отображения в Excel)
        try:
            text = response.content.decode(encoding)
            output_path.write_text(text, encoding="utf-8-sig", newline="")
            self.logger.info(
                f"Файл сохранён: {self.output_file} ({len(text)} символов, UTF-8)"
            )
        except (UnicodeDecodeError, LookupError) as e:
            self.logger.warning(f"Ошибка декодирования {encoding}, пробуем utf-8: {e}")
            try:
                text = response.content.decode("utf-8")
                output_path.write_text(text, encoding="utf-8-sig", newline="")
            except UnicodeDecodeError:
                output_path.write_bytes(response.content)
                self.logger.warning("Сохранено как сырые байты")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении файла: {e}")
