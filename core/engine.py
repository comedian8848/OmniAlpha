from core.data_provider import data_provider

class AnalysisEngine:
    def __init__(self, strategies):
        self.strategies = strategies

    def scan_one(self, code, date):
        """Scan a single stock with all strategies."""
        # Fetch data once per stock
        df = data_provider.get_daily_bars(code, date)
        
        if df is None or df.empty:
            return None
            
        for strategy in self.strategies:
            is_match, details = strategy.check(code, df)
            
            if is_match:
                res = {
                    'code': code,
                    'strategy': strategy.name,
                    'date': date
                }
                res.update(details)
                return res
        return None

    def run(self, stock_pool, date, progress_callback=None):
        results = []
        total = len(stock_pool)
        
        print(f"Engine started. Scanning {total} stocks with {len(self.strategies)} strategies...")
        
        for i, code in enumerate(stock_pool):
            if i % 10 == 0:
                print(f"Progress: {i}/{total} ({round(i/total*100, 1)}%)", end="\r")
            
            if progress_callback:
                progress_callback(i / total)
            
            # Fetch data once per stock
            # Using a default lookback of 60 days, sufficient for most daily strategies
            df = data_provider.get_daily_bars(code, date)
            
            if df is None or df.empty:
                continue
                
            for strategy in self.strategies:
                is_match, details = strategy.check(code, df)
                
                if is_match:
                    res = {
                        'code': code,
                        'strategy': strategy.name,
                        'date': date
                    }
                    res.update(details)
                    results.append(res)
                    
        print(f"Progress: {total}/{total} (100%)")
        return results
