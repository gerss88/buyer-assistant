import streamlit as st
import json
import subprocess
import time

st.set_page_config(page_title="Avito Start", layout="wide", page_icon="🛒")

@st.cache_data
def load_catalog():
    with open("data/catalog.json", encoding="utf-8") as f:
        return {item["id"]: item for item in json.load(f)}

CATALOG = load_catalog()

# --- ИНИЦИАЛИЗАЦИЯ ---
if "theme" not in st.session_state: st.session_state.theme = "light"
if "messages" not in st.session_state: st.session_state.messages = []
if "waiting_for_response" not in st.session_state: st.session_state.waiting_for_response = False

# --- ЦВЕТА ---
if st.session_state.theme == "dark":
    bg = "#121212"
    text = "#FFFFFF"
    bubble_user = "#333333"
    bubble_ai = "#2A2A2A"
    tag = "#444"
    border = "#444"
    input_bg = "#1E1E1E"
else:
    bg = "#FFFFFF"
    text = "#000000"
    bubble_user = "#F5F5F5"
    bubble_ai = "#F0F0F0"
    tag = "#F0F0F0"
    border = "#E5E5E5"
    input_bg = "#FFFFFF"

# --- CSS С АНИМАЦИЯМИ ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
    
    header, #MainMenu, footer {{ visibility: hidden; }}
    .stApp, .main, .block-container, [data-testid="stAppViewContainer"] {{
        background-color: {bg} !important;
        color: {text} !important;
        font-family: 'Inter', sans-serif;
    }}
    [data-testid="stBottom"] > div, [data-testid="stBottom"] {{
        background-color: {bg} !important;
    }}
    p, h1, h2, h3, h4, h5, h6, span, div, label {{ color: {text} !important; }}
    
    .top-bar {{ display: flex; align-items: center; gap: 15px; padding-top: 10px; padding-bottom: 20px; }}
    .logo {{ font-weight: 900; font-size: 24px; color: {text} !important; line-height: 1; }}
    .badge {{ background: {tag}; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; color: {text} !important; display: inline-block; line-height: 1; }}
    
    @keyframes slideInUp {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .bubble-user {{ 
        background: {bubble_user}; padding: 15px 20px; border-radius: 20px; font-size: 16px; 
        width: fit-content; max-width: 80%; margin-bottom: 15px; margin-left: auto; 
        border-bottom-right-radius: 4px; color: {text} !important;
        animation: slideInUp 0.4s ease-out forwards;
    }}
    .bubble-assistant {{ 
        background: {bubble_ai}; padding: 15px 20px; border-radius: 20px; 
        border-bottom-left-radius: 4px; font-size: 16px; width: fit-content; 
        max-width: 80%; margin-bottom: 15px; font-weight: 500; color: {text} !important;
        animation: slideInUp 0.4s ease-out forwards;
    }}
    
    .welcome-screen {{ text-align: center; margin-top: 15vh; margin-bottom: 20px; animation: slideInUp 0.6s ease-out forwards; }}
    .welcome-title {{ font-size: 48px; font-weight: 900; margin-bottom: 10px; color: {text} !important; }}
    .welcome-subtitle {{ font-size: 18px; color: {text} !important; opacity: 0.7; }}

    .cards-row {{ display: flex; gap: 15px; margin-bottom: 30px; }}
    @keyframes popIn {{
        0% {{ transform: scale(0.95); opacity: 0; }}
        100% {{ transform: scale(1); opacity: 1; }}
    }}
    .card {{ 
        flex: 1; padding: 25px; border-radius: 24px; display: flex; flex-direction: column; 
        justify-content: space-between; min-height: 220px; 
        animation: popIn 0.5s ease-out forwards;
    }}
    .card-blue {{ background: #D6F0FF !important; }} .card-green {{ background: #D4F5D4 !important; }} .card-purple {{ background: #E8D6FF !important; }}
    .card-header {{ font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 10px; opacity: 0.6; color: #000 !important; }}
    .card-title {{ font-size: 20px; font-weight: 900; margin-bottom: 8px; line-height: 1.2; color: #000 !important; }}
    .card-desc {{ font-size: 14px; margin-bottom: 20px; line-height: 1.4; font-weight: 500; color: rgba(0,0,0,0.7) !important; }}
    .card-price {{ font-size: 28px; font-weight: 900; margin-top: auto; color: #000 !important; }}
    .main-price {{ font-size: 72px; font-weight: 900; margin: 0; letter-spacing: -3px; line-height: 1; color: {text} !important; }}
    
    [data-testid="stChatInput"] {{
        border: 2px solid {border} !important;
        border-radius: 30px !important;
        background-color: {input_bg} !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
        box-shadow: none !important;
    }}
    [data-testid="stChatInput"]:focus-within {{
        border-color: #00AAFF !important;
        box-shadow: 0 0 0 2px rgba(0,170,255,0.3) !important;
    }}
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] textarea:focus,
    [data-testid="stChatInput"] textarea:active,
    [data-testid="stChatInput"] input {{
        color: {text} !important;
        -webkit-text-fill-color: {text} !important;
    }}
    [data-testid="stChatInput"] textarea:focus, 
    [data-testid="stChatInput"] *:focus {{
        outline: none !important;
        box-shadow: none !important;
    }}
    
    .stButton>button {{
        background-color: {tag} !important;
        color: {text} !important;
        border: 1px solid {border} !important;
        border-radius: 30px !important;
        padding: 10px 15px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }}
    .stButton>button:hover {{
        border-color: #00AAFF !important;
        color: #00AAFF !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- ШАПКА ---
col1, col2, col3 = st.columns([8, 2, 2])
with col1:
    st.markdown('''
        <div class="top-bar">
            <div class="logo">Avito Start</div>
            <div class="badge">ИИ-помощник покупателя</div>
        </div>
    ''', unsafe_allow_html=True)
with col3:
    is_dark = st.toggle("🌙 Тёмная тема", value=(st.session_state.theme == "dark"))
    st.session_state.theme = "dark" if is_dark else "light"
    if is_dark != (bg == "#121212"):
        st.rerun()

def call_backend(messages):
    payload = json.dumps({"messages": messages})
    try:
        result = subprocess.run(["./run", "--catalog", "data/catalog.json"], input=payload, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        return {"status": "no_match", "message": f"Ошибка: {str(e)}"}

def render_cards(option):
    price_str = f"{option['total_rub']:,}".replace(",", " ")
    first_item = CATALOG.get(option['listing_ids'][0], {})
    city_id = first_item.get("city_id", "taganrog")
    city_name = {"taganrog": "Таганрог", "rostov-na-donu": "Ростов-на-Дону", "azov": "Азов"}.get(city_id, city_id)
    
    html = f'<div style="font-size: 12px; font-weight: 800; color: #888; text-transform: uppercase; margin-bottom: 5px;">Комплект · {city_name}</div>'
    html += f'<div class="main-price">{price_str} ₽</div>'
    html += '<div class="cards-row">'
    colors = ["card-blue", "card-green", "card-purple"]
    
    for idx, lid in enumerate(option['listing_ids']):
        item = CATALOG.get(lid, {})
        title = item.get("title", lid)
        price = item.get("price_rub", 0)
        price_fmt = f"{price:,}".replace(",", " ")
        cat_name = {"table": "Стол", "chair": "Кресло", "lamp": "Лампа"}.get(item.get("category"), "Товар")
        
        attrs = item.get("attributes", {})
        specs = []
        if "width_cm" in attrs: specs.append(f"Ширина: {attrs['width_cm']} см")
        if "adjustable_height" in attrs: specs.append(f"Регулировка: {'да' if attrs['adjustable_height'] else 'нет'}")
        if "color_temperature_k" in attrs: specs.append(f"Свет: {attrs['color_temperature_k']} К")
        specs_html = "<br>".join(specs) if specs else "Характеристики не указаны"
        
        html += f'''
        <div class="card {colors[idx % 3]}">
            <div>
                <div class="card-header">{cat_name} · {lid}</div>
                <div class="card-title">{title}</div>
                <div class="card-desc">{specs_html}</div>
            </div>
            <div class="card-price">{price_fmt} ₽</div>
        </div>'''
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown(f"""
    <div class="welcome-screen">
        <div class="welcome-title">Что вас интересует?</div>
        <div class="welcome-subtitle">Опишите, какие товары вы ищете, и я подберу для вас идеальный комплект в рамках бюджета.</div>
    </div>
    """, unsafe_allow_html=True)

# --- ОТРИСОВКА ИСТОРИИ ---
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f'<div class="bubble-user">{msg["text"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bubble-assistant">{msg["text"]}</div>', unsafe_allow_html=True)
        
        if "option" in msg:
            render_cards(msg["option"])
            
        elif "clarify" in msg:
            question_only = msg["text"].split(".")[-1].lower()
            
            if "бюджет" in question_only or "сколько" in question_only or "сумм" in question_only:
                st.markdown("<div style='font-size: 14px; opacity: 0.6; margin-bottom: 8px;'>Выберите бюджет:</div>", unsafe_allow_html=True)
                c1, c2, c3, _ = st.columns([1.5, 1.5, 1.5, 5])
                if c1.button("10 000 ₽", key=f"b1_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "До 10 000 ₽"}); st.session_state.waiting_for_response = True; st.rerun()
                if c2.button("15 000 ₽", key=f"b2_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "До 15 000 ₽"}); st.session_state.waiting_for_response = True; st.rerun()
                if c3.button("20 000 ₽", key=f"b3_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "До 20 000 ₽"}); st.session_state.waiting_for_response = True; st.rerun()

            elif "город" in question_only:
                st.markdown("<div style='font-size: 14px; opacity: 0.6; margin-bottom: 8px;'>Уточните город:</div>", unsafe_allow_html=True)
                c1, c2, c3, _ = st.columns([1.5, 1.5, 1.5, 5])
                if c1.button("Таганрог", key=f"c1_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "Таганрог"}); st.session_state.waiting_for_response = True; st.rerun()
                if c2.button("Ростов-на-Дону", key=f"c2_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "Ростов-на-Дону"}); st.session_state.waiting_for_response = True; st.rerun()
                if c3.button("Азов", key=f"c3_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "Азов"}); st.session_state.waiting_for_response = True; st.rerun()

            elif "категор" in question_only or "товар" in question_only or "что" in question_only:
                st.markdown("<div style='font-size: 14px; opacity: 0.6; margin-bottom: 8px;'>Что именно ищем?</div>", unsafe_allow_html=True)
                c1, c2, c3, _ = st.columns([1.5, 1.5, 1.5, 5])
                if c1.button("Стол и кресло", key=f"k1_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "Стол и кресло"}); st.session_state.waiting_for_response = True; st.rerun()
                if c2.button("Всё для работы", key=f"k2_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "Стол, кресло, лампа"}); st.session_state.waiting_for_response = True; st.rerun()
                if c3.button("Только лампу", key=f"k3_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "text": "Лампа"}); st.session_state.waiting_for_response = True; st.rerun()

# --- ВВОД ---
if user_input := st.chat_input("Напишите, что нужно подобрать"):
    st.session_state.messages.append({"role": "user", "text": user_input})
    st.session_state.waiting_for_response = True
    st.rerun()

# --- ПОЛУЧЕНИЕ ОТВЕТА ---
if st.session_state.waiting_for_response:
    st.session_state.waiting_for_response = False
    with st.spinner("Ищу подходящие варианты..."):
        res = call_backend(st.session_state.messages)
        
        if res["status"] == "ok":
            opt = res["options"][0]
            price_str = f"{opt['total_rub']:,}".replace(",", " ")
            response_text = f"Нашёл комплект. Итого: {price_str} ₽."
            
            message_placeholder = st.empty()
            full_response = ""
            for chunk in response_text.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(f'<div class="bubble-assistant">{full_response}▌</div>', unsafe_allow_html=True)
            message_placeholder.markdown(f'<div class="bubble-assistant">{full_response}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "text": response_text, "option": opt})
            
        elif res["status"] == "clarify":
            user_text = next((m["text"] for m in reversed(st.session_state.messages) if m["role"] == "user"), "").lower()
            is_first_turn = not any("assistant" in m["role"] for m in st.session_state.messages[:-1])
            
            if is_first_turn and len(user_text.split()) < 3:
                prefix = "Я не совсем понял ваш запрос. "
            elif "таганрог" in user_text or "ростов" in user_text or "азов" in user_text:
                prefix = "Отлично, город понял. "
            elif "000" in user_text or "₽" in user_text:
                prefix = "Принял бюджет. "
            else:
                prefix = "Хорошо, уточним ещё одну деталь. "
                
            response_text = prefix + res["questions"][0]["text"]
            message_placeholder = st.empty()
            full_response = ""
            for chunk in response_text.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(f'<div class="bubble-assistant">{full_response}▌</div>', unsafe_allow_html=True)
            message_placeholder.markdown(f'<div class="bubble-assistant">{full_response}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "text": response_text, "clarify": True})
            
        else:
            response_text = res["message"]
            message_placeholder = st.empty()
            full_response = ""
            for chunk in response_text.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(f'<div class="bubble-assistant">{full_response}▌</div>', unsafe_allow_html=True)
            message_placeholder.markdown(f'<div class="bubble-assistant">{full_response}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "text": response_text})
    st.rerun()
