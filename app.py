import streamlit as st
from gradio_client import Client
from moviepy import AudioFileClip, concatenate_audioclips, CompositeAudioClip, AudioArrayClip
import os
import re
import tempfile
import time
import numpy as np
import json
import subprocess # 1. 引入 subprocess 用來執行系統指令
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
# 🔧 關鍵修正：改用 subprocess 執行系統指令
# 這會繞過 Python 的執行緒衝突，是最穩定的方法
# ---------------------------------------------------------
def generate_chinese_audio_subprocess(text, gender, output_path):
    voice = "zh-TW-HsiaoChenNeural" if gender == "女聲" else "zh-TW-YunJheNeural"
    
    # 組合指令： edge-tts --text "你好" --voice zh-TW-YunJheNeural --write-media output.mp3
    command = [
        "edge-tts",
        "--text", text,
        "--voice", voice,
        "--write-media", output_path
    ]
    
    try:
        # 執行系統指令，並等待完成
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Edge-TTS CLI Failed: {e}")
        # 降級至 gTTS
        try:
            tts = gTTS(text=text, lang='zh-tw')
            tts.save(output_path)
            return True
        except:
            return False
    except Exception as e:
        print(f"Unknown Error: {e}")
        return False

# ---------------------------------------------------------
# 🔧 穩定的族語合成邏輯
# ---------------------------------------------------------
def synthesize_indigenous_speech(tribe, speaker, text):
    # 建立新連線
    client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
    bypass_client_validation(client, speaker)
    
    # 切換族群
    client.predict(ethnicity=tribe, api_name="/lambda")
    
    # 強制等待 2 秒
    time.sleep(2.0)
    
    # 合成
    path = client.predict(ref=speaker, gen_text_input=text, api_name="/default_speaker_tts")
    return path

# ---------------------------------------------------------
# 2. 介面初始化
# ---------------------------------------------------------
st.set_page_config(page_title="Podcast-006: 原住民族語生成器", layout="wide")
st.title("🎙️ Podcast-006: 原住民族語生成器")
st.caption("版本功能：系統級中文合成 (修復男聲) | 穩定族語模型 | 專案存檔")

if 'dialogue_list' not in st.session_state:
    st.session_state['dialogue_list'] = [
        {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Nga'ay ho!", "zh": "你好!"}, 
        {"tribe": "太魯閣", "speaker": "太魯閣_女聲", "text": "Embiyax su hug?", "zh": "你好嗎?"}
    ]

# ---------------------------------------------------------
# 3. 分頁定義
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "單句合成 (Single)", 
    "Podcast I (全族語)", 
    "Podcast II (雙語教學)", 
    "長文有聲書 (Audiobook)"
])

# ==========================================
# 分頁 1: 單句合成
# ==========================================
with tab1:
    st.subheader("單句語音合成")
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
                with st.spinner(f"正在切換至 {s_tribe} 模型並合成..."):
                    path = synthesize_indigenous_speech(s_tribe, s_speaker, text_clean)
                    st.audio(path)
            except Exception as e:
                st.error(f"錯誤: {e}")

