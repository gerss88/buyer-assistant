const $ = selector => document.querySelector(selector);
const history = [];
let listings = [];
let cities = [];
let categories = [];
let busy = false;

fetch('/api/catalog').then(response => response.json()).then(data => {
  listings = data.catalog || [];
  cities = data.cities || [];
  categories = data.categories || [];
}).catch(() => {});

const price = value => `${Number(value).toLocaleString('ru-RU')} ₽`;
const categoryById = id => categories.find(item => item.id === id);
const cityName = id => cities.find(item => item.id === id)?.name || '';
const attributeLabel = listing => {
  const definitions = categoryById(listing.category)?.attributes || {};
  return Object.entries(listing.attributes || {}).filter(([key]) => definitions[key]).map(([key, value]) => {
    const definition = definitions[key];
    const display = typeof value === 'boolean' ? (value ? 'да' : 'нет') : String(value);
    return `${definition.name || key}: ${display}${definition.unit ? ` ${definition.unit}` : ''}`;
  }).join(' · ');
};
const conditionName = constraint => {
  const definition = categoryById(constraint.category)?.attributes?.[constraint.attribute];
  return `${categoryById(constraint.category)?.name || constraint.category} · ${definition?.name || constraint.attribute}`;
};

function scrollToBottom() { const panel = $('#conversation'); panel.scrollTop = panel.scrollHeight; }
function hideWelcome() { const welcome = $('#welcome'); if (welcome) welcome.remove(); }

function addMessage(role, text, { track = true, error = false } = {}) {
  if (track) history.push({ role, text });
  hideWelcome();
  const row = document.createElement('div');
  row.className = `message ${role === 'user' ? 'user-message' : 'assistant-message'}${error ? ' error-message' : ''}`;
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text;
  const time = document.createElement('time');
  time.textContent = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date());
  row.append(bubble, time); $('#conversation').append(row); scrollToBottom(); return row;
}

function addReplies(parent, options, mode = 'reply') {
  if (!options.length) return;
  const group = document.createElement('div'); group.className = 'quick-replies';
  options.forEach(option => {
    const button = document.createElement('button'); button.type = 'button'; button.textContent = option.label;
    button.dataset[option.mode || mode] = option.value;
    group.append(button);
  });
  parent.append(group);
}

function clarificationReplies(result) {
  const fields = new Set(result.questions.map(question => question.field));
  if (fields.has('budget_rub')) return [
    { label: '10 000 ₽', value: '10 000 ₽' }, { label: '15 000 ₽', value: '15 000 ₽' },
    { label: '20 000 ₽', value: '20 000 ₽' }, { label: 'Свой бюджет', value: '', mode: 'fill' }
  ];
  if (fields.has('city_id')) return cities.map(city => ({ label: city.name, value: city.name }));
  if (fields.has('categories')) return categories.map(category => ({ label: category.name, value: category.name }));
  return [];
}

function resultCard(option, index, count, requirements) {
  const ads = option.listing_ids.map(id => listings.find(item => item.id === id)).filter(Boolean);
  const card = document.createElement('article'); card.className = 'result-card'; card.dataset.variant = String(index);
  const kicker = document.createElement('div'); kicker.className = 'result-kicker';
  kicker.textContent = `${ads.length === 1 ? (categoryById(ads[0]?.category)?.name || 'Товар').toLocaleUpperCase('ru') : 'КОМПЛЕКТ'} · ${cityName(ads[0]?.city_id)}`;
  const header = document.createElement('div'); header.className = 'result-heading';
  const total = document.createElement('strong'); total.className = 'result-total'; total.textContent = price(option.total_rub);
  const budget = document.createElement('span'); budget.className = 'budget-note';
  if (requirements.budget_rub != null) {
    const remaining = requirements.budget_rub - option.total_rub;
    budget.textContent = `из ${price(requirements.budget_rub)} · запас ${price(remaining)}`;
  }
  header.append(total, budget);
  const meter = document.createElement('div'); meter.className = 'price-meter';
  const maximum = Math.max(option.total_rub, requirements.budget_rub || option.total_rub, 1);
  ads.forEach((ad, itemIndex) => {
    const segment = document.createElement('i'); segment.style.flexGrow = String(Math.max(1, ad.price_rub)); segment.dataset.color = String(itemIndex % 3); meter.append(segment);
  });
  const spare = document.createElement('i'); spare.className = 'meter-spare'; spare.style.flexGrow = String(Math.max(0, maximum - option.total_rub)); meter.append(spare);
  const items = document.createElement('div'); items.className = 'result-items';
  ads.forEach(ad => {
    const row = document.createElement('article'); row.className = 'result-item'; row.tabIndex = 0;
    const id = document.createElement('span'); id.className = 'item-kicker'; id.textContent = `${(categoryById(ad.category)?.name || ad.category).toLocaleUpperCase('ru')} · ${ad.id}`;
    const info = document.createElement('div'); info.className = 'item-info';
    const title = document.createElement('strong'); title.textContent = ad.title;
    const attributes = attributeLabel(ad);
    const meta = document.createElement('span'); meta.textContent = attributes || 'Характеристики не указаны';
    const amount = document.createElement('strong'); amount.className = 'item-price'; amount.textContent = price(ad.price_rub);
    const description = document.createElement('p'); description.className = 'item-description';
    description.textContent = ad.description || 'Описание не добавлено.';
    info.append(title, meta); row.append(id, info, amount, description); items.append(row);
  });
  const descriptions = document.createElement('div'); descriptions.className = 'listing-descriptions'; descriptions.hidden = true;
  ads.forEach(ad => {
    const paragraph = document.createElement('p');
    const label = document.createElement('strong'); label.textContent = `${ad.title}: `;
    paragraph.append(label, document.createTextNode(ad.description || 'Описание не добавлено.'));
    descriptions.append(paragraph);
  });
  const actions = document.createElement('div'); actions.className = 'result-actions';
  const detailsButton = document.createElement('button'); detailsButton.type = 'button'; detailsButton.dataset.details = '';
  detailsButton.textContent = 'Открыть объявления';
  actions.append(detailsButton);
  card.append(kicker, header, meter, items, actions, descriptions);
  return card;
}

