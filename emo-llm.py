import os
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import time # 引入 time 模組用於 backoff

# 參數設定區
API_KEY_FILE = "api-key.txt"
# CSV_FILE[0] 情感資料, CSV_FILE[1] 股票資料
CSV_FILE = ("sentiment-data.csv", "stock.csv") 

# 初始化 API Key 與 Gemini 模型
if not os.path.exists(API_KEY_FILE):
    raise FileNotFoundError(f"找不到 API 金鑰檔案: {API_KEY_FILE}，請創建此檔案並放入您的 API Key")

with open(API_KEY_FILE, "r", encoding="utf-8") as f:
    api_key = f.read().strip()

genai.configure(api_key=api_key)
# 僅使用一個模型進行文字對話
model_name = "gemini-2.0-flash"
model = genai.GenerativeModel(model_name)
chat = model.start_chat()

# 對話歷史儲存
start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
history_filename = f"chat_history_{start_time}.txt"

# 函數：處理與 Gemini 的對話，帶有重試機制 (Exponential Backoff)
def chat_with_gemini(user_input, max_retries=5):
    """將文字輸入發送給 Gemini API，並處理潛在的 API 錯誤與重試。"""
    prompt = user_input
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            # 這是使用 genai.client.chats 提供的 send_message，它自動處理 request
            response = chat.send_message(prompt)
            return response.text
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"API 錯誤 (嘗試 {attempt + 1}/{max_retries})，等待 {retry_delay} 秒後重試: {e}")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指數退避
            else:
                return f"錯誤: 與 Gemini API 通訊失敗，請檢查您的網路連線或 API Key。詳細錯誤: {e}"
    return "與 Gemini API 通訊失敗" # 應該不會執行到這行

# 主互動介面
if __name__ == "__main__":
    print("Gemini Chat CLI 已啟動(輸入 'exit' 或 'quit' 離開)")
    print(f"新聞模式指令: news 日期 您的問題 (將自動讀取 {CSV_FILE[0]} 和 {CSV_FILE[1]} 資料)")

    while True:
        user_input = input("您: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print(f"對話已儲存為: {history_filename}")
            break

        # 新增的 CSV 判斷邏輯
        if user_input.lower().startswith("news "):
            try:
                # 擷取日期 (itime) 和實際問題 (user_prompt)
                parts = user_input[5:].strip().split(" ", 1)
                if len(parts) < 2:
                    reply = "錯誤: 請輸入完整的指令格式: news 日期 您的問題"
                    combined_prompt = None
                    print("Gemini: ", reply)
                    continue

                itime, user_prompt = parts
                
                # --- 1. 處理 Sentiment Data (情感資料) ---
                df_sentiment = pd.read_csv(CSV_FILE[0])
                
                # 目標日期轉換：YYYY-MM-DD (例如 2024-11-25) -> YYYYMMDD (例如 20241125)
                # 這是為了與 sentiment-data.csv 中的 Time 欄位 (YYYYmmddTHHmmss) 的前 8 碼進行比對
                target_date_sentiment = itime.replace('-', '')
                
                # 過濾 Sentiment Data by Date (Time 欄位格式為 YYYYmmddTHHmmss)
                # 提取 Time 欄位的前 8 碼作為日期
                df_sentiment['Date_Only'] = df_sentiment['Time'].astype(str).str[:8]
                df_sentiment_filtered = df_sentiment[df_sentiment['Date_Only'] == target_date_sentiment]

                # 選取重要欄位
                if not df_sentiment_filtered.empty:
                    df_sentiment_context = df_sentiment_filtered[['Security', 'Title', 'Score', 'Label']]
                    sentiment_data = df_sentiment_context.to_string(index=False)
                    # print(f"已成功讀取並過濾 {len(df_sentiment_filtered)} 筆 {itime} 的市場情感資料。")
                else:
                    sentiment_data = "沒有資料"# f"警告: 在 {itime} 找不到任何市場情感資料 (請確認 Time 欄位格式是否為 YYYYmmddTHHmmss)。"
                    # print(f"警告: 在 {itime} 找不到任何市場情感資料。")

                # --- 2. 處理 Stock Data (股票收盤價資料) ---
                df_stock = pd.read_csv(CSV_FILE[1])

                # 過濾 Stock Data by Date (Date 欄位格式為 YYYY-MM-DD)
                df_stock['Date'] = df_stock['Date'].astype(str)
                df_stock_filtered = df_stock[df_stock['Date'] == itime]
                
                # 格式化 Filtered Stock Data
                if not df_stock_filtered.empty:
                    # 選取需要的欄位：股票代號, 公司名稱, 日期, 收盤價
                    df_stock_context = df_stock_filtered[['Ticker', 'Company Name', 'Date', 'Close']]
                    stock_data = df_stock_context.to_string(index=False)
                    # print(f"已成功讀取 {len(df_stock_filtered)} 筆 {itime} 的股票收盤價資料。")
                else:
                    stock_data = "沒有資料"# f"警告: 在 {itime} 找不到任何股票收盤價資料 (請確認 Date 欄位格式是否為 YYYY-MM-DD)。"
                    # print(f"警告: 在 {itime} 找不到任何股票收盤價資料。")


                # --- 3. 組合 Prompt ---
                combined_prompt = (
                    f"請參考以下提供的市場情感資料 (Stock Sentiment Data) 和指定日期的股票收盤價資料 (Stock Closing Price Data) 來回答問題\n"
                    f"市場情感資料已過濾為指定日期: {itime}\n"
                    
                    f"市場情感資料 (Sentiment Data) - 欄位: Security, Title, Score, Label\n"
                    f"{sentiment_data}\n"
                    
                    f"指定日期 ({itime}) 的股票收盤價資料 (Stock Price Data) - 欄位: Ticker, Company Name, Date, Close\n"
                    f"{stock_data}\n"
                    
                    f"問題: {user_prompt}"
                )
                
            except FileNotFoundError as e:
                # 處理找不到任一檔案的錯誤
                reply = f"錯誤: 找不到資料檔案 {str(e).split(': ')[-1]}，請確認檔案路徑和名稱是否正確: {CSV_FILE[0]} 或 {CSV_FILE[1]}。"
                combined_prompt = None
            except Exception as e:
                # 處理其他資料讀取或處理錯誤
                reply = f"讀取或處理資料檔案時發生錯誤: {type(e).__name__}: {str(e)}"
                combined_prompt = None
            
            if combined_prompt:
                reply = chat_with_gemini(combined_prompt)

        else:
            # 正常文字對話
            reply = chat_with_gemini(user_input)

        print("Gemini: ", reply)

        try:
            # 儲存對話紀錄
            with open(history_filename, "a", encoding="utf-8") as f:
                f.write(f"你: {user_input}\n\nGemini: {reply}\n\n")
        except Exception as e:
            print(f"無法儲存對話紀錄: {str(e)}")

