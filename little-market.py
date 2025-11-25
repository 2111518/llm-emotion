import pandas as pd
import requests
import time
import os

# 設定區
INPUT_FILE = "Dow-Jones-Industrial-Average.csv"
OUTPUT_FILE = "sentiment-data"
API_KEY_FILE = "alpha-api.txt"
local = time.strftime("%Y%m%d-%H%M", time.localtime(time.time()))
out_file = OUTPUT_FILE + local +".csv"

# 讀取 API Key
try:
    with open(API_KEY_FILE, 'r') as f:
        api_key = f.read().strip()
except FileNotFoundError:
    print(f"錯誤: 找不到 API Key 檔案 {API_KEY_FILE}")
    exit()

# 讀取股票代碼及公司名稱
try:
    df = pd.read_csv(INPUT_FILE)
    ticker_to_security = pd.Series(df['Security'].values, index=df['Symbol']).to_dict()
    tickers = df['Symbol'].tolist()
except FileNotFoundError:
    print(f"錯誤: 找不到輸入檔案 {INPUT_FILE}")
    exit()
except KeyError as e:
    print(f"錯誤: CSV 檔案缺少必要的欄位 {e}，請檢查 {INPUT_FILE} 檔案")
    exit()


# 使用者輸入日期
print("請輸入日期 (格式: YYYY-MM-DD)")
start_input = input("開始日期: ").strip()
end_input = input("結束日期: ").strip()

# 轉換成 API 需要的格式 (20230101T0000)
time_from = start_input.replace("-", "") + "T0000"
time_to = end_input.replace("-", "") + "T2359"

print(f"抓取 {len(tickers)} 檔股票的新聞情緒")

# 開始抓取迴圈
for ticker in tickers:
    # 取得 Security 名稱
    security_name = ticker_to_security.get(ticker, "N/A")

    # 檢查是否已經抓過 (斷點續傳)
    """if os.path.exists(OUTPUT_FILE):
        saved_df = pd.read_csv(OUTPUT_FILE)
        if 'Ticker' in saved_df.columns and ticker in saved_df['Ticker'].values:
            print(f"跳過 {ticker} (已存在)")
            continue"""

    # print(f"抓取 {ticker} ({security_name})", end = " ")

    # 發送請求
    url = "https://www.alphavantage.co/query"
    mparams = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "time_from": time_from,
        "time_to": time_to,
        "limit": 50,
        "apikey": api_key
    }

    try:
        response = requests.get(url, params = mparams, timeout = 3)
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"網絡錯誤: {e}")
        continue
    except Exception as e:
        print(f"處理 JSON 時發生錯誤: {e}")
        continue

    # 檢查 API 限制
    if "Note" in data:
        print("[停止] 已達 API 限制，請稍後重試")
        break
    
    # 處理數據並存檔
    feed = data.get('feed', [])
    news_list = []
    
    if feed:
        for item in feed:
            news_list.append({
                'Ticker': ticker,
                'Security': security_name,
                'Title': item.get('title'),
                'Time': item.get('time_published'),
                'Score': item.get('overall_sentiment_score'),
                'Label': item.get('overall_sentiment_label'),
                'URL': item.get('url')
            })
        # print(f"取得 {len(news_list)} 則新聞")
    else:
        # print("無相關新聞")
        # 即使沒新聞也要記錄一筆空的，避免下次重複抓取
        news_list.append({'Ticker': ticker, 'Security': security_name, 'Title': 'NO_DATA'})

    # 寫入 CSV (如果檔案不存在就寫入標頭，存在就附加)
    save_df = pd.DataFrame(news_list)
    header = not os.path.exists(out_file)
    try:
        save_df.to_csv(out_file, mode='a', header = header, index = False, encoding='utf-8')
    except Exception as e:
        print(f"寫入 CSV 檔案時發生錯誤: {e}")
        
    # 遵守每分鐘 5 次的限制
    time.sleep(12)

print("finish")

