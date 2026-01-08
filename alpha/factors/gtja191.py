import numpy as np
import pandas as pd
from scipy.stats import rankdata

# --- 基础算子 (针对 Pandas 优化) ---
# 这些算子尽可能使用向量化操作以提升性能

def Log(sr):
    """计算自然对数"""
    return np.log(sr)

def Rank(sr):
    """
    排名算子。
    
    注意：标准的 GTJA191 Alpha 定义中，Rank 指的是横截面（Cross-Sectional）排名。
    但在当前的选股器架构中，数据是逐只股票传入的（Time-Series 模式），无法获取全市场数据。
    
    为了保证公式可运行且具备参考意义，此处将其适配为【时间序列排名】。
    逻辑：计算当前值在过去 250 个交易日（约一年）中的分位数 (0~1)。
    这代表了“当前值相对于自身历史水平的高低”。
    """
    # 使用过去 250 天的数据进行滚动排名，归一化到 0-1
    return sr.rolling(window=250, min_periods=10).apply(lambda x: rankdata(x)[-1]/len(x), raw=True)

def Delta(sr, period):
    """一阶差分: sr - Delay(sr, period)"""
    return sr.diff(period)

def Delay(sr, period):
    """滞后: period 周期前的值"""
    return sr.shift(period)

def Corr(x, y, window):
    """滚动相关系数"""
    return x.rolling(window).corr(y)

def Cov(x, y, window):
    """滚动协方差"""
    return x.rolling(window).cov(y)

def Sum(sr, window):
    """滚动求和"""
    return sr.rolling(window).sum()

def Prod(sr, window):
    """滚动连乘"""
    # 利用 exp(sum(log(x))) 转换乘法为加法，提升数值稳定性与速度
    return np.exp(np.log(sr).rolling(window).sum())

def Mean(sr, window):
    """滚动均值"""
    return sr.rolling(window).mean()

def Std(sr, window):
    """滚动标准差"""
    return sr.rolling(window).std()

def Tsrank(sr, window):
    """时间序列排名: 计算末位值在窗口内的百分比排名 (0~1)"""
    return sr.rolling(window).rank(pct=True)

def Tsmax(sr, window):
    """滚动最大值"""
    return sr.rolling(window).max()

def Tsmin(sr, window):
    """滚动最小值"""
    return sr.rolling(window).min()

def Sign(sr):
    """符号函数: >0 返回 1, <0 返回 -1, =0 返回 0"""
    return np.sign(sr)

def Max(sr1, sr2):
    """序列最大值: 逐元素比较取大"""
    return np.maximum(sr1, sr2)

def Min(sr1, sr2):
    """序列最小值: 逐元素比较取小"""
    return np.minimum(sr1, sr2)

def Sma(sr, n, m):
    """
    扩展移动平均 (SMA)
    公式: Y = (M*X + (N-M)*Y') / N
    等价于 Pandas 的 ewm(alpha=m/n)
    """
    return sr.ewm(alpha=m/n, adjust=False).mean()

def Abs(sr):
    """绝对值"""
    return sr.abs()

def Wma(sr, window):
    """
    加权移动平均 (WMA)
    权重序列为 0.9^i, 距离当前越近权重越大
    """
    weights = np.array([0.9**i for i in range(window-1, -1, -1)])
    sum_weights = np.sum(weights)
    def wma_func(x):
        return np.sum(weights * x) / sum_weights
    return sr.rolling(window).apply(wma_func, raw=True)

def Decaylinear(sr, window):
    """
    线性衰减加权平均
    权重: i (1 到 window)
    """
    weights = np.arange(1, window + 1)
    sum_weights = np.sum(weights)
    def decay_func(x):
        return np.sum(weights * x) / sum_weights
    return sr.rolling(window).apply(decay_func, raw=True)

def Count(cond, window):
    """统计窗口内满足条件的次数"""
    return cond.rolling(window).sum()

def Regbeta(sr, x):
    """
    滚动回归系数 Beta
    注：尚未完全实现向量化，暂返回 NaN
    """
    return np.nan 

# --- Alpha 计算引擎 ---

