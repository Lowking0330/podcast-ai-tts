import streamlit as st
import streamlit.components.v1 as components  # 引入元件庫
import os
import sys

# ---------------------------------------------------------
# Google Analytics 注入函式
# ---------------------------------------------------------
def inject_ga():
    # 您的 GA4 評估 ID
    GA_ID = "G-DB6VD72CJT"
    
    ga_code = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_ID}');
    </script>
    """
    
    # 將 HTML/JS 代碼插入網頁，height=0 讓它隱形
    components.html(ga_code, height=0)

# ---------------------------------------------------------
# 程式主入口
# ---------------------------------------------------------

# 1. 設定頁面 (這行一定要在所有 Streamlit 指令的最前面)
st.set_page_config(page_title="原語 Podcast", layout="wide", initial_sidebar_state="expanded")

# 2. 啟動 GA 分析 (關鍵！這行會執行上面的函式)
inject_ga()

# 3. 標題與介面
st.title("🎙️ 族語Podcast內容產製程式")

# ... (這裡接您原本剩下的程式碼，例如 st.write 或載入 pages 的邏輯) ...
