# Stock Data Collection

> [!WARNING]
> ### ⚠️ Project Status: Deprecated & Unmaintained
>
> This repository was created solely for **learning and demo purposes** and is **no longer maintained**.
>
> All ongoing development and functionality have been merged into:
> 🔗 **[SandyCompetent/stock-market-analysis](https://github.com/SandyCompetent/stock-market-analysis)**
>
> Please refer to the new project for active updates, improved workflows, and comprehensive stock market analysis tools.

---

## About This Repository

This project contains experimental scripts and automated workflows for collecting historical stock market and financial news sentiment data for demonstration and educational purposes.

### Key Components

- **Stock Data Ingestion (`fetch_stock_data.py`)**: Fetches monthly historical stock market data (e.g., 1-minute intervals) using the Alpha Vantage API with multi-key rotation and state tracking.
- **News & Sentiment Fetching (`fetch_news_and_sentiment.py`)**: Fetches financial news headlines and sentiment scores over custom date intervals.
- **Data Consolidation (`merge_and_sort_csv.py`)**: Merges monthly CSV partitions and sorts records chronologically.
- **GitHub Actions Automation (`.github/workflows/`)**: Scheduled workflows that periodically triggered data collection tasks.

---

> [!NOTE]
> For active development, analysis pipelines, and new features, please visit **[stock-market-analysis](https://github.com/SandyCompetent/stock-market-analysis)**.
