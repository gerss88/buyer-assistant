const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const cities = require(path.join(root, 'data/cities.json'));
const catalogPath = path.join(root, 'data/catalog.json');
const catalog = require(catalogPath);
const priceFactors = { taganrog: 1, 'rostov-na-donu': 1.12, azov: 0.95, moscow: 1.48, 'saint-petersburg': 1.32, kazan: 1.08 };

function scaledPrice(cityId, base) { return Math.round(base * (priceFactors[cityId] || 1) / 100) * 100; }
function add(city, category, index, title, description, basePrice, attributes) {
  const id = `extension-${city.id}-${category}-${String(index).padStart(2, '0')}`;
  if (catalog.some(ad => ad.id === id)) return;
  catalog.push({ id, category, title, description, price_rub: scaledPrice(city.id, basePrice), city_id: city.id, attributes });
}

// Add city coverage for the starter categories with varied and missing fields.
for (const city of cities.filter(item => !['taganrog', 'rostov-na-donu', 'azov'].includes(item.id))) {
  [
    ['table', 'Письменный стол', 'Лаконичный письменный стол, состояние хорошее.', 3900, { width_cm: 80 }],
    ['table', 'Рабочий стол', 'Прочный рабочий стол для дома.', 5200, { width_cm: 100 }],
    ['table', 'Стол для кабинета', 'Вместительный стол, можно осмотреть при встрече.', 6100, { width_cm: 120 }],
    ['table', 'Стол после переезда', 'Стол после переезда. Точный размер не измеряли.', 3000, {}],
    ['chair', 'Кресло с регулировкой', 'Рабочее кресло, высота регулируется.', 4200, { adjustable_height: true }],
    ['chair', 'Простое кресло', 'Устойчивое кресло без регулировки высоты.', 2600, { adjustable_height: false }],
    ['chair', 'Компьютерное кресло', 'Кресло для рабочего места, высота меняется.', 5600, { adjustable_height: true }],
    ['chair', 'Кресло для комнаты', 'Удобное кресло, механизм не проверяли.', 1800, {}],
    ['lamp', 'Настольная лампа', 'Лампа для рабочего стола, свет 4000 К.', 1200, { color_temperature_k: 4000 }],
    ['lamp', 'Лампа тёплого света', 'Компактная лампа с тёплым светом.', 900, { color_temperature_k: 3000 }],
    ['lamp', 'Яркая настольная лампа', 'Светильник с холодным светом 6500 К.', 1500, { color_temperature_k: 6500 }],
    ['lamp', 'Лампа для дома', 'Рабочая лампа, температура света не указана.', 700, {}]
  ].forEach((row, index) => add(city, row[0], index + 1, row[1], row[2], row[3], row[4]));
}

const products = {
  sofa: [
    ['Диван-кровать компактный', 'Диван раскладывается, два посадочных места.', 28000, { width_cm: 160, seats: 2, sleeping_function: true }],
    ['Трёхместный диван', 'Трёхместный диван, механизм раскладывания исправен.', 48000, { width_cm: 210, seats: 3, sleeping_function: true }],
    ['Прямой диван', 'Прямой диван на два места, не раскладывается.', 35000, { width_cm: 180, seats: 2, sleeping_function: false }],
    ['Узкий диван-кровать', 'Небольшой диван, раскладывается, ширина 145 см.', 31500, { width_cm: 145, seats: 2, sleeping_function: true }]
  ],
  bed: [
    ['Односпальная кровать', 'Кровать шириной 90 см, без ящиков.', 16000, { width_cm: 90, has_storage: false }],
    ['Кровать с ящиками', 'Двуспальная кровать, есть ящики для хранения.', 34000, { width_cm: 160, has_storage: true }],
    ['Кровать двуспальная', 'Двуспальная кровать без встроенного хранения.', 26000, { width_cm: 140, has_storage: false }],
    ['Широкая кровать с хранением', 'Кровать шириной 180 см с местом для хранения.', 42000, { width_cm: 180, has_storage: true }]
  ],
  wardrobe: [
    ['Шкаф двухдверный', 'Двухдверный шкаф для спальни.', 17000, { width_cm: 80, height_cm: 180, door_count: 2 }],
    ['Шкаф для одежды', 'Высокий шкаф с тремя дверями.', 33000, { width_cm: 120, height_cm: 210, door_count: 3 }],
    ['Компактный шкаф', 'Компактный шкаф, две двери.', 23000, { width_cm: 100, height_cm: 190, door_count: 2 }],
    ['Однодверный шкаф', 'Узкий шкаф для небольшой комнаты.', 12500, { width_cm: 55, height_cm: 165, door_count: 1 }]
  ],
  refrigerator: [
    ['Компактный холодильник', 'Холодильник объёмом 120 л, без No Frost.', 21000, { volume_l: 120, no_frost: false }],
    ['Холодильник No Frost', 'Холодильник 250 л с системой No Frost.', 49000, { volume_l: 250, no_frost: true }],
    ['Холодильник для кухни', 'Вместительный холодильник, объём 180 л.', 35000, { volume_l: 180, no_frost: false }],
    ['Большой холодильник No Frost', 'Вместительный холодильник с системой No Frost.', 62000, { volume_l: 320, no_frost: true }]
  ]
};
const categoryStartIndex = { sofa: 1, bed: 1, wardrobe: 1, refrigerator: 1 };
for (const city of cities) for (const [category, records] of Object.entries(products)) {
  records.forEach(([title, description, basePrice, attributes], index) => add(city, category, categoryStartIndex[category] + index, title, description, basePrice, attributes));
}

// A few extra offers across the starter categories fill the remaining room
// under the 250-listing contract ceiling without changing category metadata.
const extraStarterOffers = [
  ['taganrog', 'table', 'Стол с широкой столешницей', 'Просторный письменный стол шириной 140 см.', 7200, { width_cm: 140 }],
  ['moscow', 'table', 'Компактный стол для ноутбука', 'Небольшой стол шириной 60 см.', 4500, { width_cm: 60 }],
  ['kazan', 'table', 'Стол после ремонта', 'Стол в хорошем состоянии, ширина 110 см.', 5600, { width_cm: 110 }],
  ['rostov-na-donu', 'chair', 'Кресло с мягкой спинкой', 'Кресло, регулировку высоты не проверяли.', 3500, {}],
  ['saint-petersburg', 'chair', 'Кресло для рабочего места', 'Высота кресла регулируется.', 6200, { adjustable_height: true }],
  ['azov', 'lamp', 'Лампа нейтрального света', 'Настольная лампа, цветовая температура 4500 К.', 1300, { color_temperature_k: 4500 }],
  ['moscow', 'lamp', 'Настенный светильник', 'Светильник, цветовая температура не указана.', 1700, {}]
];
const starterIndexes = { table: 5, chair: 9, lamp: 13 };
for (const [cityId, category, title, description, basePrice, attributes] of extraStarterOffers) {
  const city = cities.find(item => item.id === cityId);
  if (!city) throw new Error(`Unknown city in extra offer: ${cityId}`);
  add(city, category, starterIndexes[category]++, title, description, basePrice, attributes);
}

const ids = new Set();
for (const ad of catalog) {
  if (ids.has(ad.id)) throw new Error(`Duplicate listing id: ${ad.id}`);
  ids.add(ad.id);
}
if (catalog.length > 250) throw new Error(`Expanded catalog exceeds the contract limit: ${catalog.length}`);
fs.writeFileSync(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`, 'utf8');
console.log(`Wrote ${catalog.length} synthetic listings for ${cities.length} cities.`);
