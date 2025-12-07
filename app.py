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

def generate_chinese_audio_subprocess(text, gender, output_path):
    voice = "zh-TW-HsiaoChenNeural" if gender == "女聲" else "zh-TW-YunJheNeural"
    command = [
        sys.executable, "-m", "edge_tts",
        "--text", text,
        "--voice", voice,
        "--write-media", output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return True
    except:
        try:
            tts = gTTS(text=text, lang='zh-tw')
            tts.save(output_path)
            return False
        except: return False

def synthesize_indigenous_speech(tribe, speaker, text):
    client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
    bypass_client_validation(client, speaker)
    client.predict(ethnicity=tribe, api_name="/lambda")
    time.sleep(2.0)
    path = client.predict(ref=speaker, gen_text_input=text, api_name="/default_speaker_tts")
    return path

# ---------------------------------------------------------
# Excel/Txt 處理函式
# ---------------------------------------------------------
def convert_df_to_excel(dialogue_list):
    df = pd.DataFrame(dialogue_list)
    df = df.rename(columns={'tribe': '族群', 'speaker': '語者', 'text': '族語內容', 'zh': '中文翻譯'})
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Script')
    return output.getvalue()

def convert_list_to_txt(dialogue_list):
    txt_content = ""
    for item in dialogue_list:
        zh_part = f" | {item.get('zh', '')}" if item.get('zh') else ""
        txt_content += f"{item['text']}{zh_part}\n"
    return txt_content

def parse_uploaded_file(uploaded_file):
    try:
        filename = uploaded_file.name
        new_data = []
        if filename.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
            for _, row in df.iterrows():
                tribe = row.get('族群') or row.get('tribe') or '阿美'
                speaker = row.get('語者') or row.get('speaker') or '阿美_海岸_男聲'
                text = row.get('族語內容') or row.get('text') or ''
                zh = row.get('中文翻譯') or row.get('zh') or ''
                if pd.notna(text) and str(text).strip():
                    new_data.append({
                        'tribe': str(tribe), 'speaker': str(speaker),
                        'text': str(text), 'zh': str(zh) if pd.notna(zh) else ""
                    })
        elif filename.endswith('.txt'):
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            for line in stringio:
                line = line.strip()
                if not line: continue
                parts = line.split('|')
                raw = parts[0].strip()
                zh = parts[1].strip() if len(parts) > 1 else ""
                new_data.append({
                    'tribe': '阿美', 'speaker': '阿美_海岸_男聲',
                    'text': raw, 'zh': zh
                })
        return new_data
    except Exception as e:
        st.error(f"檔案解析失敗: {e}")
        return None

# ---------------------------------------------------------
# 2. 介面初始化
# ---------------------------------------------------------
st.set_page_config(page_title="Podcast-008 Pro", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.image("https://img.icons8.com/color/96/microphone.png", width=80)
    st.title("原語 Podcast")
    st.markdown("### 🇹🇼 臺灣原住民族語生成器")
    st.markdown("---")
    st.success("✅ 系統狀態：正常")

st.title("🎙️ Podcast 內容生產中心")
st.caption("版本: Podcast-008 Pro | 功能：Excel 存取、一鍵範例、雙語男聲")

if 'dialogue_list' not in st.session_state:
    st.session_state['dialogue_list'] = []

# ---------------------------------------------------------
# 3. 分頁定義
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 單句合成", 
    "🎧 Podcast (全族語)", 
    "🏫 Podcast (雙語教學)", 
    "📖 長文有聲書"
])

# ==========================================
# 分頁 1: 單句合成 (含範例)
# ==========================================
with tab1:
    st.markdown("### 💬 單句語音測試")
    
    if st.button("✨ 載入範例 (海岸阿美)", key="ex_single", help="快速填入阿美族問候語"):
        st.session_state['s1_tribe_idx'] = 0 
        st.session_state['s1_speaker_idx'] = 0 
        st.session_state['s1_text_val'] = "Nga'ay ho! Kicey kiso haw?" 
        st.rerun()

    def_tribe_idx = st.session_state.get('s1_tribe_idx', 0)
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            s_tribe = st.selectbox("選擇族群", list(speaker_map.keys()), key="s1_tribe", index=def_tribe_idx)
        with c2:
            avail_spks = speaker_map[s_tribe]
            def_spk_idx = st.session_state.get('s1_speaker_idx', 0)
            if def_spk_idx >= len(avail_spks): def_spk_idx = 0
            s_speaker = st.selectbox("選擇語者", avail_spks, key="s1_speaker", index=def_spk_idx)
        
        def_text = st.session_state.get('s1_text_val', "")
        s_text = st.text_area("輸入族語文字", value=def_text, height=120)
        
        if st.button("🔊 生成語音", type="primary", use_container_width=True):
            if not s_text: st.warning("請輸入文字")
            else:
                try:
                    with st.spinner(f"正在合成 ({s_tribe})..."):
                        path = synthesize_indigenous_speech(s_tribe, s_speaker, clean_text(s_text))
                        st.audio(path)
                except Exception as e: st.error(f"錯誤: {e}")

