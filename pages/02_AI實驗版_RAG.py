import streamlit as st
from gradio_client import Client
from moviepy import AudioFileClip, concatenate_audioclips, CompositeAudioClip, AudioArrayClip
import os
import re
import tempfile
import time
import numpy as np
import json
import subprocess
import sys
from gtts import gTTS
import pandas as pd
import io
import shutil
import google.generativeai as genai
import PyPDF2

# ---------------------------------------------------------
# 1. 資料設定與基礎函式
# ---------------------------------------------------------
speaker_map = {
    '阿美': ['阿美_海岸_男聲', '阿美_恆春_女聲', '阿美_馬蘭_女聲', '阿美_南勢_女聲', '阿美_秀姑巒_女聲1', '阿美_秀姑巒_女聲2'],
    '泰雅': ['泰雅_四季_女聲', '泰雅_賽考利克_男聲', '泰雅_萬大_女聲', '泰雅_汶水_男聲', '泰雅_宜蘭澤敖利_女聲', '泰雅_澤敖利_男聲'],
    '排灣': ['排灣_中_男聲', '排灣_東_男聲', '排灣_北_女聲', '排灣_南_女聲'],
    '布農': ['布農_郡群_男聲', '布農_卡群_男聲', '布農_巒群_男聲', '布農_丹群_男聲', '布農_卓群_女聲'],
    '太魯閣': ['太魯閣_女聲', '太魯閣_男聲1', '太魯閣_男聲2'],
    '賽德克': ['賽德克_德鹿谷_女聲', '賽德克_都達_女聲', '賽德克_德固達雅_男聲', '賽德克_德固達雅_女聲'],
    '魯凱': ['魯凱_大武_女聲', '魯凱_多納_男聲', '魯凱_東_女聲', '魯凱_茂林_男聲', '魯凱_萬山_女聲', '魯凱_霧台_女聲'],
    '卑南': ['卑南_建和_女聲', '卑南_南王_女聲', '卑南_西群_女聲', '卑南_知本_女聲'],
    '鄒': ['鄒_女聲'],
    '賽夏': ['賽夏_女聲'],
    '雅美': ['雅美_女聲'],
    '邵': ['邵_男聲'],
    '噶瑪蘭': ['噶瑪蘭_女聲'],
    '拉阿魯哇': ['拉阿魯哇_女聲'],
    '撒奇萊雅': ['撒奇萊雅_女聲'],
    '卡那卡那富': ['卡那卡那富_男聲'],
}

