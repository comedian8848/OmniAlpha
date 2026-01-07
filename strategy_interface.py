from abc import ABC, abstractmethod
import pandas as pd

class StockStrategy(ABC):
    """
    所有选股策略的基类。
    """
    
    @property
    @abstractmethod
    def name(self):
        """策略名称"""
        pass

    @property
    @abstractmethod
    def description(self):
        """策略描述"""
        pass

    @abstractmethod
    def check(self, code, data_df):
        """
        检查单只股票是否符合策略。
        :param code: 股票代码
        :param data_df: 该股票的历史K线数据 (DataFrame), 包含 date, close, volume 等
        :return: (bool, dict) -> (是否选中, 选股详情/原因)
        """
        pass
    
    def prepare_data(self, code, bs, end_date):
        """
        为策略准备数据。默认实现是获取最近60天的日线。
        子类可以重写此方法以获取特定数据（如分钟线、季报）。
        """
        import datetime
        start_date = (datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        
        rs = bs.query_history_k_data_plus(code,
            "date,code,open,high,low,close,volume,amount,pctChg,peTTM,pbMRQ,turn,isST",
            start_date=start_date, end_date=end_date,
            frequency="d", adjustflag="3")
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
            
        if not data_list:
            return None

        df = pd.DataFrame(data_list, columns=rs.fields)
        # 类型转换
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pctChg', 'peTTM', 'pbMRQ', 'turn']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        return df