# ==========================================
# 共用函式：Podcast 列表編輯器 (修復 Duplicate ID)
# ==========================================
def render_script_editor(key_prefix):
    # --- 範例按鈕 ---
    if st.button("✨ 載入範例劇本 (海岸阿美)", key=f"{key_prefix}_ex", use_container_width=True):
        st.session_state['dialogue_list'] = [
            {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Nga'ay ho!", "zh": "你好！"},
            {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Kicey kiso haw?", "zh": "你吃飯了嗎？"},
            {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Hay, kicey to kaku.", "zh": "是的，我吃飽了。"},
            {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Aray!", "zh": "謝謝！"}
        ]
        st.rerun()

    # --- 存檔工具列 ---
    with st.expander("📂 專案存檔/讀取 (支援 Excel/Txt)", expanded=False):
        c_save, c_load = st.columns(2)
        with c_save:
            st.markdown("#### 匯出")
            if st.session_state['dialogue_list']:
                # 🔧 修正：加上 unique key
                excel_data = convert_df_to_excel(st.session_state['dialogue_list'])
                st.download_button("📥 下載 Excel (.xlsx)", excel_data, "podcast_script.xlsx", 
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                                   key=f"{key_prefix}_dl_excel") # 加入 Key
                
                txt_data = convert_list_to_txt(st.session_state['dialogue_list'])
                st.download_button("📥 下載文字檔 (.txt)", txt_data, "podcast_script.txt", "text/plain",
                                   key=f"{key_prefix}_dl_txt") # 加入 Key
            else:
                st.info("列表為空，無法下載")

        with c_load:
            st.markdown("#### 匯入")
            uploaded = st.file_uploader("上傳 .xlsx 或 .txt", type=["xlsx", "txt"], key=f"{key_prefix}_up")
            if uploaded:
                if st.button("確認載入檔案", key=f"{key_prefix}_load"):
                    data = parse_uploaded_file(uploaded)
                    if data:
                        st.session_state['dialogue_list'] = data
                        st.success(f"成功載入 {len(data)} 筆資料！")
                        time.sleep(1)
                        st.rerun()

    # --- 快速匯入區 ---
    with st.expander("⚡ 快速劇本貼上", expanded=False):
        st.caption("設定角色後直接貼上。")
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            role_a_t = st.selectbox("A 族群", list(speaker_map.keys()), key=f"{key_prefix}_ra_t", index=0)
            role_a_s = st.selectbox("A 語者", speaker_map[role_a_t], key=f"{key_prefix}_ra_s")
        with c_r2:
            role_b_t = st.selectbox("B 族群", list(speaker_map.keys()), key=f"{key_prefix}_rb_t", index=0)
            role_b_s = st.selectbox("B 語者", speaker_map[role_b_t], key=f"{key_prefix}_rb_s")

        script_in = st.text_area("貼上劇本 (A: 族語 | 中文)", height=100, key=f"{key_prefix}_txt")
        
        if st.button("🚀 解析並追加", key=f"{key_prefix}_btn_imp"):
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
            
    st.markdown("---")
    
    # 列表顯示
    if not st.session_state['dialogue_list']:
        st.info("👋 列表是空的，請載入範例或新增。")

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
            
            ntx = col_text.text_input("族語", value=line['text'], key=f"{key_prefix}_tx_{i}", label_visibility="collapsed")
            nzh = col_zh.text_input("中文", value=line.get('zh',''), key=f"{key_prefix}_zh_{i}", label_visibility="collapsed")
            
            if col_del.button("🗑️", key=f"{key_prefix}_dl_{i}"):
                st.session_state['dialogue_list'].pop(i)
                st.rerun()
            st.session_state['dialogue_list'][i].update({'tribe': nt, 'speaker': ns, 'text': ntx, 'zh': nzh})

    c_add, c_clr = st.columns([4, 1])
    if c_add.button("➕ 新增一行", key=f"{key_prefix}_add", use_container_width=True):
        last = st.session_state['dialogue_list'][-1] if st.session_state['dialogue_list'] else {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "", "zh": ""}
        st.session_state['dialogue_list'].append(last.copy())
        st.rerun()
    if c_clr.button("🗑️ 清空", key=f"{key_prefix}_clr"):
        st.session_state['dialogue_list'] = []
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
                    
                    status.write(f"合成 #{idx+1}: {item['tribe']}語...")
                    path = synthesize_indigenous_speech(item['tribe'], item['speaker'], txt)
                    
                    clip = AudioFileClip(path)
                    clips.append(clip)
                    
                    silence = AudioArrayClip(np.zeros((int(44100 * 1.0), clip.nchannels)), fps=44100)
                    clips.append(silence)
                    progress.progress((idx+1)/len(dialogue))
                
                if clips:
                    status.write("🎵 正在進行混音...")
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
    
    if st.button("✨ 載入範例文章 (海岸阿美)", key="ex_long", use_container_width=True):
        st.session_state['l_tribe_idx'] = 0 
        st.session_state['l_speaker_idx'] = 0 
        st.session_state['l_text_val'] = "O kakalayan no 'Amis a tamdaw.\nItini i Taywan, adihay ko kasasiromaroma no yincumin.\nNikaorira, saadihayay a tamdaw i, o 'Amis." 
        st.rerun()

    def_l_idx = st.session_state.get('l_tribe_idx', 0)
    
    with st.container(border=True):
        c_l1, c_l2 = st.columns(2)
        with c_l1: long_tribe = st.selectbox("朗讀族群", list(speaker_map.keys()), key="l_tr", index=def_l_idx)
        with c_l2: 
            avail = speaker_map[long_tribe]
            def_l_s_idx = st.session_state.get('l_speaker_idx', 0)
            if def_l_s_idx >= len(avail): def_l_s_idx = 0
            long_speaker = st.selectbox("朗讀語者", avail, key="l_sp", index=def_l_s_idx)
            
        def_l_text = st.session_state.get('l_text_val', "")
        long_text = st.text_area("貼上文章 (自動切分)", value=def_l_text, height=200, placeholder="請貼上長篇故事...")
        
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