function showOptions(options, requirements) {
  const panel = $('#resultsContent'); panel.innerHTML = ''; panel.hidden = false; $('#resultsEmpty').hidden = true;
  const collection = document.createElement('div'); collection.className = 'result-list';
  const tabs = document.createElement('div'); tabs.className = 'variant-tabs';
  options.forEach((option, index) => {
    const tab = document.createElement('button'); tab.type = 'button'; tab.dataset.variantTab = String(index); tab.textContent = `Вариант ${index + 1}`;
    if (index === 0) tab.classList.add('active'); tabs.append(tab);
    collection.append(resultCard(option, index, options.length, requirements));
  });
  panel.append(tabs, collection);
  collection.querySelectorAll('.result-card').forEach((card, index) => { card.hidden = index !== 0; });
  if (options.length > 1) {
    const controls = document.createElement('div'); controls.className = 'compare-controls';
    const compare = document.createElement('button'); compare.type = 'button'; compare.dataset.compare = ''; compare.textContent = 'Сравнить варианты';
    const cheaper = document.createElement('button'); cheaper.type = 'button'; cheaper.dataset.cheaper = ''; cheaper.textContent = 'Дешевле';
    const comparePanel = document.createElement('div'); comparePanel.className = 'comparison'; comparePanel.hidden = true;
    options.forEach((option, index) => {
      const row = document.createElement('div'); row.className = 'comparison-row';
      const name = document.createElement('span'); name.textContent = index === 0 ? 'Лучший вариант' : `Вариант ${index + 1}`;
      const amount = document.createElement('strong'); amount.textContent = price(option.total_rub);
      const diff = document.createElement('small'); diff.textContent = index === 0 ? 'самый доступный' : `+${price(option.total_rub - options[0].total_rub)} к первому`;
      row.append(name, amount, diff); comparePanel.append(row);
    });
    controls.append(compare, cheaper); panel.append(controls, comparePanel);
  }
  const note = document.createElement('p'); note.className = 'catalog-note';
  note.textContent = 'Цены и характеристики проверены по каталогу. Текст объявления не меняет условия подбора.';
  panel.append(note); scrollToBottom();
}

function showNoMatchActions(requirements) {
  const row = document.createElement('div'); row.className = 'message assistant-message';
  const buttons = [
    { label: 'Изменить бюджет', value: 'Хочу увеличить бюджет до ', mode: 'fill' },
    ...requirements.constraints.map(constraint => ({ label: `Ослабить: ${conditionName(constraint)}`, value: `Больше не учитывай параметр «${categoryById(constraint.category)?.attributes?.[constraint.attribute]?.name || constraint.attribute}» для категории «${categoryById(constraint.category)?.name || constraint.category}»`, mode: 'reply' })),
    { label: 'Выбрать другой город', value: 'Хочу выбрать другой город: ', mode: 'fill' }
  ];
  addReplies(row, buttons, 'reply'); $('#conversation').append(row); scrollToBottom();
}

function renderResult(result, requirements) {
  if (result.status === 'clarify') {
    $('#resultsContent').hidden = true; $('#resultsEmpty').hidden = false;
    const text = result.questions.map(question => question.text).join('\n');
    const row = addMessage('assistant', text);
    addReplies(row, clarificationReplies(result));
  } else if (result.status === 'no_match') {
    $('#resultsContent').hidden = true; $('#resultsEmpty').hidden = false;
    addMessage('assistant', result.message);
    showNoMatchActions(requirements);
  } else if (result.status === 'ok') {
    addMessage('assistant', result.options.length === 1 ? 'Нашёл подходящий вариант. Весь состав и цены — ниже.' : `Собрал ${result.options.length} подходящих комплекта. Состав и цены каждого — ниже.`);
    showOptions(result.options, requirements);
  }
}

