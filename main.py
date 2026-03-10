"""
Главный файл для запуска всех парсеров
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Импорты парсеров
from parsers.parser1 import Parser1
from parsers.parser2 import Parser2
from parsers.parser3 import Parser3
from parsers.parser4 import Parser4
from parsers.parser5 import Parser5
from parsers.parser6 import Parser6
from parsers.parser7 import Parser7


# Маппинг имен парсеров на классы
PARSER_CLASSES = {
    'parser1': Parser1,
    'parser2': Parser2,
    'parser3': Parser3,
    'parser4': Parser4,
    'parser5': Parser5,
    'parser6': Parser6,
    'parser7': Parser7,
}


def load_config(config_path: str = 'config.json') -> Dict[str, Any]:
    """
    Загрузка конфигурации из файла
    
    Args:
        config_path: Путь к файлу конфигурации
        
    Returns:
        Словарь с конфигурацией
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Файл конфигурации {config_path} не найден")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка парсинга JSON в {config_path}: {e}")
        sys.exit(1)


def run_parser(parser_name: str, parser_config: Dict[str, Any], global_settings: Dict[str, Any]) -> None:
    """
    Запуск одного парсера
    
    Args:
        parser_name: Имя парсера
        parser_config: Конфигурация парсера
        global_settings: Глобальные настройки
    """
    if parser_name not in PARSER_CLASSES:
        logging.warning(f"Парсер {parser_name} не найден")
        return
    
    # Объединяем: глобальные настройки + переопределение из парсера
    config = {**global_settings, **parser_config}
    
    # Создаем экземпляр парсера
    parser_class = PARSER_CLASSES[parser_name]
    parser = parser_class(config)
    
    # Запускаем парсер
    try:
        parser.run()
    except Exception as e:
        logging.error(f"Критическая ошибка при работе парсера {parser_name}: {e}")


def main():
    """Главная функция"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('parsers.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Запуск системы парсеров")
    
    # Загружаем конфигурацию
    config = load_config()
    
    # Получаем настройки
    global_settings = config.get('settings', {})
    parsers_config = config.get('parsers', {})
    
    # Запускаем каждый парсер
    for parser_name, parser_config in parsers_config.items():
        logger.info(f"Обработка парсера: {parser_name}")
        run_parser(parser_name, parser_config, global_settings)
        logger.info(f"Парсер {parser_name} завершен")
    
    logger.info("Все парсеры завершили работу")


if __name__ == '__main__':
    main()


