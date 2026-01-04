"""
Модуль для проверки ответов студентов с использованием ИИ
С ИНТЕГРАЦИЕЙ КЭШИРОВАНИЯ В POSTGRESQL
ИСПРАВЛЕНА КОДИРОВКА UTF-8
"""

import os
import json
from typing import List, Dict, Optional
import requests
from dataclasses import dataclass

# Импортируем менеджер кэша
try:
    from ai_cache import cache_manager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    print("⚠️ Модуль кэширования недоступен")

@dataclass
class AICheckResult:
    """Результат проверки ответа через ИИ"""
    is_correct: bool
    confidence: float  # 0.0 - 1.0
    explanation: str
    ai_provider: str
    from_cache: bool = False  # Новое поле: из кэша или нет


class AIAnswerChecker:
    """Класс для проверки ответов студентов с помощью ИИ с кэшированием"""
    
    def __init__(self, provider: str = "gemini", api_key: Optional[str] = None):
        """
        Инициализация проверщика с кэшированием
        
        Args:
            provider: "groq", "gemini", "huggingface", "cohere", или "ollama"
            api_key: API ключ (если None, берется из переменных окружения). Для ollama не требуется.
        """
        self.provider = provider.lower()
        
        # Для Ollama API ключ не требуется
        if self.provider == "ollama":
            self.api_key = None
        else:
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
        Проверить ответ студента с помощью ИИ с использованием кэша
        
        Args:
            student_answer: Ответ студента
            correct_variants: Список правильных вариантов ответа
            question_context: Контекст вопроса (опционально)
            system_prompt: Кастомный системный промпт (опционально)
            model_name: Имя модели для использования (опционально)
        
        Returns:
            AICheckResult с результатом проверки (может быть из кэша)
        """
        from ai_config import AIConfig
        
        # Используем модель из конфига если не указана
        model_to_use = model_name or AIConfig.GEMINI_MODEL
        
        # 1. ПРОВЕРКА КЭША (если доступен и включен)
        if CACHE_AVAILABLE and AIConfig.CACHE_AI_RESPONSES:
            cached_result = cache_manager.get_cached_result(
                student_answer=student_answer,
                correct_variants=correct_variants,
                question_context=question_context,
                ai_model=model_to_use
            )
            
            if cached_result:
                print(f"✅ Использован кэшированный ответ для: '{student_answer}'")
                return AICheckResult(
                    is_correct=cached_result['is_correct'],
                    confidence=cached_result['confidence'],
                    explanation=cached_result['explanation'],
                    ai_provider=cached_result['ai_provider'],
                    from_cache=True
                )
        
        # 2. ВЫЗОВ ИИ (если не найдено в кэше)
        if self.provider == "groq":
            result = self._check_with_groq(student_answer, correct_variants, question_context, system_prompt)
        elif self.provider == "gemini":
            result = self._check_with_gemini(student_answer, correct_variants, question_context, system_prompt, model_to_use)
        elif self.provider == "huggingface":
            result = self._check_with_huggingface(student_answer, correct_variants, question_context)
        elif self.provider == "cohere":
            result = self._check_with_cohere(student_answer, correct_variants, question_context, system_prompt)
        elif self.provider == "ollama":
            result = self._check_with_ollama(student_answer, correct_variants, question_context, system_prompt, model_to_use)
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {self.provider}")
        
        # 3. СОХРАНЕНИЕ В КЭШ (если успешно и кэш доступен)
        if CACHE_AVAILABLE and AIConfig.CACHE_AI_RESPONSES and not result.from_cache:
            cache_saved = cache_manager.save_to_cache(
                student_answer=student_answer,
                correct_variants=correct_variants,
                question_context=question_context,
                ai_provider=result.ai_provider,
                ai_model=model_to_use,
                is_correct=result.is_correct,
                confidence=result.confidence,
                explanation=result.explanation,
                ttl=AIConfig.CACHE_DURATION
            )
            
            if cache_saved:
                print(f"💾 Ответ сохранен в кэш: '{student_answer}'")
            else:
                print(f"⚠️ Не удалось сохранить в кэш: '{student_answer}'")
        
        return result
    
    def _build_prompt(self, student_answer: str, correct_variants: List[str], 
                     question_context: str = "") -> str:
        """Построить промпт для проверки ответа"""
        correct_answers_str = "\n".join([f"- {v}" for v in correct_variants])
        
        return f"""Проверь, является ли ответ студента правильным.

