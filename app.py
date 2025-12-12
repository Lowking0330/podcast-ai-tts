import streamlit as st
import os

# ---------------------------------------------------------
# 進階版：直接將 GA 寫入網頁核心 (Header Injection)
# ---------------------------------------------------------
def inject_ga_head():
    GA_ID = "G-DB6VD72CJT"
    
    # 這是我們要插入的標準 GA4 代碼
    ga_code = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_ID}');
    </script>
    """
    
    # 1. 找到 Streamlit 在雲端主機上的安裝路徑
    # 通常位於 site-packages/streamlit/static/index.html
    index_path = os.path.join(os.path.dirname(st.__file__), "static", "index.html")
    
    try:
        # 2. 讀取目前的 index.html
        with open(index_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 3. 檢查是否已經插入過 (避免重複插入)
        if GA_ID not in html_content:
            # 4. 把 GA 代碼插入到 <head> 標籤的後面
            # 這樣它就會出現在網頁的最上方
            new_content = html_content.replace('<head>', f'<head>{ga_code}')
            
            # 5. 寫回檔案 (更新網頁核心)
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ GA4 代碼已成功植入網頁核心！")
            
    except Exception as e:
        print(f"⚠️ 植入失敗: {e}")

# ---------------------------------------------------------
# 程式主入口
# ---------------------------------------------------------

# 1. 設定頁面
st.set_page_config(page_title="原語 Podcast", layout="wide", initial_sidebar_state="expanded")

# 2. 執行植入 (這行會去修改底層檔案)
inject_ga_head()

# 3. 標題與介面
st.title("🎙️ 族語Podcast內容產製程式")

# ... (後面接您原本剩下的程式碼) ...
# ... (為了確保功能正常，建議把您原本的程式碼完整貼在下方) ...
