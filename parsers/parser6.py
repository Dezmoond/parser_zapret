"""
Парсер 6 - пример реализации универсального парсера
"""
import logging
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from .base_parser import BaseParser


class Parser6(BaseParser):
    """Парсер 6 - универсальный парсер с автоматическим определением типа контента"""
    
    def parse(self, response: requests.Response) -> List[Dict[str, Any]]:
        """
        Парсинг ответа с автоматическим определением типа контента
        
        Args:
            response: Response объект
            
        Returns:
            Список словарей с данными
        """
        data = []
        content_type = response.headers.get('Content-Type', '').lower()
        
        try:
            # Определяем тип контента и парсим соответственно
            if 'application/json' in content_type:
                json_data = response.json()
                if isinstance(json_data, list):
                    for item in json_data:
                        if isinstance(item, dict):
                            item['source'] = 'parser6'
                            item['content_type'] = 'json'
                            data.append(item)
                elif isinstance(json_data, dict):
                    json_data['source'] = 'parser6'
                    json_data['content_type'] = 'json'
                    data.append(json_data)
            
            elif 'application/xml' in content_type or 'text/xml' in content_type:
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.content)
                data.append({
                    'root_tag': root.tag,
                    'url': response.url,
                    'content_type': 'xml',
                    'source': 'parser6'
                })
            
            elif 'text/html' in content_type:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Извлекаем мета-информацию
                title = soup.find('title')
                meta_description = soup.find('meta', attrs={'name': 'description'})
                
                record = {
                    'url': response.url,
                    'title': title.get_text(strip=True) if title else '',
                    'description': meta_description.get('content', '') if meta_description else '',
                    'content_type': 'html',
                    'source': 'parser6'
                }
                
                # Извлекаем все ссылки
                links = soup.find_all('a', href=True)
                record['links_count'] = len(links)
                
                data.append(record)
            
            else:
                # Для других типов контента создаем базовую запись
                data.append({
                    'url': response.url,
                    'content_type': content_type,
                    'content_length': len(response.content),
                    'source': 'parser6'
                })
                
        except Exception as e:
            logging.error(f"Ошибка в Parser6: {e}")
            data.append({
                'url': response.url,
                'error': str(e),
                'content_type': content_type,
                'source': 'parser6'
            })
        
        return data