async function sendMessage(raw) {
  const text = raw.trim();
  if (!text || busy) return;
  // API accepts up to 20 alternating messages. Keep the latest context
  // instead of blocking the user after 20 messages.
  while (history.length >= 20) {
    // History is stored as user/assistant pairs; drop the oldest complete pair.
    history.splice(0, 2);
  }
  addMessage('user', text);
  $('#chatInput').value = ''; $('#chatInput').style.height = 'auto';
  busy = true; $('#sendButton').disabled = true; $('#chatInput').disabled = true;
  const typing = document.createElement('div'); typing.className = 'typing'; typing.textContent = 'Подбираю по каталогу…'; $('#conversation').append(typing); scrollToBottom();
  try {
    const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages: history }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Не удалось получить ответ помощника.');
    renderResult(data.result, data.requirements);
  } catch (error) {
    addMessage('assistant', error.message || 'Не получилось связаться с помощником. Попробуйте ещё раз.', { error: true });
  } finally {
    typing.remove(); busy = false; $('#sendButton').disabled = false; $('#chatInput').disabled = false; $('#chatInput').focus();
  }
}

$('#chatForm').addEventListener('submit', event => { event.preventDefault(); sendMessage($('#chatInput').value); });
$('#chatInput').addEventListener('input', event => { event.target.style.height = 'auto'; event.target.style.height = `${Math.min(event.target.scrollHeight, 108)}px`; });
$('#chatInput').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('#chatForm').requestSubmit(); } });
$('#conversation').addEventListener('click', event => {
  const button = event.target.closest('button'); if (!button) return;
  if (button.dataset.reply) sendMessage(button.dataset.reply);
  if (button.dataset.fill !== undefined) { $('#chatInput').value = button.dataset.fill; $('#chatInput').focus(); }
  if (button.dataset.details !== undefined) {
    const description = button.closest('.result-card').querySelector('.listing-descriptions');
    description.hidden = !description.hidden; button.textContent = description.hidden ? 'Открыть объявления' : 'Скрыть описания';
  }
  if (button.dataset.compare !== undefined) {
    const panel = button.closest('.result-list').querySelector('.comparison'); panel.hidden = !panel.hidden;
    button.textContent = panel.hidden ? 'Сравнить варианты' : 'Скрыть сравнение';
  }
  if (button.dataset.cheaper !== undefined) {
    const cards = [...button.closest('.result-list').querySelectorAll('.result-card')];
    const showAll = cards.some(card => card.hidden);
    cards.forEach((card, index) => { card.hidden = !showAll && index > 0; });
    button.textContent = showAll ? 'Только дешевле' : 'Показать все варианты';
  }
});
$('#resultsPanel').addEventListener('click', event => {
  const button = event.target.closest('button'); if (!button) return;
  if (button.dataset.details !== undefined) {
    const description = button.closest('.result-card').querySelector('.listing-descriptions');
    description.hidden = !description.hidden; button.textContent = description.hidden ? 'Открыть объявления' : 'Скрыть описания';
  }
  if (button.dataset.variantTab !== undefined) {
    const selected = Number(button.dataset.variantTab);
    $('#resultsContent').querySelectorAll('.result-card').forEach((card, index) => { card.hidden = index !== selected; });
    $('#resultsContent').querySelectorAll('[data-variant-tab]').forEach((tab, index) => tab.classList.toggle('active', index === selected));
  }
  if (button.dataset.compare !== undefined) {
    const panel = $('#resultsContent').querySelector('.comparison'); panel.hidden = !panel.hidden;
    button.textContent = panel.hidden ? 'Сравнить варианты' : 'Скрыть сравнение';
  }
  if (button.dataset.cheaper !== undefined) {
    const tabs = [...$('#resultsContent').querySelectorAll('[data-variant-tab]')];
    const cards = [...$('#resultsContent').querySelectorAll('.result-card')];
    const showAll = button.dataset.showAll === 'true';
    cards.forEach((card, index) => { card.hidden = !showAll && index > 0; });
    tabs.forEach((tab, index) => { tab.hidden = !showAll && index > 0; tab.classList.toggle('active', index === 0); });
    button.dataset.showAll = String(!showAll); button.textContent = showAll ? 'Дешевле' : 'Показать все';
  }
});
$('#newChat').addEventListener('click', () => {
  if (busy) return;
  history.length = 0;
  $('#resultsContent').innerHTML = ''; $('#resultsContent').hidden = true; $('#resultsEmpty').hidden = false;
  $('#conversation').innerHTML = '<div class="welcome" id="welcome"><h1>Что подберём?</h1><p>Напишите, что нужно, в каком городе и на какую сумму. Можно обычными словами.</p><div class="suggestions" id="suggestions"><button type="button" data-reply="Стол не шире метра, кресло и лампа. Таганрог. До 15 000 ₽ за всё.">Стол, кресло и лампа · Таганрог</button><button type="button" data-reply="Диван до 50 000 ₽ в Москве">Диван · Москва</button><button type="button" data-reply="Кровать шириной от 140 см в Казани">Кровать · Казань</button></div></div>';
  $('#chatInput').value = ''; $('#chatInput').focus();
});
$('#themeToggle').addEventListener('click', () => {
  const isDark = document.body.classList.toggle('dark');
  $('#themeLabel').textContent = isDark ? 'Тёмная' : 'Светлая';
});
