import streamlit as st
from gradio_client import Client
import os

# --- 1. 設定與連線 ---
GRADIO_URL = "https://hnang-kari-ai-asi-sluhay.ithuan.tw/"

st.set_page_config(page_title="原住民族語 Podcast 生成器", layout="wide", page_icon="🎙️")

st.title("🎙️ 族語 TTS Podcast 工作台")
st.markdown(f"Backend: `{GRADIO_URL}`")

# 快取 Client 連線，避免每次重新整理都要重連
@st.cache_resource
def get_client():
    return Client(GRADIO_URL)

try:
    client = get_client()
    st.toast("API 連線成功！", icon="✅")
except Exception as e:
    st.error(f"無法連線到 API: {e}")
    st.stop()

# --- 2. 側邊欄：設定參數 ---
with st.sidebar:
    st.header("⚙️ 語者設定")
    
    # 根據您的 Log，這裡列出已知的語者格式
    # 因為無法抓取全部，我先列出 Log 裡有的，並提供「手動輸入」選項
    speaker_options = [
        "阿美_海岸_男聲",
        "阿美_恆春_女聲",
        "阿美_馬蘭_女聲",
        "阿美_南勢_女聲",
        "阿美_秀姑巒_女聲1",
        "阿美_秀姑巒_女聲2",
        "阿美_太魯閣_男聲",
        "阿美_太魯閣_女聲",
        "手動輸入其他語者 ID..."
    ]
    
    selected_speaker = st.selectbox("選擇語者 (Speaker ID)", speaker_options)
    
    # 如果選擇手動輸入，顯示文字框
    final_speaker_id = selected_speaker
    if selected_speaker == "手動輸入其他語者 ID...":
        final_speaker_id = st.text_input("請輸入語者 ID (例如: 賽德克_都達_女聲)", value="阿美_海岸_男聲")
        st.caption("提示：請確認輸入的 ID 與網站上的選單完全一致。")

    st.info(f"目前設定語者：**{final_speaker_id}**")

# --- 3. 主畫面：輸入講稿 ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📝 輸入講稿")
    text_input = st.text_area(
        "請輸入族語或羅馬拼音", 
        height=300, 
        placeholder="Mihalay! ...",
        help="輸入您想要轉換成語音的文字內容。"
    )

with col2:
    st.subheader("🎧 生成結果")
    st.write("準備好後，點擊下方按鈕開始合成。")
    
    generate_btn = st.button("🚀 開始合成語音 (Generate)", type="primary", use_container_width=True)

# --- 4. 執行合成邏輯 ---
if generate_btn:
    if not text_input:
        st.warning("❌ 請先輸入文字內容！")
    else:
        with st.spinner(f"正在請求 API 合成 ({final_speaker_id})..."):
            try:
                # 呼叫 /default_speaker_tts 端點
                # 根據 Log: predict(ref, gen_text_input, api_name="/default_speaker_tts")
                result_path = client.predict(
                    ref=final_speaker_id,      # 第一個參數：語者 ID
                    gen_text_input=text_input, # 第二個參數：文字
                    api_name="/default_speaker_tts"
                )
                
                # 顯示成功訊息
                st.success("✅ 合成完成！")
                
                # 1. 播放音檔
                st.audio(result_path)
                
                # 2. 製作下載按鈕
                # 讀取暫存檔的二進位資料
                with open(result_path, "rb") as f:
                    audio_bytes = f.read()
                    
                st.download_button(
                    label="📥 下載 .wav 音檔",
                    data=audio_bytes,
                    file_name=f"podcast_output_{final_speaker_id}.wav",
                    mime="audio/wav",
                    use_container_width=True
                )
                
                # 除錯資訊 (可隱藏)
                with st.expander("檢視 API 回傳路徑"):
                    st.code(result_path)

            except Exception as e:
                st.error("合成失敗，請檢查以下錯誤訊息：")
                st.code(str(e))
                st.markdown("""
                **可能原因排除：**
                1. **語者 ID 錯誤**：請確認您輸入的 `賽德克_xxx` 是否與原網站下拉選單完全一致。
                2. **文字過長**：若是免費版 HuggingFace Space，可能會有限制時長。
                """)

# --- 頁尾 ---
st.markdown("---")
st.caption("Podcast AI Tool | Powered by Ithuan TTS API")
