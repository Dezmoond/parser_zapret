"""
Парсер 4 - Парсер единого федерального списка террористических организаций ФСБ
"""
import logging
import time
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .base_parser import BaseParser


class Parser4(BaseParser):
    """Парсер 4 - парсит таблицу террористических организаций с сайта ФСБ"""
    
    def __init__(self, config: Dict[str, Any]):
        """Инициализация парсера с настройками Selenium"""
        super().__init__(config)
        self.use_selenium = config.get('use_selenium', True)
        self.selenium_timeout = config.get('selenium_timeout', 30)
    
    def _init_selenium_driver(self):
        """Инициализация Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                self.logger.info("Использован webdriver-manager для ChromeDriver")
            except ImportError:
                driver = webdriver.Chrome(options=chrome_options)
                self.logger.info("Использован стандартный ChromeDriver")
            
            driver.set_page_load_timeout(self.selenium_timeout)
            return driver
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Selenium: {e}")
            raise
    
    def _parse_table(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Парсинг таблицы
        
        Args:
            soup: BeautifulSoup объект с HTML контентом
            
        Returns:
            Список словарей с данными
        """
        data = []
        
        try:
            # Ищем таблицу по селектору
            table = soup.select_one('#content > div.hold > div:nth-child(2) > table')
            if not table:
                # Пробуем альтернативные селекторы
                table = soup.find('div', {'id': 'content'})
                if table:
                    hold_div = table.find('div', class_='hold')
                    if hold_div:
                        divs = hold_div.find_all('div', recursive=False)
                        if len(divs) > 1:
                            table = divs[1].find('table')
            
            if not table:
                self.logger.warning("Таблица не найдена по селектору #content > div.hold > div:nth-child(2) > table")
                return data
            
            # Находим заголовки таблицы
            headers = []
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            else:
                # Если нет thead, ищем первую строку
                first_row = table.find('tr')
                if first_row:
                    headers = [th.get_text(strip=True) for th in first_row.find_all(['th', 'td'])]
            
            # Если заголовки не найдены, создаем по умолчанию
            if not headers:
                # Пробуем определить количество столбцов из первой строки данных
                first_data_row = table.find('tr')
                if first_data_row:
                    num_cols = len(first_data_row.find_all(['td', 'th']))
                    headers = [f'Column_{i+1}' for i in range(num_cols)]
            
            self.logger.info(f"Найдено заголовков: {len(headers)}")
            self.logger.info(f"Заголовки: {headers}")
            
            # Парсим строки таблицы
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
            else:
                # Если нет tbody, берем все строки кроме заголовков
                rows = table.find_all('tr')
                if thead or (first_row and first_row.find('th')):
                    rows = rows[1:]  # Пропускаем первую строку с заголовками
            
            self.logger.info(f"Найдено строк данных: {len(rows)}")
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) == 0:
                    continue
                
                # Создаем словарь для строки
                row_data = {}
                for i, cell in enumerate(cells):
                    header = headers[i] if i < len(headers) else f'Column_{i+1}'
                    value = cell.get_text(strip=True)
                    # Удаляем запятые из значений (так как CSV использует запятую как разделитель)
                    value = value.replace(',', '')
                    row_data[header] = value
                
                # Добавляем только если есть хотя бы одно непустое значение
                if any(row_data.values()):
                    data.append(row_data)
            
            self.logger.info(f"Обработано записей: {len(data)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга таблицы: {e}")
        
        return data
    
    def parse_with_selenium(self, url: str) -> List[Dict[str, Any]]:
        """
        Парсинг с использованием Selenium
        
        Args:
            url: URL для парсинга
            
        Returns:
            Список словарей с данными
        """
        driver = None
        data = []
        
        try:
            driver = self._init_selenium_driver()
            self.logger.info(f"Загрузка страницы: {url}")
            driver.get(url)
            
            # Ждем загрузки страницы
            self.logger.info("Ожидание загрузки данных...")
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#content > div.hold > div:nth-child(2) > table, #content table'))
                )
                self.logger.info("Таблица загружена")
            except TimeoutException:
                self.logger.warning("Таймаут ожидания таблицы")
            
            time.sleep(2)
            
            # Получаем HTML
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Парсим таблицу
            data = self._parse_table(soup)
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге с Selenium: {e}")
        finally:
            if driver:
                driver.quit()
        
        return data
    
    def parse(self, response: requests.Response) -> List[Dict[str, Any]]:
        """
        Парсинг HTML страницы (не используется, так как переопределяем run())
        """
        return []
    
    def run(self) -> None:
        """
        Переопределенный метод run для парсинга таблицы
        """
        if not self.enabled:
            self.logger.info(f"Парсер {self.name} отключен в конфигурации")
            return
        
        self.logger.info(f"Запуск парсера {self.name}")
        
        if not self.urls:
            self.logger.warning("Нет URL для парсинга")
            return
        
        url = self.urls[0]
        
        try:
            # Парсим с использованием Selenium
            data = self.parse_with_selenium(url)
            
            # Проверяем наличие данных
            if not data or len(data) == 0:
                self.logger.warning(f"⚠️  ВНИМАНИЕ: Парсер {self.name} не собрал данных с сайта {url}")
                
                from pathlib import Path
                if Path(self.output_file).exists():
                    self.logger.warning(f"Существующий файл {self.output_file} НЕ будет перезаписан пустыми данными")
                else:
                    self.logger.warning(f"Файл {self.output_file} не будет создан")
                return
            
            # Сохраняем в CSV
            self.save_to_csv(data, self.output_file)
            self.logger.info(f"✓ Сохранено {len(data)} записей в {self.output_file}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при работе парсера: {e}")
            from pathlib import Path
            if Path(self.output_file).exists():
                self.logger.warning(f"Существующий файл {self.output_file} НЕ будет перезаписан")
    
    def save_to_csv(self, data: List[Dict[str, Any]], output_file: str = None) -> None:
        """
        Сохранение данных в CSV файл
        
        Args:
            data: Список словарей с данными
            output_file: Путь к выходному файлу (если None, используется self.output_file)
        """
        if not data:
            self.logger.warning("Нет данных для сохранения")
            return
        
        import csv
        
        if output_file is None:
            output_file = self.output_file
        
        # Создаем директорию если нужно
        from pathlib import Path
        output_path = Path(output_file)
        
        # Получаем абсолютный путь
        output_path = output_path.resolve()
        
        # Создаем директорию с логированием
        try:
            self.logger.info(f"Создание директории: {output_path.parent}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Директория создана/проверена: {output_path.parent}")
            
            # Проверяем, что директория действительно существует
            if not output_path.parent.exists():
                raise Exception(f"Директория не была создана: {output_path.parent}")
                
        except Exception as e:
            self.logger.error(f"Ошибка при создании директории {output_path.parent}: {e}")
            self.logger.error(f"Длина пути: {len(str(output_path.parent))} символов")
            raise
        
        # Получаем все уникальные ключи из всех записей
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        
        # Номер всегда должен быть первым столбцом
        # Ищем столбец с номером (может быть "№ п/п", "№п/п", "номер", "Номер" и т.д.)
        fieldnames_list = list(fieldnames)
        number_field = None
        
        # Ищем поле с номером - проверяем различные варианты
        for field in fieldnames_list:
            # Убираем пробелы для сравнения
            field_no_spaces = field.replace(' ', '').replace('\xa0', '')  # \xa0 - неразрывный пробел
            field_lower = field.lower().replace(' ', '').replace('\xa0', '')
            
            # Проверяем различные варианты написания номера
            if ('№' in field or 'номер' in field_lower or 'п/п' in field_lower or 
                field_lower.startswith('№') or 'пп' in field_lower or 
                field == '№п/п' or field == '№ п/п' or field_no_spaces == '№п/п' or
                '№пп' in field_lower or field_no_spaces.lower() == '№п/п'):
                number_field = field
                self.logger.info(f"Найдено поле с номером: '{field}' (оригинальное название)")
                break
        
        if number_field:
            fieldnames_list.remove(number_field)
            fieldnames = [number_field] + sorted(fieldnames_list)
            self.logger.info(f"Столбец с номером найден и поставлен первым: {number_field}")
        else:
            # Если не нашли, пробуем найти по позиции (обычно первый или последний столбец)
            self.logger.warning("Столбец с номером не найден автоматически, используем сортировку")
            fieldnames = sorted(fieldnames_list)
        
        # Записываем данные в CSV
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        self.logger.info(f"Данные сохранены в {output_file}")

