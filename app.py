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
import sys # 新增 sys 以精確呼叫 python
from gtts import gTTS

# ---------------------------------------------------------
# 1. 資料設定與基礎函式
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
    # 嚴格清洗：保留阿美語格格音 ' 
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

# ---------------------------------------------------------
# 🔧 系統指令修正：使用 sys.executable 呼叫模組
# ---------------------------------------------------------
def generate_chinese_audio_subprocess(text, gender, output_path):
    voice = "zh-TW-HsiaoChenNeural" if gender == "女聲" else "zh-TW-YunJheNeural"
    
    # 使用 python -m edge_tts 確保使用當前環境的套件
    command = [
        sys.executable, "-m", "edge_tts",
        "--text", text,
        "--voice", voice,
        "--write-media", output_path
    ]
    
    try:
        subprocess.run(command, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Edge-TTS CLI Failed: {e}")
        try:
            # 失敗則降級至 gTTS (女聲)
            tts = gTTS(text=text, lang='zh-tw')
            tts.save(output_path)
            return False # 回傳 False 代表使用了備用方案
        except:
            return False
    except Exception as e:
        print(f"Unknown Error: {e}")
        return False

# ---------------------------------------------------------
# 🔧 穩定的族語合成邏輯 (強制握手版)
# ---------------------------------------------------------
def synthesize_indigenous_speech(tribe, speaker, text):
    client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
    bypass_client_validation(client, speaker)
    
    # 強制切換
    client.predict(ethnicity=tribe, api_name="/lambda")
    
    # 強制等待 2 秒 (保護阿美語不跑掉)
    time.sleep(2.0)
    
    path = client.predict(ref=speaker, gen_text_input=text, api_name="/default_speaker_tts")
    return path

# ---------------------------------------------------------
# 2. 介面初始化與側邊欄 (UI Polish)
# ---------------------------------------------------------
st.set_page_config(page_title="Podcast-007 Pro", layout="wide", initial_sidebar_state="expanded")

# --- 側邊欄設計 ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/microphone.png", width=80)
    st.title("原語 Podcast")
    st.markdown("### 🇹🇼 臺灣原住民族語生成器")
    st.markdown("---")
    
    st.markdown("#### 📖 使用指南")
    with st.expander("如何使用劇本模式？"):
        st.markdown("""
        **格式：** `A: 族語 | 中文`
        
        **範例：**
        ```text
        A: Nga'ay ho! | 你好
        B: Embiyax su hug? | 你好嗎
        ```
        1. 貼上文字
        2. 點擊 **⚡ 解析並匯入**
        3. 系統自動產生列表
        """)
    
    with st.expander("關於本工具"):
        st.caption("版本: Podcast-007 Pro")
        st.caption("核心: Gradio Client + MoviePy")
        st.caption("語音: IThuan Model + EdgeTTS")
    
    st.markdown("---")
    st.success("✅ 系統狀態：正常")

# --- 主標題區 ---
st.title("🎙️ Podcast 內容生產中心")
st.markdown("打造您的專屬原住民族語廣播節目，支援 **16族42語**、**雙語教學** 與 **背景混音**。")

if 'dialogue_list' not in st.session_state:
    st.session_state['dialogue_list'] = [
        {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Nga'ay ho!", "zh": "你好!"}, 
        {"tribe": "太魯閣", "speaker": "太魯閣_女聲", "text": "Embiyax su hug?", "zh": "你好嗎?"}
    ]

# ---------------------------------------------------------
# 3. 分頁定義 (美化版)
# ---------------------------------------------------------
# 使用 emoji 讓分頁更直觀
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 單句合成", 
    "🎧 Podcast (全族語)", 
    "🏫 Podcast (雙語教學)", 
    "📖 長文有聲書"
])

