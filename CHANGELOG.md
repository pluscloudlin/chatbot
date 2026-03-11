# 工作紀錄 (Changelog)

## Gemini 對話機器人 — LangChain + Gemini API

---

## 功能總覽（目前版本 v1.3）

| 功能分類 | 說明 |
|---------|------|
| 🤖 AI 模型 | Google Gemini 2.5 Flash（透過 LangChain 整合） |
| 💬 多輪對話 | 支援對話記憶，能記住上下文 |
| 🎭 角色切換 | 6 種預設角色 + 自訂 System Prompt，動態切換 |
| 🖼️ 圖片分析 | 上傳 JPG / PNG / GIF / WebP / BMP，Gemini 可描述與分析圖片內容 |
| 📄 PDF 分析 | 上傳 PDF，Gemini 可閱讀、摘要、回答問題 |
| 📝 文件分析 | 上傳 TXT / MD / CSV / JSON / 程式碼等，嵌入內容供 Gemini 分析 |
| 📂 本地檔案勾選 | 掃描本地目錄，勾選多個檔案一次傳送 |
| 🌐 Web 介面 | Streamlit 聊天介面，含檔案拖放上傳、即時圖片預覽 |
| ⌨️ CLI 介面 | 終端機互動模式，使用 `/file` 指令附件 |
| 🌏 多語言 | 系統提示預設繁體中文，可對話任何語言 |

---

## 版本紀錄

### 2026-03-04

#### 🎭 v1.3 — 動態 System Prompt 切換與檔案勾選機制

- 新增 **動態 System Prompt 切換**功能：
  - 6 種預設角色：一般助手、程式開發專家、翻譯助手、文案寫手、資料分析師、學習助教
  - ✏️ 自訂模式：可自由輸入 System Prompt
  - 切換角色時保留對話紀錄，可接續對話
  - 側邊欄即時預覽目前的 Prompt 內容
- 新增 **本地檔案勾選機制**：
  - 自動掃描指定目錄中所有支援的檔案
  - Checkbox 勾選，支援多檔同時傳送
  - ✅ 全選 / ❎ 取消全選 按鈕
  - 可自訂掃描目錄路徑
  - 勾選的檔案與上傳的檔案可同時傳送
- 新增 `build_multi_file_content()` 函式，支援多檔案合併成單一多模態訊息

#### 🌐 v1.2 — Streamlit Web 介面

- 新增 `app.py`：Streamlit 聊天 Web UI
- Web 介面功能：
  - 美觀的漸層標題與現代化設計
  - 左側邊欄：檔案上傳區（支援拖放）、即時圖片預覽、格式說明
  - 中央區域：完整聊天介面，支援對話歷史滾動
  - 一鍵清除對話紀錄
- 使用 `st.session_state` 維護 Streamlit 顯示歷史 + LangChain 訊息歷史
- 使用 `@st.cache_resource` 快取 LLM 初始化，避免重複載入
- 啟動方式：`streamlit run app.py`
- 新增依賴：`streamlit>=1.40.0`

#### ✨ v1.1 — 多模態檔案支援

- 模型升級為 `gemini-2.5-flash`
- 新增 `/file` 指令，支援傳送檔案給 Gemini 分析：
  - 🖼️ **圖片**：`.jpg`、`.jpeg`、`.png`、`.gif`、`.webp`、`.bmp`（base64 編碼傳送）
  - 📄 **PDF**：`.pdf`（base64 編碼，利用 Gemini 原生 PDF 支援）
  - 📝 **文字/程式碼**：`.txt`、`.md`、`.csv`、`.json`、`.py`、`.js` 等（直接讀取內容嵌入）
  - 📎 **其他格式**：嘗試以純文字讀取
- 指令格式：
  - `/file <路徑>` — 傳送檔案後詢問問題
  - `/file <路徑> <問題>` — 傳送檔案並直接提問
  - 支援引號路徑（含空格的檔名）
- 重構架構：手動管理訊息歷史，以支援多模態 `HumanMessage`
- 檔案大小限制：20 MB
- 對話歷史中檔案訊息僅存文字摘要，節省記憶體
- 支援多種文字編碼自動偵測（UTF-8、Big5、GB2312、Latin-1）

#### 🚀 v1.0 — 初始版本建立

- 建立專案結構：`chatbot.py`、`requirements.txt`、`.env`
- 使用 **LangChain** + **Google Gemini API** 實作多輪對話機器人
- 功能：
  - 支援繁體中文對話
  - 使用 `InMemoryChatMessageHistory` 管理對話歷史
  - 使用 `RunnableWithMessageHistory` 自動注入歷史訊息
  - 系統提示設定為友善的中文 AI 助手
- 模型：`gemini-2.0-flash`
- 依賴套件：`langchain`、`langchain-google-genai`、`python-dotenv`

---

## 專案結構

```
chatbot/
├── .env                # 環境變數（GOOGLE_API_KEY）
├── app.py              # Streamlit Web 介面（主要使用）
├── chatbot.py          # CLI 終端機介面
├── requirements.txt    # Python 依賴套件
└── CHANGELOG.md        # 本檔案（工作紀錄）
```

## 啟動方式

```bash
# Web 介面（推薦）
streamlit run app.py

# 終端機介面
python chatbot.py
```
