const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = __dirname;
const envFile = path.join(ROOT, '.env');
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf8').replace(/^\uFEFF/, '').split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!match || match[1] in process.env) continue;
    process.env[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2');
  }
}

const catalogPath = path.join(ROOT, 'data/catalog.json');
const citiesPath = path.join(ROOT, 'data/cities.json');
const categoriesPath = path.join(ROOT, 'data/categories.json');
const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
const cities = JSON.parse(fs.readFileSync(citiesPath, 'utf8'));
const categories = JSON.parse(fs.readFileSync(categoriesPath, 'utf8'));
const cityById = Object.fromEntries(cities.map(city => [city.id, city]));
const categoryById = Object.fromEntries(categories.map(category => [category.id, category]));
const { parseConversation, validateRequirements } = require('./parse');

function json(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(data));
}

function within(value, constraint) {
  if (value === undefined || value === null || !constraint) return false;
  const expected = constraint.value;
  switch (constraint.operator) {
    case 'min': return typeof value === 'number' && value >= expected;
    case 'max': return typeof value === 'number' && value <= expected;
    case 'min_exclusive': return typeof value === 'number' && value > expected;
    case 'max_exclusive': return typeof value === 'number' && value < expected;
    case 'exact': return typeof value === 'number' && value === expected;
    case 'eq': return typeof value === 'string' && typeof expected === 'string'
      ? value.toLocaleLowerCase('ru') === expected.toLocaleLowerCase('ru')
      : value === expected;
    default: return false;
  }
}

function qualifies(ad, requirements) {
  if (ad.city_id !== requirements.city_id) return false;
  const attributes = ad.attributes || {};
  return requirements.constraints.filter(constraint => constraint.category === ad.category).every(constraint =>
    Object.prototype.hasOwnProperty.call(attributes, constraint.attribute) && within(attributes[constraint.attribute], constraint)
  );
}

function findOptions(requirements, sourceCatalog = catalog) {
  const categoryBudgets = new Map((requirements.category_budgets || []).map(item => [item.category, item.budget_rub]));
  const totalBudget = requirements.budget_rub ?? requirements.categories.reduce((sum, category) => sum + (categoryBudgets.get(category) ?? 0), 0);
  const pools = requirements.categories.map(category => sourceCatalog
    .filter(ad => ad.category === category && qualifies(ad, requirements) && (!categoryBudgets.has(category) || ad.price_rub <= categoryBudgets.get(category)))
    .sort((left, right) => left.price_rub - right.price_rub));
  if (pools.some(pool => pool.length === 0)) return [];

  const cheapestRest = Array(pools.length + 1).fill(0);
  for (let i = pools.length - 1; i >= 0; i--) cheapestRest[i] = cheapestRest[i + 1] + pools[i][0].price_rub;
  const results = [];
  function visit(index, picked, total) {
    if (results.length >= 3 || total + cheapestRest[index] > totalBudget) return;
    if (index === pools.length) {
      results.push({ ads: picked, total });
      results.sort((left, right) => left.total - right.total);
      if (results.length > 3) results.pop();
      return;
    }
    if (results.length === 3 && total + cheapestRest[index] >= results[2].total) return;
    for (const ad of pools[index]) {
      if (total + ad.price_rub + cheapestRest[index + 1] > totalBudget) break;
      visit(index + 1, [...picked, ad], total + ad.price_rub);
      if (results.length >= 3) break;
    }
  }
  visit(0, [], 0);
  return results;
}

function describeAttributes(ad) {
  const definitions = categoryById[ad.category]?.attributes || {};
  return Object.entries(ad.attributes || {}).filter(([key]) => definitions[key]).map(([key, value]) => {
    const definition = definitions[key];
    const display = typeof value === 'boolean' ? (value ? 'да' : 'нет') : String(value);
    return `${definition.name || key}: ${display}${definition.unit ? ` ${definition.unit}` : ''}`;
  }).join(', ');
}