# ==========================================
# 分頁 1: 單句合成
# ==========================================
with tab1:
    st.markdown("### 💬 單句語音測試")
    st.caption("快速測試不同語者與方言的發音效果。")
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            s_tribe = st.selectbox("選擇族群 (Tribe)", list(speaker_map.keys()), key="s1_tribe", index=15)
        with c2:
            s_speaker = st.selectbox("選擇語者 (Speaker)", speaker_map[s_tribe], key="s1_speaker")
        
        s_text = st.text_area("輸入族語文字", height=120, placeholder="在此輸入要合成的句子...")
        
        if st.button("🔊 生成語音", type="primary", key="btn_single", use_container_width=True):
            text_clean = clean_text(s_text)
            if not text_clean:
                st.warning("⚠️ 請輸入文字內容")
            else:
                try:
                    with st.spinner(f"正在連線模型 ({s_tribe})..."):
                        path = synthesize_indigenous_speech(s_tribe, s_speaker, text_clean)
                        st.success("合成成功！")
                        st.audio(path)
                except Exception as e:
                    st.error(f"❌ 錯誤: {e}")

# ==========================================
# 共用函式：Podcast 列表編輯器 (UI 優化版)
# ==========================================
def render_script_editor(key_prefix):
    # 工具列
    col_tools1, col_tools2 = st.columns([1, 1])
    
    with col_tools1:
        with st.expander("📂 專案存檔/讀取", expanded=False):
            c_save, c_load = st.columns(2)
            with c_save:
                json_str = json.dumps(st.session_state['dialogue_list'], ensure_ascii=False, indent=2)
                st.download_button("📥 下載 (.json)", json_str, "project.json", "application/json", key=f"{key_prefix}_dl", use_container_width=True)
            with c_load:
                uploaded = st.file_uploader("📤 上傳 (.json)", type=["json"], key=f"{key_prefix}_up", label_visibility="collapsed")
                if uploaded and st.button("載入", key=f"{key_prefix}_load", use_container_width=True):
                    try:
                        st.session_state['dialogue_list'] = json.load(uploaded)
                        st.rerun()
                    except: st.error("格式錯誤")

    with col_tools2:
        with st.expander("⚡ 快速劇本匯入", expanded=False):
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                role_a_t = st.selectbox("A 族群", list(speaker_map.keys()), key=f"{key_prefix}_ra_t", index=15)
                role_a_s = st.selectbox("A 語者", speaker_map[role_a_t], key=f"{key_prefix}_ra_s")
            with c_r2:
                role_b_t = st.selectbox("B 族群", list(speaker_map.keys()), key=f"{key_prefix}_rb_t", index=1)
                role_b_s = st.selectbox("B 語者", speaker_map[role_b_t], key=f"{key_prefix}_rb_s")

            script_in = st.text_area("貼上劇本", height=100, key=f"{key_prefix}_txt", placeholder="A: ... | 中文\nB: ... | 中文")
            
            if st.button("🚀 解析並匯入", key=f"{key_prefix}_btn_imp", use_container_width=True):
                if script_in.strip():
                    lines = script_in.split('\n')
                    new_items = []
                    for line in lines:
                        line = line.strip()
                        if not line: continue
                        parts = line.split('|')
                        raw = parts[0].strip()
                        zh = parts[1].strip() if len(parts)>1 else ""
                        
                        entry = {"tribe": role_a_t, "speaker": role_a_s, "text": "", "zh": zh}
                        if raw.upper().startswith("A:") or raw.startswith("A："):
                            entry.update({"text": raw[2:].strip(), "tribe": role_a_t, "speaker": role_a_s})
                        elif raw.upper().startswith("B:") or raw.startswith("B："):
                            entry.update({"text": raw[2:].strip(), "tribe": role_b_t, "speaker": role_b_s})
                        else:
                            entry["text"] = raw
                        new_items.append(entry)
                    st.session_state['dialogue_list'].extend(new_items)
                    st.rerun()
            
            if st.button("🗑️ 清空所有列表", key=f"{key_prefix}_btn_clr", use_container_width=True):
                st.session_state['dialogue_list'] = []
                st.rerun()
            
    st.markdown("---")
    st.markdown("##### 📝 劇本編輯列表")
    
    # 列表顯示區 (使用 Container 做視覺分隔)
    if not st.session_state['dialogue_list']:
        st.info("👋 目前列表是空的，請使用上方的「⚡ 快速劇本匯入」或點擊下方的「新增」按鈕。")

    for i, line in enumerate(st.session_state['dialogue_list']):
        with st.container(border=True):
            col_idx, col_set, col_text, col_zh, col_del = st.columns([0.3, 2.7, 3.5, 3, 0.5])
            col_idx.write(f"**#{i+1}**")
            with col_set:
                try: idx_tr = list(speaker_map.keys()).index(line['tribe'])
                except: idx_tr = 0
                nt = st.selectbox("族", list(speaker_map.keys()), key=f"{key_prefix}_tr_{i}", index=idx_tr, label_visibility="collapsed")
                avail = speaker_map[nt]
                try: idx_sp = avail.index(line['speaker'])
                except: idx_sp = 0
                ns = st.selectbox("語", avail, key=f"{key_prefix}_sp_{i}", index=idx_sp, label_visibility="collapsed")
            
            ntx = col_text.text_input("族語", value=line['text'], key=f"{key_prefix}_tx_{i}", label_visibility="collapsed", placeholder="輸入族語...")
            nzh = col_zh.text_input("中文", value=line.get('zh',''), key=f"{key_prefix}_zh_{i}", label_visibility="collapsed", placeholder="中文翻譯...")
            
            if col_del.button("🗑️", key=f"{key_prefix}_dl_{i}"):
                st.session_state['dialogue_list'].pop(i)
                st.rerun()
            st.session_state['dialogue_list'][i].update({'tribe': nt, 'speaker': ns, 'text': ntx, 'zh': nzh})

    if st.button("➕ 新增一行", key=f"{key_prefix}_add", use_container_width=True):
        last = st.session_state['dialogue_list'][-1] if st.session_state['dialogue_list'] else {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "", "zh": ""}
        st.session_state['dialogue_list'].append(last.copy())
        st.rerun()

