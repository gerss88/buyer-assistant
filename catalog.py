import json

VALID_CATEGORIES = {"table", "chair", "lamp"}

def load_catalog(catalog_path: str, cities_path: str = "data/cities.json") -> list[dict]:
    """Загружает и валидирует каталог товаров."""
    with open(catalog_path, encoding="utf-8") as f:
        catalog = json.load(f)
        
    with open(cities_path, encoding="utf-8") as f:
        cities_data = json.load(f)

    # Адаптируемся под формат городов (список объектов)
    if isinstance(cities_data, list):
        valid_cities = {city["id"] for city in cities_data}
    else:
        valid_cities = set(cities_data.keys())

    seen_ids = set()
    for item in catalog:
        # Валидация обязательных полей
        assert item["id"] not in seen_ids, f"Дубликат ID: {item['id']}"
        seen_ids.add(item["id"])
        
        assert item["category"] in VALID_CATEGORIES, f"Неизвестная категория: {item['category']}"
        assert isinstance(item["price_rub"], int) and item["price_rub"] > 0, f"Неверная цена у {item['id']}"
        assert item["city_id"] in valid_cities, f"Неизвестный город {item['city_id']} у {item['id']}"
        assert isinstance(item.get("attributes"), dict), f"Нет поля attributes у {item['id']}"
        
    return catalog
