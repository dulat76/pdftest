"""Локальный скорер ответов с нормализацией, лемматизацией, fuzzy и семантикой."""
import re
import threading
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util

try:
    import spacy
except ImportError:  # pragma: no cover
    spacy = None

# Глобальные кэши
_model_lock = threading.Lock()
_nlp_lock = threading.Lock()
_embed_model: Optional[SentenceTransformer] = None
_nlp = None

# Кэш эмбеддингов: {(template_id, field_id): [(variant, embedding_tensor), ...]}
_variant_embeddings: Dict[Tuple[str, str], List[Tuple[str, "Tensor"]]] = {}


def normalize(text: str) -> str:
    """Приводит текст к нижнему регистру, убирает пунктуацию и лишние пробелы."""
    if text is None:
        return ""
    cleaned = re.sub(r"[^\w\s\-]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _ensure_nlp():
    """Лениво загружает модель spaCy."""
    global _nlp
    if _nlp is None and spacy:
        with _nlp_lock:
            if _nlp is None:
                try:
                    _nlp = spacy.load("ru_core_news_sm")
                except OSError:
                    # Модель не установлена — работаем без лемматизации
                    print("⚠️ spaCy model 'ru_core_news_sm' не найдена. Запустите: python -m spacy download ru_core_news_sm")
                    _nlp = None
    return _nlp


def lemmatize(text: str) -> str:
    """Возвращает лемматизированный текст (fallback на normalize)."""
    nlp = _ensure_nlp()
    if not nlp:
        return normalize(text)
    doc = nlp(text)
    return " ".join(tok.lemma_ for tok in doc)


def is_number(text: str) -> bool:
    """Пытается распознать числа, допускает запятую/точку как разделитель."""
    if text is None:
        return False
    stripped = text.replace(" ", "").replace(",", ".")
    try:
        float(stripped)
        return True
    except ValueError:
        return False


def fuzzy_score(a: str, b: str) -> float:
    """Fuzzy-метрика (0..100) на нормализованном тексте."""
    return float(fuzz.token_set_ratio(normalize(a), normalize(b)))


def _ensure_model():
    """Лениво загружает sentence-transformers модель."""
    global _embed_model
    if _embed_model is None:
        with _model_lock:
            if _embed_model is None:
                _embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                # Прогрев
                _embed_model.encode([""])
    return _embed_model


def embed(text: str, max_tokens: int = 512):
    """Строит эмбеддинг, обрезая длину входа."""
    model = _ensure_model()
    safe_text = text or ""
    # Простое усечение по словам
    tokens = safe_text.split()
    if len(tokens) > max_tokens:
        safe_text = " ".join(tokens[:max_tokens])
    return model.encode([safe_text], convert_to_tensor=True)[0]


def preload_model():
    """Явная загрузка модели и spaCy (для старта приложения)."""
    _ensure_model()
    _ensure_nlp()


def _prepare_variants(template_id: str, field_id: str, variants: List[str], max_tokens: int):
    """Сохраняет в кэш эмбеддинги вариантов."""
    cache_key = (template_id, field_id)
    if cache_key in _variant_embeddings:
        return

    prepared = []
    for v in variants:
        norm = normalize(v)
        lem = lemmatize(norm)
        emb = embed(lem, max_tokens=max_tokens)
        prepared.append((lem, emb))
    _variant_embeddings[cache_key] = prepared


def score_answer(
    student_answer: str,
    variants: List[str],
    thresholds: Dict[str, float],
    template_id: str,
    field_id: str,
) -> Dict:
    """
    Возвращает результат проверки:
    {
      is_correct: bool,
      method: exact|fuzzy_strict|fuzzy_soft|semantic,
      fuzzy_score: float,
      semantic_sim: float,
      thresholds_used: {...},
      from_cache: bool
    }
    """
    if not variants:
        return {
            "is_correct": False,
            "method": "none",
            "fuzzy_score": 0.0,
            "semantic_sim": 0.0,
            "thresholds_used": thresholds,
            "from_cache": False,
        }

    max_tokens = int(thresholds.get("embed_max_tokens", 512))
    _prepare_variants(template_id, field_id, variants, max_tokens)

    cache_key = (template_id, field_id)
    prepared = _variant_embeddings.get(cache_key, [])

    student_norm = normalize(student_answer)
    student_lem = lemmatize(student_norm)

    # Быстрые пути: числовые сравнения
    if is_number(student_answer):
        for v in variants:
            if is_number(v) and normalize(v) == student_norm:
                return {
                    "is_correct": True,
                    "method": "number",
                    "fuzzy_score": 100.0,
                    "semantic_sim": 1.0,
                    "thresholds_used": thresholds,
                    "from_cache": False,
                }

    # Exact / strict fuzzy
    for v in variants:
        if student_norm == normalize(v):
            return {
                "is_correct": True,
                "method": "exact",
                "fuzzy_score": 100.0,
                "semantic_sim": 1.0,
                "thresholds_used": thresholds,
                "from_cache": False,
            }

    strict_threshold = float(thresholds.get("fuzzy_strict", 95))
    soft_threshold = float(thresholds.get("fuzzy_soft", 90))
    sem_threshold = float(thresholds.get("sem_threshold", 0.75))

    best_fuzzy = 0.0
    for v in variants:
        score = fuzzy_score(student_answer, v)
        best_fuzzy = max(best_fuzzy, score)
        if score >= strict_threshold:
            return {
                "is_correct": True,
                "method": "fuzzy_strict",
                "fuzzy_score": score,
                "semantic_sim": 1.0,
                "thresholds_used": thresholds,
                "from_cache": False,
            }

    # Семантика + soft fuzzy
    student_emb = embed(student_lem, max_tokens=max_tokens)
    best_sem = 0.0
    for variant_lem, variant_emb in prepared:
        # semantic
        cos_sim = float(util.cos_sim(student_emb, variant_emb))
        best_sem = max(best_sem, cos_sim)
        if cos_sim >= sem_threshold:
            return {
                "is_correct": True,
                "method": "semantic",
                "fuzzy_score": best_fuzzy,
                "semantic_sim": cos_sim,
                "thresholds_used": thresholds,
                "from_cache": False,
            }

    if best_fuzzy >= soft_threshold:
        return {
            "is_correct": True,
            "method": "fuzzy_soft",
            "fuzzy_score": best_fuzzy,
            "semantic_sim": best_sem,
            "thresholds_used": thresholds,
            "from_cache": False,
        }

    return {
        "is_correct": False,
        "method": "none",
        "fuzzy_score": best_fuzzy,
        "semantic_sim": best_sem,
        "thresholds_used": thresholds,
        "from_cache": False,
    }