# ==========================================
# 分頁 2: Podcast I (全族語)
# ==========================================
with tab2:
    st.markdown("### 🎧 Podcast I (全族語模式)")
    render_script_editor("p1")
    
    st.markdown("#### ⚙️ 合成設定")
    with st.container(border=True):
        bgm_file_1 = st.file_uploader("🎵 背景音樂 (BGM)", type=["mp3", "wav"], key="bgm_1")
        if bgm_file_1:
            bgm_vol_1 = st.slider("BGM 音量", 0.05, 0.5, 0.15, 0.05, key="vol_1")
        else:
            bgm_vol_1 = 0.15

    if st.button("🎙️ 開始製作 (全族語)", type="primary", key="run_p1", use_container_width=True):
        dialogue = st.session_state['dialogue_list']
        if not dialogue:
            st.warning("⚠️ 請先輸入劇本")
        else:
            try:
                progress = st.progress(0)
                status = st.status("🚀 正在製作 Podcast...", expanded=True)
                clips = []
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    if not txt: continue
                    
                    status.write(f"正在合成 #{idx+1}: {item['tribe']}語...")
                    path = synthesize_indigenous_speech(item['tribe'], item['speaker'], txt)
                    
                    clip = AudioFileClip(path)
                    clips.append(clip)
                    
                    silence = AudioArrayClip(np.zeros((int(44100 * 1.0), clip.nchannels)), fps=44100)
                    clips.append(silence)
                    progress.progress((idx+1)/len(dialogue))
                
                if clips:
                    status.write("🎵 正在進行混音與後製...")
                    final = concatenate_audioclips(clips)
                    if bgm_file_1:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                            tmp.write(bgm_file_1.getvalue())
                            tpath = tmp.name
                        music = AudioFileClip(tpath)
                        if music.duration < final.duration:
                            music = concatenate_audioclips([music] * (int(final.duration/music.duration)+1))
                        music = music.subclipped(0, final.duration+1).with_volume_scaled(bgm_vol_1)
                        final = CompositeAudioClip([music, final])
                        os.remove(tpath)
                    
                    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final.write_audiofile(tf.name, logger=None, fps=44100)
                    for c in clips: c.close()
                    final.close()
                    
                    status.update(label="✅ 製作完成！", state="complete", expanded=False)
                    st.success("Podcast 製作成功！")
                    st.audio(tf.name)
                    with open(tf.name, "rb") as f:
                        st.download_button("📥 下載 MP3", f, "podcast_indigenous.mp3", "audio/mp3", use_container_width=True)
            except Exception as e: st.error(f"❌ 錯誤: {e}")

