"""
Парсер 1 - Парсер каталога террористов и экстремистов Росфинмониторинга
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


class Parser1(BaseParser):
    """Парсер 1 - парсит каталог террористов и экстремистов с сайта Росфинмониторинга"""
    
    def __init__(self, config: Dict[str, Any]):
        """Инициализация парсера с настройками Selenium"""
        super().__init__(config)
        self.use_selenium = config.get('use_selenium', True)
        self.selenium_timeout = config.get('selenium_timeout', 30)
        
    def _init_selenium_driver(self):
        """Инициализация Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Запуск в фоновом режиме
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            # Пробуем использовать webdriver-manager если установлен
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                self.logger.info("Использован webdriver-manager для ChromeDriver")
            except ImportError:
                # Если webdriver-manager не установлен, используем стандартный способ
                driver = webdriver.Chrome(options=chrome_options)
                self.logger.info("Использован стандартный ChromeDriver")
            
            driver.set_page_load_timeout(self.selenium_timeout)
            return driver
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Selenium: {e}")
            self.logger.error("Убедитесь, что установлен ChromeDriver или установите webdriver-manager: pip install webdriver-manager")
            raise
    
    def _parse_organizations(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Парсинг списка организаций
        
        Args:
            soup: BeautifulSoup объект с HTML контентом
            
        Returns:
            Список словарей с данными об организациях
        """
        organizations = []
        
        try:
            # Ищем контейнер с организациями по прямому селектору
            org_section = soup.select_one('#russianUL > div > ol')
            if not org_section:
                # Пробуем альтернативные селекторы
                org_section = soup.select_one('#russianUL')
                if not org_section:
                    org_section = soup.find('div', {'id': 'russianUL'})
                    if org_section:
                        ol = org_section.find('ol')
                        if ol:
                            org_section = ol
            
            if not org_section:
                self.logger.warning("Не найден раздел с организациями (#russianUL > div > ol)")
                return organizations
            
            # Ищем все элементы списка (обычно это <li> элементы внутри <ol>)
            items = org_section.find_all('li')
            self.logger.info(f"Найдено {len(items)} элементов <li> в списке организаций")
            
            # Если не найдено <li>, ищем другие элементы
            if not items:
                items = org_section.find_all(['div', 'p', 'span'])
                self.logger.info(f"Найдено {len(items)} альтернативных элементов в списке организаций")
            
            # Если все еще не найдено, ищем по тексту всего раздела
            if not items:
                text_content = org_section.get_text('\n')
                lines = text_content.split('\n')
                items = [line.strip() for line in lines if re.match(r'^\d+\.', line.strip())]
                self.logger.info(f"Найдено {len(items)} строк по тексту в списке организаций")
            
            self.logger.info(f"Всего найдено {len(items)} элементов для обработки (организации)")
            
            for item in items:
                if isinstance(item, str):
                    text = item
                else:
                    text = item.get_text(strip=True)
                
                if not text or not re.match(r'^\d+\.', text):
                    continue
                
                # Парсим строку: номер. название организации
                # Формат может быть:
                # "1. FREE RUSSIA FOUNDATION , ;"
                # "2. NATIONAL SOCIALISM/WHITE POWER* (NS/WP; ...), ;"
                # "4. АВТОНОМНАЯ НЕКОММЕРЧЕСКАЯ ОРГАНИЗАЦИЯ ... , , ИНН: 1653019714, ОГРН: 1021603062150;"
                
                # Сначала извлекаем номер
                number_match = re.match(r'^(\d+)\.\s*', text)
                if not number_match:
                    continue
                
                number = number_match.group(1).strip()
                
                # Берем все после номера до ИНН/ОГРН или до запятой с точкой с запятой
                # Убираем номер и точку из начала
                name_text = re.sub(r'^\d+\.\s*', '', text)
                
                # Если есть ИНН или ОГРН, берем только до них
                inn_match = re.search(r',\s*,?\s*ИНН:', name_text)
                if inn_match:
                    name_text = name_text[:inn_match.start()].strip()
                
                # Убираем запятые и точку с запятой в конце
                name_text = re.sub(r',\s*,?\s*;?\s*$', '', name_text).strip()
                name_text = re.sub(r',\s*$', '', name_text).strip()
                
                # Удаляем все запятые из наименования организации
                # так как запятая используется как разделитель CSV
                name_text = name_text.replace(',', '')
                
                if name_text:
                    # Номер должен быть первым столбцом
                    organizations.append({
                        'номер': number,
                        'наименование': name_text
                    })
            
            self.logger.info(f"Найдено организаций: {len(organizations)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга организаций: {e}")
        
        return organizations
    
    def _parse_individuals(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Парсинг списка физических лиц
        
        Args:
            soup: BeautifulSoup объект с HTML контентом
            
        Returns:
            Список словарей с данными о физических лицах
        """
        individuals = []
        
        try:
            # Ищем контейнер с физическими лицами по прямому селектору
            ind_section = soup.select_one('#russianFL > div > ol')
            if not ind_section:
                # Пробуем альтернативные селекторы
                ind_section = soup.select_one('#russianFL')
                if not ind_section:
                    ind_section = soup.find('div', {'id': 'russianFL'})
                    if ind_section:
                        ol = ind_section.find('ol')
                        if ol:
                            ind_section = ol
            
            if not ind_section:
                self.logger.warning("Не найден раздел с физическими лицами (#russianFL > div > ol)")
                return individuals
            
            # Ищем все элементы списка (обычно это <li> элементы внутри <ol>)
            items = ind_section.find_all('li')
            self.logger.info(f"Найдено {len(items)} элементов <li> в списке физических лиц")
            
            # Если не найдено <li>, ищем другие элементы
            if not items:
                items = ind_section.find_all(['div', 'p', 'span'])
                self.logger.info(f"Найдено {len(items)} альтернативных элементов в списке физических лиц")
            
            # Если все еще не найдено, ищем по тексту всего раздела
            if not items:
                text_content = ind_section.get_text('\n')
                lines = text_content.split('\n')
                items = [line.strip() for line in lines if re.match(r'^\d+\.', line.strip())]
                self.logger.info(f"Найдено {len(items)} строк по тексту в списке физических лиц")
            
            self.logger.info(f"Всего найдено {len(items)} элементов для обработки (физические лица)")
            
            for item in items:
                if isinstance(item, str):
                    text = item
                else:
                    text = item.get_text(strip=True)
                
                if not text or not re.match(r'^\d+\.', text):
                    continue
                
                # Парсим строку: номер. ФИО, дата рождения, место рождения
                # Формат: "3505. БУЗДЫХАНОВА АМИНА ОЛЕГОВНА*, 03.01.1984 г.р. , Г. ЧЕРКЕССК СТАВРОПОЛЬСКОГО КРАЯ;"
                # Более гибкое регулярное выражение
                match = re.match(
                    r'^(\d+)\.\s*(.+?),\s*(\d{2}\.\d{2}\.\d{4})\s*г\.р\.\s*,?\s*(.+?)(?:;|$)',
                    text,
                    re.DOTALL
                )
                
                if match:
                    number = match.group(1).strip()
                    fio = match.group(2).strip()
                    birth_date = match.group(3).strip()
                    birth_place = match.group(4).strip()
                    
                    # Убираем лишние пробелы и запятые
                    fio = re.sub(r'\s+', ' ', fio).strip()
                    birth_place = re.sub(r'\s+', ' ', birth_place).strip()
                    birth_place = re.sub(r',\s*$', '', birth_place).strip()
                    
                    # Номер должен быть первым столбцом
                    individuals.append({
                        'номер': number,
                        'ФИО': fio,
                        'дата_рождения': birth_date,
                        'место_рождения': birth_place
                    })
                else:
                    # Альтернативный парсинг - пробуем найти дату в другом формате
                    # Ищем паттерн: номер. текст до даты, дата, текст после
                    date_pattern = r'(\d{2}\.\d{2}\.\d{4})\s*г\.р\.'
                    date_match = re.search(date_pattern, text)
                    
                    if date_match:
                        number_match = re.match(r'^(\d+)\.\s*', text)
                        if number_match:
                            number = number_match.group(1).strip()
                            
                            # Разделяем по дате
                            date_pos = date_match.start()
                            before_date = text[:date_pos]
                            after_date = text[date_match.end():]
                            
                            # Извлекаем ФИО (все до первой запятой перед датой)
                            fio_match = re.search(r',\s*$', before_date)
                            if fio_match:
                                fio = before_date[:fio_match.start()].strip()
                            else:
                                fio = re.sub(r'^\d+\.\s*', '', before_date).strip()
                            
                            # Извлекаем дату
                            birth_date = date_match.group(1).strip()
                            
                            # Извлекаем место рождения (все после "г.р. ," до точки с запятой)
                            birth_place = re.sub(r'^,?\s*', '', after_date).strip()
                            birth_place = re.sub(r';?\s*$', '', birth_place).strip()
                            
                            fio = re.sub(r'\s+', ' ', fio).strip()
                            birth_place = re.sub(r'\s+', ' ', birth_place).strip()
                            
                            if fio and birth_date and birth_place:
                                # Номер должен быть первым столбцом
                                individuals.append({
                                    'номер': number,
                                    'ФИО': fio,
                                    'дата_рождения': birth_date,
                                    'место_рождения': birth_place
                                })
            
            self.logger.info(f"Найдено физических лиц: {len(individuals)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга физических лиц: {e}")
        
        return individuals
    
    def parse_with_selenium(self, url: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Парсинг с использованием Selenium для работы с динамическим контентом
        
        Args:
            url: URL для парсинга
            
        Returns:
            Кортеж (список организаций, список физических лиц)
        """
        driver = None
        organizations = []
        individuals = []
        
        try:
            driver = self._init_selenium_driver()
            self.logger.info(f"Загрузка страницы: {url}")
            driver.get(url)
            
            # Ждем загрузки страницы и появления нужных элементов
            self.logger.info("Ожидание загрузки данных...")
            try:
                # Ждем появления списка организаций
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#russianUL > div > ol, #russianUL'))
                )
                self.logger.info("Список организаций загружен")
            except TimeoutException:
                self.logger.warning("Таймаут ожидания списка организаций")
            
            try:
                # Ждем появления списка физических лиц
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#russianFL > div > ol, #russianFL'))
                )
                self.logger.info("Список физических лиц загружен")
            except TimeoutException:
                self.logger.warning("Таймаут ожидания списка физических лиц")
            
            # Дополнительная задержка для полной загрузки
            time.sleep(2)
            
            # Получаем HTML
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Парсим организации
            self.logger.info("Парсинг организаций...")
            organizations = self._parse_organizations(soup)
            
            # Парсим физические лица
            self.logger.info("Парсинг физических лиц...")
            individuals = self._parse_individuals(soup)
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге с Selenium: {e}")
        finally:
            if driver:
                driver.quit()
        
        return organizations, individuals
    
    def parse(self, response: requests.Response) -> List[Dict[str, Any]]:
        """
        Парсинг HTML страницы
        
        Args:
            response: Response объект
            
        Returns:
            Список словарей с данными (в данном случае не используется, данные сохраняются отдельно)
        """
        # Этот метод вызывается из базового класса, но для этого парсера
        # мы переопределяем run() для сохранения в два разных файла
        return []
    
    def run(self) -> None:
        """
        Переопределенный метод run для сохранения в два разных CSV файла
        """
        if not self.enabled:
            self.logger.info(f"Парсер {self.name} отключен в конфигурации")
            return
        
        self.logger.info(f"Запуск парсера {self.name}")
        
        if not self.urls:
            self.logger.warning("Нет URL для парсинга")
            return
        
        url = self.urls[0]  # Берем первый URL
        
        # Парсим с использованием Selenium
        organizations, individuals = self.parse_with_selenium(url)
        
        # Проверяем наличие данных
        from pathlib import Path
        
        has_organizations = organizations and len(organizations) > 0
        has_individuals = individuals and len(individuals) > 0
        
        # Определяем пути к выходным файлам
        org_output_file = self.output_file.replace('.csv', '_организации.csv')
        ind_output_file = self.output_file.replace('.csv', '_физические_лица.csv')
        
        # Если данных нет вообще
        if not has_organizations and not has_individuals:
            self.logger.error(f"⚠️  ВНИМАНИЕ: Парсер {self.name} не собрал данных с сайта {url}")
            self.logger.warning("Существующие CSV файлы не будут перезаписаны пустыми данными")
            
            # Проверяем существующие файлы
            if Path(org_output_file).exists():
                self.logger.info(f"Файл {org_output_file} существует и будет сохранен")
            if Path(ind_output_file).exists():
                self.logger.info(f"Файл {ind_output_file} существует и будет сохранен")
            
            return
        
        # Сохраняем организации в отдельный CSV только если есть данные
        if has_organizations:
            self.save_to_csv(organizations, org_output_file)
            self.logger.info(f"✓ Сохранено {len(organizations)} организаций в {org_output_file}")
        else:
            if Path(org_output_file).exists():
                self.logger.warning(f"⚠️  Данные об организациях не найдены на сайте. Существующий файл {org_output_file} НЕ будет перезаписан")
            else:
                self.logger.warning(f"⚠️  Данные об организациях не найдены на сайте. Файл {org_output_file} не будет создан")
        
        # Сохраняем физические лица в отдельный CSV только если есть данные
        if has_individuals:
            self.save_to_csv(individuals, ind_output_file)
            self.logger.info(f"✓ Сохранено {len(individuals)} физических лиц в {ind_output_file}")
        else:
            if Path(ind_output_file).exists():
                self.logger.warning(f"⚠️  Данные о физических лицах не найдены на сайте. Существующий файл {ind_output_file} НЕ будет перезаписан")
            else:
                self.logger.warning(f"⚠️  Данные о физических лицах не найдены на сайте. Файл {ind_output_file} не будет создан")
    
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

