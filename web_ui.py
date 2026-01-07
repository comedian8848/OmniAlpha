import streamlit as st
import pandas as pd
import altair as alt
import datetime
import time
from core.data_provider import data_provider
from core.engine import AnalysisEngine
from strategies import get_strategy, get_all_strategy_keys

# Page Config
st.set_page_config(
    page_title="OmniAlpha 选股工作台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- State Initialization ---
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'stock_pool' not in st.session_state:
    st.session_state.stock_pool = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'progress_text' not in st.session_state:
    st.session_state.progress_text = "准备就绪"

# Title and Intro
st.title("📈 OmniAlpha 智能选股工作台")
st.markdown("""
通过 **Baostock** 数据源，结合技术面与基本面策略，快速筛选 A 股优质标的。
支持 CSV 导入预选股票池，或直接全市场扫描。
""")

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ 参数配置")

# 1. Date Selection
default_date = datetime.date.today()
selected_date = st.sidebar.date_input("📅 分析日期 (回测/复盘)", default_date)
date_str = selected_date.strftime("%Y-%m-%d")

# 2. Strategy Selection
st.sidebar.subheader("🛠 策略组合")
available_strategies = get_all_strategy_keys()
selected_strategy_keys = st.sidebar.multiselect(
    "选择要应用的策略 (取交集)",
    options=available_strategies,
    default=['ma'],
    help="同时满足所选所有策略的股票才会被选中"
)

# 3. Mode Selection
st.sidebar.subheader("🎯 扫描范围")
data_source_mode = st.sidebar.radio(
    "股票池来源",
    ("沪深300 (默认)", "CSV 文件导入", "快速测试 (前20只)")
)

# --- Market Overview (New) ---
st.subheader("📊 市场大盘 (上证指数)")
try:
    with st.spinner("正在加载大盘数据..."):
        data_provider.login()
        # Fetch SSE Composite Index Data (sh.000001)
        df_index = data_provider.get_daily_bars('sh.000001', date_str, lookback_days=60)
        
        if df_index is not None and not df_index.empty:
            last_idx = df_index.iloc[-1]
            prev_idx = df_index.iloc[-2] if len(df_index) > 1 else last_idx
            
            change = last_idx['close'] - prev_idx['close']
            pct_change = (change / prev_idx['close']) * 100
            
            # Metric
            col_idx_1, col_idx_2 = st.columns([1, 3])
            with col_idx_1:
                st.metric(
                    label=f"上证指数 ({last_idx['date']})",
                    value=f"{last_idx['close']:.2f}",
                    delta=f"{change:.2f} ({pct_change:.2f}%)"
                )
            
            with col_idx_2:
                # Simple Area Chart
                chart_index = alt.Chart(df_index).mark_area(
                    line={'color':'darkblue'},
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='darkblue', offset=0),
                               alt.GradientStop(color='white', offset=1)],
                        x1=1, x2=1, y1=1, y2=0
                    )
                ).encode(
                    x=alt.X('date:T', title='Date'),
                    y=alt.Y('close:Q', scale=alt.Scale(zero=False), title='Index'),
                    tooltip=['date', 'close', 'pctChg']
                ).properties(height=150)
                st.altair_chart(chart_index, use_container_width=True)
        else:
            st.warning("暂无大盘数据，请检查日期或网络。")
except Exception as e:
    st.error(f"加载大盘数据失败: {e}")

# --- Main Logic ---

def load_stock_pool(mode, uploaded_file=None):
    """Helper to load stock pool based on mode"""
    try:
        data_provider.login()
        if mode == "CSV 文件导入":
            if uploaded_file is not None:
                df = pd.read_csv(uploaded_file)
                if 'code' in df.columns:
                    return df['code'].tolist()
                else:
                    st.error("CSV 文件必须包含 'code' 列")
                    return []
            else:
                st.warning("请上传 CSV 文件")
                return []
        elif mode == "快速测试 (前20只)":
            full_pool = data_provider.get_hs300_stocks(date_str)
            return full_pool[:20] if full_pool else []
        else: # 沪深300
            return data_provider.get_hs300_stocks(date_str)
    except Exception as e:
        st.error(f"获取股票池失败: {e}")
        return []