# ==========================================
# 分頁 3: Podcast II (雙語教學)
# ==========================================
with tab3:
    st.markdown("### 🏫 Podcast II (雙語教學模式)")
    render_script_editor("p2")
    
    st.markdown("#### ⚙️ 合成設定")
    with st.container(border=True):
        c_set1, c_set2 = st.columns(2)
        with c_set1:
            bgm_file_2 = st.file_uploader("🎵 背景音樂 (BGM)", type=["mp3", "wav"], key="bgm_2")
            bgm_vol_2 = st.slider("BGM 音量", 0.05, 0.5, 0.15, 0.05, key="vol_2") if bgm_file_2 else 0.15
        with c_set2:
            st.markdown("**🗣️ 中文語音設定**")
            zh_gender = st.radio("配音員性別", ["女聲 (HsiaoChen)", "男聲 (YunJhe)"], index=0, horizontal=True)
            zh_gender_val = "女聲" if "女聲" in zh_gender else "男聲"
            gap_time = st.slider("翻譯間隔 (秒)", 0.1, 2.0, 0.5)

    if st.button("🎙️ 開始製作 (雙語教學)", type="primary", key="run_p2", use_container_width=True):
        dialogue = st.session_state['dialogue_list']
        if not dialogue:
            st.warning("⚠️ 請先輸入劇本")
        else:
            try:
                progress = st.progress(0)
                status = st.status("🚀 正在製作雙語教材...", expanded=True)
                clips = []
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    zh = clean_text(item.get('zh', ''))
                    if not txt: continue
                    
                    # 1. 族語
                    status.write(f"合成 #{idx+1} [族語]...")
                    path = synthesize_indigenous_speech(item['tribe'], item['speaker'], txt)
                    clip_ind = AudioFileClip(path)
                    clips.append(clip_ind)
                    
                    # 2. 中文
                    if zh:
                        status.write(f"合成 #{idx+1} [中文]...")
                        gap = AudioArrayClip(np.zeros((int(44100 * gap_time), clip_ind.nchannels)), fps=44100)
                        clips.append(gap)
                        
                        tmp_zh_path = tempfile.mktemp(suffix=".mp3")
                        success = generate_chinese_audio_subprocess(zh, zh_gender_val, tmp_zh_path)
                        
                        if success and os.path.exists(tmp_zh_path):
                            clip_zh = AudioFileClip(tmp_zh_path)
                            clips.append(clip_zh)
                        else:
                            st.warning(f"#{idx+1} 中文合成使用備用音源")
                            if os.path.exists(tmp_zh_path): clips.append(AudioFileClip(tmp_zh_path))
                    
                    end_gap = AudioArrayClip(np.zeros((int(44100 * 1.0), clip_ind.nchannels)), fps=44100)
                    clips.append(end_gap)
                    
                    progress.progress((idx+1)/len(dialogue))
                
                if clips:
                    status.write("🎵 正在混音...")
                    final = concatenate_audioclips(clips)
                    if bgm_file_2:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                            tmp.write(bgm_file_2.getvalue())
                            tpath = tmp.name
                        music = AudioFileClip(tpath)
                        if music.duration < final.duration:
                            music = concatenate_audioclips([music] * (int(final.duration/music.duration)+1))
                        music = music.subclipped(0, final.duration+1).with_volume_scaled(bgm_vol_2)
                        final = CompositeAudioClip([music, final])
                        os.remove(tpath)
                    
                    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final.write_audiofile(tf.name, logger=None, fps=44100)
                    for c in clips: c.close()
                    final.close()
                    
                    status.update(label="✅ 製作完成！", state="complete", expanded=False)
                    st.success("雙語教材製作成功！")
                    st.audio(tf.name)
                    with open(tf.name, "rb") as f:
                        st.download_button("📥 下載 MP3", f, "podcast_bilingual.mp3", "audio/mp3", use_container_width=True)
            except Exception as e: st.error(f"❌ 錯誤: {e}")

