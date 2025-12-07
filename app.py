import streamlit as st
from gradio_client import Client
import re

# ---------------------------------------------------------
# 1. 設定與資料區
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

# ---------------------------------------------------------
# 2. 關鍵修復函式
# ---------------------------------------------------------

def clean_text(text):
    """
    清洗文字：移除 TTS 模型無法辨識的特殊符號 (解決 Error 1)
    """
    if not text:
        return ""
    # 移除破折號 ―, —, 以及可能導致錯誤的特殊標點
    # 這裡將它們替換為空格或逗號，保持語氣停頓
    text = text.replace("―", " ").replace("—", " ").replace("…", " ")
    # 移除多餘的空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def bypass_client_validation(client, speaker_id):
    """
    強制繞過 Gradio Client 的驗證 (解決 Error 2)
    直接針對 /default_speaker_tts 端點進行修改
    """
    try:
        # 嘗試找到 /default_speaker_tts 的定義
        # 注意：不同版本的 gradio_client 結構可能不同，這裡做多層防護
        target_endpoints = [
            client.endpoints.get('/default_speaker_tts'),
            client.endpoints.get('/custom_speaker_tts')
        ]
        
        for endpoint in target_endpoints:
            if endpoint and hasattr(endpoint, 'parameters'):
                for param in endpoint.parameters:
                    # 檢查這是不是那個限制語者清單的參數 (通常含有 'enum' 或 'choices')
                    if 'enum' in param:
                        if speaker_id not in param['enum']:
                            param['enum'].append(speaker_id)
                    
                    # 有些舊版是用 choices
                    if 'choices' in param:
                         if speaker_id not in param['choices']:
                            param['choices'].append(speaker_id)
                            
    except Exception as e:
        print(f"Bypass warning: {e}")

# ---------------------------------------------------------
# 3. 介面設計區
# ---------------------------------------------------------
st.title("臺灣原住民族語 Podcast 生成器 🎙️")
st.markdown("支援 16 族 42 種語音合成")

col1, col2 = st.columns(2)

with col1:
    # 預設 index=15 是阿美族，這裡設為 1 (太魯閣) 方便您測試
    selected_tribe = st.selectbox("步驟 1：選擇族群", list(speaker_map.keys()), index=15)

with col2:
    available_speakers = speaker_map[selected_tribe]
    selected_speaker = st.selectbox("步驟 2：選擇語者", available_speakers)

text_input = st.text_area("步驟 3：輸入要合成的文字", height=150, placeholder="請輸入族語文字...")

# ---------------------------------------------------------
# 4. 核心邏輯區
# ---------------------------------------------------------
if st.button("開始生成語音", type="primary"):
    # 1. 先執行文字清洗
    cleaned_text = clean_text(text_input)
    
    if not cleaned_text:
        st.warning("請輸入文字！(或您的文字含有過多非法符號)")
    else:
        # 顯示清洗後的文字讓使用者知道 (除錯用)
        if cleaned_text != text_input:
            st.caption(f"ℹ️ 系統已自動過濾特殊符號: {cleaned_text}")

        try:
            with st.spinner(f"正在連線並生成 {selected_speaker} 的聲音..."):
                
                client = Client("https://hnang-kari-ai-asi-sluhay.ithuan.tw/")
                
                # 2. 執行驗證繞過 (Client Hack)
                bypass_client_validation(client, selected_speaker)

                # 3. [重要] 先通知伺服器切換族群 (Server State Update)
                # 即使繞過了 Client 驗證，Server 若不知道現在是太魯閣族，也可能報錯
                try:
                    client.predict(ethnicity=selected_tribe, api_name="/lambda")
                except Exception as e:
                    print(f"切換族群警告 (可忽略): {e}")

                # 4. 正式合成
                result = client.predict(
                    ref=selected_speaker,       
                    gen_text_input=cleaned_text,  
                    api_name="/default_speaker_tts"
                )
                
                st.success("生成成功！")
                st.audio(result)
                
        except Exception as e:
            st.error("生成失敗")
            st.error(f"錯誤原因：{str(e)}")
            st.markdown("---")
            st.caption("除錯建議：")
            st.caption("1. 如果出現 Value is not in list，代表 Hack 尚未生效，請重試一次。")
            st.caption("2. 如果出現 Unknown characters，請檢查文字是否包含特殊符號。")
