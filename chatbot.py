"""
LangChain + Gemini API 對話機器人
使用 Google Gemini 模型進行多輪對話，支援對話歷史記憶。
支援傳送圖片、PDF 與文件。
"""

import os
import sys
import json
import base64
import mimetypes
from datetime import datetime

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory


# ──────────────── 支援的檔案類型 ────────────────
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm",
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".css",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".log", ".sql",
    ".sh", ".bat", ".rb", ".go", ".rs", ".swift", ".kt",
}


def get_file_type(filepath: str) -> str:
    """根據副檔名判斷檔案類型，回傳 'image' / 'pdf' / 'text' / 'unknown'。"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in TEXT_EXTENSIONS:
        return "text"
    return "unknown"


def encode_file_base64(filepath: str) -> str:
    """將檔案內容編碼為 base64 字串。"""
    with open(filepath, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def read_text_file(filepath: str) -> str:
    """以多種編碼嘗試讀取文字檔案。"""
    for enc in ("utf-8", "big5", "gb2312", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"無法以已知編碼讀取檔案：{filepath}")


def build_file_message(filepath: str, user_text: str) -> HumanMessage:
    """根據檔案類型建立含多模態內容的 HumanMessage。"""
    file_type = get_file_type(filepath)
    filename = os.path.basename(filepath)

    if file_type == "image":
        mime_type = mimetypes.guess_type(filepath)[0] or "image/jpeg"
        b64 = encode_file_base64(filepath)
        content = [
            {"type": "text", "text": user_text or f"請描述這張圖片：{filename}"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
            },
        ]

    elif file_type == "pdf":
        b64 = encode_file_base64(filepath)
        content = [
            {"type": "text", "text": user_text or f"請閱讀並摘要這份 PDF 文件：{filename}"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:application/pdf;base64,{b64}"},
            },
        ]

    elif file_type == "text":
        text_content = read_text_file(filepath)
        content = [
            {
                "type": "text",
                "text": (
                    f"以下是檔案 `{filename}` 的內容：\n"
                    f"```\n{text_content}\n```\n\n"
                    f"{user_text or '請閱讀上述檔案內容並提供摘要。'}"
                ),
            },
        ]

    else:
        # 未知類型 → 嘗試以純文字讀取
        try:
            text_content = read_text_file(filepath)
            content = [
                {
                    "type": "text",
                    "text": (
                        f"以下是檔案 `{filename}` 的內容：\n"
                        f"```\n{text_content}\n```\n\n"
                        f"{user_text or '請閱讀上述檔案內容並提供摘要。'}"
                    ),
                },
            ]
        except Exception:
            raise ValueError(f"不支援的檔案格式：{filename}")

    return HumanMessage(content=content)


# ──────────────── 對話歷史儲存 ────────────────

HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history")
os.makedirs(HISTORY_DIR, exist_ok=True)


def save_history(messages: list, session_id: str = "default"):
    """將對話歷史儲存為 JSON 檔案至 history/ 資料夾。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_{session_id}_{timestamp}.json"
    filepath = os.path.join(HISTORY_DIR, filename)

    records = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        records.append({"role": role, "content": content})

    data = {
        "session_id": session_id,
        "saved_at": datetime.now().isoformat(),
        "messages": records,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


# ──────────────── 建立 Chatbot ────────────────

def create_chatbot():
    """建立 Gemini LLM、系統訊息與對話歷史管理函式。"""
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到 GOOGLE_API_KEY。")
        print("   請在 .env 檔案中設定 GOOGLE_API_KEY=你的金鑰")
        sys.exit(1)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.7,
    )

    system_message = SystemMessage(content=(
        "你是一個友善且樂於助人的 AI 助手。"
        "請用繁體中文回答使用者的問題，回覆要清楚、簡潔且有幫助。"
        "你可以分析使用者傳送的圖片、PDF 和各種文件。"
    ))

    store: dict[str, InMemoryChatMessageHistory] = {}

    def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]

    return llm, system_message, get_session_history


# ──────────────── 輸入解析 ────────────────

