"""Utility functions for the PDF testing application."""
import re
import secrets
import string
from typing import Optional


# Транслитерация кириллицы в латиницу
CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}


def transliterate(text: str) -> str:
    """
    Transliterate Cyrillic text to Latin.
    
    Args:
        text: Text to transliterate
        
    Returns:
        Transliterated text
    """
    result = []
    for char in text:
        if char in CYRILLIC_TO_LATIN:
            result.append(CYRILLIC_TO_LATIN[char])
        else:
            result.append(char)
    return ''.join(result)


def generate_topic_slug(topic: str) -> str:
    """
    Generate URL-friendly slug from topic name.
    
    Args:
        topic: Topic name (can be in Cyrillic)
        
    Returns:
        URL-friendly slug (lowercase, with hyphens)
    
    Example:
        "Математика 5 класс" -> "matematika-5-klass"
    """
    # Транслитерация
    slug = transliterate(topic)
    
    # Приведение к lowercase
    slug = slug.lower()
    
    # Замена пробелов и спецсимволов на дефисы
    slug = re.sub(r'[^\w\s-]', '', slug)  # Удаление спецсимволов
    slug = re.sub(r'[\s_]+', '-', slug)  # Замена пробелов и подчеркиваний на дефисы
    
    # Удаление множественных дефисов
    slug = re.sub(r'-+', '-', slug)
    
    # Удаление дефисов в начале и конце
    slug = slug.strip('-')
    
    # Ограничение длины
    if len(slug) > 100:
        slug = slug[:100].rstrip('-')
    
    return slug


def generate_username(city_code: str, school_code: str) -> str:
    """
    Generate username from city and school codes.
    DEPRECATED: Используйте generate_username_from_name() для новых учителей.
    
    Args:
        city_code: City code (e.g., "ast")
        school_code: School code (e.g., "sch59")
        
    Returns:
        Username (e.g., "astsch59")
    """
    # Приведение к lowercase и удаление пробелов
    city_code = city_code.strip().lower()
    school_code = school_code.strip().lower()
    
    # Удаление недопустимых символов
    city_code = re.sub(r'[^a-z0-9]', '', city_code)
    school_code = re.sub(r'[^a-z0-9]', '', school_code)
    
    # Объединение
    username = city_code + school_code
    
    return username


def generate_username_from_name(last_name: str, first_name: str, existing_usernames: Optional[list] = None) -> str:
    """
    Generate username from teacher's name (lastname.firstname format).
    
    Args:
        last_name: Teacher's last name
        first_name: Teacher's first name
        existing_usernames: List of existing usernames to avoid duplicates (optional)
        
    Returns:
        Username in format "lastname.firstname" or "lastname.firstname.2" if duplicate
    """
    # Транслитерация
    last_name_lat = transliterate(last_name.strip())
    first_name_lat = transliterate(first_name.strip())
    
    # Приведение к lowercase
    last_name_lat = last_name_lat.lower()
    first_name_lat = first_name_lat.lower()
    
    # Удаление недопустимых символов (оставляем только буквы, цифры, точки, дефисы, подчеркивания)
    last_name_lat = re.sub(r'[^a-z0-9._-]', '', last_name_lat)
    first_name_lat = re.sub(r'[^a-z0-9._-]', '', first_name_lat)
    
    # Удаление точек и дефисов в начале/конце
    last_name_lat = last_name_lat.strip('._-')
    first_name_lat = first_name_lat.strip('._-')
    
    # Базовая генерация логина
    base_username = f"{last_name_lat}.{first_name_lat}"
    
    # Если список существующих логинов не передан, возвращаем базовый
    if existing_usernames is None:
        return base_username
    
    # Проверка уникальности и добавление номера при необходимости
    username = base_username
    counter = 1
    while username in existing_usernames:
        counter += 1
        username = f"{base_username}.{counter}"
    
    return username


def generate_random_password(length: int = 12) -> str:
    """
    Generate a random password.
    
    Args:
        length: Password length (default: 12)
        
    Returns:
        Random password
    """
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def sanitize_username(username: str) -> str:
    """
    Sanitize username to ensure it's safe for use.
    
    Args:
        username: Username to sanitize
        
    Returns:
        Sanitized username
    """
    # Приведение к lowercase
    username = username.lower()
    
    # Удаление недопустимых символов
    username = re.sub(r'[^a-z0-9]', '', username)
    
    return username




