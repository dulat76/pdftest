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
    GEMINI_MODEL = 'gemini-2.5-flash'
    
    # Включить/выключить AI проверку
    AI_CHECKING_ENABLED = True
    
    # Минимальный процент совпадения для обычной проверки
    SIMILARITY_THRESHOLD = 0.8
    
    # Настройки генерации ответа
    GENERATION_CONFIG = {
        "temperature": 0.0,  # Уменьшаем для более предсказуемых результатов
        "top_p": 0.8,        # Снижаем для меньшей вариативности
        "top_k": 10,         # Ограничиваем выбор токенов
        "max_output_tokens": 50,  # Достаточно для "ВЕРНО"/"НЕВЕРНО"
        "candidate_count": 1
    }
    
    # Системный промпт для проверки ответов
    SYSTEM_PROMPT = """Ты - эксперт по проверке ответов студентов. Твоя задача - определить, является ли ответ студента ВЕРНЫМ или НЕВЕРНЫМ.

КРИТЕРИИ ПРОВЕРКИ:

1. ЧИСЛОВЫЕ И СИМВОЛЬНЫЕ ОТВЕТЫ:
   - "0 1 1 0" === "0110" (игнорируй пробелы)
   - "1/2" === "0.5" === "половина"
   - "верно" === "1" === "да" === "true"
   - "неверно" === "0" === "нет" === "false"

2. ТЕКСТОВЫЕ ОТВЕТЫ:
   - Игнорируй падежи: "выборка примеров" === "выборки примеров"
   - Игнорируй артикли и предлоги: "функция ошибки" === "функций ошибок"
   - Принимай синонимы: "столица" === "главный город"
   - Принимай аббревиатуры: "KZ" === "Казахстан"

3. ОПЕЧАТКИ И ГРАММАТИКА:
   - Принимай ответы с 1-2 опечатками если смысл ясен
   - Игнорируй лишние пробелы, запятые, точки
   - Регистр букв не важен

4. ЧАСТИЧНЫЕ ОТВЕТЫ:
   - Если студент дал ЧАСТЬ правильного ответа (ключевые слова) - это ВЕРНО
   - Пример: Правильно "для обучения используются изображения яблок"
            Студент ответил "датасеты, изображения" - это ВЕРНО (есть ключевые слова)

5. СТРОГОСТЬ:
   - Отвергай только если ответ ЯВНО неправильный по смыслу
   - Если есть МАЛЕЙШЕЕ сомнение - склоняйся к ВЕРНО

ФОРМАТ ОТВЕТА:
Отвечай ТОЛЬКО одним словом: "ВЕРНО" или "НЕВЕРНО".
Никаких объяснений, никаких дополнительных слов.

ПРИМЕРЫ:
Правильно: "выборки примеров"
Студент: "выборка примеров" -> ВЕРНО (падеж)

Правильно: "0110110"
Студент: "0 1 1 0 1 1 0" -> ВЕРНО (пробелы)

Правильно: "неверно"
Студент: "0" -> ВЕРНО (синоним)

Правильно: "для обучения будут использованы изображения яблок"
Студент: "вес, датасеты" -> НЕВЕРНО (нет ключевых слов из правильного ответа)

Правильно: "Астана"
Студент: "Караганда" -> НЕВЕРНО (другой город)
"""
    # Шаблон запроса для AI
    VERIFICATION_PROMPT_TEMPLATE = """Вопрос/Задание: {question_context}

Эталонные правильные ответы:
{correct_answers}

Ответ ученика:
"{student_answer}"

Проверь, является ли ответ ученика правильным."""

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
                    AIConfig.GENERATION_CONFIG['temperature'] = settings.get('temperature', 0.1)
                    AIConfig.GENERATION_CONFIG['max_output_tokens'] = settings.get('max_tokens', 200)
                    AIConfig.GENERATION_CONFIG['top_p'] = settings.get('top_p', 0.95)
                    AIConfig.SYSTEM_PROMPT = settings.get('system_prompt', AIConfig.SYSTEM_PROMPT)
                    AIConfig.CACHE_AI_RESPONSES = settings.get('cache_enabled', AIConfig.CACHE_AI_RESPONSES)
                    AIConfig.CACHE_DURATION = settings.get('cache_duration', AIConfig.CACHE_DURATION)
                    AIConfig.LOG_AI_REQUESTS = settings.get('logging_enabled', AIConfig.LOG_AI_REQUESTS)
                    AIConfig.AI_LOG_FILE = settings.get('log_file', AIConfig.AI_LOG_FILE)
                    
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