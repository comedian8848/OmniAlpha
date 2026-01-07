from strategy_interface import StockStrategy
import pandas as pd

class MovingAverageStrategy(StockStrategy):
    @property
    def name(self):
        return "MA_Trend"

    @property
    def description(self):
        return "均线趋势策略: 收盘价 > MA20 且 MA5 > MA20"

    def check(self, code, df):
        if df is None or len(df) < 20:
            return False, {}
            
        # 计算均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        
        last_row = df.iloc[-1]
        
        condition_1 = last_row['close'] > last_row['MA20']
        condition_2 = last_row['MA5'] > last_row['MA20']
        
        if condition_1 and condition_2:
            return True, {
                'price': last_row['close'],
                'MA5': round(last_row['MA5'], 2),
                'MA20': round(last_row['MA20'], 2)
            }
        return False, {}

class VolumeRiseStrategy(StockStrategy):
    @property
    def name(self):
        return "Volume_Breakout"

    @property
    def description(self):
        return "放量上涨: 涨幅>2% 且 成交量 > 5日均量 * 1.5"

    def check(self, code, df):
        if df is None or len(df) < 6:
            return False, {}
            
        # 计算5日均量 (不包含当天，或者包含当天均可，这里取包含当天的移动平均比较方便)
        # 为了严谨，通常比较 当天量 vs 过去5天均量。
        # 这里简单处理：MA_VOL5
        df['MA_VOL5'] = df['volume'].rolling(window=5).mean()
        
        last_row = df.iloc[-1]
        
        # 涨幅 > 2% (注意 baostock 的 pctChg 是百分比字符串还是数字，我们在 interface 里转成了 numeric)
        # baostock pctChg data is like '2.5' meaning 2.5%
        is_up = last_row['pctChg'] > 2.0
        
        # 量比
        is_volume_up = last_row['volume'] > (last_row['MA_VOL5'] * 1.5)
        
        if is_up and is_volume_up:
            return True, {
                'price': last_row['close'],
                'pctChg': last_row['pctChg'],
                'vol_ratio': round(last_row['volume'] / last_row['MA_VOL5'], 2)
            }
        return False, {}

class LowPeStrategy(StockStrategy):
    @property
    def name(self):
        return "Value_LowPE"
        
    @property
    def description(self):
        return "低估值策略: 0 < PE_TTM < 30"
        
    def check(self, code, df):
        if df is None or len(df) < 1:
            return False, {}
            
        last_row = df.iloc[-1]
        
        # 确保字段存在
        if 'peTTM' not in last_row:
            return False, {}
            
        pe = last_row['peTTM']
        
        # 排除亏损股(pe<0)和高估值股
        if 0 < pe < 30:
            return True, {
                'price': last_row['close'],
                'peTTM': round(pe, 2),
                'pbMRQ': round(last_row.get('pbMRQ', 0), 2)
            }
        return False, {}

class HighTurnoverStrategy(StockStrategy):
    @property
    def name(self):
        return "High_Turnover"
        
    @property
    def description(self):
        return "资金活跃: 换手率 > 5% 且非 ST"
        
    def check(self, code, df):
        if df is None or len(df) < 1:
            return False, {}
            
        last_row = df.iloc[-1]
        turn = last_row.get('turn', 0)
        is_st = last_row.get('isST', '0') # '1' is ST, '0' is Normal
        
        # 排除ST股，且换手率 > 5%
        if turn > 5 and str(is_st) != '1':
            return True, {
                'price': last_row['close'],
                'turn': round(turn, 2),
                'pctChg': round(last_row.get('pctChg', 0), 2)
            }
        return False, {}
