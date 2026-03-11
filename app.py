"""
Streamlit 聊天介面 — LangChain + Gemini API
支援多輪對話、圖片 / PDF / 文件上傳、動態 System Prompt、本地檔案勾選。
"""

import os
import base64
import mimetypes
import glob

import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ──────────────── 常數 ────────────────
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm",
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".css",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".log", ".sql",
    ".sh", ".bat", ".rb", ".go", ".rs", ".swift", ".kt",
}
ALL_SUPPORTED = IMAGE_EXTENSIONS | PDF_EXTENSIONS | TEXT_EXTENSIONS
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# 預設 System Prompt 模板
SYSTEM_PROMPTS = {
    "🤖 一般助手": (
        "你是一個友善且樂於助人的 AI 助手。"
        "請用繁體中文回答使用者的問題，回覆要清楚、簡潔且有幫助。"
        "你可以分析使用者傳送的圖片、PDF 和各種文件。"
    ),
    "💻 程式開發專家": (
        "你是一位資深的全端軟體開發專家。"
        "請用繁體中文回答，重點提供程式碼範例、最佳實踐和技術解釋。"
        "回覆中請使用 Markdown 格式化程式碼區塊，並標註程式語言。"
        "如果使用者提供程式碼或檔案，請仔細 review 並給出改進建議。"
    ),
    "🌐 翻譯助手": (
        "你是一位專業的多語言翻譯助手。"
        "根據使用者的需求翻譯文字，預設將內容翻譯為繁體中文和英文。"
        "翻譯時保留原文的語氣與風格，並在必要時提供翻譯說明。"
        "如果使用者傳送文件，請翻譯文件內容。"
    ),
    "📝 文案寫手": (
        "你是一位創意文案與內容寫作專家。"
        "請用繁體中文協助使用者撰寫各類文案，包括行銷文案、社群貼文、"
        "部落格文章、電子郵件等。回覆要有創意且引人入勝。"
    ),
    "📊 資料分析師": (
        "你是一位資料分析專家。"
        "請用繁體中文協助使用者分析資料，解讀圖表、統計數據。"
        "如果使用者傳送 CSV 或資料檔案，請分析內容並提供見解與建議。"
        "善用表格和條列式清單來呈現分析結果。"
    ),
    "📚 學習助教": (
        "你是一位耐心且知識淵博的學習助教。"
        "請用繁體中文回答，以清楚易懂的方式解釋概念。"
        "善用比喻和範例幫助理解，並在適當時提出引導性問題。"
        "如果使用者傳送教材或筆記，請協助整理重點和複習。"
    ),
    "✏️ 自訂": None,  # 代表由使用者自行輸入
}


# ──────────────── 工具函式 ────────────────

def get_file_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in TEXT_EXTENSIONS:
        return "text"
    return "unknown"