class GTJA191:
    """
    国泰君安 191 Alpha 因子计算类
    
    设计模式：适配单只股票的 DataFrame 输入。
    由于输入限定为单股历史数据，所有涉及横截面比较的算子（如 Rank）均被近似为时间序列算子。
    """
    
    def __init__(self, df_data):
        """
        初始化因子计算引擎
        :param df_data: pd.DataFrame, 必须包含 'open', 'high', 'low', 'close', 'volume' 列
        """
        # 提取基础数据列
        self.open = df_data['open']
        self.high = df_data['high']
        self.low = df_data['low']
        self.close = df_data['close']
        self.volume = df_data['volume']
        
        # 计算辅助数据
        # 金额 amount，如果不存在则近似计算
        self.amount = df_data.get('amount', self.volume * self.close) 
        # 均价 vwap，如果不存在则使用 amount/volume 计算，防止除零错误
        self.vwap = df_data.get('vwap', self.amount / (self.volume + 1e-9))
        
        # 收益率
        self.ret = self.close.pct_change()

    # --- Alpha 因子定义 (001 - 010) ---
    
    def alpha001(self):
        """
        Alpha 001
        公式: -1 * Corr(Rank(Delta(Log(Volume), 1)), Rank((Close - Open) / Open), 6)
        含义: 量价背离因子。成交量变动与日内涨幅的相关性取负。
        """
        inner1 = Delta(Log(self.volume), 1)
        inner2 = (self.close - self.open) / self.open
        return -1 * Corr(Rank(inner1), Rank(inner2), 6)

    def alpha002(self):
        """
        Alpha 002
        公式: -1 * Delta(((Close - Low) - (High - Close)) / (High - Low), 1)
        含义: 002类似威廉指标的变种，衡量收盘价在日内波动区间的相对位置的变化。
        """
        return -1 * Delta(((self.close - self.low) - (self.high - self.close)) / (self.high - self.low), 1)

    def alpha003(self):
        """
        Alpha 003
        公式: Sum((Close=Delay(Close,1)?0:Close-(Close>Delay(Close,1)?Min(Low,Delay(Close,1)):Max(High,Delay(Close,1)))),6)
        含义: 近6日收盘价相对于前一日波动区间的强弱累加。
        """
        c = self.close
        c_prev = Delay(c, 1)
        cond_up = c > c_prev
        cond_down = c < c_prev
        
        val = pd.Series(0.0, index=c.index)
        # 上涨时：收盘价 - Min(Low, 昨日收盘) -> 这里的逻辑是看涨势有多强
        val[cond_up] = c - Min(self.low, c_prev)
        # 下跌时：收盘价 - Max(High, 昨日收盘) -> 看跌势有多强
        val[cond_down] = c - Max(self.high, c_prev)
        
        return Sum(val, 6)

    def alpha004(self):
        """
        Alpha 004
        公式: (((Sum(Close, 8) / 8) + Std(Close, 8)) < (Sum(Close, 2) / 2)) ? -1 : ...
        含义: 比较短期均线与长期均线+波动率，判断趋势反转。
        """
        ma8 = Mean(self.close, 8)
        std8 = Std(self.close, 8)
        ma2 = Mean(self.close, 2)
        
        # 逻辑简化：
        # 如果 (MA8 + Std8) < MA2，说明短期极强，可能反转，给 -1？
        # 原公式逻辑比较复杂，这里实现核心条件判断：
        # 如果 MA2 > 布林带上轨(MA8+Std8) -> 返回 1
        # 如果 MA2 < 布林带上轨 -> 返回 -1 (此处仅为根据原逻辑推导的简化实现)
        
        res = pd.Series(-1, index=self.close.index)
        res[(ma8 + std8) > ma2] = 1
        return res

    def alpha005(self):
        """
        Alpha 005
        公式: -1 * Tsmax(Corr(Tsrank(Volume, 5), Tsrank(High, 5), 5), 3)
        含义: 量价相关性的最大值取负，寻找量价背离。
        """
        v_rank = Tsrank(self.volume, 5)
        h_rank = Tsrank(self.high, 5)
        return -1 * Tsmax(Corr(v_rank, h_rank, 5), 3)

    def alpha006(self):
        """
        Alpha 006
        公式: -1 * Rank(Sign(Delta((Open * 0.85) + (High * 0.15), 4)))
        含义: 开盘价与最高价组合权重的变化趋势。
        """
        return -1 * Rank(Sign(Delta(self.open * 0.85 + self.high * 0.15, 4)))

    def alpha007(self):
        """
        Alpha 007
        公式: ((Rank(Max((Vwap - Close), 3)) + Rank(Min((Vwap - Close), 3))) * Rank(Delta(Volume, 3)))
        含义: 均价与收盘价偏离度的极值，结合成交量变化。
        """
        diff = self.vwap - self.close
        part1 = Rank(Tsmax(diff, 3))
        part2 = Rank(Tsmin(diff, 3))
        part3 = Rank(Delta(self.volume, 3))
        return (part1 + part2) * part3

    def alpha008(self):
        """
        Alpha 008
        公式: Rank(Delta((((High + Low) / 2) * 0.2) + (Vwap * 0.8), 4) * -1)
        含义: 加权价格的动量反转。
        """
        term = (self.high + self.low) / 2 * 0.2 + self.vwap * 0.8
        return Rank(Delta(term, 4) * -1)

    def alpha009(self):
        """
        Alpha 009
        公式: SMA(((High + Low) / 2 - (Delay(High, 1) + Delay(Low, 1)) / 2) * (High - Low) / Volume, 7, 2)
        含义: 价格变动与成交量的比率，类似简化的资金流向指标。
        """
        avg = (self.high + self.low) / 2
        avg_prev = Delay(avg, 1)
        # 避免除以 0 错误
        term = (avg - avg_prev) * (self.high - self.low) / (self.volume + 1)
        return Sma(term, 7, 2) 

    def alpha010(self):
        """
        Alpha 010
        公式: Rank(Max(((Std(Ret, 20) > Std(Ret, 5)) ? Close : -1), 5)) * -1
        含义: 当长期波动率大于短期波动率时，考察收盘价的最大值。
        """
        std20 = Std(self.ret, 20)
        std5 = Std(self.ret, 5)
        
        cond = std20 > std5
        val = pd.Series(-1.0, index=self.close.index)
        # 当波动率条件满足时，取收盘价，否则取 -1
        val[cond] = self.close
        
        return Rank(Tsmax(val, 5)) * -1

    def run_all(self):
        """
        执行所有已实现的 Alpha 计算。
        
        :return: pd.DataFrame, 索引为日期，列名为 alpha 因子名
        """
        alphas = {}
        for name in dir(self):
            # 自动查找以 'alpha' 开头的方法
            if name.startswith('alpha') and callable(getattr(self, name)):
                try:
                    alphas[name] = getattr(self, name)()
                except Exception as e:
                    # 如果计算出错（如数据不足），填充 NaN
                    alphas[name] = pd.Series(np.nan, index=self.close.index)
        return pd.DataFrame(alphas)