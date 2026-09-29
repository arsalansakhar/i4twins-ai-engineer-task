"""Deterministic calculator skill with a restricted AST evaluator."""

from __future__ import annotations

import ast
import math
import operator
import re
from collections.abc import Callable
from typing import TypeAlias

from app.state import AgentState

Number: TypeAlias = int | float

MAX_EXPRESSION_LENGTH = 256
MAX_AST_NODES = 64
MAX_ABSOLUTE_RESULT = 1e100
MAX_ABSOLUTE_EXPONENT = 100


class CalculatorError(ValueError):
    """Base class for safe, user-facing calculator failures."""


class ExpressionExtractionError(CalculatorError):
    """Raised when no usable arithmetic expression can be found."""


class UnsafeExpressionError(CalculatorError):
    """Raised when an expression contains unsupported or unsafe syntax."""


_DIGIT_TRANSLATION = str.maketrans(
    {
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
        "٫": ".", "٬": "", "−": "-", "×": "*", "÷": "/", "^": "**",
    }
)

_OPERATOR_PHRASES = (
    (r"\bmultiplied\s+by\b", "*"),
    (r"\bdivided\s+by\b", "/"),
    (r"\bto\s+the\s+power\s+of\b", "**"),
    (r"\bmodulo\b|\bmod\b", "%"),
    (r"\btimes\b", "*"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"ضرب\s*در|ضربدر", "*"),
    (r"تقسیم\s*بر", "/"),
    (r"به\s*علاوه", "+"),
    (r"منهای", "-"),
    (r"باقی\s*مانده|باقیمانده", "%"),
)

_TOKEN_PATTERN = re.compile(r"\*\*|\d+(?:\.\d+)?|\.\d+|[+\-*/%()]|\S+")
_ARITHMETIC_TOKEN = re.compile(r"^(?:\*\*|\d+(?:\.\d+)?|\.\d+|[+\-*/%()])$")

_BINARY_OPERATORS: dict[type[ast.operator], Callable[[Number, Number], Number]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[Number], Number]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def normalize_mathematical_text(text: str) -> str:
    """Normalize Persian/Arabic digits and common written operators."""

    normalized = text.translate(_DIGIT_TRANSLATION).lower()
    for pattern, replacement in _OPERATOR_PHRASES:
        normalized = re.sub(pattern, f" {replacement} ", normalized)
    return normalized


def extract_expression(user_input: str) -> str:
    """Extract arithmetic tokens from a natural-language request.

    This is deliberately a small interpretation layer, not a general natural-
    language mathematics parser. A future LLM extractor may replace it, but its
    output must still pass through :func:`evaluate_expression`.
    """

    normalized = normalize_mathematical_text(user_input)
    arithmetic_tokens = [
        token
        for token in _TOKEN_PATTERN.findall(normalized)
        if _ARITHMETIC_TOKEN.fullmatch(token)
    ]
    expression = "".join(arithmetic_tokens)
    if not expression or not any(character.isdigit() for character in expression):
        raise ExpressionExtractionError("No arithmetic expression was found.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise UnsafeExpressionError("The arithmetic expression is too long.")
    return expression


def _validate_result(value: Number) -> Number:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UnsafeExpressionError("Only real numeric results are supported.")
    if isinstance(value, float) and not math.isfinite(value):
        raise UnsafeExpressionError("The result must be finite.")
    if abs(value) > MAX_ABSOLUTE_RESULT:
        raise UnsafeExpressionError("The result is too large.")
    return value


def _evaluate_node(node: ast.AST) -> Number:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise UnsafeExpressionError("Only integer and decimal literals are allowed.")
        return _validate_result(node.value)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _validate_result(_UNARY_OPERATORS[type(node.op)](_evaluate_node(node.operand)))

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_ABSOLUTE_EXPONENT:
            raise UnsafeExpressionError("The exponent is too large.")
        try:
            result = _BINARY_OPERATORS[type(node.op)](left, right)
        except ZeroDivisionError as exc:
            raise CalculatorError("Division or modulo by zero is not allowed.") from exc
        except (OverflowError, ValueError) as exc:
            raise UnsafeExpressionError("The expression cannot produce a safe real result.") from exc
        return _validate_result(result)

    raise UnsafeExpressionError(f"Unsupported syntax: {type(node).__name__}.")


def evaluate_expression(expression: str) -> Number:
    """Evaluate arithmetic using a strict AST whitelist; never use ``eval``."""

    if not expression.strip():
        raise ExpressionExtractionError("The arithmetic expression is empty.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise UnsafeExpressionError("The arithmetic expression is too long.")
    try:
        parsed = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise CalculatorError("The arithmetic expression is malformed.") from exc
    if sum(1 for _ in ast.walk(parsed)) > MAX_AST_NODES:
        raise UnsafeExpressionError("The arithmetic expression is too complex.")
    return _evaluate_node(parsed.body)


def format_result(value: Number) -> str:
    """Return a concise, stable representation suitable for the CLI."""

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, ".15g")
    return str(value)


def calculator_node(state: AgentState) -> dict[str, str]:
    """Interpret input, compute deterministically, and return a safe response."""

    try:
        expression = extract_expression(state["user_input"])
        result = evaluate_expression(expression)
    except CalculatorError as exc:
        return {"final_response": f"Calculator error: {exc}"}
    return {"final_response": f"{expression} = {format_result(result)}"}
