import streamlit as st
import streamlit.components.v1 as components
import os



# ---------------------------------------------------------
# 程式主入口
# ---------------------------------------------------------
st.set_page_config(page_title="原語 Podcast", layout="wide", initial_sidebar_state="expanded")

# 啟動 GA (這行一定要有！)
inject_ga()

st.title("🎙️ 族語Podcast內容產製程式")

# ... (請將您原本載入 pages 或其他邏輯貼在下方) ...
