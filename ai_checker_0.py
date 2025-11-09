"""
Модуль для проверки ответов студентов с использованием ИИ
Поддерживает несколько API: Groq, Google Gemini, HuggingFace
"""

import os
import json
from typing import List, Dict, Optional
import requests
from dataclasses import dataclass

@dataclass
class AICheckResult:
    """Результат проверки ответа через ИИ"""
    is_correct: bool
    confidence: float  # 0.0 - 1.0
    explanation: str
    ai_provider: str


class AIAnswerChecker:
    """Класс для проверки ответов студентов с помощью ИИ"""
    
    def __init__(self, provider: str = "groq", api_key: Optional[str] = None):
        """
        Инициализация проверщика
        
        Args:
            provider: "groq", "gemini", "huggingface", или "cohere"
            api_key: API ключ (если None, берется из переменных окружения)
        """
        self.provider = provider.lower()
        # Приоритет: переданный ключ, затем переменная окружения
        self.api_key = api_key if api_key else self._get_api_key_from_env()
        
        if not self.api_key:
            raise ValueError(f"API ключ для {provider} не найден. "
                           f"Установите переменную окружения {self._get_env_var_name()} или передайте его напрямую.")
    
    def _get_env_var_name(self) -> str:
        """Получить имя переменной окружения для API ключа"""
        env_vars = {
            "groq": "GROQ_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
            "cohere": "COHERE_API_KEY"
        }
        return env_vars.get(self.provider, "AI_API_KEY")
    
    def _get_api_key_from_env(self) -> Optional[str]:
        """Получить API ключ из переменных окружения"""
        return os.getenv(self._get_env_var_name())
    
    def check_answer(self, 
                     student_answer: str, 
                     correct_variants: List[str],
                     question_context: str = "",
                     system_prompt: Optional[str] = None,
                     model_name: Optional[str] = None) -> AICheckResult:
        """
        Проверить ответ студента с помощью ИИ
        
        Args:
            student_answer: Ответ студента
            correct_variants: Список правильных вариантов ответа
            question_context: Контекст вопроса (опционально)
            system_prompt: Кастомный системный промпт (опционально)
            model_name: Имя модели для использования (опционально)
        
        Returns:
            AICheckResult с результатом проверки
        """
        if self.provider == "groq":
            return self._check_with_groq(student_answer, correct_variants, question_context, system_prompt)
        elif self.provider == "gemini":
            return self._check_with_gemini(student_answer, correct_variants, question_context, system_prompt, model_name)
        elif self.provider == "huggingface":
            return self._check_with_huggingface(student_answer, correct_variants, question_context)
        elif self.provider == "cohere":
            return self._check_with_cohere(student_answer, correct_variants, question_context, system_prompt)
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {self.provider}")
    
    def _check_with_groq(self, student_answer: str, correct_variants: List[str], 
                        question_context: str = "",
                        system_prompt: Optional[str] = None) -> AICheckResult:
        """Проверка через Groq API"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Для Groq оставим старую логику, так как он хорошо с ней работает
        user_prompt = f"Правильные ответы: {correct_variants}. Ответ студента: '{student_answer}'. Верно или нет?"
        
        data = {
            "model": "llama-3.1-8b-instant",  # Быстрая модель
            "messages": [
                {"role": "system", "content": system_prompt or "Ты - эксперт по проверке ответов. Всегда отвечай только валидным JSON."},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,  # Низкая температура для стабильности
            "max_tokens": 200
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Извлекаем JSON из ответа
            json_result = self._extract_json(content)
            
            return AICheckResult(
                is_correct=json_result.get('is_correct', False),
                confidence=json_result.get('confidence', 0) / 100.0,
                explanation=json_result.get('explanation', 'Не удалось получить объяснение'),
                ai_provider='groq'
            )
            
        except Exception as e:
            print(f"Ошибка Groq API: {e}")
            # Fallback на простую проверку
            return self._fallback_check(student_answer, correct_variants)
    
    def _build_gemini_request_body(self, student_answer: str, correct_variants: List[str],
                                   question_context: str, system_prompt: str,
                                   generation_config: Dict) -> Dict:
        """Формирует тело запроса для Gemini API по новому формату."""
        
        # Формируем строку с правильными ответами
        correct_answers_str = "\n".join([f"- {v}" for v in correct_variants])
        
        # Заполняем шаблон промпта
        user_prompt_text = system_prompt.format(
            question_context=question_context or "Контекст не указан",
            correct_answers=correct_answers_str,
            student_answer=student_answer
        )
        
        # Собираем тело запроса
        request_body = {
            "contents": [{
                "parts": [{"text": user_prompt_text}]
            }],
            "generationConfig": generation_config
        }
        
        return request_body

    def _check_with_gemini(self, student_answer: str, correct_variants: List[str],
                          question_context: str = "",
                          system_prompt: Optional[str] = None,
                          model_name: Optional[str] = None) -> AICheckResult:
        """Проверка через Google Gemini API"""
        from ai_config import AIConfig

        # Динамически формируем URL с правильным именем модели
        model_to_use = model_name or AIConfig.GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1/models/{model_to_use}:generateContent?key={self.api_key}"
        
        # Используем новый метод для формирования тела запроса
        data = self._build_gemini_request_body(
            student_answer, correct_variants, question_context,
            system_prompt or AIConfig.VERIFICATION_PROMPT_TEMPLATE,
            AIConfig.GENERATION_CONFIG
        )
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            content = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            json_result = self._extract_json(content)
            
            return AICheckResult(
                is_correct=json_result.get('is_correct', False),
                confidence=json_result.get('confidence', 0) / 100.0,
                explanation=json_result.get('explanation', 'Не удалось получить объяснение'),
                ai_provider='gemini'
            )
            
        except Exception as e:
            print(f"Ошибка Gemini API: {e}")
            return self._fallback_check(student_answer, correct_variants, error_message=str(e))
    
    def _check_with_huggingface(self, student_answer: str, correct_variants: List[str],
                               question_context: str = "") -> AICheckResult:
        """Проверка через HuggingFace API"""
        # Используем модель для классификации текста
        url = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Формируем гипотезы для проверки
        hypothesis = f"Ответ '{student_answer}' эквивалентен одному из: {', '.join(correct_variants)}"
        
        data = {
            "inputs": student_answer,
            "parameters": {"candidate_labels": ["correct", "incorrect"]}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # Анализируем результат
            is_correct = result['labels'][0] == 'correct'
            confidence = result['scores'][0]
            
            return AICheckResult(
                is_correct=is_correct,
                confidence=confidence,
                explanation=f"Классификация: {result['labels'][0]} ({confidence*100:.1f}%)",
                ai_provider='huggingface'
            )
            
        except Exception as e:
            print(f"Ошибка HuggingFace API: {e}")
            return self._fallback_check(student_answer, correct_variants, error_message=str(e))
    
    def _check_with_cohere(self, student_answer: str, correct_variants: List[str],
                          question_context: str = "",
                          system_prompt: Optional[str] = None) -> AICheckResult:
        """Проверка через Cohere API"""
        url = "https://api.cohere.ai/v1/generate"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        user_prompt = self._build_prompt(student_answer, correct_variants, question_context)
        
        data = {
            "model": "command-light",
            "prompt": f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt,
            "max_tokens": 200,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            content = result['generations'][0]['text'].strip()
            
            json_result = self._extract_json(content)
            
            return AICheckResult(
                is_correct=json_result.get('is_correct', False),
                confidence=json_result.get('confidence', 0) / 100.0,
                explanation=json_result.get('explanation', 'Не удалось получить объяснение'),
                ai_provider='cohere'
            )
            
        except Exception as e:
            print(f"Ошибка Cohere API: {e}")
            return self._fallback_check(student_answer, correct_variants, error_message=str(e))
    
    def _extract_json(self, text: str) -> Dict:
        """Извлечь JSON из текста"""
        try:
            # Умный поиск JSON: находим первую '{' и последнюю '}'
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = text[start:end]
                return json.loads(json_str)
            
            # Если не нашли, пробуем парсить весь текст как есть
            return json.loads(text)
        except json.JSONDecodeError:
            # Если не удалось распарсить, возвращаем дефолтные значения
            return {
                "is_correct": False,
                "confidence": 0,
                "explanation": f"Не удалось распознать JSON из ответа AI: '{text}'"
            }
    
    def _fallback_check(self, student_answer: str, correct_variants: List[str], 
                        error_message: str = "Нет точного совпадения") -> AICheckResult:
        """Простая проверка без ИИ (fallback)"""
        student_lower = student_answer.strip().lower()
        
        for variant in correct_variants:
            if student_lower == variant.strip().lower():
                return AICheckResult(
                    is_correct=True,
                    confidence=1.0,
                    explanation="Точное совпадение (fallback)",
                    ai_provider='fallback'
                )
        
        return AICheckResult(
            is_correct=False,
            confidence=0.8,
            explanation=f"Fallback: {error_message}",
            ai_provider='fallback'
        )
    
    def batch_check_answers(self, answers_data: List[Dict]) -> List[AICheckResult]:
        """
        Проверить несколько ответов одновременно
        
        Args:
            answers_data: Список словарей с ключами:
                - student_answer: str
                - correct_variants: List[str]
                - question_context: str (опционально)
        
        Returns:
            Список результатов проверки
        """
        results = []
        
        for data in answers_data:
            result = self.check_answer(
                student_answer=data['student_answer'],
                correct_variants=data['correct_variants'],
                question_context=data.get('question_context', '')
            )
            results.append(result)
        
        return results


# Вспомогательная функция для быстрой проверки
def quick_check_answer(student_answer: str, 
                      correct_variants: List[str],
                      provider: str = "groq",
                      api_key: Optional[str] = None) -> bool:
    """
    Быстрая проверка одного ответа
    
    Returns:
        True если ответ правильный, False если нет
    """
    try:
        checker = AIAnswerChecker(provider=provider, api_key=api_key)
        result = checker.check_answer(student_answer, correct_variants)
        return result.is_correct and result.confidence > 0.5
    except Exception as e:
        print(f"Ошибка при проверке ответа: {e}")
        # Fallback на простую проверку
        student_lower = student_answer.strip().lower()
        return any(student_lower == v.strip().lower() for v in correct_variants)


if __name__ == "__main__":
    # Пример использования
    print("=== Тестирование AI Answer Checker ===\n")
    
    # Тестовые данные
    test_cases = [
        {
            "student_answer": "голубой",
            "correct_variants": ["синий", "blue"],
            "expected": True
        },
        {
            "student_answer": "двадцать пять",
            "correct_variants": ["25"],
            "expected": True
        },
        {
            "student_answer": "сжатие файлов",
            "correct_variants": ["архивация", "компрессия"],
            "expected": True
        },
        {
            "student_answer": "Лондон",
            "correct_variants": ["Париж"],
            "expected": False
        }
    ]
    
    try:
        checker = AIAnswerChecker(provider="groq")  # Измените на нужный провайдер
        
        for i, test in enumerate(test_cases, 1):
            print(f"Тест {i}:")
            print(f"  Ответ студента: {test['student_answer']}")
            print(f"  Правильные варианты: {test['correct_variants']}")
            
            result = checker.check_answer(
                test['student_answer'],
                test['correct_variants']
            )
            
            print(f"  Результат: {'✅ Правильно' if result.is_correct else '❌ Неправильно'}")
            print(f"  Уверенность: {result.confidence*100:.1f}%")
           # print(f "  Объяснение: {result.explanation}")
            print(f"  Объяснение: {result.explanation}")
            print(f"  Провайдер: {result.ai_provider}")
            print(f"  Ожидалось: {'✅' if test['expected'] else '❌'}")
            print()
            
    except Exception as e:
        print(f"Ошибка: {e}")
        print("\nУстановите API ключ в переменной окружения GROQ_API_KEY")