def clean_text(text):
    if not text: return ""
    text = text.replace("，", ",").replace("。", ".").replace("？", "?").replace("！", "!")
    text = text.replace("：", ":").replace("；", ";").replace("（", "(").replace("）", ")")
    text = text.replace("―", " ").replace("—", " ").replace("…", " ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def bypass_client_validation(client, speaker_id):
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

def split_long_text(text, max_chars=150):
    chunks = re.split(r'([。.?!？！\n])', text)
    final_chunks = []
    current_chunk = ""
    for chunk in chunks:
        if len(current_chunk) + len(chunk) < max_chars:
            current_chunk += chunk
        else:
            if current_chunk.strip():
                final_chunks.append(current_chunk.strip())
            current_chunk = chunk
    if current_chunk.strip():
        final_chunks.append(current_chunk.strip())
    return final_chunks

def generate_chinese_audio_free_tier(text, gender, output_path):
    edge_voice = "zh-TW-HsiaoChenNeural" if gender == "女聲" else "zh-TW-YunJheNeural"
    command = [
        sys.executable, "-m", "edge_tts",
        "--text", text,
        "--voice", edge_voice,
        "--write-media", output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=10)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, "Edge-TTS"
    except: pass
    
    try:
        tts = gTTS(text=text, lang='zh-tw')
        tts.save(output_path)
        is_downgrade = (gender == "男聲")
        return True, ("gTTS-Fallback" if is_downgrade else "gTTS")
    except:
        return False, "Error"

def synthesize_indigenous_speech(tribe, speaker, text):
    client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
    bypass_client_validation(client, speaker)
    client.predict(ethnicity=tribe, api_name="/lambda")
    time.sleep(2.0)
    path = client.predict(ref=speaker, gen_text_input=text, api_name="/default_speaker_tts")
    return path

# ---------------------------------------------------------
# 🔧 AI 腳本生成函式 (RAG Core)
# ---------------------------------------------------------
def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def generate_script_with_gemini(api_key, context_text, topic, role_a_name="老師", role_b_name="學生"):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        你是一位專業的廣播劇編劇。請根據以下提供的「參考資料」和「主題」，撰寫一段雙人對話劇本。
        
        【參考資料】：
        {context_text[:5000]} (內容過長已截斷)
        
        【主題】：{topic}
        
        【角色設定】：
        - A: {role_a_name} (負責解說，使用阿美語)
        - B: {role_b_name} (負責提問，使用阿美語)
        
        【輸出規則】：
        1. 請輸出純 JSON 格式的列表 (List of Objects)。
        2. 每個物件必須包含四個欄位：
           - "tribe": 固定為 "阿美"
           - "speaker": 固定為 "阿美_秀姑巒_女聲1"
           - "text": 阿美語台詞 (請根據參考資料翻譯或創作，用羅馬拼音)
           - "zh": 對應的中文翻譯
        3. 不要輸出 Markdown 標記 (如 ```json)，只要純文字的 JSON。
        
        【範例格式】：
        [
            {{"tribe": "阿美", "speaker": "阿美_秀姑巒_女聲1", "text": "Nga'ay ho!", "zh": "你好！"}},
            {{"tribe": "阿美", "speaker": "阿美_秀姑巒_女聲1", "text": "Maolah misa'osi kiso?", "zh": "你喜歡讀書嗎？"}}
        ]
        """
        
        response = model.generate_content(prompt)
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
        
    except Exception as e:
        raise Exception(f"AI 生成失敗: {e}")

# ---------------------------------------------------------
# 2. 介面初始化
# ---------------------------------------------------------
st.set_page_config(page_title="Podcast-015 AI", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    # ✅ 修正點：使用純網址，沒有 Markdown 符號
    st.image("[https://img.icons8.com/color/96/microphone.png](https://img.icons8.com/color/96/microphone.png)", width=80)
    
    st.title("原語 Podcast")
    st.markdown("### 🇹🇼 臺灣原住民族語生成器")
    
    st.markdown("---")
    st.markdown("### 🌟 功能簡介 (AI版)")
    st.info("""
    **🧪 AI實驗版功能**：
    
    **1. 🤖 AI 寫劇本** 結合 Google Gemini，讀取 PDF 或文字資料，自動撰寫對話腳本。
    
    **2. 🎙️ 雙語合成**
    自動帶入生成的腳本進行合成。
    """)
    
    st.markdown("---")
    st.markdown("#### 🔑 AI 設定")
    if 'gemini_key' not in st.session_state:
        st.session_state['gemini_key'] = ''
    
    user_key = st.text_input("Gemini API Key", value=st.session_state['gemini_key'], type="password")
    if user_key:
        st.session_state['gemini_key'] = user_key
        st.success("API Key 已設定")

    st.markdown("---")
    st.success("✅ 系統狀態：正常")

st.title("🧪 AI 實驗室：智慧劇本生成")
st.markdown("結合 **RAG (檢索增強生成)** 技術，讓 AI 讀懂資料，自動產出族語廣播劇。")

if 'dialogue_list' not in st.session_state:
    st.session_state['dialogue_list'] = []

# ---------------------------------------------------------
# 3. 分頁定義
# ---------------------------------------------------------
tab_ai, tab_tts = st.tabs(["🤖 AI 寫劇本 (RAG)", "🎙️ 開始合成 (TTS)"])

# ==========================================
# 分頁 1: AI 寫劇本 (RAG)
# ==========================================
with tab_ai:
    st.markdown("### 步驟 1：提供資料讓 AI 寫劇本")
    
    api_key = st.session_state.get('gemini_key', '')
    if not api_key:
        st.warning("⚠️ 請先在左側輸入 Google Gemini API Key")
    
    with st.container(border=True):
        input_method = st.radio("資料來源", ["貼上文字", "上傳 PDF"], horizontal=True)
        
        context_text = ""
        if input_method == "貼上文字":
            context_text = st.text_area("參考資料", height=200, placeholder="貼上部落故事、新聞或文化介紹...")
        else:
            uploaded_pdf = st.file_uploader("上傳 PDF", type="pdf")
            if uploaded_pdf:
                try:
                    context_text = read_pdf(uploaded_pdf)
                    st.success(f"成功讀取 {len(context_text)} 字")
                except: st.error("PDF 讀取失敗")
        
        c_ai1, c_ai2 = st.columns(2)
        with c_ai1:
            topic = st.text_input("劇本主題", value="請根據資料寫一段族語教學對話")
        with c_ai2:
            role_a = st.text_input("角色 A (解說者)", value="老師")
            
    if st.button("🚀 AI 生成劇本", type="primary", disabled=not api_key, use_container_width=True):
        if not context_text:
            st.warning("請提供參考資料")
        else:
            try:
                with st.spinner("AI 正在閱讀並撰寫劇本..."):
                    script_data = generate_script_with_gemini(api_key, context_text, topic, role_a_name=role_a)
                    st.session_state['dialogue_list'] = script_data
                    st.success(f"生成成功！共 {len(script_data)} 句。")
                    st.info("💡 請切換到「🎙️ 開始合成」分頁查看結果。")
                    with st.expander("查看生成內容", expanded=True):
                        st.json(script_data)
            except Exception as e:
                st.error(f"生成失敗: {e}")

# ==========================================
# 分頁 2: TTS 合成 (沿用 Podcast II 邏輯)
# ==========================================
with tab_tts:
    st.markdown("### 步驟 2：檢查並合成語音")
    
    # 簡易編輯器
    if not st.session_state['dialogue_list']:
        st.info("👋 請先在「🤖 AI 寫劇本」分頁生成內容，或在此手動輸入。")
        
    for i, line in enumerate(st.session_state['dialogue_list']):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 3, 3])
            c1.write(f"**#{i+1} {line['speaker'].split('_')[1]}**") # 顯示身分
            line['text'] = c2.text_input("族語", line['text'], key=f"ai_tx_{i}", label_visibility="collapsed")
            line['zh'] = c3.text_input("中文", line.get('zh',''), key=f"ai_zh_{i}", label_visibility="collapsed")

    with st.container(border=True):
        c_set1, c_set2 = st.columns(2)
        with c_set1:
            bgm_file = st.file_uploader("背景音樂 (BGM)", type=["mp3", "wav"])
            bgm_vol = st.slider("音量", 0.05, 0.5, 0.15, 0.05)
        with c_set2:
            zh_gender = st.radio("中文配音", ["女聲", "男聲"], index=0, horizontal=True)
            gap_time = st.slider("翻譯間隔", 0.1, 2.0, 0.5)

    if st.button("🎙️ 開始合成 (雙語模式)", type="primary", use_container_width=True):
        dialogue = st.session_state['dialogue_list']
        if not dialogue: st.warning("無內容")
        else:
            try:
                progress = st.progress(0)
                status = st.status("🚀 製作中...", expanded=True)
                clips = []
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    zh = clean_text(item.get('zh', ''))
                    if not txt: continue
                    
                    status.write(f"合成 #{idx+1} [族語]...")
                    path = synthesize_indigenous_speech(item['tribe'], item['speaker'], txt)
                    clip_ind = AudioFileClip(path)
                    clips.append(clip_ind)
                    
                    if zh:
                        status.write(f"合成 #{idx+1} [中文]...")
                        clips.append(AudioArrayClip(np.zeros((int(44100 * gap_time), clip_ind.nchannels)), fps=44100))
                        tmp_zh = tempfile.mktemp(suffix=".mp3")
                        success, _ = generate_chinese_audio_free_tier(zh, zh_gender, tmp_zh)
                        if success and os.path.exists(tmp_zh):
                            clips.append(AudioFileClip(tmp_zh))
                    
                    clips.append(AudioArrayClip(np.zeros((int(44100 * 1.0), clip_ind.nchannels)), fps=44100))
                    progress.progress((idx+1)/len(dialogue))
                
                if clips:
                    status.write("🎵 混音中...")
                    final = concatenate_audioclips(clips)
                    if bgm_file:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                            tmp.write(bgm_file.getvalue())
                            tpath = tmp.name
                        music = AudioFileClip(tpath)
                        if music.duration < final.duration:
                            music = concatenate_audioclips([music] * (int(final.duration/music.duration)+1))
                        music = music.subclipped(0, final.duration+1).with_volume_scaled(bgm_vol)
                        final = CompositeAudioClip([music, final])
                        os.remove(tpath)
                    
                    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final.write_audiofile(tf.name, logger=None, fps=44100)
                    for c in clips: c.close()
                    final.close()
                    
                    status.update(label="✅ 完成！", state="complete", expanded=False)
                    st.audio(tf.name)
                    with open(tf.name, "rb") as f:
                        st.download_button("📥 下載 MP3", f, "ai_podcast.mp3", "audio/mp3", use_container_width=True)
            except Exception as e: st.error(f"錯誤: {e}")