def build_file_content(file_bytes: bytes, filename: str, user_text: str) -> list:
    """根據檔案類型建立多模態 content 列表。"""
    file_type = get_file_type(filename)
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    if file_type == "image":
        mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
        return [
            {"type": "text", "text": user_text or f"請描述這張圖片：{filename}"},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]

    if file_type == "pdf":
        return [
            {"type": "text", "text": user_text or f"請閱讀並摘要這份 PDF：{filename}"},
            {"type": "image_url", "image_url": {"url": f"data:application/pdf;base64,{b64}"}},
        ]

    # 文字類或未知類型 → 嘗試解碼
    text_content = None
    for enc in ("utf-8", "big5", "gb2312", "latin-1"):
        try:
            text_content = file_bytes.decode(enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if text_content is None:
        raise ValueError(f"無法讀取檔案：{filename}")

    return [
        {
            "type": "text",
            "text": (
                f"以下是檔案 `{filename}` 的內容：\n```\n{text_content}\n```\n\n"
                f"{user_text or '請閱讀上述檔案並提供摘要。'}"
            ),
        }
    ]


def build_multi_file_content(files_data: list[tuple[bytes, str]], user_text: str) -> list:
    """將多個檔案合併成一個多模態 content 列表。"""
    parts = []
    file_names = []

    for file_bytes, filename in files_data:
        file_type = get_file_type(filename)
        b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
        file_names.append(filename)

        if file_type == "image":
            mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
            parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        elif file_type == "pdf":
            parts.append({"type": "image_url", "image_url": {"url": f"data:application/pdf;base64,{b64}"}})
        else:
            # 文字檔
            text_content = None
            for enc in ("utf-8", "big5", "gb2312", "latin-1"):
                try:
                    text_content = file_bytes.decode(enc)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            if text_content:
                parts.append({
                    "type": "text",
                    "text": f"以下是檔案 `{filename}` 的內容：\n```\n{text_content}\n```",
                })

    # 最後加上使用者的問題
    names_str = "、".join(file_names)
    default_text = f"請分析以上 {len(file_names)} 個檔案（{names_str}）並提供摘要。"
    parts.insert(0, {"type": "text", "text": user_text or default_text})

    return parts


def scan_local_files(directory: str) -> list[dict]:
    """掃描指定目錄，回傳支援的檔案清單。"""
    files = []
    if not os.path.isdir(directory):
        return files

    for entry in sorted(os.listdir(directory)):
        filepath = os.path.join(directory, entry)
        if not os.path.isfile(filepath):
            continue
        ext = os.path.splitext(entry)[1].lower()
        if ext not in ALL_SUPPORTED:
            continue
        size = os.path.getsize(filepath)
        if size > MAX_FILE_SIZE:
            continue
        files.append({
            "name": entry,
            "path": filepath,
            "type": get_file_type(entry),
            "size": size,
        })
    return files


# ──────────────── 初始化 LLM ────────────────

@st.cache_resource
def init_llm():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ 找不到 GOOGLE_API_KEY，請在 `.env` 中設定。")
        st.stop()
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.7,
    )


# ──────────────── 頁面設定 ────────────────