# File Uploader (Conditional)
uploaded_file = None
if data_source_mode == "CSV 文件导入":
    uploaded_file = st.file_uploader("📂 拖拽或选择 CSV 文件 (包含 'code' 列)", type=['csv'])

# Control Buttons
col_start, col_stop, col_status = st.columns([1, 1, 4])

with col_start:
    start_btn = st.button("🚀 开始分析", type="primary", disabled=st.session_state.is_running)

with col_stop:
    stop_btn = st.button("🛑 停止分析", type="secondary", disabled=not st.session_state.is_running)

# --- Start Logic ---
if start_btn:
    if not selected_strategy_keys:
        st.error("请至少选择一种策略！")
    else:
        with st.spinner(f"正在获取股票池 ({data_source_mode})..."):
            pool = load_stock_pool(data_source_mode, uploaded_file)
        
        if pool:
            st.session_state.stock_pool = pool
            st.session_state.current_index = 0
            st.session_state.analysis_results = [] # Reset results
            st.session_state.is_running = True
            st.session_state.progress_text = "开始扫描..."
            st.rerun()
        else:
            if data_source_mode != "CSV 文件导入":
                 st.warning("股票池为空，请检查日期或网络。")

# --- Stop Logic ---
if stop_btn:
    st.session_state.is_running = False
    st.session_state.progress_text = "已手动停止分析"
    st.rerun()

# --- Execution Loop (Batch Processing) ---
if st.session_state.is_running:
    pool = st.session_state.stock_pool
    idx = st.session_state.current_index
    total = len(pool)
    
    # Init Engine
    strategies = [get_strategy(k) for k in selected_strategy_keys]
    engine = AnalysisEngine(strategies)
    
    # Show Progress Bar
    progress_val = min(idx / total, 1.0)
    st.progress(progress_val)
    st.info(f"正在扫描: {idx}/{total} ({int(progress_val*100)}%) - {st.session_state.progress_text}")

    # Process a Batch (e.g., 5 stocks)
    BATCH_SIZE = 5
    end_idx = min(idx + BATCH_SIZE, total)
    
    try:
        data_provider.login()
        
        for i in range(idx, end_idx):
            code = pool[i]
            res = engine.scan_one(code, date_str)
            if res:
                st.session_state.analysis_results.append(res)
        
        # Update State
        st.session_state.current_index = end_idx
        
        if end_idx >= total:
            st.session_state.is_running = False
            st.session_state.progress_text = "分析完成！"
            st.rerun()
        else:
            # Continue Loop
            time.sleep(0.01) # Yield slightly
            st.rerun()
            
    except Exception as e:
        st.error(f"运行时错误: {e}")
        st.session_state.is_running = False

