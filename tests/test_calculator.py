"""Deterministic and security-focused tests for the calculator skill."""

import pytest

from app.skills.calculator import (
    CalculatorError,
    ExpressionExtractionError,
    UnsafeExpressionError,
    calculator_node,
    evaluate_expression,
    extract_expression,
    normalize_mathematical_text,
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", 14),
        ("(2 + 3) * 4", 20),
        ("-5 + 2", -3),
        ("+5", 5),
        ("3.5 * 2", 7.0),
        ("2 ** 10", 1024),
        ("17 % 5", 2),
        ("20 / 4", 5.0),
    ],
)
def test_evaluate_expression(expression: str, expected: int | float) -> None:
    assert evaluate_expression(expression) == expected


@pytest.mark.parametrize("expression", ["2 +", "(2 + 3", ""])
def test_malformed_expressions_are_rejected(expression: str) -> None:
    with pytest.raises(CalculatorError):
        evaluate_expression(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo unsafe')",
        "open('secret.txt')",
        "(1).__class__",
        "[1, 2, 3]",
        "2 // 1",
        "2 << 3",
        "True + 1",
        "10 ** 101",
    ],
)
def test_unsupported_or_malicious_syntax_is_rejected(expression: str) -> None:
    with pytest.raises(UnsafeExpressionError):
        evaluate_expression(expression)


@pytest.mark.parametrize("expression", ["1 / 0", "1 % 0"])
def test_division_and_modulo_by_zero_are_rejected(expression: str) -> None:
    with pytest.raises(CalculatorError, match="zero"):
        evaluate_expression(expression)


def test_persian_and_arabic_digits_are_normalized() -> None:
    assert normalize_mathematical_text("۱۲۵ + ٣٨") == "125 + 38"


def test_persian_natural_language_request_is_extracted() -> None:
    assert extract_expression("حاصل ۱۲۵ ضربدر ۳۸ چقدر است؟") == "125*38"


def test_english_natural_language_request_is_extracted() -> None:
    assert extract_expression("What is 12 multiplied by (3 plus 2)?") == "12*(3+2)"


def test_sentence_period_is_not_treated_as_decimal_point() -> None:
    assert extract_expression("calculate 12 * 9.") == "12*9"


def test_missing_expression_is_reported() -> None:
    with pytest.raises(ExpressionExtractionError):
        extract_expression("سلام، حالت چطور است؟")


def test_calculator_node_computes_persian_request() -> None:
    assert calculator_node({"user_input": "حاصل ۱۲۵ ضربدر ۳۸ چقدر است؟"}) == {
        "final_response": "125*38 = 4750"
    }


def test_calculator_node_returns_safe_error_message() -> None:
    result = calculator_node({"user_input": "calculate 1 / 0"})

    assert result["final_response"].startswith("Calculator error:")
    assert "zero" in result["final_response"]
