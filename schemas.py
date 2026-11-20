"""Validation for the parser-to-solver contract."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VALID_CATEGORIES = {"table", "chair", "lamp"}
VALID_ATTRIBUTES = {
    "table": {"width_cm"},
    "chair": {"adjustable_height"},
    "lamp": {"color_temperature_k"},
}


def _valid_limit(value, attribute):
    if attribute == "adjustable_height":
        return isinstance(value, bool)
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def validate_parsed_request(value: dict) -> dict:
    """Reject malformed or unsafe model output and return canonical fields."""
    if not isinstance(value, dict):
        raise ValueError("Ответ парсера должен быть JSON-объектом")
    required = {"city_id", "budget_rub", "categories", "constraints", "missing"}
    if set(value) != required:
        raise ValueError("Ответ парсера должен содержать только поля внутреннего контракта")

    cities = json.loads((PROJECT_ROOT / "data" / "cities.json").read_text(encoding="utf-8"))
    valid_cities = {city["id"] for city in cities}
    city_id = value["city_id"]
    if city_id is not None and (not isinstance(city_id, str) or city_id not in valid_cities):
        raise ValueError("Неизвестный city_id")

    budget = value["budget_rub"]
    if budget is not None and (not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0):
        raise ValueError("budget_rub должен быть положительным целым числом или null")

    categories = value["categories"]
    if (not isinstance(categories, list)
            or any(not isinstance(category, str) or category not in VALID_CATEGORIES for category in categories)
            or len(set(categories)) != len(categories)):
        raise ValueError("categories содержит недопустимые или повторяющиеся категории")

    constraints = value["constraints"]
    if not isinstance(constraints, dict):
        raise ValueError("constraints должен быть объектом")
    for category, category_rules in constraints.items():
        if category not in VALID_CATEGORIES or not isinstance(category_rules, dict):
            raise ValueError("Недопустимая категория в constraints")
        for attribute, rules in category_rules.items():
            if attribute not in VALID_ATTRIBUTES[category] or not isinstance(rules, dict):
                raise ValueError("Недопустимый атрибут в constraints")
            if not rules or not set(rules).issubset({"min", "max", "eq"}):
                raise ValueError("Правило ограничения должно содержать min, max или eq")
            if any(not _valid_limit(limit, attribute) for limit in rules.values()):
                raise ValueError("Значение ограничения имеет неверный тип или диапазон")

    expected_missing = []
    if city_id is None:
        expected_missing.append("city_id")
    if budget is None:
        expected_missing.append("budget_rub")
    if not categories:
        expected_missing.append("categories")
    if value["missing"] != expected_missing:
        raise ValueError("missing не соответствует отсутствующим обязательным данным")

    return {
        "city_id": city_id,
        "budget_rub": budget,
        "categories": categories,
        "constraints": constraints,
        "missing": expected_missing,
    }