# --- Result Display ---
if st.session_state.analysis_results is not None and not st.session_state.is_running:
    results = st.session_state.analysis_results
    if results:
        st.success(f"{st.session_state.progress_text} 共筛选出 {len(results)} 只股票")
        st.divider()
        
        df_results = pd.DataFrame(results)
        
        # Reorder cols
        cols = ['code', 'strategy'] + [c for c in df_results.columns if c not in ['code', 'strategy', 'date']]
        df_results = df_results[cols]
        
        # Interactive Table
        st.dataframe(df_results, use_container_width=True)
        
        # Download
        csv = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 下载结果 CSV",
            data=csv,
            file_name=f"omnialpha_selection_{date_str}.csv",
            mime='text/csv',
        )
        
        # --- Visual Analysis Section ---
        st.divider()
        st.subheader("📈 优选股可视化分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'peTTM' in df_results.columns:
                st.caption("市盈率 (PE-TTM) 分布")
                chart_pe = alt.Chart(df_results).mark_bar().encode(
                    x=alt.X('peTTM', bin=True, title='PE TTM'),
                    y='count()',
                    tooltip=['count()']
                ).interactive()
                st.altair_chart(chart_pe, use_container_width=True)
            else:
                st.info("结果中不包含 PE 数据，无法展示分布图。")
                
        with col2:
            if 'turn' in df_results.columns and 'pctChg' in df_results.columns:
                st.caption("换手率 vs 涨跌幅")
                chart_scatter = alt.Chart(df_results).mark_circle(size=60).encode(
                    x=alt.X('turn', title='Turnover (%)'),
                    y=alt.Y('pctChg', title='Change (%)'),
                    color='strategy',
                    tooltip=['code', 'turn', 'pctChg', 'price']
                ).interactive()
                st.altair_chart(chart_scatter, use_container_width=True)
            elif 'price' in df_results.columns:
                st.caption("股价分布")
                chart_price = alt.Chart(df_results).mark_bar().encode(
                x=alt.X('price', bin=True, title='Close Price'),
                y='count()',
                ).interactive()
                st.altair_chart(chart_price, use_container_width=True)

        # Detail View
        st.subheader("🔍 个股详情查看")
        selected_stock = st.selectbox("选择一只股票查看深度分析", df_results['code'].tolist())
        
        if selected_stock:
            with st.spinner("加载K线与指标计算..."):
                try:
                    data_provider.login()
                    df_k = data_provider.get_daily_bars(selected_stock, date_str, lookback_days=180) # Fetch more history for indicators
                except Exception as e:
                    st.error(f"加载数据失败: {e}")
                    df_k = None
                finally:
                    data_provider.logout()

                if df_k is not None and len(df_k) > 0:
                    # --- Indicator Calculation ---
                    df_k['MA5'] = df_k['close'].rolling(window=5).mean()
                    df_k['MA20'] = df_k['close'].rolling(window=20).mean()
                    df_k['MA60'] = df_k['close'].rolling(window=60).mean()
                    
                    # RSI Calculation (Simple 14-day)
                    delta = df_k['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    df_k['RSI'] = 100 - (100 / (1 + rs))
                    
                    # Fill NaN for plotting
                    df_plot = df_k.tail(100).fillna(0) # Show last 100 days
                    
                    # --- Charts ---
                    base = alt.Chart(df_plot).encode(x=alt.X('date:T', axis=alt.Axis(title='Date')))
                    
                    # 1. Price & MA Chart
                    line_close = base.mark_line(color='black').encode(y=alt.Y('close:Q', scale=alt.Scale(zero=False), title='Price'))
                    line_ma5 = base.mark_line(color='#ff7f0e', strokeDash=[2,2]).encode(y='MA5', tooltip=['MA5'])
                    line_ma20 = base.mark_line(color='#2ca02c').encode(y='MA20', tooltip=['MA20'])
                    line_ma60 = base.mark_line(color='#1f77b4').encode(y='MA60', tooltip=['MA60'])
                    
                    chart_price = (line_close + line_ma5 + line_ma20 + line_ma60).properties(height=250, title=f"股价趋势 & 均线 ({selected_stock})")
                    
                    # 2. Volume Chart
                    chart_vol = base.mark_bar(color='#9467bd').encode(
                        y=alt.Y('volume:Q', axis=alt.Axis(title='Volume')),
                        tooltip=['volume']
                    ).properties(height=100)
                    
                    # 3. RSI Chart
                    chart_rsi = base.mark_line(color='#d62728').encode(
                        y=alt.Y('RSI:Q', scale=alt.Scale(domain=[0, 100]), title='RSI')
                    ).properties(height=100)
                    
                    rsi_rule_top = base.mark_rule(color='gray', strokeDash=[4,4]).encode(y=alt.datum(70))
                    rsi_rule_bot = base.mark_rule(color='gray', strokeDash=[4,4]).encode(y=alt.datum(30))
                    
                    chart_rsi_final = chart_rsi + rsi_rule_top + rsi_rule_bot

                    # Combine
                    final_chart = alt.vconcat(chart_price, chart_vol, chart_rsi_final).resolve_scale(x='shared')
                    
                    st.altair_chart(final_chart, use_container_width=True)
                    
                    with st.expander("查看原始数据"):
                        st.dataframe(df_k.tail(10))
    else:
        st.warning(f"{st.session_state.progress_text}，但未找到符合条件的股票。")

# Footer
st.markdown("---")
st.caption("OmniAlpha Strategy Engine v1.1 | Powered by Baostock & Streamlit")