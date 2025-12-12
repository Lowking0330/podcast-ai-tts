import streamlit as st
import os
import streamlit_analytics # <--- 1. 引入套件

# ---------------------------------------------------------
# 程式主入口
# ---------------------------------------------------------
with streamlit_analytics.track(): # <--- 2. 包裝所有邏輯
    
    st.set_page_config(page_title="原語 Podcast", layout="wide", initial_sidebar_state="expanded") 
    
    # ... (您的所有 UI 程式碼，從這裡開始都需要縮排)
    st.title("🎙️ 族語Podcast內容產製程式")
    # ...
