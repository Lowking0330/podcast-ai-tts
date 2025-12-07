import streamlit as st
import requests
import json
import time

# --- 設定頁面資訊 ---
st.set_page_config(page_title="原住民族語 Podcast 生成器", layout="wide")

st.title("🎙️ 原住民族語 Podcast 生成工作台")
st.markdown("輸入講稿文字，透過自研 TTS 模型生成族語音檔。")

# --- 側邊欄：API 設定與參數 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    # 這裡模擬填入你們 TTS API 的位置
    api_url = st.text_input("TTS API 網址", value="http://your-tts-api.com/synthesize")
    api_key = st.text_input("API Key (若需要)", type="password")
    
    st.divider()
    
    # 模擬選擇族語或語者
    language = st.selectbox("選擇語言", ["阿美語 (Amis)", "排灣語 (Paiwan)", "泰雅語 (Atayal)"])
    speaker_id = st.selectbox("選擇語者", ["Female_01 (耆老)", "Male_01 (青年)"])
    
    speed = st.slider("語速調整", 0.5, 2.0, 1.0)

# --- 主畫面：輸入講稿 ---
col1, col2 = st.columns([2, 1])

with col1:
    episode_title = st.text_input("單集標題", "第一集：族語生活會話")
    # 文字輸入區
    text_input = st.text_area("在此輸入講稿 (支援族語羅馬拼音)", height=300)

# --- 核心功能：呼叫 API 並生成 ---
def call_tts_api(text, lang, spk, speed):
    """
    這裡負責將資料傳送給你們開發的 TTS API
    """
    # 準備要傳給 API 的資料 (Payload)
    payload = {
        "text": text,
        "language": lang,
        "speaker": spk,
        "speed": speed
    }
    
    # 加上 Header (若有驗證機制)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        # 注意：這裡是一個模擬的 request，實際使用時請取消註解並填入正確參數
        # response = requests.post(api_url, json=payload, headers=headers)
        
        # --- 模擬 API 回傳 (為了讓範例能跑，我這裡做一個假延遲) ---
        time.sleep(2) 
        if text:
            return True, "模擬音檔.wav" # 假設成功回傳
        else:
            return False, "請輸入文字"
        # -----------------------------------------------------
        
        # 真正的程式碼應該長這樣：
        # if response.status_code == 200:
        #     return True, response.content (音檔二進位資料)
        # else:
        #     return False, response.text

    except Exception as e:
        return False, str(e)

# 生成按鈕
if st.button("🚀 開始合成語音", type="primary"):
    if not text_input:
        st.warning("請先輸入講稿內容！")
    else:
        with st.spinner("正在呼叫族語 TTS 引擎進行合成..."):
            success, result = call_tts_api(text_input, language, speaker_id, speed)
            
        if success:
            st.success("合成成功！")
            
            # 顯示音訊播放器
            # 注意：如果 API 回傳的是二進位資料 (bytes)，直接用 result 即可
            # 如果是模擬，這裡只是示範 UI
            st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", format="audio/mp3")
            
            # 提供下載按鈕
            st.download_button(
                label="📥 下載 Podcast 音檔 (.wav)",
                data=b"Fake Audio Bytes", # 這裡放入真正的音檔 bytes
                file_name=f"{episode_title}.wav",
                mime="audio/wav"
            )
            
            st.info(f"已使用參數：語言={language}, 語者={speaker_id}")
            
        else:
            st.error(f"合成失敗：{result}")

# --- 頁尾 ---
st.markdown("---")
st.caption("Powered by 自研原住民族語 TTS 系統 | Internal Tool")
