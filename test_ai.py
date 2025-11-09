"""
Скрипт для тестирования AI проверки ответов
"""
from ai_checker_0 import get_ai_checker
from ai_config import AIConfig
import sys

def print_result(test_name, result):
    """Красивый вывод результата теста"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")
    print(f"✅ Правильно: {result['is_correct']}")
    print(f"🤖 Проверено AI: {result.get('checked_by_ai', False)}")
    
    if result.get('ai_confidence'):
        confidence = result['ai_confidence'] * 100
        print(f"📊 Уверенность: {confidence:.1f}%")
    
    if result.get('method'):
        print(f"🔍 Метод: {result['method']}")
    
    if result.get('error'):
        print(f"❌ Ошибка: {result['error']}")
    
    print(f"{'='*60}\n")

def run_tests():
    """Запуск набора тестов"""
    print("🚀 Начало тестирования AI Checker")
    print(f"📌 API Key настроен: {'Да' if AIConfig.GEMINI_API_KEY != 'YOUR_API_KEY_HERE' else 'Нет'}")
    print(f"📌 AI проверка включена: {'Да' if AIConfig.AI_CHECKING_ENABLED else 'Нет'}")
    print(f"📌 Порог схожести: {AIConfig.SIMILARITY_THRESHOLD * 100}%\n")
    
    try:
        checker = get_ai_checker()
        print("✅ AI Checker успешно инициализирован\n")
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        sys.exit(1)
    
    # ========== ТЕСТЫ ==========
    
    # Тест 1: Точное совпадение (без AI)
    result = checker.check_answer(
        student_answer="Москва",
        correct_variants=["Москва", "москва", "МОСКВА"]
    )
    print_result("Тест 1: Точное совпадение", result)
    
    # Тест 2: Регистронезависимое совпадение
    result = checker.check_answer(
        student_answer="мОсКвА",
        correct_variants=["Москва"]
    )
    print_result("Тест 2: Разный регистр", result)
    
    # Тест 3: Синоним (должен использовать AI)
    result = checker.check_answer(
        student_answer="столица России",
        correct_variants=["Москва"],
        question_context="Столица Российской Федерации"
    )
    print_result("Тест 3: Синоним (AI)", result)
    
    # Тест 4: Опечатка
    result = checker.check_answer(
        student_answer="Маскава",
        correct_variants=["Москва"]
    )
    print_result("Тест 4: Опечатка", result)
    
    # Тест 5: Химическая формула
    result = checker.check_answer(
        student_answer="вода",
        correct_variants=["H2O", "h2o"],
        question_context="Химическая формула воды"
    )
    print_result("Тест 5: Синоним (вода = H2O)", result)
    
    # Тест 6: Математическая эквивалентность
    result = checker.check_answer(
        student_answer="0.5",
        correct_variants=["1/2", "одна второя"],
        question_context="Дробь одна вторая"
    )
    print_result("Тест 6: Математика (0.5 = 1/2)", result)
    
    # Тест 7: Неправильный ответ
    result = checker.check_answer(
        student_answer="Санкт-Петербург",
        correct_variants=["Москва"]
    )
    print_result("Тест 7: Неправильный ответ", result)
    
    # Тест 8: Перефразирование
    result = checker.check_answer(
        student_answer="процесс превращения света в энергию растениями",
        correct_variants=["Фотосинтез", "фотосинтез"],
        question_context="Процесс питания растений светом"
    )
    print_result("Тест 8: Перефразирование", result)
    
    # Тест 9: Исторические даты
    result = checker.check_answer(
        student_answer="конец второй мировой войны",
        correct_variants=["1945"],
        question_context="Год окончания Второй мировой войны"
    )
    print_result("Тест 9: Дата = событие", result)
    
    # Тест 10: Сокращение
    result = checker.check_answer(
        student_answer="РФ",
        correct_variants=["Российская Федерация"],
        question_context="Официальное название России"
    )
    print_result("Тест 10: Сокращение", result)
    
    print("\n" + "="*60)
    print("✅ Все тесты завершены!")
    print("="*60)

if __name__ == "__main__":
    run_tests()