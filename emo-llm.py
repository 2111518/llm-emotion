import os
from datetime import datetime
import google.generativeai as genai
import pandas as pd

# 參數設定區
API_KEY_FILE = "api-key.txt"
CSV_FILE = "sentiment-data.csv"

# 初始化 API Key 與 Gemini 模型
if not os.path.exists(API_KEY_FILE):
    raise FileNotFoundError(f"找不到 API 金鑰檔案: {API_KEY_FILE}")

with open(API_KEY_FILE, "r", encoding="utf-8") as f:
    api_key = f.read().strip()

genai.configure(api_key=api_key)
# 僅使用一個模型進行文字對話
model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat()

# 對話歷史儲存
start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
history_filename = f"chat_history_{start_time}.txt"

# Gemini 主對話邏輯 (僅處理純文字輸入)
def chat_with_gemini(user_input):
    prompt = user_input
    response = chat.send_message(prompt)
    return response.text

# 主互動介面
if __name__ == "__main__":
    print("Gemini Chat CLI 已啟動(輸入 'exit' 或 'quit' 離開)")
    print(f"新聞模式指令: news 您的問題 (將自動讀取 {CSV_FILE} 資料)")

    while True:
        user_input = input("您: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print(f"對話已儲存為: {history_filename}")
            break

        # 新增的 CSV 判斷邏輯
        if user_input.lower().startswith("news "):
            user_prompt = user_input[4:].strip() # 擷取實際問題
            
            try:
                # 1. 讀取 CSV 檔案
                df = pd.read_csv(CSV_FILE)
                
                # 2. 格式化資料為純文字上下文
                # 為了節省 Token，我們只選取幾個重要欄位並轉換成字串
                df_context = df[['Ticker', 'Title', 'Score', 'Label']]# .head(50) # 限制行數以避免 Token 超限
                
                # 將 DataFrame 轉換為 Markdown Table 或簡單的文字格式
                context_data = df_context.to_string(index=False)
                
                # 3. 組合 Prompt
                combined_prompt = (
                    f"請參考以下提供的股票市場情感資料 (Stock Sentiment Data) 回答。資料中的欄位分別為 Ticker, Title, Score, Label\n\n"
                    f"資料開始\n"
                    f"{context_data}\n"
                    f"資料結束\n"
                    f"問題: {user_prompt}"
                )
                # print(f"檢測到 'news' 指令，已讀取 {len(df)} 筆資料（限制前 50 筆）作為上下文。")

            except FileNotFoundError:
                reply = f"錯誤: 找不到新聞資料檔案 {CSV_FILE}，請確認檔案路徑"
                combined_prompt = None
            except Exception as e:
                reply = f"讀取資料檔案時發生錯誤: {str(e)}"
                combined_prompt = None
            
            if combined_prompt:
                reply = chat_with_gemini(combined_prompt)

        else:
            # 正常文字對話
            reply = chat_with_gemini(user_input)

        print("Gemini: ", reply)

        try:
            with open(history_filename, "a", encoding="utf-8") as f:
                f.write(f"你: {user_input}\n\nGemini: {reply}\n\n")
        except Exception as e:
            print(f"無法儲存對話紀錄: {str(e)}")