def parse_input(user_input: str):
    """解析使用者輸入，判斷是否含有 /file 指令。

    支援格式：
        /file <路徑>           → 僅附件（稍後詢問問題）
        /file <路徑> <問題>    → 附件 + 問題
        /file "<含空格路徑>"   → 引號包裹路徑
        一般文字               → 純文字訊息

    Returns:
        (filepath | None, text)
    """
    if not user_input.startswith("/file "):
        return None, user_input

    rest = user_input[6:].strip()

    # 處理引號路徑
    if rest and rest[0] in ('"', "'"):
        quote = rest[0]
        end = rest.find(quote, 1)
        if end != -1:
            return rest[1:end], rest[end + 1:].strip()
        return rest[1:], ""

    # 無引號：從長到短找出合法的檔案路徑
    tokens = rest.split()
    for i in range(len(tokens), 0, -1):
        candidate = " ".join(tokens[:i])
        if os.path.isfile(candidate):
            return candidate, " ".join(tokens[i:])

    # 找不到時，以第一個 token 當作路徑（之後會報錯提示）
    return tokens[0], " ".join(tokens[1:]) if len(tokens) > 1 else ""


# ──────────────── 主程式 ────────────────

def main():
    """啟動互動式對話迴圈。"""
    print("=" * 55)
    print("🤖  Gemini 對話機器人 (LangChain + 多模態)")
    print("=" * 55)
    print("指令說明：")
    print("  /file <路徑>          傳送檔案（圖片 / PDF / 文件）")
    print("  /file <路徑> <問題>   傳送檔案並提問")
    print("  quit / exit / 結束    結束對話")
    print("-" * 55)
    print(f"📁 支援格式：圖片({', '.join(sorted(IMAGE_EXTENSIONS))})")
    print(f"             PDF(.pdf)、程式碼與文字檔")
    print("-" * 55)

    llm, system_message, get_session_history = create_chatbot()
    session_id = "default"
    history = get_session_history(session_id)

    while True:
        try:
            user_input = input("\n🧑 你：").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 再見！")
            if history.messages:
                fp = save_history(history.messages, session_id)
                print(f"💾 對話紀錄已儲存：{fp}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "bye", "結束"):
            print("\n👋 再見！感謝使用！")
            if history.messages:
                fp = save_history(history.messages, session_id)
                print(f"💾 對話紀錄已儲存：{fp}")
            break

        try:
            filepath, text = parse_input(user_input)

            if filepath:
                # ── 檔案模式 ──
                filepath = os.path.expanduser(filepath)

                if not os.path.isfile(filepath):
                    print(f"\n❌ 找不到檔案：{filepath}")
                    continue

                file_size = os.path.getsize(filepath)
                max_size = 20 * 1024 * 1024  # 20 MB
                if file_size > max_size:
                    print(f"\n❌ 檔案太大（{file_size / 1024 / 1024:.1f} MB），上限為 20 MB")
                    continue

                file_type = get_file_type(filepath)
                emoji = {"image": "🖼️", "pdf": "📄", "text": "📝"}.get(file_type, "📎")
                print(f"\n{emoji} 正在處理檔案：{os.path.basename(filepath)}...")

                # 若使用者未附帶問題，則再詢問一次
                if not text:
                    try:
                        text = input("❓ 請輸入關於此檔案的問題（直接 Enter 使用預設提問）：").strip()
                    except (KeyboardInterrupt, EOFError):
                        print("\n\n👋 再見！")
                        break

                message = build_file_message(filepath, text)
            else:
                # ── 純文字模式 ──
                message = HumanMessage(content=text)

            # 組合訊息列表：系統提示 + 對話歷史 + 當前訊息
            messages = [system_message] + history.messages + [message]

            # 呼叫 Gemini
            response = llm.invoke(messages)

            # 更新對話歷史（檔案訊息只記錄文字摘要，避免佔用過多記憶體）
            if filepath:
                summary = f"[已傳送檔案：{os.path.basename(filepath)}] {text}"
                history.add_message(HumanMessage(content=summary))
            else:
                history.add_message(message)
            history.add_message(response)

            print(f"\n🤖 Gemini：{response.content}")

        except ValueError as e:
            print(f"\n❌ {e}")
        except Exception as e:
            print(f"\n❌ 發生錯誤：{e}")


if __name__ == "__main__":
    main()
