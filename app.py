import streamlit as st
from gradio_client import Client
# 1. 新增 AudioClip 用來製造靜音
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, AudioClip
import os
import re
import tempfile
import time
# 2. 新增 numpy 用來計算靜音數據
import numpy as np

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
st.set_page_config(page_title="原住民族語 Podcast 生成器", layout="wide")
st.title("臺灣原住民族語 Podcast 生成器 🎙️")

if 'dialogue_list' not in st.session_state:
    st.session_state['dialogue_list'] = [
        {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": "Nga'ay ho!"}, 
        {"tribe": "太魯閣", "speaker": "太魯閣_女聲", "text": "Embiyax su hug?"}
    ]

# ---------------------------------------------------------
# 3. 分頁設計
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
# 分頁 2: Podcast 對話 (含 1秒延遲)
# ==========================================
with tab2:
    st.subheader("Podcast 對話腳本編輯器")
    
    with st.expander("🎵 背景音樂設定 (BGM Settings)", expanded=False):
        col_bgm1, col_bgm2 = st.columns([3, 1])
        with col_bgm1:
            bgm_file_d = st.file_uploader("上傳背景音樂", type=["mp3", "wav"], key="bgm_d")
        with col_bgm2:
            bgm_vol_d = st.slider("音樂音量", 0.05, 0.5, 0.15, 0.05, key="vol_d")

    # 腳本 UI
    for i, line in enumerate(st.session_state['dialogue_list']):
        with st.container():
            col_idx, col_tribe, col_spk, col_text, col_del = st.columns([0.5, 2, 3, 6, 0.5])
            col_idx.write(f"#{i+1}")
            new_tribe = col_tribe.selectbox("族群", list(speaker_map.keys()), key=f"d_tr_{i}", index=list(speaker_map.keys()).index(line['tribe']) if line['tribe'] in speaker_map else 0, label_visibility="collapsed")
            avail_spks = speaker_map[new_tribe]
            idx_spk = avail_spks.index(line['speaker']) if line['speaker'] in avail_spks else 0
            new_speaker = col_spk.selectbox("語者", avail_spks, key=f"d_sp_{i}", index=idx_spk, label_visibility="collapsed")
            new_text = col_text.text_input("台詞", value=line['text'], key=f"d_tx_{i}", label_visibility="collapsed")
            if col_del.button("❌", key=f"d_dl_{i}"):
                st.session_state['dialogue_list'].pop(i)
                st.rerun()
            st.session_state['dialogue_list'][i].update({'tribe': new_tribe, 'speaker': new_speaker, 'text': new_text})

    c_add, c_run = st.columns([1, 4])
    if c_add.button("➕ 新增"):
        last = st.session_state['dialogue_list'][-1] if st.session_state['dialogue_list'] else {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": ""}
        st.session_state['dialogue_list'].append(last.copy())
        st.rerun()

    if c_run.button("🎙️ 開始合成 Podcast (含間隔)", type="primary"):
        dialogue = st.session_state['dialogue_list']
        if not dialogue:
            st.warning("腳本是空的！")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            audio_clips = []
            
            try:
                client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    spk = item['speaker']
                    trb = item['tribe']
                    if not txt: continue 
                    
                    status_text.text(f"正在合成第 {idx+1}/{len(dialogue)} 句...")
                    bypass_client_validation(client, spk)
                    try: client.predict(ethnicity=trb, api_name="/lambda")
                    except: pass
                    
                    audio_path = client.predict(ref=spk, gen_text_input=txt, api_name="/default_speaker_tts")
                    
                    # 1. 加入人聲
                    clip = AudioFileClip(audio_path)
                    audio_clips.append(clip)
                    
                    # ----------------------------------------------------
                    # 💡 核心修改：在每句話後面加入 1 秒鐘靜音
                    # ----------------------------------------------------
                    # 偵測聲道數 (1=單聲道, 2=雙聲道)，確保靜音格式跟人聲一樣
                    ch = clip.nchannels 
                    # 產生 1 秒鐘的靜音數據 (全部填 0)
                    silence = AudioClip(lambda t: np.zeros((len(t), ch)), duration=1.0, fps=44100)
                    audio_clips.append(silence)
                    # ----------------------------------------------------
                    
                    progress_bar.progress((idx + 1) / len(dialogue))

                if audio_clips:
                    status_text.text("合成完成，正在接合...")
                    voice_track = concatenate_audioclips(audio_clips)
                    
                    # (以下為 BGM 混音邏輯，與之前相同)
                    final_output = voice_track
                    if bgm_file_d is not None:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_bgm:
                            tmp_bgm.write(bgm_file_d.getvalue())
                            tmp_bgm_path = tmp_bgm.name
                        music_track = AudioFileClip(tmp_bgm_path)
                        if music_track.duration < voice_track.duration:
                            n_loops = int(voice_track.duration / music_track.duration) + 1
                            music_track = concatenate_audioclips([music_track] * n_loops)
                        music_track = music_track.subclip(0, voice_track.duration + 1).volumex(bgm_vol_d)
                        final_output = CompositeAudioClip([music_track, voice_track])
                        os.remove(tmp_bgm_path)
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final_output.write_audiofile(temp_file.name, logger=None, fps=44100)
                    
                    # 關閉資源 (包含靜音片段)
                    for c in audio_clips: c.close()
                    final_output.close()
                    
                    st.success("🎉 Podcast 完成！(已加入每句 1 秒間隔)")
                    st.audio(temp_file.name, format="audio/mp3")
                    with open(temp_file.name, "rb") as f:
                        st.download_button("📥 下載 MP3", f, "podcast_with_delay.mp3", "audio/mp3")

            except Exception as e:
                st.error(f"錯誤: {e}")

# ==========================================
# 分頁 3: 長文有聲書 (含 1秒延遲)
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
                client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
                try: client.predict(ethnicity=long_tribe, api_name="/lambda")
                except: pass
                bypass_client_validation(client, long_speaker)

                for idx, chunk in enumerate(chunks):
                    stat.text(f"合成第 {idx+1}/{len(chunks)} 段...")
                    path = client.predict(ref=long_speaker, gen_text_input=chunk, api_name="/default_speaker_tts")
                    
                    clip = AudioFileClip(path)
                    clips_l.append(clip)
                    
                    # ----------------------------------------------------
                    # 💡 核心修改：每段結束後加入 1 秒鐘靜音
                    # ----------------------------------------------------
                    ch = clip.nchannels
                    silence = AudioClip(lambda t: np.zeros((len(t), ch)), duration=1.0, fps=44100)
                    clips_l.append(silence)
                    # ----------------------------------------------------
                    
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
                        mtrk = mtrk.subclip(0, voice_trk.duration + 1).volumex(bgm_vol_l)
                        final_out = CompositeAudioClip([mtrk, voice_trk])
                        os.remove(tmppath)

                    tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final_out.write_audiofile(tmpf.name, logger=None, fps=44100)
                    
                    for c in clips_l: c.close()
                    final_out.close()
                    
                    st.success("🎉 有聲書完成！(含段落間隔)")
                    st.audio(tmpf.name, format="audio/mp3")
                    with open(tmpf.name, "rb") as f:
                        st.download_button("📥 下載有聲書", f, "audiobook_delayed.mp3", "audio/mp3")

            except Exception as e:
                st.error(f"錯誤: {e}")
