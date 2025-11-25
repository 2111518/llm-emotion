import pandas as pd
import requests as req
from io import StringIO
from pathlib import Path
import json

def check_file_exists(file_name: str | None) -> bool:
    if not file_name:
        return False

    file_path = Path(file_name)
    return file_path.is_file()

def read_link() -> tuple:
    lrf = []
    with open("link.txt", "r", encoding="utf-8") as file:
        for line in file:
            # 使用列表推導式一次性處理切割和移除空白
            parts = [part.strip().strip("\"") for part in line.strip().split(",")]
            lrf.append(parts)
    lrf = [item for sublist in lrf for item in sublist]
    return tuple(lrf)

def read_json_data(headf: str) -> dict:
    fin = "user"
    retn = {}
    with open(headf, "r", encoding="utf-8") as file:
        data = json.load(file)

    for i in data["headers"]:
        if fin in i.lower():
            retn[i] = data["headers"][i]

    return retn

def file_diff(file: tuple, dfl: list, suc: list) -> list:
    update = []

    for i in range(len(file)):
        if check_file_exists(file[i]):
            df_or = pd.read_csv(file[i])
            if suc[i]:
                if df_or.equals(dfl[i]):
                    update.append(False)
                else:
                    update.append(True)
            else:
                update.append(False)
        else:
            update.append(True)

    return update

def main():
    lfile = "link.txt"
    if check_file_exists(lfile):
        link = read_link()
    else:
        print(f"{lfile} does not exists")
        return

    file = ("sp-400.csv", "sp-500.csv", "sp-600.csv", "Dow-Jones-Industrial-Average.csv", "Nasdaq-100.csv")
    table_n = (0, 1, 0, 2, 4)

    headf = "headers145.json"
    if check_file_exists(headf):
        mheaders = read_json_data(headf)
    else:
        print(f"{headf} does not exists")
        return

    suc = []
    dfl = [] # new csv data list
    # 下載新的資料
    for i in range(len(link)):
        tn = table_n[i]
        res = req.get(link[i], headers = mheaders, timeout = 3)
        if res.status_code == 200:
            res.encoding = "utf-8"
            df = pd.read_html(StringIO(res.text), header = 0)[tn]
            df.columns = df.columns.str.replace(r"\[\d+\]", "", regex = True)
            df = df.replace(r"\[\d+\]", "", regex = True)
            dfl.append(df)
            suc.append(True)
        else:
            print(f"{i}, http status: {res.status_code}")
            dfl.append(None) # Add a placeholder for failed downloads
            suc.append(False)

    # 修改csv標頭
    colu = {"Company": "Security", "Ticker": "Symbol"}
    for j in range(len(link)):
        if suc[j]:
            dfl[j] = dfl[j].rename(columns = colu)

    update = file_diff(file, dfl, suc)
    for m in range(len(file)):
        if update[m]:
            dfl[m].to_csv(file[m], index = False)
            
    print("Finish")

if __name__ == "__main__":
    main()

