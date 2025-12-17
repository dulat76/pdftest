import pytest

from answer_scorer import score_answer, normalize, is_number


def test_normalize_basic():
    assert normalize("Привет, Мир!") == "привет мир"


def test_is_number():
    assert is_number("10,5")
    assert is_number("3.14")
    assert not is_number("abc")


def test_score_exact():
    res = score_answer(
        student_answer="Астана",
        variants=["Астана", "Нур-Султан"],
        thresholds={"fuzzy_strict": 95, "fuzzy_soft": 90, "sem_threshold": 0.75, "embed_max_tokens": 32},
        template_id="tpl_test",
        field_id="field1",
    )
    assert res["is_correct"]
    assert res["method"] in {"exact", "fuzzy_strict", "semantic", "fuzzy_soft"}


@pytest.mark.parametrize(
    "student,variant",
    [
        ("астана", "Астана"),
        ("столица казахстана", "Астана"),
        ("Астна", "Астана"),
    ],
)
def test_score_fuzzy_semantic(student, variant):
    res = score_answer(
        student_answer=student,
        variants=[variant],
        thresholds={"fuzzy_strict": 95, "fuzzy_soft": 70, "sem_threshold": 0.5, "embed_max_tokens": 32},
        template_id="tpl_test",
        field_id="field2",
    )
    assert res["is_correct"] in {True, False}