function answer(requirements, sourceCatalog = catalog) {
  const missing = [];
  const categoryNames = categories.map(category => category.name).join(', ');
  const cityNames = cities.map(city => city.name).join(', ');
  if (!requirements.categories.length || requirements.unsupported_categories.length) {
    const ask = requirements.unsupported_categories.length
      ? `В каталоге нет категории «${requirements.unsupported_categories.join(', ')}». Что из каталога подобрать: ${categoryNames}?`
      : `Какие товары нужны? В каталоге есть: ${categoryNames}.`;
    missing.push({ field: 'categories', text: ask });
  }
  if (!requirements.city_id || !cityById[requirements.city_id]) {
    const ask = requirements.city_mentioned
      ? `В каталоге пока нет города «${requirements.city_mentioned}». Выберите город: ${cityNames}.`
      : `В каком городе будете забирать товары: ${cityNames}?`;
    missing.push({ field: 'city_id', text: ask });
  }
  const categoryBudgets = new Map((requirements.category_budgets || []).map(item => [item.category, item.budget_rub]));
  const everyCategoryHasBudget = requirements.categories.length > 0 && requirements.categories.every(category => categoryBudgets.has(category));
  if (requirements.budget_rub === null && !everyCategoryHasBudget) missing.push({ field: 'budget_rub', text: requirements.categories.length > 1 ? 'Какой общий бюджет рассматриваете на весь комплект? Отдельные лимиты по товарам я сохраню.' : 'Какой бюджет рассматриваете на эту покупку?' });
  if (requirements.unsupported_constraints?.length) {
    const details = requirements.unsupported_constraints.map(item => {
      const categoryName = categoryById[item.category]?.name || item.category;
      return `«${item.attribute_name}» (${categoryName.toLocaleLowerCase('ru')}: ${item.requested_value})`;
    });
    missing.push({
      field: 'unsupported_constraints',
      text: `В каталоге нет структурированной характеристики для ${details.join(', ')}. Я не буду игнорировать это условие или показывать непроверенные объявления как подходящие. Можно продолжить подбор без этого требования.`,
      suggestions: requirements.unsupported_constraints.map(item => ({
        label: `Продолжить без «${item.attribute_name}»`,
        value: `Убери требование «${item.attribute_name}» для категории «${categoryById[item.category]?.name || item.category}» и продолжи подбор без него.`
      }))
    });
  }
  if (missing.length) return { status: 'clarify', questions: missing };

  const options = findOptions(requirements, sourceCatalog);
  if (!options.length) {
    const pools = requirements.categories.map(category => sourceCatalog.filter(ad => ad.category === category && qualifies(ad, requirements) && (!categoryBudgets.has(category) || ad.price_rub <= categoryBudgets.get(category))));
    const unavailable = requirements.categories.filter((category, index) => pools[index].length === 0);
    const place = cityById[requirements.city_id].name;
    const message = unavailable.length
      ? `В ${place} не нашёл ${unavailable.map(category => categoryById[category].name.toLowerCase()).join(', ')} с такими характеристиками. Можно ослабить ограничение или выбрать другой город.`
      : `Самый недорогой полный комплект в ${place} стоит ${pools.reduce((sum, pool) => sum + Math.min(...pool.map(ad => ad.price_rub)), 0).toLocaleString('ru-RU')} ₽, это выше бюджета ${requirements.budget_rub.toLocaleString('ru-RU')} ₽.`;
    return { status: 'no_match', message };
  }
  return { status: 'ok', options: options.map(option => ({
    listing_ids: option.ads.map(ad => ad.id),
    total_rub: option.total,
    explanation: option.ads.map(ad => {
      const attributes = describeAttributes(ad);
      return `${categoryById[ad.category].name.toLowerCase()}: «${ad.title}» — ${ad.price_rub.toLocaleString('ru-RU')} ₽${attributes ? `, ${attributes}` : ''}`;
    }).join('; ')
  })) };
}

const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8' };
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (req.method === 'GET' && url.pathname === '/api/catalog') return json(res, 200, { catalog, cities, categories });
  if (req.method === 'POST' && url.pathname === '/api/chat') {
    let raw = '';
    req.on('data', chunk => { raw += chunk; if (raw.length > 200000) req.destroy(); });
    req.on('end', async () => {
      try {
        const body = JSON.parse(raw);
        if (!Array.isArray(body.messages) || !body.messages.length || body.messages.length > 20 || body.messages[0]?.role !== 'user' || body.messages.at(-1)?.role !== 'user' || body.messages.some((message, index) => !['user', 'assistant'].includes(message.role) || typeof message.text !== 'string' || !message.text.trim() || (index && body.messages[index - 1].role === message.role))) {
          return json(res, 400, { error: 'Передайте корректную историю диалога: до 20 чередующихся сообщений.' });
        }
        const requirements = await parseConversation(body.messages, {
          cities, categories,
          baseUrl: process.env.LLM_BASE_URL,
          model: process.env.LLM_MODEL,
          apiKey: process.env.LLM_API_KEY,
          userAgent: process.env.LLM_USER_AGENT
        });
        json(res, 200, { result: answer(requirements), requirements });
      } catch (error) {
        console.error(error.message || error);
        json(res, 502, { error: error.message || 'Не удалось обработать запрос.' });
      }
    });
    return;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') return json(res, 405, { error: 'Method not allowed' });
  const requested = url.pathname === '/' ? '/index.html' : url.pathname;
  const publicRoot = path.resolve(ROOT, 'public');
  const file = path.resolve(publicRoot, `.${requested}`);
  if (!file.startsWith(publicRoot + path.sep)) return json(res, 403, { error: 'Forbidden' });
  fs.readFile(file, (error, data) => {
    if (error) return json(res, 404, { error: 'Not found' });
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
    res.end(req.method === 'HEAD' ? undefined : data);
  });
});

const port = Number(process.env.PORT || 4173);
if (require.main === module) server.listen(port, '127.0.0.1', () => console.log(`Локальный сайт: http://127.0.0.1:${port}`));

module.exports = { answer, describeAttributes, findOptions, qualifies, validateRequirements, within, catalog, cities, categories };
