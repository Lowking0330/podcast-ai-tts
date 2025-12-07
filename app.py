import streamlit as st
from gradio_client import Client
# 引入 moviepy 的核心與合成工具
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip
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
# 分頁 2: Podcast 功能 (含 BGM 混音)
# ==========================================
with tab2:
    st.subheader("Podcast 對話腳本編輯器")
    
    # ------------------
    # 新增：BGM 設定區
    # ------------------
    with st.expander("🎵 背景音樂設定 (BGM Settings)", expanded=True):
        col_bgm1, col_bgm2 = st.columns([3, 1])
        with col_bgm1:
            bgm_file = st.file_uploader("上傳背景音樂 (支援 .mp3, .wav)", type=["mp3", "wav"])
        with col_bgm2:
            bgm_volume = st.slider("背景音樂音量", 0.05, 0.5, 0.15, 0.05, help="1.0 是原聲，建議設定在 0.1~0.2 之間以免蓋過人聲")

    st.markdown("---")

    # --- 腳本編輯區 (維持不變) ---
    for i, line in enumerate(st.session_state['dialogue_list']):
        with st.container():
            col_idx, col_tribe, col_spk, col_text, col_del = st.columns([0.5, 2, 3, 6, 0.5])
            col_idx.write(f"#{i+1}")
            
            new_tribe = col_tribe.selectbox(
                "族群", list(speaker_map.keys()), 
                key=f"tribe_{i}", 
                index=list(speaker_map.keys()).index(line['tribe']) if line['tribe'] in speaker_map else 0,
                label_visibility="collapsed"
            )
            
            avail_spks = speaker_map[new_tribe]
            current_spk_idx = 0
            if line['speaker'] in avail_spks:
                current_spk_idx = avail_spks.index(line['speaker'])
                
            new_speaker = col_spk.selectbox(
                "語者", avail_spks, 
                key=f"spk_{i}", 
                index=current_spk_idx,
                label_visibility="collapsed"
            )
            
            new_text = col_text.text_input(
                "台詞", value=line['text'], 
                key=f"text_{i}",
                label_visibility="collapsed",
                placeholder="請輸入台詞..."
            )
            
            if col_del.button("❌", key=f"del_{i}"):
                st.session_state['dialogue_list'].pop(i)
                st.rerun()

            st.session_state['dialogue_list'][i]['tribe'] = new_tribe
            st.session_state['dialogue_list'][i]['speaker'] = new_speaker
            st.session_state['dialogue_list'][i]['text'] = new_text

    st.markdown("---")
    c_add, c_run = st.columns([1, 4])
    
    if c_add.button("➕ 新增一句對話"):
        last_item = st.session_state['dialogue_list'][-1] if st.session_state['dialogue_list'] else {"tribe": "阿美", "speaker": "阿美_海岸_男聲", "text": ""}
        st.session_state['dialogue_list'].append({
            "tribe": last_item['tribe'],
            "speaker": last_item['speaker'],
            "text": ""
        })
        st.rerun()

    if c_run.button("🎙️ 開始合成完整 Podcast (含混音)", type="primary"):
        dialogue = st.session_state['dialogue_list']
        if not dialogue:
            st.warning("腳本是空的！")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            audio_clips = []
            
            try:
                # -----------------------
                # 階段 1: 合成人聲
                # -----------------------
                client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
                
                for idx, item in enumerate(dialogue):
                    txt = clean_text(item['text'])
                    spk = item['speaker']
                    trb = item['tribe']
                    
                    if not txt: continue 
                    
                    status_text.text(f"正在合成第 {idx+1}/{len(dialogue)} 句：{spk} 說「{txt[:10]}...」")
                    
                    bypass_client_validation(client, spk)
                    try: client.predict(ethnicity=trb, api_name="/lambda")
                    except: pass
                    
                    audio_path = client.predict(
                        ref=spk, 
                        gen_text_input=txt, 
                        api_name="/default_speaker_tts"
                    )
                    
                    # 讀取人聲片段
                    clip = AudioFileClip(audio_path)
                    audio_clips.append(clip)
                    
                    # 加入一個小小的靜音間隔 (0.5秒)
                    # 注意：moviepy 1.0.3 產生靜音比較麻煩，我們這裡暫時直接用「空格」
                    # 如果需要更精確的靜音，可以載入一個空的靜音檔，但簡單拼接已足夠
                    
                    progress_bar.progress((idx + 1) / len(dialogue))

                if audio_clips:
                    status_text.text("人聲合成完畢，正在進行 BGM 混音...")
                    
                    # 1. 串接所有人聲
                    voice_track = concatenate_audioclips(audio_clips)
                    final_duration = voice_track.duration
                    
                    final_output = voice_track # 預設輸出只有人聲
                    
                    # -----------------------
                    # 階段 2: BGM 混音邏輯
                    # -----------------------
                    if bgm_file is not None:
                        # 將上傳的檔案存為暫存檔
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_bgm:
                            tmp_bgm.write(bgm_file.getvalue())
                            tmp_bgm_path = tmp_bgm.name
                        
                        # 讀取 BGM
                        music_track = AudioFileClip(tmp_bgm_path)
                        
                        # A. 調整長度：如果音樂太短，就循環播放；如果太長，就切掉
                        # MoviePy 1.0.3 的 loop 寫法
                        if music_track.duration < final_duration:
                            # 計算需要循環幾次
                            n_loops = int(final_duration / music_track.duration) + 1
                            # 簡單暴力法：串接自己 n 次
                            music_track = concatenate_audioclips([music_track] * n_loops)
                        
                        # 裁切到跟人聲一樣長 (多給 1 秒緩衝)
                        music_track = music_track.subclip(0, final_duration + 1)
                        
                        # B. 調整音量 (Volumex)
                        music_track = music_track.volumex(bgm_volume)
                        
                        # C. 合成 (Composite)
                        # 將人聲和背景音樂疊加
                        # 確保人聲在最上層
                        final_output = CompositeAudioClip([music_track, voice_track])
                        
                        # 刪除 BGM 暫存檔
                        os.remove(tmp_bgm_path)

                    # -----------------------
                    # 階段 3: 匯出
                    # -----------------------
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final_output.write_audiofile(temp_file.name, logger=None, fps=44100) # 設定 fps 避免相容性問題
                    
                    # 釋放資源
                    for clip in audio_clips:
                        clip.close()
                    final_output.close()

                    st.success("🎉 專業 Podcast 製作完成！")
                    st.audio(temp_file.name, format="audio/mp3")
                    
                    with open(temp_file.name, "rb") as f:
                        st.download_button(
                            label="📥 下載最終 MP3",
                            data=f,
                            file_name="professional_indigenous_podcast.mp3",
                            mime="audio/mp3"
                        )
                else:
                    st.warning("沒有成功生成任何語音片段。")
                
            except Exception as e:
                st.error("發生錯誤")
                st.error(f"詳細錯誤: {e}")