# ==========================================
# 共用函式：Podcast 列表編輯器
# ==========================================
def render_script_editor(key_prefix):
    with st.expander("💾 專案存檔與讀取", expanded=False):
        c_save, c_load = st.columns(2)
        with c_save:
            json_str = json.dumps(st.session_state['dialogue_list'], ensure_ascii=False, indent=2)
            st.download_button("📥 下載劇本 (.json)", json_str, "podcast_project.json", "application/json", key=f"{key_prefix}_dl")
        with c_load:
            uploaded = st.file_uploader("📤 上傳劇本 (.json)", type=["json"], key=f"{key_prefix}_up")
            if uploaded and st.button("確認載入", key=f"{key_prefix}_load"):
                try:
                    st.session_state['dialogue_list'] = json.load(uploaded)
                    st.success("載入成功！")
                    st.rerun()
                except: st.error("格式錯誤")

    with st.expander("⚡ 快速劇本匯入", expanded=False):
        st.caption("格式： `A: 族語 | 中文`")
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            role_a_t = st.selectbox("A 族群", list(speaker_map.keys()), key=f"{key_prefix}_ra_t", index=15)
            role_a_s = st.selectbox("A 語者", speaker_map[role_a_t], key=f"{key_prefix}_ra_s")
        with c_r2:
            role_b_t = st.selectbox("B 族群", list(speaker_map.keys()), key=f"{key_prefix}_rb_t", index=1)
            role_b_s = st.selectbox("B 語者", speaker_map[role_b_t], key=f"{key_prefix}_rb_s")

        script_in = st.text_area("貼上劇本", height=100, key=f"{key_prefix}_txt", placeholder="A: Nga'ay ho! | 你好")
        
        c_imp1, c_imp2 = st.columns([1, 4])
        if c_imp1.button("⚡ 匯入", key=f"{key_prefix}_btn_imp"):
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
        if c_imp2.button("🗑️ 清空", key=f"{key_prefix}_btn_clr"):
            st.session_state['dialogue_list'] = []
            st.rerun()
            
    st.markdown("---")
    
    for i, line in enumerate(st.session_state['dialogue_list']):
        with st.container():
            col_idx, col_set, col_text, col_zh, col_del = st.columns([0.5, 2.5, 3.5, 3, 0.5])
            col_idx.write(f"#{i+1}")
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
            
            if col_del.button("❌", key=f"{key_prefix}_dl_{i}"):
                st.session_state['dialogue_list'].pop(i)
                st.rerun()
            st.session_state['dialogue_list'][i].update({'tribe': nt, 'speaker': ns, 'text': ntx, 'zh': nzh})

    if st.button("➕ 新增一句", key=f"{key_prefix}_add"):
        last = st.session_state['dialogue_list'][-1] if st.session_state['dialogue_list'] else {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "", "zh": ""}
        st.session_state['dialogue_list'].append(last.copy())
        st.rerun()

# ==========================================
# 分頁 2: Podcast I (全族語模式)
# ==========================================
with tab2:
    st.subheader("Podcast I (全族語模式)")
    st.caption("此模式僅合成「族語」部分，適合製作沉浸式母語節目。")
    
    render_script_editor("p1")
    
    with st.expander("🎵 背景音樂設定", expanded=True):
        bgm_file_1 = st.file_uploader("上傳 BGM", type=["mp3", "wav"], key="bgm_1")
        bgm_vol_1 = st.slider("音量", 0.05, 0.5, 0.15, 0.05, key="vol_1")

    if st.button("🎙️ 開始合成 (全族語)", type="primary", key="run_p1"):
        dialogue = st.session_state['dialogue_list']
        if not dialogue:
            st.warning("腳本是空的")
        else:
            try:
                progress = st.progress(0)
                status = st.empty()
                clips = []
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    if not txt: continue
                    
                    status.text(f"合成 #{idx+1} [族語] {item['tribe']}...")
                    
                    # 使用穩定版合成
                    path = synthesize_indigenous_speech(item['tribe'], item['speaker'], txt)
                    
                    clip = AudioFileClip(path)
                    clips.append(clip)
                    
                    # 1秒間隔
                    silence = AudioArrayClip(np.zeros((int(44100 * 1.0), clip.nchannels)), fps=44100)
                    clips.append(silence)
                    progress.progress((idx+1)/len(dialogue))
                
                if clips:
                    status.text("混音中...")
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
                    st.success("完成！")
                    st.audio(tf.name)
            except Exception as e: st.error(f"錯誤: {e}")