# ==========================================
# 分頁 4: 長文有聲書
# ==========================================
with tab4:
    st.markdown("### 📖 長文有聲書製作")
    st.caption("自動將長篇文章切分為段落，並串接成完整音檔。")
    
    with st.container(border=True):
        c_l1, c_l2 = st.columns(2)
        with c_l1: long_tribe = st.selectbox("朗讀族群", list(speaker_map.keys()), key="l_tr", index=15)
        with c_l2: long_speaker = st.selectbox("朗讀語者", speaker_map[long_tribe], key="l_sp")
            
        long_text = st.text_area("貼上文章 (自動切分)", height=200, placeholder="請貼上長篇故事...")
        
        c_b3, c_b4 = st.columns([3, 1])
        with c_b3: bgm_file_l = st.file_uploader("背景音樂", type=["mp3", "wav"], key="bgm_l")
        with c_b4: bgm_vol_l = st.slider("音量", 0.05, 0.5, 0.15, 0.05, key="vol_l")

    if st.button("📖 開始製作有聲書", type="primary", use_container_width=True):
        if not long_text.strip():
            st.warning("⚠️ 請先輸入文字")
        else:
            chunks = split_long_text(clean_text(long_text), 120)
            st.info(f"ℹ️ 已切分為 {len(chunks)} 個段落，預計耗時 {len(chunks)*4} 秒...")
            
            progress = st.progress(0)
            status = st.status("🚀 正在朗讀中...", expanded=True)
            clips_l = []
            
            try:
                for idx, chunk in enumerate(chunks):
                    status.write(f"正在朗讀第 {idx+1}/{len(chunks)} 段...")
                    
                    path = synthesize_indigenous_speech(long_tribe, long_speaker, chunk)
                    
                    clip = AudioFileClip(path)
                    clips_l.append(clip)
                    
                    ch = clip.nchannels 
                    silence = AudioArrayClip(np.zeros((int(44100 * 1.0), ch)), fps=44100)
                    clips_l.append(silence)
                    
                    progress.progress((idx + 1) / len(chunks))
                
                if clips_l:
                    status.write("🎵 正在混音...")
                    voice_trk = concatenate_audioclips(clips_l)
                    final_out = voice_trk
                    
                    if bgm_file_l:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                            tmp.write(bgm_file_l.getvalue())
                            tmppath = tmp.name
                        mtrk = AudioFileClip(tmppath)
                        if mtrk.duration < voice_trk.duration:
                            nl = int(voice_trk.duration / mtrk.duration) + 1
                            mtrk = concatenate_audioclips([mtrk]*nl)
                        mtrk = mtrk.subclipped(0, voice_trk.duration + 1).with_volume_scaled(bgm_vol_l)
                        final_out = CompositeAudioClip([mtrk, voice_trk])
                        os.remove(tmppath)

                    tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final_out.write_audiofile(tmpf.name, logger=None, fps=44100)
                    for c in clips_l: c.close()
                    final_out.close()
                    
                    status.update(label="✅ 有聲書製作完成！", state="complete", expanded=False)
                    st.audio(tmpf.name)
                    with open(tmpf.name, "rb") as f:
                        st.download_button("📥 下載有聲書", f, "audiobook.mp3", "audio/mp3", use_container_width=True)
            except Exception as e:
                st.error(f"❌ 錯誤: {e}")