Контекст вопроса: {question_context or "Не указан"}

Правильные варианты ответа:
{correct_answers_str}

Ответ студента: "{student_answer}"

Верни ТОЛЬКО JSON в формате:
{{"is_correct": true/false, "confidence": число от 0 до 100, "explanation": "краткое пояснение"}}"""
    
    def _check_with_groq(self, student_answer: str, correct_variants: List[str], 
                        question_context: str = "",
                        system_prompt: Optional[str] = None) -> AICheckResult:
        """Проверка через Groq API"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        user_prompt = self._build_prompt(student_answer, correct_variants, question_context)
        
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt or "Ты - эксперт по проверке ответов. Всегда отвечай только валидным JSON."},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 200
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            json_result = self._extract_json(content)
            
            return AICheckResult(
                is_correct=json_result.get('is_correct', False),
                confidence=json_result.get('confidence', 0) / 100.0,
                explanation=json_result.get('explanation', 'Не удалось получить объяснение'),
                ai_provider='groq',
                from_cache=False
            )
            
        except Exception as e:
            print(f"Ошибка Groq API: {e}")
            return self._fallback_check(student_answer, correct_variants, error_message=str(e))
    
    def _build_gemini_request_body(self, student_answer: str, correct_variants: List[str],
                                   question_context: str, system_prompt: str,
                                   generation_config: Dict) -> Dict:
        """Формирует тело запроса для Gemini API с правильной кодировкой"""
        
        correct_answers_str = "\n".join([f"- {v}" for v in correct_variants])
        
        # ВСЕГДА используем наш фиксированный промпт
        user_prompt_text = f"""Проверь ответ студента. Верни ТОЛЬКО валидный JSON, без дополнительного текста.

Вопрос/Контекст: {question_context or "Не указан"}

Правильные ответы:
{correct_answers_str}

Ответ студента: "{student_answer}"

Критерии:
- Учитывай синонимы, опечатки, падежи
- Будь лоялен если суть верна
- VR = virtual reality (разные форматы допустимы)
- Истина/Верно/True - синонимы
- Ложь/Не верно/False - синонимы

Формат ответа (только JSON, ничего больше):
{{"is_correct": true, "confidence": 95, "explanation": "краткое пояснение"}}"""
        
        # Более строгие настройки для JSON генерации
        json_generation_config = {
            "temperature": 0.0,
            "top_p": 0.8,
            "top_k": 10,
            "max_output_tokens": 100,
            "candidate_count": 1
        }
        
        request_body = {
            "contents": [{
                "parts": [{"text": user_prompt_text}]
            }],
            "generationConfig": json_generation_config
        }
        
        return request_body

    def _check_with_gemini(self, student_answer: str, correct_variants: List[str],
                          question_context: str = "",
                          system_prompt: Optional[str] = None,
                          model_name: Optional[str] = None) -> AICheckResult:
        """Проверка через Google Gemini API с правильной обработкой кодировки"""
        from ai_config import AIConfig

        model_to_use = model_name or AIConfig.GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1/models/{model_to_use}:generateContent?key={self.api_key}"
        
        data = self._build_gemini_request_body(
            student_answer, correct_variants, question_context,
            system_prompt or AIConfig.VERIFICATION_PROMPT_TEMPLATE,
            AIConfig.GENERATION_CONFIG
        )
        
        try:
            # КРИТИЧНО: Явно указываем кодировку UTF-8
            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.post(
                url, 
                json=data, 
                headers=headers,
                timeout=15
            )
            
            # КРИТИЧНО: Устанавливаем кодировку ответа
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            # Получаем текст с правильной кодировкой
            result = response.json()
            
            # Проверяем наличие candidates
            if 'candidates' not in result or not result['candidates']:
                error_msg = "Gemini не вернул ответ"
                if 'promptFeedback' in result:
                    error_msg += f": {result['promptFeedback']}"
                raise Exception(error_msg)
            
            content = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Парсим JSON с правильной обработкой русских символов
            json_result = self._extract_json(content)
            
            return AICheckResult(
                is_correct=json_result.get('is_correct', False),
                confidence=json_result.get('confidence', 0) / 100.0,
                explanation=json_result.get('explanation', 'Нет объяснения от AI'),
                ai_provider='gemini',
                from_cache=False
            )
            
        except Exception as e:
            print(f"Ошибка Gemini API: {e}")
            return self._fallback_check(student_answer, correct_variants, error_message=str(e))
    
    def _check_with_huggingface(self, student_answer: str, correct_variants: List[str],
                               question_context: str = "") -> AICheckResult:
        """Проверка через HuggingFace API"""
        url = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        data = {
            "inputs": student_answer,
            "parameters": {"candidate_labels": ["correct", "incorrect"]}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            result = response.json()
            
            is_correct = result['labels'][0] == 'correct'
            confidence = result['scores'][0]
            
            return AICheckResult(
                is_correct=is_correct,
                confidence=confidence,
                explanation=f"Классификация: {result['labels'][0]} ({confidence*100:.1f}%)",
                ai_provider='huggingface',
                from_cache=False
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
            "Content-Type": "application/json; charset=utf-8"
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
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            result = response.json()
            content = result['generations'][0]['text'].strip()
            
            json_result = self._extract_json(content)
            
            return AICheckResult(
                is_correct=json_result.get('is_correct', False),
                confidence=json_result.get('confidence', 0) / 100.0,
                explanation=json_result.get('explanation', 'Не удалось получить объяснение'),
                ai_provider='cohere',
                from_cache=False
            )
            
        except Exception as e:
            print(f"Ошибка Cohere API: {e}")
            return self._fallback_check(student_answer, correct_variants, error_message=str(e))
    
    def _check_with_ollama(self, student_answer: str, correct_variants: List[str],
                           question_context: str = "",
                           system_prompt: Optional[str] = None,
                           model_name: str = "qwen2.5:1.5b") -> AICheckResult:
        """Проверка ответа через локальную Ollama модель"""
        # Получаем URL Ollama из переменной окружения или используем по умолчанию
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        
        # Формируем промпт аналогично Gemini
        correct_answers_str = "\n".join([f"- {v}" for v in correct_variants])
        
        user_prompt = f"""Проверь ответ студента. Верни ТОЛЬКО валидный JSON, без дополнительного текста.

Вопрос/Контекст: {question_context or "Не указан"}

Правильные ответы:
{correct_answers_str}

Ответ студента: "{student_answer}"

Критерии:
- Учитывай синонимы, опечатки, падежи
- Будь лоялен если суть верна
- VR = virtual reality (разные форматы допустимы)
- Истина/Верно/True - синонимы
- Ложь/Не верно/False - синонимы

Формат ответа (только JSON, ничего больше):
{{"is_correct": true, "confidence": 95, "explanation": "краткое пояснение"}}"""
        
        try:
            url = f"{ollama_url}/api/generate"
            
            response = requests.post(
                url,
                json={
                    "model": model_name,
                    "prompt": user_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 200,
                        "top_p": 0.8,
                        "top_k": 10
                    }
                },
                timeout=30  # Ollama может работать медленнее на CPU
            )
            
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "").strip()
            
            # Парсим JSON из ответа
            json_result = self._extract_json(content)
            
            return AICheckResult(
                is_correct=json_result.get('is_correct', False),
                confidence=json_result.get('confidence', 0) / 100.0,
                explanation=json_result.get('explanation', 'Нет объяснения от AI'),
                ai_provider='ollama',
                from_cache=False
            )
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Не удалось подключиться к Ollama по адресу {ollama_url}. Убедитесь, что Ollama запущен."
            print(f"❌ Ошибка Ollama: {error_msg}")
            return self._fallback_check(student_answer, correct_variants, error_message=error_msg)
        except Exception as e:
            print(f"❌ Ошибка Ollama: {e}")
            return self._fallback_check(student_answer, correct_variants, error_message=str(e))
    
    def _extract_json(self, text: str) -> Dict:
        """Извлечь JSON из текста с правильной обработкой UTF-8"""
        try:
            # Убеждаемся что текст в UTF-8
            if isinstance(text, bytes):
                text = text.decode('utf-8')
            
            # Убираем markdown форматирование и лишние пробелы
            text = text.replace('```json', '').replace('```', '').strip()
            
            # Умный поиск JSON блока
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = text[start:end]
                
                # Попытка парсинга (в Python 3.x json.loads автоматически работает с unicode)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Если не получилось, пробуем исправить распространенные ошибки
                    
                    # 1. Заменяем одинарные кавычки на двойные
                    json_str = json_str.replace("'", '"')
                    
                    # 2. Убираем trailing commas
                    import re
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                    
                    # 3. Исправляем булевы значения
                    json_str = json_str.replace('True', 'true').replace('False', 'false')
                    
                    return json.loads(json_str)
            
            # Последняя попытка - парсинг всего текста
            return json.loads(text)
            
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            print(f"⚠️ Ошибка парсинга JSON: {e}")
            print(f"📄 Исходный текст: {text[:200]}")
            
            # Умный fallback - извлекаем данные regex
            try:
                import re
                
                # Пытаемся найти is_correct
                is_correct_match = re.search(r'"?is_correct"?\s*:\s*(true|false)', text, re.IGNORECASE)
                is_correct = is_correct_match.group(1).lower() == 'true' if is_correct_match else False
                
                # Пытаемся найти confidence
                confidence_match = re.search(r'"?confidence"?\s*:\s*(\d+)', text)
                confidence = int(confidence_match.group(1)) if confidence_match else 0
                
                # Пытаемся найти explanation с учетом Unicode
                explanation_match = re.search(r'"?explanation"?\s*:\s*"([^"]*)"', text, re.UNICODE)
                explanation = explanation_match.group(1) if explanation_match else "Не удалось извлечь объяснение"
                
                print(f"✅ Извлечено через regex: correct={is_correct}, conf={confidence}")
                
                return {
                    "is_correct": is_correct,
                    "confidence": confidence,
                    "explanation": explanation
                }
                
            except Exception as regex_error:
                print(f"❌ Regex fallback не сработал: {regex_error}")
                
                # Полный fallback
                return {
                    "is_correct": False,
                    "confidence": 0,
                    "explanation": f"Не удалось распознать ответ AI. Оригинал: {text[:100]}..."
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
                    ai_provider='fallback',
                    from_cache=False
                )
        
        return AICheckResult(
            is_correct=False,
            confidence=0.0,
            explanation=f"Fallback: {error_message}",
            ai_provider='fallback',
            from_cache=False
        )
    
    def batch_check_answers(self, answers_data: List[Dict]) -> List[AICheckResult]:
        """
        Проверить несколько ответов одновременно
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


def quick_check_answer(student_answer: str, 
                      correct_variants: List[str],
                      provider: str = "groq",
                      api_key: Optional[str] = None) -> bool:
    """Быстрая проверка одного ответа с кэшированием"""
    try:
        checker = AIAnswerChecker(provider=provider, api_key=api_key)
        result = checker.check_answer(student_answer, correct_variants)
        return result.is_correct and result.confidence > 0.5
    except Exception as e:
        print(f"Ошибка при проверке ответа: {e}")
        student_lower = student_answer.strip().lower()
        return any(student_lower == v.strip().lower() for v in correct_variants)