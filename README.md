# 📊 Stock Screener with Momentum & F-Score Analysis

A comprehensive stock screening tool that combines **technical momentum analysis** with **enhanced fundamental Piotroski F-Score** evaluation for Nordic stocks, featuring **AI-powered financial data extraction** and **quarterly report support**.

## 🚀 Features

### 📈 **Momentum Screening**
- **Multi-timeframe analysis**: 3-month, 6-month, 12-month returns
- **Composite momentum score**: Weighted average of returns
- **Price level tracking**: Current vs historical price points
- **Caching system**: Fast repeated analysis with 7-day cache

### 📊 **Enhanced Piotroski F-Score Analysis**
- **Multi-source data fetching**: AI PDF parser + web scraping + Yahoo Finance fallback
- **Quarterly report support**: Analyze interim reports with `--use-quarterly` flag
- **AI-powered extraction**: OpenAI GPT-4 parses complex financial statements
- **Comprehensive scoring**: 9-point fundamental strength assessment
- **Intelligent fallback**: Graceful degradation when enhanced data unavailable
- **Cache optimization**: Expensive calculations cached for performance
- **Enhanced companies**: BioArctic, SAAB, Intellego Technologies with detailed data

### 🎯 **Integrated Screening**
- **Quality-Momentum composite**: Combines technical + fundamental metrics
- **Flexible weighting**: Customize momentum vs F-Score weights (default 70%/30%)
- **F-Score filtering**: Minimum F-Score thresholds
- **CSV file support**: Read ticker lists from files

## 📁 Project Structure

```
screener/
├── src/screener/                 # Main package source code
│   ├── core/                     # Core screening logic
│   │   └── momentum.py           # Momentum screening algorithms
│   ├── data/                     # Data fetching and processing
│   │   ├── models.py            # Data models and schemas
│   │   ├── fetcher.py           # Web scraping and data fetching
│   │   ├── pdf_parser.py        # AI-powered PDF parsing
│   │   ├── tickers.csv          # Default ticker list
│   │   └── annual_report_urls.json  # Company report URLs
│   ├── analysis/                # Financial analysis
│   │   ├── parser.py            # F-Score calculation logic
│   │   └── fscore_calculator.py # Enhanced F-Score calculator
│   ├── cli/                     # Command-line interfaces
│   │   ├── screener_cli.py      # Momentum screening CLI
│   │   ├── fscore_cli.py        # F-Score calculation CLI
│   │   └── ticker_cli.py        # Ticker data CLI
│   └── utils/                   # Utility functions
├── tests/                       # Test suite
├── docs/                        # Documentation
├── scripts/                     # Utility scripts
├── screener.py                  # Entry point for screener CLI
├── fscore.py                    # Entry point for F-Score CLI
├── ticker_data.py               # Entry point for ticker CLI
├── pyproject.toml               # Project configuration
└── cache/                       # Performance cache (auto-generated, git-ignored)
```

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.12+**
- **uv** package manager

### Installation Options

#### Option 1: Development Installation (Recommended)
```bash
# Clone and setup
git clone <your-repo>
cd screener

# Install dependencies
uv sync

# Install package in development mode
uv pip install -e .
```

#### Option 2: Direct Execution
```bash
# Clone and setup
git clone <your-repo>
cd screener

# Install dependencies
uv sync

# Run directly without installation
uv run python screener.py --ticker-file src/screener/data/tickers.csv
```

### Quick Start
```bash
# Run momentum screener with F-Score integration
uv run python screener.py --ticker-file src/screener/data/tickers.csv

# Use quarterly reports for F-Score calculation
uv run python screener.py --use-quarterly --top-n 10

# Analyze individual stock with detailed F-Score breakdown  
uv run python fscore.py BIOA-B.ST --detailed

# Get simple price data for a stock
uv run python ticker_data.py BIOA-B.ST
```

## 📖 Usage Examples

### 🔍 **Individual Stock Analysis**

**Detailed F-Score Analysis** (shows actual financial numbers):
```bash
uv run python fscore.py VOLV-B.ST --detailed
```
*Output: Complete financial breakdown with Income Statement, Balance Sheet, Cash Flow, and ratio calculations*

**Standard F-Score Analysis** (clean summary):
```bash
uv run python fscore.py VOLV-B.ST
```
*Output: F-Score summary with pass/fail indicators*

**Price Analysis**:
```bash
uv run python ticker_data.py VOLV-B.ST
```
*Output: Historical price data with company info and market cap*

### 📊 **Batch Analysis**

**F-Score for Multiple Stocks**:
```bash
uv run python fscore.py tickers.csv --verbose --output f_scores.csv
```
*Output: CSV file with F-Scores for all tickers*

