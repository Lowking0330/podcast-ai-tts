import streamlit as st
from gradio_client import Client
from pydub import AudioSegment
import os
import re
import tempfile

# ---------------------------------------------------------
# 1. 資料設定與清洗函式
# ---------------------------------------------------------
speaker_map = {
    '賽德克': ['賽德克_德鹿谷_女聲', '賽德克_都達_女聲', '賽德克_德固達雅_男聲', '賽德克_德固達雅_女聲'],
    '太魯閣': ['太魯閣_女聲', '太魯閣_男聲1', '太魯閣_男聲2'],
    '賽夏': ['賽夏_女聲'],
    '布農': ['布農_郡群_男聲', '布農_卡群_男聲', '布農_巒群_男聲', '布農_丹群_男聲', '布農_卓群_女聲'],
    '泰雅': ['泰雅_四季_女聲', '泰雅_賽考利克_男聲', '泰雅_萬大_女聲', '泰雅_汶水_男聲', '泰雅_宜蘭澤敖利_女聲', '泰雅_澤敖利_男聲'],
    '鄒': ['鄒_女聲'],
    '魯凱': ['魯凱_大武_女聲', '魯凱_多納_男聲', '魯凱_東_女聲', '魯凱_茂林_男聲', '魯凱_萬山_女聲', '魯凱_霧台_女聲'],
    '排灣': ['排灣_中_男聲', '排灣_東_男聲', '排灣_北_女聲', '排灣_南_女聲'],
    '雅美': ['雅美_女聲'],
    '卑南': ['卑南_建和_女聲', '卑南_南王_女聲', '卑南_西群_女聲', '卑南_知本_女聲'],
    '邵': ['邵_男聲'],
    '噶瑪蘭': ['噶瑪蘭_女聲'],
    '拉阿魯哇': ['拉阿魯哇_女聲'],
    '撒奇萊雅': ['撒奇萊雅_女聲'],
    '卡那卡那富': ['卡那卡那富_男聲'],
    '阿美': ['阿美_海岸_男聲', '阿美_恆春_女聲', '阿美_馬蘭_女聲', '阿美_南勢_女聲', '阿美_秀姑巒_女聲1', '阿美_秀姑巒_女聲2'],
}

