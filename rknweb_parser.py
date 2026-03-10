"""
Отдельный парсер для сайта rknweb.ru - Реестр заблокированных сайтов
"""
import logging
import time
import csv
from typing import List, Dict, Any
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


class RKNWebParser:
    """Парсер реестра заблокированных сайтов rknweb.ru"""
    
    def __init__(self, output_file: str = "rknweb_blocked_sites.csv", headless: bool = True, 
                 start_page: int = 1, end_page: int = 48801):
        """
        Инициализация парсера
        
        Args:
            output_file: Путь к выходному CSV файлу
            headless: Запуск браузера в фоновом режиме
            start_page: Номер начальной страницы (по умолчанию 1)
            end_page: Номер конечной страницы (по умолчанию 48801)
        """
        self.output_file = output_file
        self.headless = headless
        self.base_url_template = "https://rknweb.ru/blocked/page/{}/"
        self.start_page = start_page
        self.end_page = end_page
        self.current_page = start_page
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Создание директории для выходных файлов
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.driver = None
        self.all_data = []
        self.row_number = 1  # Порядковый номер для CSV
        
        # При возобновлении — продолжаем нумерацию с последней записи в CSV
        if start_page > 1 and output_path.exists():
            self._init_row_number_from_csv()
    
    def _init_row_number_from_csv(self) -> None:
        """Читает последний порядковый номер из существующего CSV для продолжения нумерации"""
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line
                if last_line:
                    first_col = last_line.strip().split(',')[0]
                    try:
                        last_num = int(first_col)
                        self.row_number = last_num + 1
                        self.logger.info(f"Продолжение с порядкового номера {self.row_number}")
                    except ValueError:
                        pass
        except Exception as e:
            self.logger.warning(f"Не удалось прочитать CSV: {e}")
    
    def _init_selenium_driver(self):
        """Инициализация Selenium WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
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
            
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Selenium: {e}")
            self.logger.error("Убедитесь, что установлен ChromeDriver или установите webdriver-manager: pip install webdriver-manager")
            raise
    
    def _parse_table(self) -> List[Dict[str, Any]]:
        """
        Парсинг таблицы с текущей страницы
        
        Returns:
            Список словарей с данными из таблицы
        """
        page_data = []
        
        try:
            # Ждем загрузки таблицы
            wait = WebDriverWait(self.driver, 20)
            table_container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.rkn-items.js-rkn-result"))
            )
            
            # Находим все строки таблицы - используем правильный селектор
            rows = table_container.find_elements(By.CSS_SELECTOR, "div.item.js-open-detail")
            if not rows:
                # Альтернативный селектор
                rows = table_container.find_elements(By.CSS_SELECTOR, "div.item")
            
            self.logger.info(f"Найдено строк на странице: {len(rows)}")
            
            if len(rows) == 0:
                self.logger.warning("Строки таблицы не найдены! Проверьте селектор.")
                # Попробуем найти любые элементы item
                all_items = table_container.find_elements(By.CSS_SELECTOR, "div.item")
                self.logger.info(f"Найдено элементов div.item: {len(all_items)}")
            
            for idx, row in enumerate(rows):
                try:
                    # Извлекаем данные из строки по правильным селекторам
                    date = ""
                    resource = ""
                    ip = ""
                    requisites = ""
                    
                    # Дата - div.date
                    try:
                        date_elem = row.find_element(By.CSS_SELECTOR, "div.date")
                        date = date_elem.text.strip()
                    except NoSuchElementException:
                        self.logger.warning(f"Не найдена дата в строке {idx + 1}")
                    
                    # Ресурс - div.resurs, берем текст из первой ссылки (не кнопки "Подробнее")
                    try:
                        resurs_elem = row.find_element(By.CSS_SELECTOR, "div.resurs")
                        # Ищем все ссылки
                        links = resurs_elem.find_elements(By.TAG_NAME, "a")
                        # Берем первую ссылку, которая не является кнопкой "Подробнее"
                        for link in links:
                            link_class = link.get_attribute('class') or ''
                            if 'btn-detail' not in link_class:
                                resource = link.text.strip()
                                break
                        # Если не нашли подходящую ссылку, берем весь текст и убираем "Подробнее"
                        if not resource:
                            resource = resurs_elem.text.strip()
                            resource = resource.replace("Подробнее", "").strip()
                    except NoSuchElementException:
                        self.logger.warning(f"Не найден ресурс в строке {idx + 1}")
                    
                    # IP-адрес - div.ip-adres.scroll, может содержать несколько IP через <br>
                    try:
                        # Пробуем найти по полному селектору или только по классу ip-adres
                        try:
                            ip_elem = row.find_element(By.CSS_SELECTOR, "div.ip-adres.scroll")
                        except NoSuchElementException:
                            ip_elem = row.find_element(By.CSS_SELECTOR, "div.ip-adres")
                        # Получаем весь текст, заменяем переносы строк на пробелы
                        ip = ip_elem.text.strip().replace('\n', ' ').replace('\r', ' ')
                        # Убираем лишние пробелы
                        ip = ' '.join(ip.split())
                    except NoSuchElementException:
                        self.logger.warning(f"Не найден IP-адрес в строке {idx + 1}")
                    
                    # Реквизиты - div.authority
                    try:
                        authority_elem = row.find_element(By.CSS_SELECTOR, "div.authority")
                        requisites = authority_elem.text.strip()
                    except NoSuchElementException:
                        self.logger.warning(f"Не найдены реквизиты в строке {idx + 1}")
                    
                    # Создаем запись только если есть хотя бы дата или ресурс
                    if date or resource:
                        record = {
                            'Порядковый номер': self.row_number,
                            'Дата внесения в реестр': date,
                            'Внесённый ресурс': resource,
                            'IP-адрес': ip,
                            'Реквизиты основания внесения в реестр': requisites
                        }
                        
                        page_data.append(record)
                        self.row_number += 1
                    else:
                        self.logger.warning(f"Не удалось извлечь данные из строки {idx + 1}")
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка при обработке строки {idx + 1}: {e}")
                    continue
            
        except TimeoutException:
            self.logger.error("Таймаут при ожидании загрузки таблицы")
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге таблицы: {e}")
        
        return page_data
    
    def _get_page_url(self, page_number: int) -> str:
        """
        Получить URL для страницы с указанным номером
        
        Args:
            page_number: Номер страницы
            
        Returns:
            URL страницы
        """
        # Первая страница может быть без /page/1/
        if page_number == 1:
            return "https://rknweb.ru/blocked/"
        return self.base_url_template.format(page_number)
    
    def _go_to_page(self, page_number: int) -> bool:
        """
        Переход на страницу с указанным номером
        
        Args:
            page_number: Номер страницы
            
        Returns:
            True если переход успешен, False иначе
        """
        try:
            url = self._get_page_url(page_number)
            self.logger.info(f"Переход на страницу {page_number}: {url}")
            self.driver.get(url)
            
            # Ждем загрузки страницы
            time.sleep(2)
            
            # Ждем загрузки таблицы
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.rkn-items.js-rkn-result"))
                )
                self.logger.info(f"Страница {page_number} успешно загружена")
                return True
            except TimeoutException:
                self.logger.warning(f"Таблица не загрузилась на странице {page_number}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка при переходе на страницу {page_number}: {e}")
            return False
    
    def _save_to_csv(self, data: List[Dict[str, Any]]) -> None:
        """
        Сохранение данных в CSV файл
        
        Args:
            data: Список словарей с данными
        """
        if not data:
            self.logger.warning("Нет данных для сохранения")
            return
        
        # Определяем заголовки
        fieldnames = [
            'Порядковый номер',
            'Дата внесения в реестр',
            'Внесённый ресурс',
            'IP-адрес',
            'Реквизиты основания внесения в реестр'
        ]
        
        # Записываем данные в CSV
        file_exists = Path(self.output_file).exists()
        
        with open(self.output_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Записываем заголовок только если файл новый
            if not file_exists:
                writer.writeheader()
            
            writer.writerows(data)
        
        self.logger.info(f"Сохранено {len(data)} записей в {self.output_file}")
    
    def run(self) -> None:
        """Запуск парсера"""
        self.logger.info(f"Запуск парсера rknweb.ru (страницы {self.start_page} - {self.end_page})")
        
        try:
            # Инициализируем драйвер
            self.driver = self._init_selenium_driver()
            
            # Счетчики для статистики
            empty_pages_count = 0
            max_empty_pages = 10  # Если подряд 10 пустых страниц, останавливаемся
            
            # Перебираем страницы по номерам
            for page_num in range(self.start_page, self.end_page + 1):
                self.current_page = page_num
                
                # Переходим на страницу
                if not self._go_to_page(page_num):
                    self.logger.warning(f"Не удалось загрузить страницу {page_num}, пропускаем")
                    empty_pages_count += 1
                    if empty_pages_count >= max_empty_pages:
                        self.logger.info(f"Подряд {max_empty_pages} пустых страниц, останавливаем парсинг")
                        break
                    continue
                
                # Парсим таблицу на текущей странице
                self.logger.info(f"Парсинг страницы {page_num}")
                page_data = self._parse_table()
                
                if page_data:
                    # Сбрасываем счетчик пустых страниц при успешном парсинге
                    empty_pages_count = 0
                    
                    self.all_data.extend(page_data)
                    # Сохраняем данные после каждой страницы (на случай прерывания)
                    self._save_to_csv(page_data)
                    self.logger.info(f"Страница {page_num}: получено {len(page_data)} записей (всего: {len(self.all_data)})")
                else:
                    empty_pages_count += 1
                    self.logger.warning(f"Страница {page_num}: данные не найдены (пустых подряд: {empty_pages_count})")
                    
                    # Если подряд много пустых страниц, возможно достигнут конец
                    if empty_pages_count >= max_empty_pages:
                        self.logger.info(f"Подряд {max_empty_pages} пустых страниц, возможно достигнут конец данных")
                        break
                
                # Небольшая задержка между страницами (чтобы не перегружать сервер)
                time.sleep(1)
                
                # Логируем прогресс каждые 100 страниц
                if page_num % 100 == 0:
                    self.logger.info(f"Прогресс: обработано {page_num - self.start_page + 1} страниц из {self.end_page - self.start_page + 1}")
            
            self.logger.info(f"Парсинг завершен. Обработано страниц: {self.current_page - self.start_page + 1}, записей: {len(self.all_data)}")
            
        except KeyboardInterrupt:
            self.logger.info("Парсинг прерван пользователем")
        except Exception as e:
            self.logger.error(f"Критическая ошибка при работе парсера: {e}", exc_info=True)
        finally:
            # Закрываем браузер
            if self.driver:
                self.driver.quit()
                self.logger.info("Браузер закрыт")


def main():
    """Главная функция для запуска парсера"""
    parser = RKNWebParser(
        output_file="rknweb_blocked_sites.csv",
        headless=True,   # Установите False для видимого браузера
        start_page=20905,  # Продолжение со страницы 20905
        end_page=48801
    )
    parser.run()


if __name__ == '__main__':
    main()

