"""Input validation utilities for the PDF testing application."""
import re
from typing import Any, Dict, List, Optional
from werkzeug.datastructures import FileStorage


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_file_upload(file: FileStorage, allowed_extensions: set, max_size_mb: int = 16) -> None:
    """
    Validate uploaded file.
    
    Args:
        file: Uploaded file object
        allowed_extensions: Set of allowed file extensions
        max_size_mb: Maximum file size in megabytes
        
    Raises:
        ValidationError: If validation fails
    """
    if not file or file.filename == '':
        raise ValidationError("Файл не выбран")
    
    # Check extension
    if '.' not in file.filename:
        raise ValidationError("Файл должен иметь расширение")
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Неподдерживаемый формат файла. Разрешены: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if size > max_size_bytes:
        raise ValidationError(f"Файл слишком большой. Максимум: {max_size_mb}MB")


def validate_template_data(data: Dict[str, Any]) -> None:
    """
    Validate template JSON data.
    
    Args:
        data: Template data dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    required_fields = ['name', 'fields']
    
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Отсутствует обязательное поле: {field}")
    
    # Validate name
    if not isinstance(data['name'], str) or len(data['name'].strip()) == 0:
        raise ValidationError("Название шаблона не может быть пустым")
    
    if len(data['name']) > 200:
        raise ValidationError("Название шаблона слишком длинное (максимум 200 символов)")
    
    # Validate fields
    if not isinstance(data['fields'], list):
        raise ValidationError("Поля должны быть списком")
    
    if len(data['fields']) == 0:
        raise ValidationError("Шаблон должен содержать хотя бы одно поле")
    
    if len(data['fields']) > 100:
        raise ValidationError("Слишком много полей (максимум 100)")
    
    # Validate each field
    for i, field in enumerate(data['fields']):
        validate_field(field, i)


def validate_field(field: Dict[str, Any], index: int) -> None:
    """
    Validate a single field in template.
    
    Args:
        field: Field data dictionary
        index: Field index for error messages
        
    Raises:
        ValidationError: If validation fails
    """
    required = ['id', 'variants']
    
    for req in required:
        if req not in field:
            raise ValidationError(f"Поле {index + 1}: отсутствует {req}")
    
    # Validate ID
    if not isinstance(field['id'], str) or not field['id']:
        raise ValidationError(f"Поле {index + 1}: некорректный ID")
    
    # Validate variants
    if not isinstance(field['variants'], list):
        raise ValidationError(f"Поле {index + 1}: варианты должны быть списком")
    
    if len(field['variants']) == 0:
        raise ValidationError(f"Поле {index + 1}: должен быть хотя бы один правильный вариант")
    
    for variant in field['variants']:
        if not isinstance(variant, str):
            raise ValidationError(f"Поле {index + 1}: все варианты должны быть строками")


def validate_student_info(data: Dict[str, Any]) -> None:
    """
    Validate student information.
    
    Args:
        data: Student info dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    required = ['name', 'class']
    
    for field in required:
        if field not in data or not data[field]:
            raise ValidationError(f"Не указано: {field}")
    
    # Validate name
    name = data['name'].strip()
    if len(name) < 2:
        raise ValidationError("ФИО слишком короткое")
    
    if len(name) > 100:
        raise ValidationError("ФИО слишком длинное")
    
    # Basic name validation (letters, spaces, hyphens)
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-]+$', name):
        raise ValidationError("ФИО содержит недопустимые символы")
    
    # Validate class
    class_name = data['class'].strip()
    if len(class_name) > 20:
        raise ValidationError("Название класса слишком длинное")