def clean_text(text):
    if not text: return ""
    text = text.replace("―", " ").replace("—", " ").replace("…", " ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def bypass_client_validation(client, speaker_id):
    """ 強制將語者加入白名單 """
    try:
        target_endpoints = [client.endpoints.get('/default_speaker_tts'), client.endpoints.get('/custom_speaker_tts')]
        for endpoint in target_endpoints:
            if endpoint and hasattr(endpoint, 'parameters'):
                for param in endpoint.parameters:
                    if 'enum' in param and speaker_id not in param['enum']:
                        param['enum'].append(speaker_id)
                    if 'choices' in param and speaker_id not in param['choices']:
                        param['choices'].append(speaker_id)
    except Exception:
        pass

# ---------------------------------------------------------
# 2. 介面初始化
# ---------------------------------------------------------
st.set_page_config(page_title="原住民族語 Podcast 生成器", layout="wide")
st.title("臺灣原住民族語 Podcast 生成器 🎙️")

# 使用 Session State 來儲存對話腳本
if 'dialogue_list' not in st.session_state:
    st.session_state['dialogue_list'] = [
        {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Nga'ay ho! (你好!)"}, 
        {"tribe": "太魯閣", "speaker": "太魯閣_女聲", "text": "Embiyax su hug? (你好嗎?)"}
    ]

# ---------------------------------------------------------
# 3. 分頁設計
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["單句測試 (Single)", "Podcast 對話製作 (Dialogue)"])

# ==========================================
# 分頁 1: 原本的單句功能
# ==========================================
with tab1:
    st.subheader("單句語音合成測試")
    c1, c2 = st.columns(2)
    with c1:
        s_tribe = st.selectbox("選擇族群", list(speaker_map.keys()), key="s1_tribe", index=15)
    with c2:
        s_speaker = st.selectbox("選擇語者", speaker_map[s_tribe], key="s1_speaker")
    
    s_text = st.text_area("輸入文字", height=100)
    
    if st.button("生成單句", key="btn_single"):
        text_clean = clean_text(s_text)
        if not text_clean:
            st.warning("請輸入文字")
        else:
            try:
                with st.spinner("生成中..."):
                    client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
                    bypass_client_validation(client, s_speaker)
                    try: client.predict(ethnicity=s_tribe, api_name="/lambda")
                    except: pass
                    
                    result = client.predict(ref=s_speaker, gen_text_input=text_clean, api_name="/default_speaker_tts")
                    st.audio(result)
            except Exception as e:
                st.error(f"錯誤: {e}")

# ==========================================
# 分頁 2: 多語者對話模式 (Podcast 核心功能)
# ==========================================
with tab2:
    st.subheader("Podcast 對話腳本編輯器")
    st.caption("在此安排您的節目腳本，系統將自動合成並串接成一個完整的音檔。")

    # --- 腳本編輯區 ---
    for i, line in enumerate(st.session_state['dialogue_list']):
        with st.container():
            col_idx, col_tribe, col_spk, col_text, col_del = st.columns([0.5, 2, 3, 6, 0.5])
            
            # 顯示序號
            col_idx.write(f"#{i+1}")
            
            # 族群選擇
            new_tribe = col_tribe.selectbox(
                "族群", list(speaker_map.keys()), 
                key=f"tribe_{i}", 
                index=list(speaker_map.keys()).index(line['tribe']) if line['tribe'] in speaker_map else 0,
                label_visibility="collapsed"
            )
            
            # 語者選擇 (根據族群連動)
            avail_spks = speaker_map[new_tribe]
            # 確保原本的語者還在新的清單裡，否則選第一個
            current_spk_idx = 0
            if line['speaker'] in avail_spks:
                current_spk_idx = avail_spks.index(line['speaker'])
                
            new_speaker = col_spk.selectbox(
                "語者", avail_spks, 
                key=f"spk_{i}", 
                index=current_spk_idx,
                label_visibility="collapsed"
            )
            
            # 文字輸入
            new_text = col_text.text_input(
                "台詞", value=line['text'], 
                key=f"text_{i}",
                label_visibility="collapsed",
                placeholder="請輸入台詞..."
            )
            
            # 刪除按鈕
            if col_del.button("❌", key=f"del_{i}"):
                st.session_state['dialogue_list'].pop(i)
                st.rerun()

            # 更新 Session State
            st.session_state['dialogue_list'][i]['tribe'] = new_tribe
            st.session_state['dialogue_list'][i]['speaker'] = new_speaker
            st.session_state['dialogue_list'][i]['text'] = new_text

    # --- 操作按鈕區 ---
    st.markdown("---")
    c_add, c_run = st.columns([1, 4])
    
    if c_add.button("➕ 新增一句對話"):
        # 預設複製上一句的設定，方便連續輸入
        last_item = st.session_state['dialogue_list'][-1] if st.session_state['dialogue_list'] else {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": ""}
        st.session_state['dialogue_list'].append({
            "tribe": last_item['tribe'],
            "speaker": last_item['speaker'],
            "text": ""
        })
        st.rerun()

    if c_run.button("🎙️ 開始合成完整 Podcast", type="primary"):
        dialogue = st.session_state['dialogue_list']
        if not dialogue:
            st.warning("腳本是空的！")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 準備一個空的 AudioSegment 來裝結果
            combined_audio = AudioSegment.empty()
            # 設定靜音間隔 (毫秒)，讓對話之間不要太趕
            silence = AudioSegment.silent(duration=500) 
            
            try:
                client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    spk = item['speaker']
                    trb = item['tribe']
                    
                    if not txt: continue # 跳過空行
                    
                    status_text.text(f"正在合成第 {idx+1}/{len(dialogue)} 句：{spk} 說「{txt[:10]}...」")
                    
                    # 1. 繞過驗證
                    bypass_client_validation(client, spk)
                    
                    # 2. 切換族群 (這步很重要，避免模型錯亂)
                    try: client.predict(ethnicity=trb, api_name="/lambda")
                    except: pass
                    
                    # 3. 合成
                    audio_path = client.predict(
                        ref=spk, 
                        gen_text_input=txt, 
                        api_name="/default_speaker_tts"
                    )
                    
                    # 4. 使用 pydub 讀取並串接
                    # Gradio 回傳的通常是 WAV 或 FLAC
                    segment = AudioSegment.from_file(audio_path)
                    combined_audio += segment + silence
                    
                    # 更新進度條
                    progress_bar.progress((idx + 1) / len(dialogue))

                status_text.text("合成完成！正在匯出音檔...")
                
                # 匯出成 Bytes
                buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                combined_audio.export(buffer.name, format="mp3")
                
                st.success("🎉 Podcast 製作完成！")
                st.audio(buffer.name, format="audio/mp3")
                
                # 提供下載按鈕
                with open(buffer.name, "rb") as f:
                    st.download_button(
                        label="📥 下載 MP3 檔案",
                        data=f,
                        file_name="my_indigenous_podcast.mp3",
                        mime="audio/mp3"
                    )
                
            except Exception as e:
                st.error("發生錯誤，可能是 pydub 找不到 ffmpeg，或是網路問題。")
                st.error(f"詳細錯誤: {e}")
                st.info("💡 如果是 ffmpeg 錯誤，請確認您的電腦有安裝 ffmpeg，或在 Streamlit Cloud 的 packages.txt 加入 ffmpeg。")
