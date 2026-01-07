import baostock as bs
import pandas as pd
import datetime
import argparse
import sys

# 引入我们定义的模块
from strategy_interface import StockStrategy
from strategies import MovingAverageStrategy, VolumeRiseStrategy, LowPeStrategy, HighTurnoverStrategy

# 注册可用策略
AVAILABLE_STRATEGIES = {
    'ma': MovingAverageStrategy(),
    'vol': VolumeRiseStrategy(),
    'pe': LowPeStrategy(),
    'turn': HighTurnoverStrategy()
}

def get_latest_trading_date():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    start_lookback = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    rs = bs.query_trade_dates(start_date=start_lookback, end_date=today)
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    if not data_list: return today
    df = pd.DataFrame(data_list, columns=rs.fields)
    trading_days = df[df['is_trading_day'] == '1']['calendar_date'].tolist()
    return trading_days[-1] if trading_days else today

def get_stock_pool(date, limit=None):
    print(f"正在获取 {date} 的沪深300成分股...")
    rs = bs.query_hs300_stocks(date=date)
    hs300_stocks = []
    while (rs.error_code == '0') & rs.next():
        hs300_stocks.append(rs.get_row_data()[1])
    
    if limit:
        return hs300_stocks[:limit]
    return hs300_stocks

def run_analysis(strategy_keys, date, quick_mode=False):
    # 1. 登录
    bs.login()
    
    # 2. 准备策略实例
    active_strategies = [AVAILABLE_STRATEGIES[k] for k in strategy_keys]
    print(f"已启用策略: {', '.join([s.name for s in active_strategies])}")
    
    # 3. 获取股票池
    # quick_mode 用于测试，只跑前20只
    limit = 20 if quick_mode else None
    stock_pool = get_stock_pool(date, limit)
    
    if not stock_pool:
        print("股票池为空，退出。")
        bs.logout()
        return

    results = []
    
    print(f"开始扫描 {len(stock_pool)} 只股票...")
    
    for i, code in enumerate(stock_pool):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(stock_pool)}", end="\r")
            
        # 优化：为该股票获取一次数据，传给所有策略（假设策略都需要日线）
        # 如果策略需要不同数据，可以在策略内部自行处理，或者在这里做一个通用的数据上下文
        # 这里我们使用第一个策略的 prepare_data 方法作为通用数据获取器
        # (简单起见，假设所有策略都基于日线)
        data_df = active_strategies[0].prepare_data(code, bs, date)
        
        if data_df is None:
            continue
            
        # 遍历选中的策略
        for strategy in active_strategies:
            is_match, details = strategy.check(code, data_df)
            
            if is_match:
                # 记录结果
                res = {
                    'code': code,
                    'strategy': strategy.name,
                    'date': date
                }
                # 合并策略返回的详细信息
                res.update(details)
                results.append(res)
    
    bs.logout()
    return results

def main():
    parser = argparse.ArgumentParser(description="A股 AI 选股助手 (Baostock版)")
    
    parser.add_argument('--date', type=str, help='指定日期 YYYY-MM-DD，默认自动获取最近交易日')
    parser.add_argument('--strategies', type=str, default='ma',
                        help=f'选择策略，用逗号分隔。可用: {', '.join(AVAILABLE_STRATEGIES.keys())} (例如: ma,vol)')
    parser.add_argument('--quick', action='store_true', help='快速模式 (仅扫描前20只股票用于测试)')
    
    args = parser.parse_args()
    
    # 解析策略
    selected_strategies = args.strategies.split(',')
    valid_strategies = []
    for s in selected_strategies:
        if s in AVAILABLE_STRATEGIES:
            valid_strategies.append(s)
        else:
            print(f"警告: 策略 '{s}' 未知，已跳过。")
            
    if not valid_strategies:
        print("未选择有效策略，默认使用 'ma'")
        valid_strategies = ['ma']
        
    # 确定日期
    target_date = args.date
    if not target_date:
        # 这里需要临时login一下来查日期，或者我们在 run_analysis 里查
        # 为了简单，我们先login一下查日期
        bs.login()
        target_date = get_latest_trading_date()
        bs.logout()
        print(f"自动选择最近交易日: {target_date}")
        
    # 运行
    results = run_analysis(valid_strategies, target_date, args.quick)
    
    # 输出
    print("\n\n====== 最终结果 ======")
    if results:
        df = pd.DataFrame(results)
        # 调整列顺序
        cols = ['date', 'code', 'strategy'] + [c for c in df.columns if c not in ['date', 'code', 'strategy']]
        df = df[cols]
        
        print(df)
        filename = f"selection_{target_date}_{'_'.join(valid_strategies)}.csv"
        df.to_csv(filename, index=False)
        print(f"\n结果已保存至: {filename}")
    else:
        print("没有股票符合所选策略。")

if __name__ == "__main__":
    main()
