import argparse
import json
import re
import sys

from catalog import load_catalog
from llm_client import parse_with_llm
from schemas import validate_parsed_request
from solver import solve


def parse_request_with_regex(messages: list[dict]) -> dict:
    """Parse the latest user message using the local, offline fallback."""
    text = next(
        (message.get("text", "") for message in reversed(messages)
         if message.get("role") == "user" and isinstance(message.get("text", ""), str)),
        "",
    ).lower()

    parsed = {
        "city_id": None,
        "budget_rub": None,
        "categories": [],
        "constraints": {},
        "missing": [],
    }

    city_aliases = {
        "taganrog": ("таганрог",),
        "rostov-na-donu": ("ростов-на-дону", "ростов на дону", "ростов"),
        "azov": ("азов",),
    }
    for city_id, aliases in city_aliases.items():
        if any(alias in text for alias in aliases):
            parsed["city_id"] = city_id
            break
    if parsed["city_id"] is None:
        parsed["missing"].append("city_id")

    budget_match = re.search(r"до\s*([\d\s\u00a0]+?)\s*(?:₽|руб(?:лей|ля|ль)?\b|р\.)", text)
    if budget_match:
        digits = re.sub(r"\D", "", budget_match.group(1))
        if digits:
            parsed["budget_rub"] = int(digits)
    if parsed["budget_rub"] is None:
        parsed["missing"].append("budget_rub")

    if "стол" in text:
        parsed["categories"].append("table")
    if "кресл" in text:
        parsed["categories"].append("chair")
    if "ламп" in text:
        parsed["categories"].append("lamp")
    if not parsed["categories"]:
        parsed["missing"].append("categories")

    if "не шире метра" in text or re.search(r"до\s*100\s*см", text):
        parsed["constraints"]["table"] = {"width_cm": {"max": 100}}
    return parsed


def parse_request(messages: list[dict]) -> dict:
    """Prefer the configured LLM; use regex parsing on any failure."""
    try:
        result = parse_with_llm(messages)
        return validate_parsed_request(result)
    except Exception as exc:
        print(f"LLM parsing unavailable; using regex fallback: {exc}", file=sys.stderr)
        return validate_parsed_request(parse_request_with_regex(messages))


def get_question_text(field: str) -> str:
    questions = {
        "budget_rub": "Какой у вас бюджет на весь комплект?",
        "city_id": "В каком городе искать?",
        "categories": "Какие категории товаров нужны?",
    }
    return questions.get(field, "Уточните запрос.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, help="Путь к файлу catalog.json")
    args = parser.parse_args()

    try:
        input_data = json.load(sys.stdin)
        messages = input_data.get("messages", [])
        if not messages:
            raise ValueError("Пустой список messages")

        catalog = load_catalog(args.catalog)
        parsed = parse_request(messages)

        if parsed["missing"]:
            output = {
                "status": "clarify",
                "questions": [
                    {"field": field, "text": get_question_text(field)}
                    for field in parsed["missing"]
                ],
            }
            print(json.dumps(output, ensure_ascii=False))
            return

        result = solve(catalog, parsed)
        if result["status"] == "no_match":
            output = {"status": "no_match", "message": result["reason"]}
        else:
            catalog_dict = {item["id"]: item for item in catalog}
            options = []
            for option in result["options"]:
                titles = [catalog_dict[item_id]["title"] for item_id in option["listing_ids"]]
                explanation = (
                    f"В комплект входят: {', '.join(titles)}. "
                    f"Общая стоимость: {option['total_rub']} ₽."
                )
                options.append({
                    "listing_ids": option["listing_ids"],
                    "total_rub": option["total_rub"],
                    "explanation": explanation,
                })
            output = {"status": "ok", "options": options}

        print(json.dumps(output, ensure_ascii=False))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(json.dumps({
            "status": "clarify",
            "questions": [{
                "field": "retry",
                "text": "Произошла ошибка при обработке запроса. Попробуйте еще раз.",
            }],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
