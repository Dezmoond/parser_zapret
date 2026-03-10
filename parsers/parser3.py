"""
Парсер 3 - Парсер перечня организаций, признанных экстремистскими Минюста
"""
import logging
import re
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


class Parser3(BaseParser):
    """Парсер 3 - парсит перечень экстремистских организаций с сайта Минюста"""
    
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
    
    def _parse_content(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Парсинг содержимого страницы
        
        Args:
            soup: BeautifulSoup объект с HTML контентом
            
        Returns:
            Список словарей с данными
        """
        data = []
        
        try:
            # Ищем контейнер с данными
            content_div = soup.select_one('#documentcontent > div')
            if not content_div:
                # Пробуем альтернативные селекторы
                content_div = soup.find('div', {'id': 'documentcontent'})
                if content_div:
                    content_div = content_div.find('div')
            
            if not content_div:
                self.logger.warning("Не найден раздел #documentcontent > div")
                return data
            
            # Получаем весь текст
            text_content = content_div.get_text('\n')
            lines = text_content.split('\n')
            
            # Парсим каждую строку
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Ищем строки, начинающиеся с номера (например, "1. ", "2. ")
                match = re.match(r'^(\d+)\.\s*(.+)$', line)
                if match:
                    number = match.group(1).strip()
                    rest = match.group(2).strip()
                    
                    # Ищем решение в последней паре круглых скобок
                    # Может быть несколько пар скобок, нужна последняя
                    # Находим все пары скобок
                    all_brackets = list(re.finditer(r'\(([^)]+)\)', rest))
                    
                    if all_brackets:
                        # Берем последнюю пару скобок (решение)
                        last_bracket = all_brackets[-1]
                        decision = last_bracket.group(1).strip()
                        # Название организации - все до последних скобок
                        org_name = rest[:last_bracket.start()].strip()
                        # Убираем точку в конце названия, если есть
                        org_name = re.sub(r'\.\s*$', '', org_name).strip()
                    else:
                        # Нет решения в скобках
                        org_name = rest
                        # Убираем точку в конце, если есть
                        org_name = re.sub(r'\.\s*$', '', org_name).strip()
                        decision = ''
                    
                    # Удаляем запятые из названия организации (так как CSV использует запятую как разделитель)
                    org_name = org_name.replace(',', '')
                    
                    data.append({
                        'номер': number,
                        'наименование_организации': org_name,
                        'решение': decision
                    })
            
            self.logger.info(f"Найдено организаций: {len(data)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга содержимого: {e}")
        
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
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#documentcontent > div, #documentcontent'))
                )
                self.logger.info("Контент загружен")
            except TimeoutException:
                self.logger.warning("Таймаут ожидания контента")
            
            time.sleep(2)
            
            # Получаем HTML
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Парсим данные
            data = self._parse_content(soup)
            
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
        Переопределенный метод run для парсинга страницы
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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Получаем все уникальные ключи из всех записей
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        
        # Номер всегда должен быть первым столбцом
        fieldnames_list = list(fieldnames)
        if 'номер' in fieldnames_list:
            fieldnames_list.remove('номер')
            fieldnames = ['номер'] + sorted(fieldnames_list)
        else:
            fieldnames = sorted(fieldnames_list)
        
        # Записываем данные в CSV
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        self.logger.info(f"Данные сохранены в {output_file}")

