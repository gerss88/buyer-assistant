import streamlit as st
import json
import subprocess

st.set_page_config(page_title="Avito Start", layout="wide", page_icon="🛒")

# --- ИНИЦИАЛИЗАЦИЯ ---
if "theme" not in st.session_state: st.session_state.theme = "light"
if "messages" not in st.session_state: st.session_state.messages = []
if "current_state" not in st.session_state: st.session_state.current_state = "start"
if "last_option" not in st.session_state: st.session_state.last_option = None

# --- ПЕРЕКЛЮЧАТЕЛЬ В САЙДБАРЕ (скрыт, управляем через шапку) ---
with st.sidebar:
    st.write("Настройки")
    is_dark = st.toggle("🌙 Тёмная тема", value=(st.session_state.theme == "dark"))
    st.session_state.theme = "dark" if is_dark else "light"

# --- ЦВЕТА ---
if st.session_state.theme == "dark":
    bg = "#1A1A1A"
    text = "#FFFFFF"
    bubble_user = "#2A2A2A"
    bubble_ai = "#333333"
    tag = "#444"
    input_bg = "#2A2A2A"
    border = "#444"
else:
    bg = "#FFFFFF"
    text = "#000000"
    bubble_user = "#F5F5F5"
    bubble_ai = "#F0F0F0"
    tag = "#F0F0F0"
    input_bg = "#F9F9F9"
    border = "#E5E5E5"

