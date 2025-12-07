# ==========================================
# 分頁 2: Podcast 對話 (含 1秒延遲 + 快速劇本模式)
# ==========================================
with tab2:
    st.subheader("Podcast 對話腳本編輯器")
    
    # -------------------------------------------------------
    # 🚀 新增功能：快速劇本匯入區 (Quick Script Import)
    # -------------------------------------------------------
    with st.expander("⚡ 快速劇本匯入 (大量輸入專用)", expanded=False):
        st.caption("設定好角色代號 (A, B)，直接貼上對話，省去一筆一筆選擇的時間。")
        
        # 1. 設定角色 (Role Definition)
        c_role1, c_role2 = st.columns(2)
        with c_role1:
            st.markdown("**🧑‍🦰 角色 A 設定**")
            role_a_tribe = st.selectbox("A 族群", list(speaker_map.keys()), key="ra_t", index=15) # 預設阿美
            role_a_spk = st.selectbox("A 語者", speaker_map[role_a_tribe], key="ra_s")
        
        with c_role2:
            st.markdown("**👩‍🦱 角色 B 設定**")
            role_b_tribe = st.selectbox("B 族群", list(speaker_map.keys()), key="rb_t", index=1) # 預設太魯閣
            role_b_spk = st.selectbox("B 語者", speaker_map[role_b_tribe], key="rb_s")

        # 2. 貼上劇本
        script_text = st.text_area(
            "請貼上劇本 (格式： 'A: 內容' 或 'B: 內容')", 
            height=200,
            placeholder="範例：\nA: Nga'ay ho! 你好嗎？\nB: Embiyax su hug? 我很好！\nA: 今天天氣真不錯。\nB: 是的，很適合去山上走走。"
        )

        c_imp1, c_imp2 = st.columns([1, 4])
        # 匯入按鈕
        if c_imp1.button("⚡ 解析並匯入"):
            if not script_text.strip():
                st.warning("請先輸入劇本內容！")
            else:
                lines = script_text.split('\n')
                new_entries = []
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    # 判斷是 A 還是 B 講話
                    if line.upper().startswith("A:") or line.startswith("A："):
                        clean_content = line[2:].strip()
                        new_entries.append({"tribe": role_a_tribe, "speaker": role_a_spk, "text": clean_content})
                    elif line.upper().startswith("B:") or line.startswith("B："):
                        clean_content = line[2:].strip()
                        new_entries.append({"tribe": role_b_tribe, "speaker": role_b_spk, "text": clean_content})
                    else:
                        # 如果沒寫 A 或 B，預設給 A (或是您可以選擇忽略)
                        new_entries.append({"tribe": role_a_tribe, "speaker": role_a_spk, "text": line})
                
                # 將新劇本加入 Session State
                # 您可以選擇是 "附加 (extend)" 還是 "覆蓋 (Override)"，這裡示範附加
                st.session_state['dialogue_list'].extend(new_entries)
                st.success(f"成功匯入 {len(new_entries)} 句台詞！請往下滑動查看。")
                st.rerun()
                
        if c_imp2.button("🗑️ 清空目前列表"):
            st.session_state['dialogue_list'] = []
            st.rerun()

    st.markdown("---")

    # -------------------------------------------------------
    # 原有的：手動編輯與背景音樂區
    # -------------------------------------------------------
    with st.expander("🎵 背景音樂設定 (BGM Settings)", expanded=False):
        col_bgm1, col_bgm2 = st.columns([3, 1])
        with col_bgm1:
            bgm_file_d = st.file_uploader("上傳背景音樂", type=["mp3", "wav"], key="bgm_d")
        with col_bgm2:
            bgm_vol_d = st.slider("音樂音量", 0.05, 0.5, 0.15, 0.05, key="vol_d")

    # 列表顯示區 (這部分維持原本的樣子，讓您可以手動微調)
    if not st.session_state['dialogue_list']:
        st.info("目前列表是空的，請使用上方的「快速劇本匯入」或點擊「新增」按鈕。")
    
    for i, line in enumerate(st.session_state['dialogue_list']):
        with st.container():
            col_idx, col_tribe, col_spk, col_text, col_del = st.columns([0.5, 2, 3, 6, 0.5])
            col_idx.write(f"#{i+1}")
            
            # 這裡加上 try-except 是為了防止匯入時語者名稱變更導致報錯
            try:
                idx_tribe = list(speaker_map.keys()).index(line['tribe'])
            except: idx_tribe = 0
            
            new_tribe = col_tribe.selectbox("族群", list(speaker_map.keys()), key=f"d_tr_{i}", index=idx_tribe, label_visibility="collapsed")
            
            avail_spks = speaker_map[new_tribe]
            try:
                idx_spk = avail_spks.index(line['speaker'])
            except: idx_spk = 0
            
            new_speaker = col_spk.selectbox("語者", avail_spks, key=f"d_sp_{i}", index=idx_spk, label_visibility="collapsed")
            new_text = col_text.text_input("台詞", value=line['text'], key=f"d_tx_{i}", label_visibility="collapsed")
            
            if col_del.button("❌", key=f"d_dl_{i}"):
                st.session_state['dialogue_list'].pop(i)
                st.rerun()
            
            st.session_state['dialogue_list'][i].update({'tribe': new_tribe, 'speaker': new_speaker, 'text': new_text})

    # 操作按鈕
    c_add, c_run = st.columns([1, 4])
    if c_add.button("➕ 手動新增一句"):
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
                    
                    clip = AudioFileClip(audio_path)
                    audio_clips.append(clip)
                    
                    # 加入 1 秒靜音
                    ch = clip.nchannels 
                    silence = AudioClip(lambda t: np.zeros((len(t), ch)), duration=1.0, fps=44100)
                    audio_clips.append(silence)
                    
                    progress_bar.progress((idx + 1) / len(dialogue))

                if audio_clips:
                    status_text.text("合成完成，正在接合...")
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
                        music_track = music_track.subclip(0, voice_track.duration + 1).volumex(bgm_vol_d)
                        final_output = CompositeAudioClip([music_track, voice_track])
                        os.remove(tmp_bgm_path)
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                    final_output.write_audiofile(temp_file.name, logger=None, fps=44100)
                    
                    for c in audio_clips: c.close()
                    final_output.close()
                    
                    st.success("🎉 Podcast 完成！")
                    st.audio(temp_file.name, format="audio/mp3")
                    with open(temp_file.name, "rb") as f:
                        st.download_button("📥 下載 MP3", f, "podcast_fast_import.mp3", "audio/mp3")

            except Exception as e:
                st.error(f"錯誤: {e}")
