import streamlit as st
import streamlit.components.v1 as components  # <--- 1. 引入元件庫

# ... 其他 import (如 os, sys 等) ...

# ---------------------------------------------------------
# Google Analytics 注入函式
# ---------------------------------------------------------
def inject_ga():
    # 👇👇👇 請在這裡填入您的 GA4 評估 ID 👇👇👇
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
    
    # 這裡將 HTML/JS 代碼插入網頁，height=0 讓它隱形
    components.html(ga_code, height=0)

# ---------------------------------------------------------
# 程式主入口
# ---------------------------------------------------------
# ... (上面是 def inject_ga 函式定義) ...

# 1. 設定頁面 (這行一定要在最前面)
st.set_page_config(page_title="原語 Podcast", layout="wide", initial_sidebar_state="expanded")

# 👇👇👇 2. 關鍵修正：請加上這一行！ 👇👇👇
inject_ga() 
# 👆👆👆 這行才是真正啟動 GA 的開關 👆👆👆

# 3. 標題與其他內容
st.title("🎙️ 族語Podcast內容產製程式")

# ... (後面接您原本的程式碼) ...