# ==========================================
# 分頁 3: Podcast II (雙語教學模式)
# ==========================================
with tab3:
    st.subheader("Podcast II (雙語教學模式)")
    st.caption("此模式會合成「族語 + 中文翻譯」，並可選擇中文配音員的性別。")
    
    render_script_editor("p2")
    
    c_set1, c_set2 = st.columns(2)
    with c_set1:
        with st.expander("🎵 背景音樂設定", expanded=True):
            bgm_file_2 = st.file_uploader("上傳 BGM", type=["mp3", "wav"], key="bgm_2")
            bgm_vol_2 = st.slider("音量", 0.05, 0.5, 0.15, 0.05, key="vol_2")
    with c_set2:
        with st.expander("🗣️ 中文語音設定", expanded=True):
            zh_gender = st.radio("中文配音員性別", ["女聲 (HsiaoChen)", "男聲 (YunJhe)"], index=0)
            zh_gender_val = "女聲" if "女聲" in zh_gender else "男聲"
            gap_time = st.slider("翻譯間隔 (秒)", 0.1, 2.0, 0.5)

    if st.button("🎙️ 開始合成 (雙語教學)", type="primary", key="run_p2"):
        dialogue = st.session_state['dialogue_list']
        if not dialogue:
            st.warning("腳本是空的")
        else:
            try:
                progress = st.progress(0)
                status = st.empty()
                clips = []
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    zh = clean_text(item.get('zh', ''))
                    if not txt: continue
                    
                    # 1. 族語 (使用穩定版)
                    status.text(f"合成 #{idx+1} [族語] {item['tribe']}...")
                    path = synthesize_indigenous_speech(item['tribe'], item['speaker'], txt)
                    clip_ind = AudioFileClip(path)
                    clips.append(clip_ind)
                    
                    # 2. 中文 (如果有)
                    if zh:
                        status.text(f"合成 #{idx+1} [中文] ({zh_gender_val})...")
                        gap = AudioArrayClip(np.zeros((int(44100 * gap_time), clip_ind.nchannels)), fps=44100)
                        clips.append(gap)
                        
                        tmp_zh_path = tempfile.mktemp(suffix=".mp3")
                        
                        # 🔧 呼叫新的 subprocess 函式
                        success = generate_chinese_audio_subprocess(zh, zh_gender_val, tmp_zh_path)
                        
                        if success and os.path.exists(tmp_zh_path):
                            clip_zh = AudioFileClip(tmp_zh_path)
                            clips.append(clip_zh)
                        else:
                            st.warning(f"#{idx+1} 中文合成失敗")
                    
                    # 句尾大間隔
                    end_gap = AudioArrayClip(np.zeros((int(44100 * 1.0), clip_ind.nchannels)), fps=44100)
                    clips.append(end_gap)
                    
                    progress.progress((idx+1)/len(dialogue))
                
                if clips:
                    status.text("混音中...")
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
                    st.success("完成！")
                    st.audio(tf.name)
            except Exception as e: st.error(f"錯誤: {e}")

# ==========================================
# 分頁 4: 長文有聲書
# ==========================================
with tab4:
    st.subheader("長文有聲書製作")
    c_l1, c_l2 = st.columns(2)
    with c_l1: long_tribe = st.selectbox("朗讀族群", list(speaker_map.keys()), key="l_tr", index=15)
    with c_l2: long_speaker = st.selectbox("朗讀語者", speaker_map[long_tribe], key="l_sp")
        
    long_text = st.text_area("貼上長文 (自動切分)", height=250)
    
    with st.expander("🎵 背景音樂設定", expanded=True):
        c_b3, c_b4 = st.columns([3, 1])
        with c_b3: bgm_file_l = st.file_uploader("上傳音樂", type=["mp3", "wav"], key="bgm_l")
        with c_b4: bgm_vol_l = st.slider("音量", 0.05, 0.5, 0.15, 0.05, key="vol_l")

    if st.button("📖 開始製作", type="primary"):
        if not long_text.strip():
            st.warning("請先輸入文字")
        else:
            chunks = split_long_text(clean_text(long_text), 120)
            st.info(f"已切分為 {len(chunks)} 段，開始合成...")
            
            prog = st.progress(0)
            stat = st.empty()
            clips_l = []
            
            try:
                for idx, chunk in enumerate(chunks):
                    stat.text(f"合成第 {idx+1}/{len(chunks)} 段...")
                    
                    path = synthesize_indigenous_speech(long_tribe, long_speaker, chunk)
                    
                    clip = AudioFileClip(path)
                    clips_l.append(clip)
                    
                    ch = clip.nchannels 
                    silence = AudioArrayClip(np.zeros((int(44100 * 1.0), ch)), fps=44100)
                    clips_l.append(silence)
                    
                    prog.progress((idx + 1) / len(chunks))
                
                if clips_l:
                    stat.text("接合中...")
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
                    st.success("完成！")
                    st.audio(tmpf.name)
            except Exception as e:
                st.error(f"錯誤: {e}")
