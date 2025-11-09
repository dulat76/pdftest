"""
Тестирование конкретных проблемных случаев из вашего примера
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_checker_0 import AIAnswerChecker
from ai_config import AIConfig
from dataclasses import asdict

def test_problematic_cases():
    """Тест конкретных проблемных случаев"""
    
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ПРОБЛЕМНЫХ СЛУЧАЕВ")
    print("=" * 70)
    
    # Загружаем конфигурацию
    AIConfig.load_from_file()
    
    # Создаем checker
    try:
        checker = AIAnswerChecker(provider="gemini", api_key=AIConfig.GEMINI_API_KEY)
        print(f"✅ AI Checker инициализирован")
        print(f"   API Key: {'***' + AIConfig.GEMINI_API_KEY[-4:] if AIConfig.GEMINI_API_KEY else 'НЕТ'}")
        print(f"   Модель: {AIConfig.GEMINI_MODEL}")
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return
    
    print("\n" + "=" * 70)
    
    # Тестовые случаи из вашего примера
    test_cases = [
        {
            "name": "Опечатка: икусственный -> искусственный",
            "student_answer": "икусственный",
            "correct_variants": ["искусственный"],
            "context": "Полное название технологии AI"
        },
        {
            "name": "Разные регистры: VRом -> vr",
            "student_answer": "VRом",
            "correct_variants": ["vr"],
            "context": "Аббревиатура технологии виртуальной реальности"
        },
        {
            "name": "Синонимы: истина -> верно",
            "student_answer": "истина",
            "correct_variants": ["верно"],
            "context": "Булево значение true"
        },
        {
            "name": "Синонимы: ложь -> не верно",
            "student_answer": "ложь",
            "correct_variants": ["не верно"],
            "context": "Булево значение false"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"ТЕСТ {i}: {test['name']}")
        print(f"{'=' * 70}")
        print(f"📝 Ответ студента: '{test['student_answer']}'")
        print(f"✓  Правильные варианты: {test['correct_variants']}")
        print(f"📄 Контекст: {test['context']}")
        print(f"\nОтправка запроса к Gemini API...")
        
        try:
            result = checker.check_answer(
                student_answer=test['student_answer'],
                correct_variants=test['correct_variants'],
                question_context=test['context'],
                system_prompt=AIConfig.SYSTEM_PROMPT,
                model_name=AIConfig.GEMINI_MODEL
            )
            
            result_dict = asdict(result)
            
            print(f"\n{'─' * 70}")
            print(f"РЕЗУЛЬТАТ:")
            print(f"{'─' * 70}")
            print(f"  {'✅ ВЕРНО' if result.is_correct else '❌ НЕВЕРНО'}")
            print(f"  Уверенность: {result.confidence * 100:.1f}%")
            print(f"  Объяснение: {result.explanation}")
            print(f"  Провайдер: {result.ai_provider}")
            
            # Показываем сырой ответ для отладки
            print(f"\n  📋 Детали:")
            for key, value in result_dict.items():
                print(f"     {key}: {value}")
            
        except Exception as e:
            print(f"\n❌ ОШИБКА: {e}")
            import traceback
            print("\nПолный traceback:")
            traceback.print_exc()
            
            # Пробуем понять причину
            print(f"\n🔍 Диагностика:")
            print(f"   - Тип ошибки: {type(e).__name__}")
            print(f"   - Сообщение: {str(e)}")
    
    print(f"\n{'=' * 70}")
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 70)


def test_raw_api_call():
    """Прямой тест API вызова для отладки"""
    
    print("\n" + "=" * 70)
    print("ПРЯМОЙ ТЕСТ API ВЫЗОВА")
    print("=" * 70)
    
    import requests
    
    AIConfig.load_from_file()
    
    model = AIConfig.GEMINI_MODEL
    api_key = AIConfig.GEMINI_API_KEY
    
    url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"
    
    # Простой тестовый запрос
    test_prompt = """Проверь ответ студента. Верни ТОЛЬКО валидный JSON, без дополнительного текста.

Правильные ответы:
- верно

Ответ студента: "истина"

Формат ответа (только JSON):
{"is_correct": true, "confidence": 95, "explanation": "краткое пояснение"}"""
    
    data = {
        "contents": [{
            "parts": [{"text": test_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.0,
            "top_p": 0.8,
            "top_k": 10,
            "max_output_tokens": 100,
            "candidate_count": 1
        }
    }
    
    print(f"\n📤 Отправка запроса к: {url[:80]}...")
    print(f"📝 Промпт: {test_prompt[:100]}...")
    
    try:
        response = requests.post(url, json=data, timeout=15)
        
        print(f"\n📥 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ Полный ответ от API:")
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0]['content']['parts'][0]['text']
                print(f"\n📄 Извлеченный текст:")
                print(content)
                
                # Пробуем распарсить
                print(f"\n🔍 Попытка парсинга JSON...")
                try:
                    content = content.replace('```json', '').replace('```', '').strip()
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    if start != -1 and end != 0:
                        json_str = content[start:end]
                        parsed = json.loads(json_str)
                        print(f"✅ JSON успешно распарсен:")
                        print(json.dumps(parsed, indent=2, ensure_ascii=False))
                except Exception as parse_error:
                    print(f"❌ Ошибка парсинга: {parse_error}")
            else:
                print(f"⚠️ Нет candidates в ответе")
        else:
            print(f"❌ Ошибка API: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка вызова: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  ОТЛАДКА ПРОБЛЕМНЫХ СЛУЧАЕВ AI ПРОВЕРКИ".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70 + "\n")
    
    # Сначала прямой тест API
    test_raw_api_call()
    
    # Затем тест через checker
    test_problematic_cases()
    
    print("\n" + "=" * 70)
    print("РЕКОМЕНДАЦИИ:")
    print("=" * 70)
    print("""
1. Проверьте, что Gemini API возвращает валидный JSON
2. Если видите лишний текст - промпт нужно доработать
3. Если ошибка парсинга - включился regex fallback
4. Проверьте квоты API в Google Cloud Console
5. Попробуйте другую модель (gemini-1.5-pro вместо gemini-2.0-flash)
    """)