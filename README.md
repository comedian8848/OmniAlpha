# OmniAlpha: 全场景智能量化研究与交易引擎

**OmniAlpha** 是一个专为 A 股市场设计的模块化量化交易平台。它不仅集成了实时行情获取、历史回测和模拟盘执行，更核心的突破在于其**双循环架构**：内置基于遗传算法与强化学习的 **AlphaGen 因子挖掘工厂**，并预留了 **LLM（大语言模型）** 接口，用于语义情感分析与策略自动化生成。

## 🌟 核心特性

*   **🖥️ 可视化工作台**: 基于 Streamlit 打造的交互式 Web 界面，支持大盘监控、策略组合选股、结果可视化分析。
*   **🛠️ 模块化架构**: 采用依赖倒置设计，Data Provider、Strategy、Engine 高度解耦，方便扩展。
*   **📈 多维度策略**: 内置均线趋势、放量突破、低估值、高换手等多种实战策略，支持自由组合。
*   **🔍 深度个股诊断**: 自动计算 MA5/20/60、RSI 等指标，提供量价时空全方位图表分析。

---

## 📂 项目结构 (Project Structure)

```text
BlackOil-OmniAlpha/
├── main.py                 # 🚀 CLI 入口：命令行模式运行
├── web_ui.py               # 🌐 Web 入口：启动图形化工作台
├── core/                   # 🧠 核心逻辑层
│   ├── data_provider.py    # 数据适配器 (Baostock)
│   └── engine.py           # 策略执行引擎
├── strategies/             # 📈 策略仓库
│   ├── __init__.py         # 策略注册中心
│   ├── base.py             # 策略基类接口
│   ├── technical.py        # 技术面策略 (MA, Vol, Turn)
│   └── fundamental.py      # 基本面策略 (PE)
├── utils/                  # 🛠️ 工具集
│   ├── file_io.py          # CSV 文件读写
│   └── date_utils.py       # 日期处理
└── requirements.txt        # 📦 项目依赖清单
```

---

## 🛠️ 本地部署指南 (Installation)

### 1. 环境准备
确保您的系统已安装 **Python 3.8+**。

### 2. 克隆项目
```bash
git clone https://github.com/YourUsername/OmniAlpha.git
cd OmniAlpha
```

### 3. 安装依赖
建议使用虚拟环境（如 venv 或 conda）以避免依赖冲突。
```bash
# 创建虚拟环境 (可选)
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 安装核心依赖
pip install -r requirements.txt
```
*(主要依赖：`streamlit`, `baostock`, `pandas`, `altair`)*

---

## 🚀 使用说明 (Usage)

### 方式一：Web 图形化工作台 (推荐)
适合直观地进行选股、复盘和图表分析。

1.  **启动服务**:
    ```bash
    streamlit run web_ui.py
    ```
2.  **浏览器访问**:
    服务启动后，自动打开浏览器访问 `http://localhost:8501`。
3.  **操作流程**:
    *   **顶部**: 查看 **沪深300指数** 当日走势，判断市场冷暖。
    *   **左侧栏**:
        *   **日期**: 选择回测或复盘的日期。
        *   **策略**: 勾选需要的策略（如同时勾选 `ma` 和 `pe`，系统会筛选出既符合均线多头又低估值的股票）。
        *   **来源**: 选择“沪深300”全扫描，或上传 CSV 文件进行二次筛选。
    *   **执行**: 点击 **“🚀 开始分析”**。支持随时点击 **“🛑 停止分析”** 查看已跑出的结果。
    *   **分析**:
        *   查看选股结果列表、PE 分布图、换手率散点图。
        *   点击列表中任意股票，底部自动展示 **K线 + 均线 + 成交量 + RSI** 组合图表。

### 方式二：CLI 命令行模式
适合脚本自动化或服务器后台运行。

*   **快速测试**:
    ```bash
    python main.py --quick --strategies ma,pe
    ```
*   **全量扫描**:
    ```bash
    python main.py --strategies ma,vol,turn
    ```
*   **管道模式 (CSV导入)**:
    ```bash
    python main.py --file my_stock_pool.csv --strategies pe
    ```

---

## 📅 项目规划 (Roadmap)

*   [x] **Phase 1**: 核心引擎重构与模块化。
*   [x] **Phase 2**: 集成 Baostock 数据源，实现基础策略库。
*   [x] **Phase 3**: **Web UI 工作台上线**，支持可视化交互与深度图表。
*   [ ] **Phase 4**: 接入 Backtrader 回测框架，验证选股结果的胜率。
*   [ ] **Phase 5**: 接入 LLM (大模型) 接口，实现基于新闻情绪的因子加权。

---

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request！
*   **策略贡献**: 请在 `strategies/` 目录下添加新的策略类，并在 `__init__.py` 中注册。
*   **Bug 反馈**: 请附上详细的报错信息和复现步骤。

---
