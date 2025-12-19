import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import io

# ==========================================
# 1. 網頁設定
# ==========================================
st.set_page_config(page_title="Shopee AI v20.1", page_icon="💎")
st.title("💎 Shopee AI 視覺生成器 v20.1")
st.markdown("### 結構化腳本 + 真實模型清單 (防呆修復版)")
st.write("---")

# ==========================================
# 2. 金鑰輸入
# ==========================================
col1, col2 = st.columns(2)
with col1:
    user_google_key = st.text_input("1. Google API Key", type="password", placeholder="AIzaSy...")
with col2:
    user_bg_key = st.text_input("2. Remove.bg API Key", type="password", placeholder="8A2f9c...")

if not user_google_key or not user_bg_key:
    st.warning("⚠️ 請填寫金鑰以開始使用。")
    st.stop()

# 設定 Google AI
genai.configure(api_key=user_google_key.strip())

# ==========================================
# 3. 獨立功能函式 (避免縮排錯誤)
# ==========================================

def get_real_models_from_google():
    """直接向 Google 查詢此帳號能用的模型"""
    print(">>> 正在讀取模型清單...")
    try:
        model_list = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_list.append(m.name)
        return model_list
    except Exception as e:
        print(f"讀取模型失敗: {e}")
        return []

def call_remove_bg(file_bytes, api_key):
    """執行去背的獨立函式"""
    try:
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': file_bytes},
            data={'size': 'auto'},
            headers={'X-Api-Key': api_key},
        )
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content)), "成功"
        else:
            return None, f"錯誤代碼 {response.status_code}"
    except Exception as e:
        return None, str(e)

def analyze_product(model_name, image_input):
    """執行 AI 分析的獨立函式"""
    model = genai.GenerativeModel(model_name)
    prompt = """
    你是一個專業的 AI 影片提示詞工程師。
    請分析這張產品圖片，並回傳以下 4 個資訊：
    1. 產品名稱 (Product Name)
    2. 目標受眾 (Target Audience)
    3. 核心痛點 (Pain Point, 請翻譯成英文)
    4. 解決方案 (Key Feature/Solution, 請翻譯成英文)
    請直接列出內容，不需要標題。
    """
    return model.generate_content([prompt, image_input])

# ==========================================
# 4. 主程式邏輯
# ==========================================

# (A) 讀取模型清單
if 'my_model_list' not in st.session_state:
    st.session_state['my_model_list'] = []

if st.button("🔄 點我讀取您的可用模型清單"):
    with st.spinner("連線 Google 中..."):
        real_models = get_real_models_from_google()
        if real_models:
            st.session_state['my_model_list'] = real_models
            st.success(f"✅ 讀取成功！共找到 {len(real_models)} 個模型。")
        else:
            st.error("❌ 讀取失敗，請檢查 API Key。")

# (B) 顯示選單與上傳
if st.session_state['my_model_list']:
    st.write("---")
    
    # 智慧預選：優先找 flash
    default_idx = 0
    for i, name in enumerate(st.session_state['my_model_list']):
        if 'flash' in name and 'exp' not in name:
            default_idx = i
            break
            
    selected_real_model = st.selectbox(
        "🤖 請選擇 AI 模型", 
        st.session_state['my_model_list'],
        index=default_idx
    )
    
    uploaded_file = st.file_uploader("選擇圖片", type=['jpg', 'png', 'jpeg'])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption='原始圖片', width=300)
        
        if st.button("🚀 啟動生成", type="primary"):
            
            # 1. 去背
            with st.spinner("✂️ 正在去背..."):
                # 重置指標很重要
                uploaded_file.seek(0) 
                no_bg_img, status = call_remove_bg(uploaded_file.getvalue(), user_bg_key.strip())
                
                if no_bg_img:
                    st.session_state['processed_image'] = no_bg_img
                    st.success("✅ 去背成功！")
                else:
                    st.warning(f"⚠️ 去背失敗: {status}")

            # 2. 分析
            with st.spinner(f"🤖 正在使用 {selected_real_model} 分析..."):
                try:
                    response = analyze_product(selected_real_model, image)
                    st.success("✅ 分析成功！")
                    
                    # 解析文字
                    lines = [line for line in response.text.split('\n') if line.strip()]
                    # 防呆處理
                    p_name = lines[0].split(":")[-1] if len(lines)>0 else "Product"
                    p_aud = lines[1].split(":")[-1] if len(lines)>1 else "Users"
                    p_pain = lines[2].split(":")[-1] if len(lines)>2 else "Pain"
                    p_sol = lines[3].split(":")[-1] if len(lines)>3 else "Solution"
                    
                    st.session_state['analyzed_data'] = {
                        "name": p_name, "audience": p_aud, "pain": p_pain, "sol": p_sol
                    }
                    
                except Exception as e:
                    st.error(f"執行失敗: {e}")
                    if "429" in str(e): st.error("❌ 額度滿了，請休息 1 分鐘後再試。")

# (C) 結果顯示
if st.session_state.get('analyzed_data'):
    st.write("---")
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        if st.session_state.get('processed_image'):
            st.image(st.session_state['processed_image'], caption="去背圖")
            buf = io.BytesIO()
            st.session_state['processed_image'].save(buf, format="PNG")
            st.download_button("⬇️ 下載去背圖", buf.getvalue(), "lock.png", "image/png")
            
    with col_b:
        d = st.session_state['analyzed_data']
        st.subheader("📋 您的腳本")
        st.code(f"Pain (T2V): Cinematic, Taiwanese person ({d['audience']}) frustrated by {d['pain']}, 4k.")
        st.code(f"Solution (I2V): Shot of **{d['name']} from start frame**, modern table, glowing, {d['sol']}, 4k.")
        st.code(f"Scenario (I2V): Lifestyle, Taiwanese model using **{d['name']} from start frame**, sunny day.")
        st.code(f"CTA (T2V): Close up product, thumbs up, text 'Shop Now'.")