def validate_answers(answers: Dict[str, str], max_answer_length: int = 500) -> None:
    """
    Validate student answers.
    
    Args:
        answers: Dictionary of field_id -> answer
        max_answer_length: Maximum length for a single answer
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(answers, dict):
        raise ValidationError("Ответы должны быть словарём")
    
    for field_id, answer in answers.items():
        if not isinstance(field_id, str):
            raise ValidationError("ID поля должен быть строкой")
        
        if not isinstance(answer, str):
            raise ValidationError(f"Ответ для поля {field_id} должен быть строкой")
        
        if len(answer) > max_answer_length:
            raise ValidationError(
                f"Ответ для поля {field_id} слишком длинный (максимум {max_answer_length} символов)"
            )


def validate_google_sheets_url(url: str) -> None:
    """
    Validate Google Sheets URL.
    
    Args:
        url: Google Sheets URL
        
    Raises:
        ValidationError: If validation fails
    """
    if not url:
        return  # URL is optional
    
    pattern = r'https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9_-]+(/.*)?'
    if not re.match(pattern, url):
        raise ValidationError("Некорректная ссылка на Google Таблицу")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.replace('\\', '/').split('/')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename


def validate_api_key(api_key: str, provider: str = "gemini") -> None:
    """
    Validate API key format.
    
    Args:
        api_key: API key to validate
        provider: API provider name
        
    Raises:
        ValidationError: If validation fails
    """
    if not api_key or api_key == 'YOUR_API_KEY_HERE':
        raise ValidationError(f"API ключ {provider} не настроен")
    
    # Basic length check
    if len(api_key) < 20:
        raise ValidationError(f"API ключ {provider} слишком короткий")
    
    # Gemini keys start with "AIza"
    if provider == "gemini" and not api_key.startswith("AIza"):
        raise ValidationError("Некорректный формат API ключа Gemini")


def validate_pagination(page: int, per_page: int, max_per_page: int = 100) -> tuple:
    """
    Validate pagination parameters.
    
    Args:
        page: Page number (1-indexed)
        per_page: Items per page
        max_per_page: Maximum items per page
        
    Returns:
        Tuple of (validated_page, validated_per_page)
        
    Raises:
        ValidationError: If validation fails
    """
    if page < 1:
        raise ValidationError("Номер страницы должен быть >= 1")
    
    if per_page < 1:
        raise ValidationError("Количество элементов на странице должно быть >= 1")
    
    if per_page > max_per_page:
        raise ValidationError(f"Максимум {max_per_page} элементов на странице")
    
    return page, per_page


def validate_teacher_data(data: Dict[str, Any]) -> None:
    """
    Validate teacher data.
    
    Args:
        data: Teacher data dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    required_fields = ['city', 'city_code', 'school', 'school_code']
    
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(f"Не указано обязательное поле: {field}")
    
    # Validate city
    city = data['city'].strip()
    if len(city) < 2:
        raise ValidationError("Название города слишком короткое")
    if len(city) > 100:
        raise ValidationError("Название города слишком длинное")
    
    # Validate city_code
    city_code = data['city_code'].strip().lower()
    if not validate_city_code(city_code):
        raise ValidationError("Некорректный код города")
    
    # Validate school
    school = data['school'].strip()
    if len(school) < 2:
        raise ValidationError("Название школы слишком короткое")
    if len(school) > 200:
        raise ValidationError("Название школы слишком длинное")
    
    # Validate school_code
    school_code = data['school_code'].strip().lower()
    if not validate_school_code(school_code):
        raise ValidationError("Некорректный код школы")
    
    # Validate password if provided
    if 'password' in data and data['password']:
        password = data['password']
        if len(password) < 8:
            raise ValidationError("Пароль должен содержать минимум 8 символов")
        if len(password) > 128:
            raise ValidationError("Пароль слишком длинный (максимум 128 символов)")


def validate_city_code(code: str) -> bool:
    """
    Validate city code format.
    
    Args:
        code: City code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not code:
        return False
    
    # Only lowercase letters and numbers, 2-20 characters
    if not re.match(r'^[a-z0-9]{2,20}$', code):
        return False
    
    return True


def validate_school_code(code: str) -> bool:
    """
    Validate school code format.
    
    Args:
        code: School code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not code:
        return False
    
    # Only lowercase letters and numbers, 2-50 characters
    if not re.match(r'^[a-z0-9]{2,50}$', code):
        return False
    
    return True


def validate_username_format(username: str) -> bool:
    """
    Validate username format.
    
    Args:
        username: Username to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not username:
        return False
    
    # Only lowercase letters and numbers, 3-100 characters
    if not re.match(r'^[a-z0-9]{3,100}$', username):
        return False
    
    return True


def validate_topic_slug(slug: str) -> None:
    """
    Validate topic slug format.
    
    Args:
        slug: Topic slug to validate
        
    Raises:
        ValidationError: If validation fails
    """
    if not slug:
        raise ValidationError("Slug темы не может быть пустым")
    
    if len(slug) > 100:
        raise ValidationError("Slug темы слишком длинный (максимум 100 символов)")
    
    # Only lowercase letters, numbers, and hyphens
    if not re.match(r'^[a-z0-9\-]+$', slug):
        raise ValidationError("Slug темы может содержать только латинские буквы, цифры и дефисы")
    
    # Cannot start or end with hyphen
    if slug.startswith('-') or slug.endswith('-'):
        raise ValidationError("Slug темы не может начинаться или заканчиваться дефисом")
    
    # Cannot have consecutive hyphens
    if '--' in slug:
        raise ValidationError("Slug темы не может содержать подряд идущие дефисы")


def validate_topic(topic: str) -> None:
    """
    Validate topic name.
    
    Args:
        topic: Topic name to validate
        
    Raises:
        ValidationError: If validation fails
    """
    if not topic or not topic.strip():
        raise ValidationError("Тема теста не может быть пустой")
    
    topic = topic.strip()
    
    if len(topic) < 2:
        raise ValidationError("Тема теста слишком короткая")
    
    if len(topic) > 200:
        raise ValidationError("Тема теста слишком длинная (максимум 200 символов)")