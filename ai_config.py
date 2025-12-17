# -*- coding: utf-8 -*-
"""
Конфигурация для AI-проверки ответов
Настройки могут быть изменены через веб-интерфейс
"""
import os
import json

class AIConfig:
    """Настройки для интеграции с Gemini AI"""
    
    # Путь к файлу настроек
    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'ai_settings.json')
    
    # API ключ Gemini (лучше хранить в переменных окружения)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
    
    # Модель Gemini для использования
    GEMINI_MODEL = 'gemini-2.0-flash'
    
    # Включить/выключить AI проверку
    AI_CHECKING_ENABLED = True

    # Локальный скорер (fuzzy + semantic)
    LOCAL_SCORER_ENABLED = True

    # Пороги локального скорера
    FUZZY_STRICT = 95
    FUZZY_SOFT = 90
    SEM_THRESHOLD = 0.75
    EMBED_MAX_TOKENS = 512
    
    # Минимальный процент совпадения для обычной проверки
    SIMILARITY_THRESHOLD = 0.8
    
    # Настройки генерации ответа
    GENERATION_CONFIG = {
        "temperature": 0.0,  # Уменьшаем для более предсказуемых результатов
        "top_p": 0.8,        # Снижаем для меньшей вариативности
        "top_k": 10,         # Ограничиваем выбор токенов
        "max_output_tokens": 100,  # Достаточно для JSON
        "candidate_count": 1
    }
    
    # ВАЖНО: Этот промпт НЕ используется в _build_gemini_request_body
    # Оставлен для совместимости с веб-интерфейсом
    SYSTEM_PROMPT = """Ты - эксперт по проверке ответов студентов. 
Отвечай СТРОГО в формате JSON: {{"is_correct": true/false, "confidence": число от 0 до 100, "explanation": "краткое пояснение"}}"""
    
    # Этот промпт тоже НЕ используется напрямую в новой версии
    # Промпт теперь встроен в _build_gemini_request_body для избежания проблем с .format()
    VERIFICATION_PROMPT_TEMPLATE = """Проверь ответ студента.
Контекст: {{question_context}}
Правильные ответы: {{correct_answers}}
Ответ студента: {{student_answer}}
Ответь в JSON формате."""
    
    # Настройки логирования AI запросов
    LOG_AI_REQUESTS = True
    AI_LOG_FILE = 'logs/ai_checks.log'
    
    # Таймауты и повторные попытки
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 2
    
    # Кэширование AI ответов
    CACHE_AI_RESPONSES = True
    CACHE_DURATION = 3600

    @staticmethod
    def load_from_file():
        """Загрузка настроек из файла"""
        if os.path.exists(AIConfig.SETTINGS_FILE):
            try:
                with open(AIConfig.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                    # Обновляем настройки класса
                    AIConfig.AI_CHECKING_ENABLED = settings.get('ai_enabled', AIConfig.AI_CHECKING_ENABLED)
                    AIConfig.SIMILARITY_THRESHOLD = settings.get('similarity_threshold', AIConfig.SIMILARITY_THRESHOLD)
                    
                    if settings.get('api_key') and not settings['api_key'].startswith('***'):
                        AIConfig.GEMINI_API_KEY = settings['api_key']
                    
                    AIConfig.GEMINI_MODEL = settings.get('ai_model', AIConfig.GEMINI_MODEL)
                    AIConfig.GENERATION_CONFIG['temperature'] = settings.get('temperature', 0.0)
                    AIConfig.GENERATION_CONFIG['max_output_tokens'] = settings.get('max_tokens', 100)
                    AIConfig.GENERATION_CONFIG['top_p'] = settings.get('top_p', 0.8)
                    
                    # Загружаем промпты, но они не используются в новой версии
                    if 'system_prompt' in settings:
                        AIConfig.SYSTEM_PROMPT = settings['system_prompt']
                    
                    AIConfig.CACHE_AI_RESPONSES = settings.get('cache_enabled', AIConfig.CACHE_AI_RESPONSES)
                    AIConfig.CACHE_DURATION = settings.get('cache_duration', AIConfig.CACHE_DURATION)
                    AIConfig.LOG_AI_REQUESTS = settings.get('logging_enabled', AIConfig.LOG_AI_REQUESTS)
                    AIConfig.AI_LOG_FILE = settings.get('log_file', AIConfig.AI_LOG_FILE)

                    AIConfig.LOCAL_SCORER_ENABLED = settings.get('local_scorer_enabled', AIConfig.LOCAL_SCORER_ENABLED)
                    AIConfig.FUZZY_STRICT = settings.get('fuzzy_strict', AIConfig.FUZZY_STRICT)
                    AIConfig.FUZZY_SOFT = settings.get('fuzzy_soft', AIConfig.FUZZY_SOFT)
                    AIConfig.SEM_THRESHOLD = settings.get('sem_threshold', AIConfig.SEM_THRESHOLD)
                    AIConfig.EMBED_MAX_TOKENS = settings.get('embed_max_tokens', AIConfig.EMBED_MAX_TOKENS)
                    
                    return True
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
                return False
        return False

    @staticmethod
    def save_to_file(settings):
        """Сохранение настроек в файл"""
        try:
            with open(AIConfig.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False

    @staticmethod
    def validate_config():
        """Проверка корректности конфигурации"""
        if AIConfig.AI_CHECKING_ENABLED:
            if AIConfig.GEMINI_API_KEY == 'YOUR_API_KEY_HERE':
                # Пытаемся загрузить из переменной окружения
                env_key = os.getenv('GEMINI_API_KEY')
                if env_key and env_key != 'YOUR_API_KEY_HERE':
                    AIConfig.GEMINI_API_KEY = env_key
                else:
                    raise ValueError(
                        "Не установлен API ключ Gemini. "
                        "Установите переменную окружения GEMINI_API_KEY, "
                        "укажите ключ в ai_config.py или настройте через веб-интерфейс (/ai-settings)"
                    )
        return True

# Пытаемся загрузить настройки при импорте
AIConfig.load_from_file()