**F-Score with Quarterly Reports**:
```bash
uv run python fscore.py tickers.csv --use-quarterly --output quarterly_scores.csv
```
*Output: F-Scores calculated from quarterly/interim reports*

**Momentum + F-Score Screening**:
```bash
uv run python screener.py --ticker-file tickers.csv
```
*Output: Ranked stocks by composite Quality-Momentum score*

**Advanced Screening Options**:
```bash
# Custom weightings (momentum 80%, F-Score 20%)
uv run python screener.py --momentum-weight 0.8 --f-score-weight 0.2

# Minimum F-Score filter (only stocks with F-Score ≥ 6)
uv run python screener.py --min-f-score 6

# Use quarterly reports for F-Score calculation
uv run python screener.py --use-quarterly --top-n 10

# Disable F-Score integration (momentum only)
uv run python screener.py --no-f-score
```

## 📈 Understanding the Analysis

### 📊 **Piotroski F-Score Breakdown** (0-9 scale)

**💰 Profitability Tests (4 points)**
1. **ROA Positive**: Return on Assets > 0
2. **Operating Cash Flow Positive**: Positive operating cash flow
3. **Net Income Positive**: Profit is growing year-over-year
4. **CFO > Net Income**: Cash quality test (operating cash > accounting profit)

**💵 Leverage & Liquidity Tests (3 points)**  
5. **Decreasing Leverage**: Debt-to-equity ratio declining
6. **Increasing Current Ratio**: Improving short-term liquidity
7. **No Share Dilution**: Shares outstanding not increasing

**⚙️ Operating Efficiency Tests (2 points)**
8. **Higher Gross Margin**: Gross margin improving year-over-year  
9. **Higher Asset Turnover**: Revenue/assets ratio improving

### 📈 **Momentum Scoring**
- **3-month return**: Recent performance momentum
- **6-month return**: Medium-term trend  
- **12-month return**: Long-term momentum
- **Composite score**: Weighted average of all periods

### 🎯 **Quality-Momentum Composite**
- Combines technical momentum (relative performance) with fundamental strength
- **Default weights**: 70% momentum, 30% F-Score
- F-Score acts as quality filter: high momentum + solid fundamentals = best picks

## ⚙️ Configuration

### 📋 **Ticker List Format** (`tickers.csv`)
```csv
ticker
VOLV-B.ST
ERIC-B.ST  
SAND.ST
```
- One ticker per line
- Use Yahoo Finance ticker symbols
- Supports international exchanges (.ST, .OL, .HE, .CO, etc.)

### 🔧 **Command Line Options**

**Main Screener (`screener.py`)**:
- `--ticker-file FILE`: Specify ticker list file (default: tickers.csv)
- `--start-date DATE`: Analysis start date (default: 450 days ago)
- `--min-f-score N`: Minimum F-Score filter (default: 0)
- `--f-score-weight N`: F-Score weight in composite (default: 0.3)
- `--momentum-weight N`: Momentum weight in composite (default: 0.7)
- `--no-f-score`: Disable F-Score integration

**F-Score Tool (`fscore.py`)**:
- `--detailed`: Enhanced report with financial numbers
- `--verbose`: Detailed batch output
- `--no-cache`: Disable caching (always fetch fresh data)
- `--output FILE`: Specify output CSV file

## 🚨 Troubleshooting

### **Common Issues**

**"Insufficient historical data"**
- Ensure ticker symbols are correct Yahoo Finance format
- Try setting earlier `--start-date` for historical analysis

**"Empty DataFrame" results**
- Check ticker list contains valid, tradeable stocks
- Verify internet connection for Yahoo Finance data
- Clear cache with `--no-cache` if data seems stale

**"IndexError" or data extraction errors**
- Update dependencies: `uv sync --upgrade`
- Temporary Yahoo Finance API issues - retry later

### **Performance Tips**
- Cache is enabled by default - slow first run, fast subsequent runs
- Use `--start-date` closer to present for faster momentum calculations
- Batch F-Score analysis uses efficient caching

## 📚 Notes

- **Nordic Focus**: Designed for Swedish (.ST), Norwegian (.OL), Danish (.CO), Finnish (.HE) stocks
- **Data Source**: Yahoo Finance (real-time prices, historical financials)
- **Cache Duration**: 7 days (automatically refreshes old data)
- **Currency**: Supports multi-currency analysis (SEK, NOK, DKK, EUR)

## 🎯 Current Status

See `TODO.md` for planned analysis tasks and known investigation areas.

---

*Built with Python, pandas, yfinance - for educational and analysis purposes.*
