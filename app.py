import streamlit as st
import streamlit.components.v1 as components
import os

# ---------------------------------------------------------
# Google Analytics 注入函式 (標準元件版)
# ---------------------------------------------------------
def inject_ga():
    GA_ID = "G-DB6VD72CJT"
    
    # 注意：這裡加上了 id="ga-container" 方便我們等一下尋找
    ga_code = f"""
    <div id="ga-container">
        <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){{dataLayer.push(arguments);}}
            gtag('js', new Date());
            gtag('config', '{GA_ID}');
            console.log('GA Initialized with ID: {GA_ID}'); // 加這行讓我們在後台看得到
        </script>
    </div>
    """
    
    # 插入一個隱形的 HTML 區塊
    components.html(ga_code, height=0, width=0)

# ---------------------------------------------------------
# 程式主入口
# ---------------------------------------------------------
st.set_page_config(page_title="原語 Podcast", layout="wide", initial_sidebar_state="expanded")

# 啟動 GA (這行一定要有！)
inject_ga()

st.title("🎙️ 族語Podcast內容產製程式")

# ... (請將您原本載入 pages 或其他邏輯貼在下方) ...
