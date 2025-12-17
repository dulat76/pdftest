"""Unit tests for answer_scorer module."""
import pytest
from answer_scorer import (
    normalize,
    lemmatize,
    is_number,
    fuzzy_score,
    score_answer,
    preload_model,
)


class TestNormalize:
    """Tests for text normalization."""
    
    def test_lowercase(self):
        """Test conversion to lowercase."""
        assert normalize("HELLO") == "hello"
    
    def test_remove_punctuation(self):
        """Test punctuation removal."""
        assert normalize("Hello, World!") == "hello world"
    
    def test_multiple_spaces(self):
        """Test multiple spaces collapsed."""
        assert normalize("hello    world") == "hello world"
    
    def test_none_input(self):
        """Test None input returns empty string."""
        assert normalize(None) == ""


class TestIsNumber:
    """Tests for number detection."""
    
    def test_integer(self):
        """Test integer detection."""
        assert is_number("123") is True
    
    def test_float_with_dot(self):
        """Test float with dot."""
        assert is_number("123.45") is True
    
    def test_float_with_comma(self):
        """Test float with comma (Russian format)."""
        assert is_number("123,45") is True
    
    def test_not_a_number(self):
        """Test non-number string."""
        assert is_number("abc") is False
    
    def test_none(self):
        """Test None input."""
        assert is_number(None) is False


class TestFuzzyScore:
    """Tests for fuzzy matching."""
    
    def test_exact_match(self):
        """Test exact match returns 100."""
        score = fuzzy_score("hello", "hello")
        assert score == 100.0
    
    def test_case_insensitive(self):
        """Test case insensitive matching."""
        score = fuzzy_score("Hello", "hello")
        assert score == 100.0
    
    def test_typo_tolerance(self):
        """Test typo tolerance."""
        score = fuzzy_score("helo", "hello")
        assert score > 80.0  # Should be high similarity
    
    def test_completely_different(self):
        """Test completely different strings."""
        score = fuzzy_score("hello", "goodbye")
        assert score < 50.0


class TestScoreAnswer:
    """Tests for answer scoring."""
    
    def test_exact_match(self):
        """Test exact match."""
        result = score_answer(
            student_answer="Астана",
            variants=["астана"],
            thresholds={
                "fuzzy_strict": 95,
                "fuzzy_soft": 90,
                "sem_threshold": 0.75,
                "embed_max_tokens": 512
            },
            template_id="test",
            field_id="field1"
        )
        assert result["is_correct"] is True
        assert result["method"] == "exact"
    
    def test_number_match(self):
        """Test number matching."""
        result = score_answer(
            student_answer="123.45",
            variants=["123,45"],
            thresholds={
                "fuzzy_strict": 95,
                "fuzzy_soft": 90,
                "sem_threshold": 0.75,
                "embed_max_tokens": 512
            },
            template_id="test",
            field_id="field2"
        )
        assert result["is_correct"] is True
        assert result["method"] == "number"
    
    def test_no_variants(self):
        """Test with no variants."""
        result = score_answer(
            student_answer="answer",
            variants=[],
            thresholds={
                "fuzzy_strict": 95,
                "fuzzy_soft": 90,
                "sem_threshold": 0.75,
                "embed_max_tokens": 512
            },
            template_id="test",
            field_id="field3"
        )
        assert result["is_correct"] is False
        assert result["method"] == "none"
    
    def test_fuzzy_match(self):
        """Test fuzzy matching."""
        result = score_answer(
            student_answer="Астанa",  # Typo
            variants=["Астана"],
            thresholds={
                "fuzzy_strict": 95,
                "fuzzy_soft": 90,
                "sem_threshold": 0.75,
                "embed_max_tokens": 512
            },
            template_id="test",
            field_id="field4"
        )
        # Should match via fuzzy
        assert result["fuzzy_score"] > 90.0


class TestPreloadModel:
    """Tests for model preloading."""
    
    def test_preload_does_not_crash(self):
        """Test that preload_model doesn't crash."""
        # Should not raise
        try:
            preload_model()
        except Exception as e:
            # It's okay if models aren't installed in test environment
            assert "not found" in str(e).lower() or "no module" in str(e).lower()
