import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

def get_tickers_info_from_file(filepath: Path) -> list[tuple[str, str]]:
    """
    從 CSV 檔案讀取股票代碼和公司名稱資訊。CSV 檔案必須包含 'Symbol' 和 'Security' 欄位。
    """
    if not filepath.exists():
        print(f"X 檔案 '{filepath}' 找不到，請確認檔案是否存在。")
        return []

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"X 讀取 CSV 檔案時發生錯誤: {e}")
        return []

    # 移除 'GICS Sector' 的檢查
    required_columns = {"Symbol", "Security"}
    if not required_columns.issubset(df.columns):
        print(f"X 檔案缺少必要欄位: {required_columns - set(df.columns)}")
        return []

    tickers_info = []
    for _, row in df.iterrows():
        ticker = str(row["Symbol"]).strip().upper().replace(".", "-")
        name = str(row["Security"]).strip()
        # 移除 GICS Sector 的讀取
        tickers_info.append((ticker, name))

    # 排序邏輯只剩下 Symbol
    return sorted(tickers_info, key=lambda x: x[0])

def fetch_prices_by_range(tickers_info: list[tuple[str, str]], start_date: str, end_date: str) -> pd.DataFrame:
    """
    根據股票代碼列表和日期區間，從 yfinance 取得收盤價資料。
    """
    try:
        start_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_obj = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print("X 日期格式錯誤，請使用 YYYY-MM-DD")
        return pd.DataFrame()

    tickers = [t[0] for t in tickers_info]
    # info_lookup 只儲存 (name)
    info_lookup = {t[0]: t[1] for t in tickers_info}  # ticker -> name
    stocks = yf.Tickers(" ".join(tickers))

    all_results = []

    for ticker in tickers:
        try:
            stock = stocks.tickers[ticker]
            hist = stock.history(start=start_date, end=end_date)
            if not hist.empty:
                name = info_lookup.get(ticker, ticker) # 預設為 ticker
                # 移除 gics 變數
                for date, row in hist.iterrows():
                    all_results.append([
                        ticker,
                        name,
                        date.strftime("%Y-%m-%d"),
                        row["Close"]
                    ])
            else:
                print(f"! {ticker} 在區間 {start_date} 到 {end_date} 沒有資料")
        except Exception as e:
            print(f"X 取得 {ticker} 的資料時發生錯誤: {e}")

    # DataFrame 欄位移除 GICS
    df = pd.DataFrame(all_results, columns=["Ticker", "Company Name", "Date", "Close"])
    # 排序邏輯移除 GICS
    return df.sort_values(by=["Ticker", "Date"])

def main():
    filepath = Path("Dow-Jones-Industrial-Average.csv")
    # 函數回傳值的型別已改變
    tickers_info = get_tickers_info_from_file(filepath)
    filename_str = str(filepath).split(".")[0]
    filename = ""
    for i in range(len(filename_str)):
        if i == 0 or filename_str[i].isupper() or filename_str[i - 1] == "-":
            filename = filename + filename_str[i]

    if not tickers_info:
        return

    start_date = input("請輸入起始日期 (YYYY-MM-DD): ").strip()
    end_date = input("請輸入結束日期 (YYYY-MM-DD): ").strip()

    # 函數呼叫保持不變
    df = fetch_prices_by_range(tickers_info, start_date, end_date)

    if not df.empty:
        output_file = f"{filename}_{start_date}_{end_date}.csv"
        df.to_csv(output_file, index=False)
        print(f"-> 資料已儲存到 {output_file}")

if __name__ == "__main__":
    main()

