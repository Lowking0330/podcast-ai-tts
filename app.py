import streamlit as st

st.set_page_config(
    page_title="Podcast 產製中心",
    page_icon="🎙️",
)

st.title("🎙️ 歡迎來到 Podcast 產製中心")

st.info("請展開左側的側邊欄 (Sidebar) 選擇功能頁面")

st.markdown("""
### 👈 請從左側選單選擇：

#### 1. 📄 穩定版_Podcast
> 這是您原本運作正常的功能（單句、對話、長文）。
> 如果不想測試新功能，請直接用這個。

#### 2. 🧪 AI實驗版_RAG
> 這是最新的測試功能，結合了 Google Gemini AI。
> 可以讀取 PDF 並自動撰寫劇本。

---
*系統狀態：Multi-Page 架構運作中*
""")
