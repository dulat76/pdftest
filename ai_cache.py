"""
Модуль для кэширования ответов ИИ в PostgreSQL
"""

import psycopg2
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

class AICacheManager:
    """Менеджер кэша для ответов ИИ"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'flask_db'),
            'database': os.getenv('POSTGRES_DB', 'flask_db'),
            'user': os.getenv('POSTGRES_USER', 'flask_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'flask_password123'),
            'port': int(os.getenv('POSTGRES_PORT', 5432))
        }
        self.default_ttl = int(os.getenv('AI_CACHE_TTL', 3600))  # 1 час по умолчанию
    
    def _get_connection(self):
        """Получить подключение к БД"""
        return psycopg2.connect(**self.db_config)
    
    def _generate_cache_key(self, student_answer: str, correct_variants: list, 
                          question_context: str, ai_model: str) -> str:
        """Генерация ключа кэша"""
        data = f"{student_answer}_{json.dumps(correct_variants, sort_keys=True)}_{question_context}_{ai_model}"
        return hashlib.md5(data.encode('utf-8')).hexdigest()
    
    def get_cached_result(self, student_answer: str, correct_variants: list,
                         question_context: str, ai_model: str) -> Optional[Dict[str, Any]]:
        """
        Получить закэшированный результат
        
        Returns:
            Dict или None если не найдено в кэше
        """
        cache_key = self._generate_cache_key(student_answer, correct_variants, question_context, ai_model)
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT is_correct, confidence, explanation, ai_provider
                FROM ai_response_cache 
                WHERE cache_key = %s AND expires_at > NOW()
            """, (cache_key,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                # Увеличиваем счетчик использования
                self._increment_usage_count(cache_key)
                return {
                    'is_correct': result[0],
                    'confidence': result[1],
                    'explanation': result[2],
                    'ai_provider': result[3]
                }
            
        except Exception as e:
            print(f"⚠️ Ошибка при чтении из кэша: {e}")
        
        return None
    
    def _increment_usage_count(self, cache_key: str):
        """Увеличить счетчик использования записи"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ai_response_cache 
                SET usage_count = usage_count + 1 
                WHERE cache_key = %s
            """, (cache_key,))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Ошибка при обновлении счетчика: {e}")
    
    def save_to_cache(self, student_answer: str, correct_variants: list,
                     question_context: str, ai_provider: str, ai_model: str,
                     is_correct: bool, confidence: float, explanation: str,
                     ttl: Optional[int] = None) -> bool:
        """
        Сохранить результат в кэш
        
        Args:
            ttl: время жизни в секундах (по умолчанию 1 час)
        """
        if ttl is None:
            ttl = self.default_ttl
            
        cache_key = self._generate_cache_key(student_answer, correct_variants, question_context, ai_model)
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Используем UPSERT (обновляем если существует)
            cursor.execute("""
                INSERT INTO ai_response_cache 
                (cache_key, student_answer, correct_variants, question_context, 
                 ai_provider, ai_model, is_correct, confidence, explanation, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) 
                DO UPDATE SET 
                    usage_count = ai_response_cache.usage_count + 1,
                    expires_at = EXCLUDED.expires_at
            """, (
                cache_key,
                student_answer,
                json.dumps(correct_variants, ensure_ascii=False),
                question_context,
                ai_provider,
                ai_model,
                is_correct,
                confidence,
                explanation,
                expires_at
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"⚠️ Ошибка при сохранении в кэш: {e}")
            return False
    
    def clear_expired_entries(self) -> int:
        """Очистить устаревшие записи и вернуть количество удаленных"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM ai_response_cache WHERE expires_at < NOW()")
            deleted_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return deleted_count
            
        except Exception as e:
            print(f"⚠️ Ошибка при очистке кэша: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN expires_at > NOW() THEN 1 END) as valid_entries,
                    SUM(usage_count) as total_usage,
                    AVG(confidence) as avg_confidence,
                    COUNT(DISTINCT ai_provider) as providers_count
                FROM ai_response_cache
            """)
            
            stats = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return {
                'total_entries': stats[0] or 0,
                'valid_entries': stats[1] or 0,
                'total_usage': stats[2] or 0,
                'avg_confidence': float(stats[3] or 0),
                'providers_count': stats[4] or 0
            }
            
        except Exception as e:
            print(f"⚠️ Ошибка при получении статистики: {e}")
            return {
                'total_entries': 0,
                'valid_entries': 0,
                'total_usage': 0,
                'avg_confidence': 0,
                'providers_count': 0
            }


# Глобальный экземпляр менеджера кэша
cache_manager = AICacheManager()