st.set_page_config(
    page_title="Gemini 對話機器人",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0 0.5rem;
    }
    .main-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        margin-bottom: 0.25rem;
    }
    .main-header p { color: #888; font-size: 0.9rem; }

    .file-badge {
        display: inline-flex; align-items: center; gap: 0.4rem;
        padding: 0.35rem 0.75rem; border-radius: 1rem;
        font-size: 0.8rem; font-weight: 500; margin-bottom: 0.5rem;
    }
    .file-badge.image { background: #e8f5e9; color: #2e7d32; }
    .file-badge.pdf   { background: #fce4ec; color: #c62828; }
    .file-badge.text  { background: #e3f2fd; color: #1565c0; }
    .file-badge.other { background: #f3e5f5; color: #6a1b9a; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9ff 0%, #f0f2ff 100%);
    }
    [data-testid="stFileUploader"] { margin-bottom: 0; }

    .prompt-preview {
        background: #f8f9fa; border-left: 3px solid #667eea;
        padding: 0.5rem 0.75rem; border-radius: 0 0.5rem 0.5rem 0;
        font-size: 0.78rem; color: #555; margin-top: 0.5rem;
        max-height: 80px; overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────── 初始化 Session State ────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.lc_messages = []

if "active_prompt_name" not in st.session_state:
    st.session_state.active_prompt_name = "🤖 一般助手"
    st.session_state.active_prompt_text = SYSTEM_PROMPTS["🤖 一般助手"]
    st.session_state.custom_prompt = ""

if "files_dir" not in st.session_state:
    st.session_state.files_dir = os.path.dirname(os.path.abspath(__file__))


# ──────────────── 側邊欄 ────────────────

with st.sidebar:
    # ── 1. System Prompt 切換 ──
    st.markdown("### 🎭 角色設定")

    prompt_names = list(SYSTEM_PROMPTS.keys())
    current_idx = prompt_names.index(st.session_state.active_prompt_name) \
        if st.session_state.active_prompt_name in prompt_names else 0

    selected_name = st.selectbox(
        "選擇角色",
        prompt_names,
        index=current_idx,
        key="prompt_selector",
    )

    # 自訂 prompt 輸入
    if selected_name == "✏️ 自訂":
        custom_text = st.text_area(
            "輸入自訂 System Prompt",
            value=st.session_state.custom_prompt,
            height=120,
            placeholder="例如：你是一位專業的法律顧問，請用繁體中文回答法律相關問題...",
        )
    else:
        custom_text = None

    # 判斷 prompt 是否有變更
    if selected_name == "✏️ 自訂":
        new_prompt_text = custom_text or ""
    else:
        new_prompt_text = SYSTEM_PROMPTS[selected_name]

    prompt_changed = (
        selected_name != st.session_state.active_prompt_name
        or new_prompt_text != st.session_state.active_prompt_text
    )

    # 套用按鈕
    if prompt_changed and new_prompt_text:
        if st.button("🔄 套用新角色", use_container_width=True, type="primary"):
            st.session_state.active_prompt_name = selected_name
            st.session_state.active_prompt_text = new_prompt_text
            if selected_name == "✏️ 自訂":
                st.session_state.custom_prompt = custom_text
            st.rerun()

    # 顯示目前的 prompt 預覽
    st.markdown(
        f'<div class="prompt-preview">📋 <b>目前角色：</b>{st.session_state.active_prompt_name}<br>'
        f'{st.session_state.active_prompt_text[:100]}{"…" if len(st.session_state.active_prompt_text) > 100 else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── 2. 檔案上傳 ──
    st.markdown("### 📤 上傳檔案")
    uploaded_file = st.file_uploader(
        "拖放或點擊上傳",
        type=[ext.lstrip(".") for ext in ALL_SUPPORTED],
        help="支援圖片、PDF、程式碼和文字檔（≤ 20 MB）",
    )

    if uploaded_file:
        ftype = get_file_type(uploaded_file.name)
        emoji = {"image": "🖼️", "pdf": "📄", "text": "📝"}.get(ftype, "📎")
        cls = {"image": "image", "pdf": "pdf", "text": "text"}.get(ftype, "other")
        st.markdown(
            f'<div class="file-badge {cls}">{emoji} {uploaded_file.name} '
            f'({uploaded_file.size / 1024:.0f} KB)</div>',
            unsafe_allow_html=True,
        )
        if ftype == "image":
            st.image(uploaded_file, use_container_width=True)

    st.divider()

    # ── 3. 本地檔案勾選 ──
    st.markdown("### 📂 本地檔案")

    files_dir = st.text_input(
        "掃描目錄",
        value=st.session_state.files_dir,
        help="輸入要掃描的資料夾路徑",
    )
    st.session_state.files_dir = files_dir

    local_files = scan_local_files(files_dir)

    if local_files:
        st.caption(f"找到 {len(local_files)} 個支援的檔案：")

        # 全選 / 取消全選
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 全選", use_container_width=True, key="select_all"):
                for f in local_files:
                    st.session_state[f"file_check_{f['name']}"] = True
                st.rerun()
        with col2:
            if st.button("❎ 取消全選", use_container_width=True, key="deselect_all"):
                for f in local_files:
                    st.session_state[f"file_check_{f['name']}"] = False
                st.rerun()

        selected_local_files = []
        for f in local_files:
            emoji = {"image": "🖼️", "pdf": "📄", "text": "📝"}.get(f["type"], "📎")
            size_str = f"{f['size'] / 1024:.0f} KB" if f["size"] < 1024 * 1024 else f"{f['size'] / 1024 / 1024:.1f} MB"
            checked = st.checkbox(
                f"{emoji} {f['name']} ({size_str})",
                key=f"file_check_{f['name']}",
            )
            if checked:
                selected_local_files.append(f)

        if selected_local_files:
            st.success(f"已選取 {len(selected_local_files)} 個檔案")
    else:
        selected_local_files = []
        if files_dir and os.path.isdir(files_dir):
            st.info("此目錄沒有支援的檔案")
        elif files_dir:
            st.warning("目錄不存在")

    st.divider()

    # ── 4. 其他操作 ──
    if st.button("🗑️ 清除對話紀錄", use_container_width=True):
        st.session_state.messages = []
        st.session_state.lc_messages = []
        st.rerun()


# ──────────────── 主區域 ────────────────

st.markdown(
    '<div class="main-header">'
    "<h1>🤖 Gemini 對話機器人</h1>"
    "<p>LangChain + Gemini 2.5 Flash — 支援圖片、PDF、文件分析</p>"
    "</div>",
    unsafe_allow_html=True,
)

llm = init_llm()
system_message = SystemMessage(content=st.session_state.active_prompt_text)

# 顯示對話歷史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "file_info" in msg:
            fi = msg["file_info"]
            if isinstance(fi, list):
                for f in fi:
                    emoji = {"image": "🖼️", "pdf": "📄", "text": "📝"}.get(f["type"], "📎")
                    st.caption(f"{emoji} 已附件：{f['name']}")
            else:
                emoji = {"image": "🖼️", "pdf": "📄", "text": "📝"}.get(fi["type"], "📎")
                st.caption(f"{emoji} 已附件：{fi['name']}")
                if fi["type"] == "image" and "preview" in fi:
                    st.image(base64.b64decode(fi["preview"]), use_container_width=True)
        st.markdown(msg["content"])


# 處理使用者輸入
user_input = st.chat_input("輸入訊息，或上傳 / 勾選檔案後提問…")

if user_input:
    # ── 收集所有附件 ──
    all_files = []    # list of (bytes, filename)
    all_file_info = []  # for display

    # 上傳的檔案
    if uploaded_file is not None:
        fb = uploaded_file.getvalue()
        if len(fb) <= MAX_FILE_SIZE:
            all_files.append((fb, uploaded_file.name))
            ftype = get_file_type(uploaded_file.name)
            info = {"name": uploaded_file.name, "type": ftype}
            if ftype == "image":
                info["preview"] = base64.standard_b64encode(fb).decode("utf-8")
            all_file_info.append(info)

    # 勾選的本地檔案
    for f in selected_local_files:
        try:
            with open(f["path"], "rb") as fh:
                fb = fh.read()
            all_files.append((fb, f["name"]))
            all_file_info.append({"name": f["name"], "type": f["type"]})
        except Exception:
            pass

    has_files = len(all_files) > 0

    # ── 顯示使用者訊息 ──
    display_msg = {"role": "user", "content": user_input}
    if all_file_info:
        display_msg["file_info"] = all_file_info
    st.session_state.messages.append(display_msg)

    with st.chat_message("user"):
        for fi in all_file_info:
            emoji = {"image": "🖼️", "pdf": "📄", "text": "📝"}.get(fi["type"], "📎")
            st.caption(f"{emoji} 已附件：{fi['name']}")
            if fi["type"] == "image" and "preview" in fi:
                st.image(base64.b64decode(fi["preview"]), use_container_width=True)
        st.markdown(user_input)

    # ── 建立 LangChain 訊息 ──
    if has_files:
        try:
            if len(all_files) == 1:
                content_parts = build_file_content(all_files[0][0], all_files[0][1], user_input)
            else:
                content_parts = build_multi_file_content(all_files, user_input)
            lc_msg = HumanMessage(content=content_parts)
            names = "、".join(fi["name"] for fi in all_file_info)
            history_msg = HumanMessage(content=f"[已附件：{names}] {user_input}")
        except ValueError as e:
            st.error(str(e))
            st.stop()
    else:
        lc_msg = HumanMessage(content=user_input)
        history_msg = lc_msg

    # ── 呼叫 Gemini ──
    with st.chat_message("assistant"):
        with st.spinner("思考中…"):
            try:
                full_messages = [system_message] + st.session_state.lc_messages + [lc_msg]
                response = llm.invoke(full_messages)
                reply = response.content
            except Exception as e:
                reply = f"❌ 發生錯誤：{e}"
        st.markdown(reply)

    # ── 更新歷史 ──
    st.session_state.lc_messages.append(history_msg)
    st.session_state.lc_messages.append(AIMessage(content=reply))
    st.session_state.messages.append({"role": "assistant", "content": reply})
