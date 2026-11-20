import itertools

def _check_constraints(item: dict, constraints: dict) -> bool:
    """Проверяет, подходит ли товар под ограничения (например, ширина <= 100)."""
    attributes = item.get("attributes", {})
    
    for attr_name, rules in constraints.items():
        # Если покупатель просит характеристику, а её нет в карточке — товар НЕ подходит
        if attr_name not in attributes:
            return False
            
        val = attributes[attr_name]
        
        if "max" in rules and not (val <= rules["max"]):
            return False
        if "min" in rules and not (val >= rules["min"]):
            return False
        if "eq" in rules and val != rules["eq"]:
            return False
            
    return True

def solve(catalog: list[dict], parsed: dict) -> dict:
    city = parsed.get("city_id")
    budget = parsed.get("budget_rub")
    categories = parsed.get("categories", [])
    constraints = parsed.get("constraints", {})

    # Словарь для красивого вывода названий городов (без падежей)
    city_names = {
        "taganrog": "Таганрог",
        "rostov-na-donu": "Ростов-на-Дону",
        "azov": "Азов"
    }
    city_ru = city_names.get(city, city)

    # 1. Группируем подходящие товары по категориям
    by_category = {}
    for cat in categories:
        valid_items = []
        for item in catalog:
            if item["category"] == cat and item["city_id"] == city:
                if _check_constraints(item, constraints.get(cat, {})):
                    valid_items.append(item)
        
        # Если хотя бы одной категории нет — комплект собрать невозможно
        if not valid_items:
            return {
                "status": "no_match",
                "reason": f"В городе {city_ru} нет подходящих товаров в категории '{cat}' с нужными характеристиками."
            }
            
        by_category[cat] = sorted(valid_items, key=lambda x: x["price_rub"])

    # 2. Перебираем все возможные комбинации
    options = []
    for combo in itertools.product(*[by_category[c] for c in categories]):
        total_price = sum(item["price_rub"] for item in combo)
        
        if total_price <= budget:
            options.append({
                "listing_ids": [item["id"] for item in combo],
                "total_rub": total_price
            })
            
        if len(options) >= 3:
            break

    # 3. Если ничего не влезло в бюджет
    if not options:
        return {
            "status": "no_match",
            "reason": f"В городе {city_ru} не удалось собрать комплект в бюджет {budget} ₽. Попробуйте увеличить бюджет или убрать строгие ограничения."
        }

    return {"status": "ok", "options": options}
