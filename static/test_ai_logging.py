"""
Тестовый скрипт для проверки AI логирования и работы проверки
Запустите этот файл отдельно для диагностики проблем
"""

import os
import sys
import json
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ai_config():
    """Тест загрузки конфигурации AI"""
    print("=" * 60)
    print("ТЕСТ 1: Проверка конфигурации AI")
    print("=" * 60)
    
    try:
        from ai_config import AIConfig
        
        print(f"✅ AI модуль загружен успешно")
        print(f"   API Key настроен: {AIConfig.GEMINI_API_KEY != 'YOUR_API_KEY_HERE'}")
        print(f"   Модель: {AIConfig.GEMINI_MODEL}")
        print(f"   AI проверка включена: {AIConfig.AI_CHECKING_ENABLED}")
        print(f"   Логирование включено: {AIConfig.LOG_AI_REQUESTS}")
        print(f"   Файл логов: {AIConfig.AI_LOG_FILE}")
        
        # Проверяем директорию для логов
        log_dir = os.path.dirname(AIConfig.AI_LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            print(f"✅ Создана директория для логов: {log_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False


def test_ai_checker():
    """Тест инициализации AI checker"""
    print("\n" + "=" * 60)
    print("ТЕСТ 2: Инициализация AI Checker")
    print("=" * 60)
    
    try:
        from ai_checker_0 import AIAnswerChecker
        from ai_config import AIConfig
        
        checker = AIAnswerChecker(provider="gemini", api_key=AIConfig.GEMINI_API_KEY)
        print(f"✅ AI Checker создан успешно")
        print(f"   Провайдер: {checker.provider}")
        print(f"   API Key присутствует: {bool(checker.api_key)}")
        
        return checker
        
    except Exception as e:
        print(f"❌ Ошибка создания AI Checker: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_ai_check(checker):
    """Тест проверки ответа через AI"""
    print("\n" + "=" * 60)
    print("ТЕСТ 3: Проверка ответа через AI")
    print("=" * 60)
    
    if not checker:
        print("❌ AI Checker не инициализирован")
        return False
    
    test_cases = [
        {
            "student_answer": "Астана",
            "correct_variants": ["Астана", "астана"],
            "context": "Столица Казахстана"
        },
        {
            "student_answer": "столица Казахстана",
            "correct_variants": ["Астана"],
            "context": "Главный город страны"
        },
        {
            "student_answer": "Караганда",
            "correct_variants": ["Астана"],
            "context": "Столица Казахстана"
        }
    ]
    
    from ai_config import AIConfig
    from dataclasses import asdict
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nТест {i}:")
        print(f"  Ответ студента: '{test['student_answer']}'")
        print(f"  Правильные ответы: {test['correct_variants']}")
        
        try:
            result = checker.check_answer(
                student_answer=test['student_answer'],
                correct_variants=test['correct_variants'],
                question_context=test['context'],
                system_prompt=AIConfig.SYSTEM_PROMPT,
                model_name=AIConfig.GEMINI_MODEL
            )
            
            result_dict = asdict(result)
            
            print(f"  ✅ Результат: {'ВЕРНО' if result.is_correct else 'НЕВЕРНО'}")
            print(f"  Уверенность: {result.confidence * 100:.1f}%")
            print(f"  Объяснение: {result.explanation}")
            print(f"  Провайдер: {result.ai_provider}")
            
            # Тест логирования
            if AIConfig.LOG_AI_REQUESTS:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "test_case": i,
                    "student_answer": test['student_answer'],
                    "correct_variants": test['correct_variants'],
                    "result": result_dict,
                    "success": True
                }
                
                log_file = AIConfig.AI_LOG_FILE
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
                print(f"  📝 Лог записан в {log_file}")
            
        except Exception as e:
            print(f"  ❌ Ошибка проверки: {e}")
            import traceback
            traceback.print_exc()
    
    return True


def check_log_file():
    """Проверка файла логов"""
    print("\n" + "=" * 60)
    print("ТЕСТ 4: Проверка файла логов")
    print("=" * 60)
    
    try:
        from ai_config import AIConfig
        
        log_file = AIConfig.AI_LOG_FILE
        
        if not os.path.exists(log_file):
            print(f"⚠️  Файл логов не существует: {log_file}")
            return False
        
        print(f"✅ Файл логов найден: {log_file}")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"   Количество записей: {len(lines)}")
        
        if lines:
            print(f"\n   Последние 3 записи:")
            for line in lines[-3:]:
                try:
                    entry = json.loads(line)
                    print(f"   - {entry.get('timestamp', 'N/A')}: {entry.get('student_answer', 'N/A')}")
                except:
                    print(f"   - [Некорректная запись]")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки логов: {e}")
        return False


def main():
    """Главная функция тестирования"""
    print("\n" + "█" * 60)
    print("█" + " " * 58 + "█")
    print("█" + "  ТЕСТИРОВАНИЕ AI ПРОВЕРКИ И ЛОГИРОВАНИЯ".center(58) + "█")
    print("█" + " " * 58 + "█")
    print("█" * 60 + "\n")
    
    # Тест 1: Конфигурация
    if not test_ai_config():
        print("\n❌ Тесты остановлены из-за ошибки конфигурации")
        return
    
    # Тест 2: Инициализация checker
    checker = test_ai_checker()
    if not checker:
        print("\n❌ Тесты остановлены из-за ошибки инициализации")
        return
    
    # Тест 3: Проверка ответов
    test_ai_check(checker)
    
    # Тест 4: Проверка логов
    check_log_file()
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    print("\nРекомендации:")
    print("1. Проверьте, что GEMINI_API_KEY установлен корректно")
    print("2. Убедитесь, что директория 'logs/' существует и доступна для записи")
    print("3. Проверьте логи в файле для отладки проблем")
    print("4. Если AI не работает, проверьте квоты API в Google Cloud Console")


if __name__ == "__main__":
    main()