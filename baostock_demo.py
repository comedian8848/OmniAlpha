import baostock as bs
import pandas as pd

def fetch_baostock_data(code="sh.600000", start_date="2024-01-01", end_date="2024-12-31"):
    # 1. 登录系统
    lg = bs.login()
    # 显示登录返回信息
    print(f"Login respond error_code: {lg.error_code}")
    print(f"Login respond  error_msg: {lg.error_msg}")

    # 2. 获取历史K线数据
    # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
    # 周月线指标：date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg
    rs = bs.query_history_k_data_plus(code,
        "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
        start_date=start_date, end_date=end_date,
        frequency="d", adjustflag="3") # frequency="d"取日k线，adjustflag="3"默认不复权

    print(f"query_history_k_data_plus respond error_code: {rs.error_code}")
    print(f"query_history_k_data_plus respond  error_msg: {rs.error_msg}")

    # 3. 打印结果集
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())
    
    result = pd.DataFrame(data_list, columns=rs.fields)

    # 4. 登出系统
    bs.logout()

    return result

if __name__ == "__main__":
    # 获取浦发银行(sh.600000)的数据
    df = fetch_baostock_data()
    
    # 打印前5行
    print("\nData Preview:")
    print(df.head())
    
    # 保存为CSV (可选)
    # df.to_csv("baostock_data.csv", index=False)