# --- КАСТОМНЫЙ CSS ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
    
    /* Скрываем стандартные элементы */
    header {{ visibility: hidden; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    
    .stApp {{
        background-color: {bg} !important;
        color: {text} !important;
        font-family: 'Inter', sans-serif;
        transition: background-color 0.4s ease;
    }}
    
    /* Шапка */
    .top-bar {{ display: flex; align-items: center; gap: 15px; padding-bottom: 20px; margin-bottom: 20px; }}
    .logo {{ font-weight: 900; font-size: 20px; color: {text}; }}
    .badge {{ background: {tag}; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: 600; color: {text}; }}
    
    /* Чат */
    .bubble-user {{
        background: {bubble_user}; padding: 15px 20px; border-radius: 20px; 
        font-size: 16px; width: fit-content; max-width: 80%; margin-bottom: 15px; 
        margin-left: auto; border-bottom-right-radius: 4px; color: {text} !important;
    }}
    .bubble-assistant {{
        background: {bubble_ai}; padding: 15px 20px; border-radius: 20px; 
        border-bottom-left-radius: 4px; font-size: 16px; width: fit-content; 
        max-width: 80%; margin-bottom: 15px; font-weight: 500; color: {text} !important;
    }}
    
    /* Теги */
    .tags {{ display: flex; gap: 8px; margin-bottom: 30px; flex-wrap: wrap; }}
    .tag {{ background: {tag}; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; color: {text}; }}
    
    /* Цена */
    .price-title {{ font-size: 12px; font-weight: 800; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;}}
    .main-price {{ font-size: 72px; font-weight: 900; margin: 0; letter-spacing: -3px; line-height: 1; color: {text}; }}
    .sub-price {{ font-size: 16px; color: #888; margin-top: 5px; font-weight: 500;}}
    
    /* Прогресс-бар */
    .progress-container {{ display: flex; gap: 4px; height: 10px; margin-bottom: 30px; border-radius: 5px; overflow: hidden; }}
    .seg-blue {{ background: #00AAFF; width: 40%; border-radius: 5px; }}
    .seg-green {{ background: #97CF26; width: 30%; border-radius: 5px; }}
    .seg-purple {{ background: #9B59B6; width: 20%; border-radius: 5px; }}
    .seg-empty {{ background: {border}; width: 10%; border-radius: 5px; border: 1px dashed #888; }}
    
    /* Карточки (яркие, текст внутри черный) */
    .cards-row {{ display: flex; gap: 15px; margin-bottom: 30px; }}
    .card {{ flex: 1; padding: 25px; border-radius: 24px; display: flex; flex-direction: column; justify-content: space-between; min-height: 200px; }}
    .card-blue {{ background: #D6F0FF; }}
    .card-green {{ background: #D4F5D4; }}
    .card-purple {{ background: #E8D6FF; }}
    .card-header {{ font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 10px; opacity: 0.6; color: #000; }}
    .card-title {{ font-size: 20px; font-weight: 900; margin-bottom: 8px; line-height: 1.2; color: #000; }}
    .card-desc {{ font-size: 14px; margin-bottom: 20px; line-height: 1.4; font-weight: 500; color: rgba(0,0,0,0.7); }}
    .card-price {{ font-size: 28px; font-weight: 900; margin-top: auto; color: #000; }}
    
    /* Кнопки */
    .stButton>button {{
        background-color: {tag} !important;
        color: {text} !important;
        border: 1px solid {border} !important;
        border-radius: 30px !important;
        padding: 10px 24px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{ border-color: #00AAFF !important; color: #00AAFF !important; }}
    
    /* Кнопка-ссылка */
    .link-btn {{ background: #00AAFF; color: white !important; padding: 14px 28px; border-radius: 30px; text-decoration: none; font-weight: 700; display: inline-block; margin-right: 10px; }}
    
    /* Поле ввода */
    .stChatInput {{ border-radius: 30px !important; border: 1px solid {border} !important; background: {input_bg} !important; }}
    .stChatInput textarea {{ color: {text} !important; }}
</style>
""", unsafe_allow_html=True)

# --- ФУНКЦИИ ---
def call_backend(messages):
    payload = json.dumps({"messages": messages})
    try:
        result = subprocess.run(["./run", "--catalog", "data/catalog.json"], input=payload, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        return {"status": "no_match", "message": f"Ошибка: {str(e)}"}

# --- ШАПКА ---
st.markdown(f"""
<div class="top-bar">
    <div class="logo">Avito Start</div>
    <div class="badge">ИИ-помощник покупателя</div>
</div>
""", unsafe_allow_html=True)

# --- ИСТОРИЯ ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="bubble-user">{msg["text"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bubble-assistant">{msg["text"]}</div>', unsafe_allow_html=True)

# --- ВВОД ---
if user_input := st.chat_input("Напишите, что нужно подобрать"):
    st.session_state.messages.append({"role": "user", "text": user_input})
    res = call_backend(st.session_state.messages)
    st.session_state.current_state = res["status"]
    
    if res["status"] == "ok":
        opt = res["options"][0]
        price_str = f"{opt['total_rub']:,}".replace(",", " ")
        st.session_state.messages.append({"role": "assistant", "text": f"Нашёл комплект. Итого: {price_str} ₽."})
        st.session_state.last_option = opt
    elif res["status"] == "clarify":
        st.session_state.messages.append({"role": "assistant", "text": res["questions"][0]["text"]})
    else:
        st.session_state.messages.append({"role": "assistant", "text": res["message"]})
    st.rerun()

# --- СОСТОЯНИЕ: OK ---
if st.session_state.current_state == "ok" and st.session_state.last_option:
    opt = st.session_state.last_option
    price_str = f"{opt['total_rub']:,}".replace(",", " ")
    
    st.markdown(f"""
    <div class="tags">
        <span class="tag">Таганрог</span>
        <span class="tag">до 15 000 ₽</span>
        <span class="tag">стол ≤ 100 см</span>
        <span class="tag">кресло</span>
        <span class="tag">лампа</span>
    </div>
    <div class="price-block">
        <div class="price-title">Комплект · Таганрог</div>
        <div class="main-price">{price_str} ₽</div>
    </div>
    <div class="progress-container">
        <div class="seg-blue"></div><div class="seg-green"></div><div class="seg-purple"></div><div class="seg-empty"></div>
    </div>
    <div class="cards-row">
        <div class="card card-blue">
            <div>
                <div class="card-header">Стол · {opt['listing_ids'][0]}</div>
                <div class="card-title">Письменный стол</div>
                <div class="card-desc">Ширина 95 см — подтверждено</div>
            </div>
            <div class="card-price">6 500 ₽</div>
        </div>
        <div class="card card-green">
            <div>
                <div class="card-header">Кресло · {opt['listing_ids'][1]}</div>
                <div class="card-title">Кресло</div>
                <div class="card-desc">Регулировка высоты: да</div>
            </div>
            <div class="card-price">4 200 ₽</div>
        </div>
        <div class="card card-purple">
            <div>
                <div class="card-header">Лампа · {opt['listing_ids'][2]}</div>
                <div class="card-title">Лампа</div>
                <div class="card-desc">Цена из каталога</div>
            </div>
            <div class="card-price">1 500 ₽</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Ссылки
    st.markdown("<div style='margin-bottom: 40px;'>", unsafe_allow_html=True)
    for lid in opt['listing_ids']:
        url = f"https://www.avito.ru/taganrog?q={lid}"
        st.markdown(f'<a href="{url}" target="_blank" class="link-btn">Открыть {lid}</a>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- СОСТОЯНИЕ: CLARIFY ---
elif st.session_state.current_state == "clarify":
    st.markdown(f"""
    <div style="margin-top: 20px;">
        <div style="font-size: 40px; font-weight: 900; line-height: 1.1; margin-bottom: 30px; color: {text};">Какой бюджет на весь комплект?</div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    if c1.button("10 000 ₽"): st.session_state.messages.append({"role": "user", "text": "До 10 000 ₽"}); st.rerun()
    if c2.button("15 000 ₽"): st.session_state.messages.append({"role": "user", "text": "До 15 000 ₽"}); st.rerun()
    if c3.button("20 000 ₽"): st.session_state.messages.append({"role": "user", "text": "До 20 000 ₽"}); st.rerun()

# --- СОСТОЯНИЕ: NO_MATCH ---
elif st.session_state.current_state == "no_match":
    st.markdown(f"""
    <div style="margin-top: 20px;">
        <div style="font-size: 120px; font-weight: 900; color: #FF4053; line-height: 1; margin-bottom: 10px;">0</div>
        <div style="font-size: 36px; font-weight: 900; margin-bottom: 20px; color: {text};">ПОЛНЫХ КОМПЛЕКТОВ</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Увеличить бюджет"): st.session_state.messages.append({"role": "user", "text": "Увеличить бюджет"}); st.rerun()
    if st.button("Ослабить ширину"): st.session_state.messages.append({"role": "user", "text": "Ослабить ширину"}); st.rerun()
