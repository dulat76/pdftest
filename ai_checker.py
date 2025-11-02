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
        self.api_key = api_key or self._get_api_key_from_env()
        
        if not self.api_key:
            raise ValueError(f"API ключ для {provider} не найден. "
                           f"Установите переменную окружения {self._get_env_var_name()}")
    
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
                     question_context: str = "") -> AICheckResult:
        """
        Проверить ответ студента с помощью ИИ
        
        Args:
            student_answer: Ответ студента
            correct_variants: Список правильных вариантов ответа
            question_context: Контекст вопроса (опционально)
        
        Returns:
            AICheckResult с результатом проверки
        """
        if self.provider == "groq":
            return self._check_with_groq(student_answer, correct_variants, question_context)
        elif self.provider == "gemini":
            return self._check_with_gemini(student_answer, correct_variants, question_context)
        elif self.provider == "huggingface":
            return self._check_with_huggingface(student_answer, correct_variants, question_context)
        elif self.provider == "cohere":
            return self._check_with_cohere(student_answer, correct_variants, question_context)
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {self.provider}")
    
    def _build_prompt(self, student_answer: str, correct_variants: List[str], 
                     question_context: str = "") -> str:
        """Создать промпт для ИИ"""
        variants_str = ", ".join([f'"{v}"' for v in correct_variants])
        
        prompt = f"""Ты - система проверки ответов на тесты. Твоя задача - определить, является ли ответ студента правильным по смыслу.

Правильные варианты ответа: {variants_str}

Ответ студента: "{student_answer}"

{'Контекст вопроса: ' + question_context if question_context else ''}

Проанализируй ответ студента и определи:
1. Является ли он правильным по смыслу (даже если формулировка отличается)?
2. Насколько ты уверен в своей оценке (от 0% до 100%)?
3. Краткое объяснение (1-2 предложения)

Верни ответ СТРОГО в формате JSON:
{{
    "is_correct": true или false,
    "confidence": число от 0 до 100,
    "explanation": "краткое объяснение"
}}

Примеры:
- Правильный ответ: "синий", Ответ студента: "голубой" → is_correct: true (похожие цвета)
- Правильный ответ: "25", Ответ студента: "двадцать пять" → is_correct: true (то же число)
- Правильный ответ: "Париж", Ответ студента: "Лондон" → is_correct: false (разные города)
- Правильный ответ: "архивация", Ответ студента: "сжатие файлов" → is_correct: true (синонимы)

Твой ответ (только JSON):"""
        
        return prompt
    
    def _check_with_groq(self, student_answer: str, correct_variants: List[str], 
                        question_context: str = "") -> AICheckResult:
        """Проверка через Groq API"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = self._build_prompt(student_answer, correct_variants, question_context)
        
        data = {
            "model": "llama-3.1-8b-instant",  # Быстрая модель
            "messages": [
                {"role": "system", "content": "Ты - эксперт по проверке ответов. Всегда отвечай только валидным JSON."},
                {"role": "user", "content": prompt}
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
    
    def _check_with_gemini(self, student_answer: str, correct_variants: List[str],
                          question_context: str = "") -> AICheckResult:
        """Проверка через Google Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        
        prompt = self._build_prompt(student_answer, correct_variants, question_context)
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 200
            }
        }
        
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
            return self._fallback_check(student_answer, correct_variants)
    
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
            return self._fallback_check(student_answer, correct_variants)
    
    def _check_with_cohere(self, student_answer: str, correct_variants: List[str],
                          question_context: str = "") -> AICheckResult:
        """Проверка через Cohere API"""
        url = "https://api.cohere.ai/v1/generate"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = self._build_prompt(student_answer, correct_variants, question_context)
        
        data = {
            "model": "command-light",
            "prompt": prompt,
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
            return self._fallback_check(student_answer, correct_variants)
    
    def _extract_json(self, text: str) -> Dict:
        """Извлечь JSON из текста"""
        try:
            # Ищем JSON в тексте
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = text[start:end]
                return json.loads(json_str)
            else:
                # Пробуем парсить весь текст
                return json.loads(text)
        except:
            # Если не удалось распарсить, возвращаем дефолтные значения
            return {
                "is_correct": False,
                "confidence": 0,
                "explanation": "Не удалось распознать ответ ИИ"
            }
    
    def _fallback_check(self, student_answer: str, correct_variants: List[str]) -> AICheckResult:
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
            explanation="Нет точного совпадения (fallback)",
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