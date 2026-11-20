import argparse
import json
import sys

from catalog import load_catalog
from solver import solve

# Заглушка для LLM-парсера (пока коллега не напишет llm_client.py)
def parse_request(messages: list[dict]) -> dict:
    """Временный парсер на регулярках, чтобы можно было тестировать бэкенд."""
    import re
    text = next((m["text"] for m in reversed(messages) if m["role"] == "user"), "").lower()
    
    parsed = {
        "city_id": None,
        "budget_rub": None,
        "categories": [],
        "constraints": {},
        "missing": []
    }

    # Ищем город
    if "таганрог" in text:
        parsed["city_id"] = "taganrog"
    elif "ростов" in text:
        parsed["city_id"] = "rostov"
    else:
        parsed["missing"].append("city_id")

    # Ищем бюджет (например, "до 15000", "до 15 000")
    budget_match = re.search(r"до\s*([\d\s]+)\s*(?:₽|руб|р\.)", text)
    if budget_match:
        # Убираем пробелы из числа
        budget_str = budget_match.group(1).replace(" ", "")
        parsed["budget_rub"] = int(budget_str)
    else:
        parsed["missing"].append("budget_rub")

    # Ищем категории
    if "стол" in text:
        parsed["categories"].append("table")
    if "кресл" in text:
        parsed["categories"].append("chair")
    if "ламп" in text:
        parsed["categories"].append("lamp")
        
    if not parsed["categories"]:
        parsed["missing"].append("categories")

    # Ищем ограничения (ширина)
    if "не шире метра" in text or "до 100 см" in text:
        parsed["constraints"]["table"] = {"width_cm": {"max": 100}}

    return parsed

def get_question_text(field: str) -> str:
    """Возвращает текст уточняющего вопроса."""
    questions = {
        "budget_rub": "Какой у вас бюджет на весь комплект?",
        "city_id": "В каком городе искать?",
        "categories": "Какие категории товаров нужны?"
    }
    return questions.get(field, "Уточните запрос.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, help="Путь к файлу catalog.json")
    args = parser.parse_args()

    try:
        # Читаем JSON из stdin
        input_data = json.load(sys.stdin)
        messages = input_data.get("messages", [])
        
        if not messages:
            raise ValueError("Пустой список messages")

        # 1. Загружаем каталог
        catalog = load_catalog(args.catalog)

        # 2. Парсим запрос (пока локальной заглушкой)
        parsed = parse_request(messages)

        # 3. Если чего-то не хватает — уточняем
        if parsed["missing"]:
            output = {
                "status": "clarify",
                "questions": [
                    {"field": field, "text": get_question_text(field)}
                    for field in parsed["missing"]
                ]
            }
            print(json.dumps(output, ensure_ascii=False))
            return

        # 4. Ищем комплекты
        result = solve(catalog, parsed)

        # 5. Формируем ответ
        if result["status"] == "no_match":
            output = {
                "status": "no_match",
                "message": result["reason"]
            }
        else:
            # Для каждого найденного комплекта делаем объяснение
            catalog_dict = {item["id"]: item for item in catalog}
            options = []
            for opt in result["options"]:
                # Собираем строку объяснения из названий товаров
                titles = [catalog_dict[lid]["title"] for lid in opt["listing_ids"]]
                explanation = f"В комплект входят: {', '.join(titles)}. Общая стоимость: {opt['total_rub']} ₽."
                
                options.append({
                    "listing_ids": opt["listing_ids"],
                    "total_rub": opt["total_rub"],
                    "explanation": explanation
                })
            
            output = {
                "status": "ok",
                "options": options
            }

        # Выводим строго один JSON в stdout
        print(json.dumps(output, ensure_ascii=False))

    except Exception as e:
        # При любой ошибке логируем в stderr и отдаем понятный JSON
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({
            "status": "clarify",
            "questions": [{"field": "retry", "text": "Произошла ошибка при обработке запроса. Попробуйте еще раз."}]
        }, ensure_ascii=False))

if __name__ == "__main__":
    main()
