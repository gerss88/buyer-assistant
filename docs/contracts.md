# Контракты проекта

**Бэкенд: готов**

## CLI
./run --catalog data/catalog.json
- stdin → один JSON
- stdout → один JSON
- логи → stderr

## Вход
{"messages":[{"role":"user","text":"..."}]}

## Выход ok
{"status":"ok","options":[{"listing_ids":["t12","c04","l09"],"total_rub":12200,"explanation":"..."}]}

## Выход clarify
{"status":"clarify","questions":[{"field":"budget_rub","text":"Какой у вас бюджет на весь комплект?"}]}

## Выход no_match
{"status":"no_match","message":"В Таганроге нет стола шириной ≤ 100 см в бюджет 15 000 ₽"}

## Объявление
id, category, title, description, price_rub, city_id, attributes{}

## Атрибуты по категориям
- table: width_cm (number)
- chair: adjustable_height (bool)
- lamp: color_temperature_k (number)

## Внутренний контракт парсера (LLM ↔ solver)
{
  "city_id": "taganrog" | null,
  "budget_rub": 15000 | null,
  "categories": ["table","chair","lamp"],
  "constraints": {"table": {"width_cm": {"max": 100}}},
  "missing": ["budget_rub"]
}
