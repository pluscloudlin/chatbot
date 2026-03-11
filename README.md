# chatbot
## 小組：只剩兩個人
## 組員：
  - D1149890 林伽紜
## 專案簡介
本專案是一個基於 **LangChain + Google Gemini API** 的多功能對話機器人，支援純文字對話與多模態檔案分析（圖片、PDF、程式碼與文字檔）。提供兩種使用方式：終端機互動模式與 Streamlit 網頁介面，並具備多輪對話記憶、動態角色切換、本地檔案勾選等進階功能。

## 目前功能
- **多輪對話**：支援上下文記憶，能延續先前的對話內容
- **多模態檔案分析**：
  - 🖼️ 圖片（`.jpg`、`.png`、`.gif`、`.webp`、`.bmp`）
  - 📄 PDF 文件（`.pdf`）
  - 📝 程式碼與文字檔（`.py`、`.js`、`.json`、`.csv`、`.md`、`.txt` 等 30+ 種格式）
- **Streamlit 網頁介面**（`app.py`）：
  - 拖放上傳檔案
  - 本地檔案掃描與勾選（支援全選 / 取消全選）
  - 多檔案同時分析
  - 動態 System Prompt 角色切換（一般助手、程式開發專家、翻譯助手、文案寫手、資料分析師、學習助教、自訂角色）
  - 清除對話紀錄
- **終端機互動模式**（`chatbot.py`）：
  - 使用 `/file <路徑>` 指令傳送檔案
  - 支援引號包裹含空格的檔案路徑
- **檔案大小限制**：單一檔案上限 20 MB
- **多編碼支援**：自動嘗試 UTF-8、Big5、GB2312、Latin-1 等編碼

## 執行方式
下載專案

範例指令：

```bash
git clone 你的專案網址
```

安裝依賴套件：

```bash
pip install -r requirements.txt
```

啟動 Streamlit 網頁介面：

```bash
streamlit run app.py
```

啟動終端機互動模式：

```bash
python chatbot.py
```

## 環境變數說明
請自行建立 .env 檔案，並填入自己的 API key。

範例：

```
GOOGLE_API_KEY=your_api_key_here
```

## 遇到的問題與解法
### 問題 1
- 問題： Git Push 被拒絕
- 解法： 在本地初始化 Git 並嘗試 `git push` 時，出現 `rejected - fetch first` 錯誤，因為 GitHub 遠端 repo 建立時自動產生了 README 等檔案，導致本地與遠端歷史不一致。

## 學習心得
在今天Git版本控制操作時，學到了許多經驗。包括了`.gitignore` 的設定、`git rm --cached` 取消追蹤、`git pull --rebase` 解決歷史分歧。這些都是實際開發中常會遇到的情境，對未來的協作開發很有幫助。

## GitHub 專案連結
- https://github.com/pluscloudlin/chatbot
- https://github.com/BobJu0721/Chatbot
