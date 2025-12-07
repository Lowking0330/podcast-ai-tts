import streamlit as st
from gradio_client import Client
import os
import re
import tempfile
import time
import numpy as np
import json
# 1. 新增 gTTS 用於中文合成
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
# 2. 介面初始化
# ---------------------------------------------------------
st.set_page_config(page_title="Podcast-001: 原住民族語生成器", layout="wide")
st.title("🎙️ Podcast-001: 原住民族語生成器")
st.caption("版本功能：單句合成 | 雙語對話 | 長文有聲書 | 專案存檔")

if 'dialogue_list' not in st.session_state:
    st.session_state['dialogue_list'] = [
        {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Nga'ay ho!", "zh": "你好!"}, 
        {"tribe": "太魯閣", "speaker": "太魯閣_女聲", "text": "Embiyax su hug?", "zh": "你好嗎?"}
    ]

# ---------------------------------------------------------
# 3. 分頁定義
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["單句測試 (Single)", "Podcast 對話 (Dialogue)", "長文有聲書 (Audiobook)"])

# ==========================================
# 分頁 1: 單句功能
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
# 分頁 2: Podcast 對話 (新增：存檔 + 雙語)
# ==========================================
with tab2:
    st.subheader("Podcast 對話腳本編輯器")
    
    # ------------------------------------------
    # 💾 功能 3：專案存檔與讀取
    # ------------------------------------------
    with st.expander("💾 專案存檔與讀取 (Project Save/Load)", expanded=False):
        c_save, c_load = st.columns(2)
        with c_save:
            # 匯出 JSON
            json_str = json.dumps(st.session_state['dialogue_list'], ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 下載目前劇本 (.json)",
                data=json_str,
                file_name="podcast_project.json",
                mime="application/json"
            )
        with c_load:
            # 匯入 JSON
            uploaded_file = st.file_uploader("📤 上傳劇本檔 (.json)", type=["json"])
            if uploaded_file is not None:
                if st.button("確認載入專案"):
                    try:
                        data = json.load(uploaded_file)
                        st.session_state['dialogue_list'] = data
                        st.success("專案載入成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"檔案格式錯誤: {e}")

    # ------------------------------------------
    # ⚡ 快速劇本匯入 (升級版：支援雙語)
    # ------------------------------------------
    with st.expander("⚡ 快速劇本匯入 (支援雙語)", expanded=False):
        st.caption("格式範例： `A: Nga'ay ho! | 你好` (使用 `|` 分隔族語和中文)")
        c_role1, c_role2 = st.columns(2)
        with c_role1:
            st.markdown("**🧑‍🦰 角色 A 設定**")
            role_a_tribe = st.selectbox("A 族群", list(speaker_map.keys()), key="ra_t", index=15)
            role_a_spk = st.selectbox("A 語者", speaker_map[role_a_tribe], key="ra_s")
        with c_role2:
            st.markdown("**👩‍🦱 角色 B 設定**")
            role_b_tribe = st.selectbox("B 族群", list(speaker_map.keys()), key="rb_t", index=1)
            role_b_spk = st.selectbox("B 語者", speaker_map[role_b_tribe], key="rb_s")

        script_text = st.text_area("請貼上劇本", height=150, placeholder="A: Nga'ay ho! | 你好\nB: Embiyax su hug? | 你好嗎")

        c_imp1, c_imp2 = st.columns([1, 4])
        if c_imp1.button("⚡ 解析並匯入"):
            if not script_text.strip():
                st.warning("請先輸入劇本內容！")
            else:
                lines = script_text.split('\n')
                new_entries = []
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    # 解析族語與中文
                    parts = line.split('|')
                    raw_text = parts[0].strip()
                    zh_text = parts[1].strip() if len(parts) > 1 else ""
                    
                    current_entry = {"tribe": role_a_tribe, "speaker": role_a_spk, "text": "", "zh": zh_text}
                    
                    if raw_text.upper().startswith("A:") or raw_text.startswith("A："):
                        current_entry["text"] = raw_text[2:].strip()
                        current_entry["tribe"] = role_a_tribe
                        current_entry["speaker"] = role_a_spk
                    elif raw_text.upper().startswith("B:") or raw_text.startswith("B："):
                        current_entry["text"] = raw_text[2:].strip()
                        current_entry["tribe"] = role_b_tribe
                        current_entry["speaker"] = role_b_spk
                    else:
                        current_entry["text"] = raw_text
                    
                    new_entries.append(current_entry)
                    
                st.session_state['dialogue_list'].extend(new_entries)
                st.success(f"成功匯入 {len(new_entries)} 句！")
                st.rerun()
        if c_imp2.button("🗑️ 清空列表"):
            st.session_state['dialogue_list'] = []
            st.rerun()

    st.markdown("---")
    
    # BGM 與 雙語模式設定
    c_set1, c_set2 = st.columns(2)
    with c_set1:
        with st.expander("🎵 背景音樂 (BGM)", expanded=True):
            bgm_file_d = st.file_uploader("上傳背景音樂", type=["mp3", "wav"], key="bgm_d")
            bgm_vol_d = st.slider("音量", 0.05, 0.5, 0.15, 0.05, key="vol_d")
    with c_set2:
        with st.expander("🗣️ 雙語教學模式 (Bilingual)", expanded=True):
            enable_bilingual = st.checkbox("啟用雙語朗讀 (族語 + 中文)", value=True, help="合成時會先唸族語，再唸中文翻譯")
            bilingual_gap = st.slider("翻譯間隔 (秒)", 0.0, 2.0, 0.5, 0.1)

    # 列表編輯區 (新增中文欄位)
    st.markdown("##### 📝 腳本列表")
    for i, line in enumerate(st.session_state['dialogue_list']):
        with st.container():
            # 調整欄位比例，增加中文欄位
            col_idx, col_set, col_text, col_zh, col_del = st.columns([0.5, 2.5, 3.5, 3, 0.5])
            col_idx.write(f"#{i+1}")
            
            with col_set:
                try: idx_tr = list(speaker_map.keys()).index(line['tribe'])
                except: idx_tr = 0
                new_tribe = st.selectbox("族群", list(speaker_map.keys()), key=f"d_tr_{i}", index=idx_tr, label_visibility="collapsed")
                
                avail_spks = speaker_map[new_tribe]
                try: idx_sp = avail_spks.index(line['speaker'])
                except: idx_sp = 0
                new_speaker = st.selectbox("語者", avail_spks, key=f"d_sp_{i}", index=idx_sp, label_visibility="collapsed")
            
            new_text = col_text.text_input("族語", value=line['text'], key=f"d_tx_{i}", label_visibility="collapsed", placeholder="族語台詞")
            # 確保有 zh 欄位 (舊專案可能沒有)
            curr_zh = line.get('zh', '')
            new_zh = col_zh.text_input("中文翻譯", value=curr_zh, key=f"d_zh_{i}", label_visibility="collapsed", placeholder="中文翻譯")
            
            if col_del.button("❌", key=f"d_dl_{i}"):
                st.session_state['dialogue_list'].pop(i)
                st.rerun()
            
            st.session_state['dialogue_list'][i].update({'tribe': new_tribe, 'speaker': new_speaker, 'text': new_text, 'zh': new_zh})

    c_add, c_run = st.columns([1, 4])
    if c_add.button("➕ 新增"):
        last = st.session_state['dialogue_list'][-1] if st.session_state['dialogue_list'] else {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "", "zh": ""}
        st.session_state['dialogue_list'].append(last.copy())
        st.rerun()

    if c_run.button("🎙️ 開始合成 Podcast-001", type="primary"):
        dialogue = st.session_state['dialogue_list']
        if not dialogue:
            st.warning("腳本是空的！")
        else:
            try:
                from moviepy import AudioFileClip, concatenate_audioclips, CompositeAudioClip, AudioArrayClip
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                audio_clips = []
                
                client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    zh_txt = clean_text(item.get('zh', ''))
                    spk = item['speaker']
                    trb = item['tribe']
                    
                    if not txt: continue 
                    
                    # 1. 合成族語
                    status_text.text(f"合成 #{idx+1} [族語]: {txt[:10]}...")
                    bypass_client_validation(client, spk)
                    try: client.predict(ethnicity=trb, api_name="/lambda")
                    except: pass
                    audio_path = client.predict(ref=spk, gen_text_input=txt, api_name="/default_speaker_tts")
                    
                    clip_indigenous = AudioFileClip(audio_path)
                    audio_clips.append(clip_indigenous)
                    
                    # 2. 功能 4：合成中文 (如果有啟用且有文字)
                    if enable_bilingual and zh_txt:
                        status_text.text(f"合成 #{idx+1} [中文]: {zh_txt[:10]}...")
                        # 加一點小間隔
                        silence_gap = AudioArrayClip(np.zeros((int(44100 * bilingual_gap), 2)), fps=44100)
                        audio_clips.append(silence_gap)
                        
                        # 使用 gTTS 合成中文
                        tts_zh = gTTS(text=zh_txt, lang='zh-tw')
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_zh:
                            tts_zh.save(tmp_zh.name)
                            tmp_zh_path = tmp_zh.name
                        
                        clip_zh = AudioFileClip(tmp_zh_path)
                        audio_clips.append(clip_zh)
                        
                    # 3. 每句結束的 1 秒大間隔
                    silence_end = AudioArrayClip(np.zeros((int(44100 * 1.0), 2)), fps=44100)
                    audio_clips.append(silence_end)
                    
                    progress_bar.progress((idx + 1) / len(dialogue))

                if audio_clips:
                    status_text.text("混音處理中...")
                    voice_track = concatenate_audioclips(audio_clips)
                    
                    final_output = voice_track
                    if bgm_file_d is not None:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_bgm:
                            tmp_bgm.write(bgm_file_d.getvalue())
                            tmp_bgm_path = tmp_bgm.name
                        music_track = AudioFileClip(tmp_bgm_path)
                        if music_track.duration < voice_track.duration:
                            n_loops = int(voice_track.duration / music_track.duration) + 1
                            music_track = concatenate_audioclips([music_track] * n_loops)
                        music_track = music_track.subclipped(0, voice_track.duration + 1).with_volume_scaled(bgm_vol_d)
                        final_output = CompositeAudioClip([music_track, voice_track])
                        os.remove(tmp_bgm_path)
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final_output.write_audiofile(temp_file.name, logger=None, fps=44100)
                    
                    for c in audio_clips: c.close()
                    final_output.close()
                    
                    st.success("🎉 Podcast-001 完成！")
                    st.audio(temp_file.name, format="audio/mp3")
                    with open(temp_file.name, "rb") as f:
                        st.download_button("📥 下載 MP3", f, "podcast_001.mp3", "audio/mp3")

            except ImportError as e:
                st.error("環境錯誤：請確認 requirements.txt 包含 gTTS, numpy, moviepy")
            except Exception as e:
                st.error(f"執行錯誤: {e}")

# ==========================================
# 分頁 3: 長文有聲書
# ==========================================
with tab3:
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
                from moviepy import AudioFileClip, concatenate_audioclips, CompositeAudioClip, AudioArrayClip

                client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
                try: client.predict(ethnicity=long_tribe, api_name="/lambda")
                except: pass
                bypass_client_validation(client, long_speaker)

                for idx, chunk in enumerate(chunks):
                    stat.text(f"合成第 {idx+1}/{len(chunks)} 段...")
                    path = client.predict(ref=long_speaker, gen_text_input=chunk, api_name="/default_speaker_tts")
                    
                    clip = AudioFileClip(path)
                    clips_l.append(clip)
                    
                    ch = clip.nchannels 
                    silence_array = np.zeros((int(44100 * 1.0), ch))
                    silence = AudioArrayClip(silence_array, fps=44100)
                    clips_l.append(silence)
                    
                    time.sleep(0.5)
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
                    
                    st.success("🎉 有聲書完成！")
                    st.audio(tmpf.name, format="audio/mp3")
                    with open(tmpf.name, "rb") as f:
                        st.download_button("📥 下載有聲書", f, "audiobook_final.mp3", "audio/mp3")

            except ImportError as e:
                st.error("環境安裝錯誤。請確認 requirements.txt")
                st.error(e)
            except Exception as e:
                st.error(f"錯誤: {e}")
