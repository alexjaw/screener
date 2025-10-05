# Screener Package Structure

This document describes the recommended Python package structure for the screener application.

## 📁 Directory Structure

```
screener/
├── src/screener/                 # Main package source code
│   ├── __init__.py              # Package initialization
│   ├── __main__.py              # Main CLI entry point
│   ├── core/                    # Core screening logic
│   │   ├── __init__.py
│   │   └── momentum.py          # Momentum screening algorithms
│   ├── data/                    # Data fetching and processing
│   │   ├── __init__.py
│   │   ├── models.py            # Data models and schemas
│   │   ├── fetcher.py           # Web scraping and data fetching
│   │   ├── pdf_parser.py        # AI-powered PDF parsing
│   │   ├── tickers.csv          # Default ticker list
│   │   └── annual_report_urls.json  # Company report URLs
│   ├── analysis/                # Financial analysis
│   │   ├── __init__.py
│   │   ├── parser.py            # F-Score calculation logic
│   │   └── fscore_calculator.py # Enhanced F-Score calculator
│   ├── cli/                     # Command-line interfaces
│   │   ├── __init__.py
│   │   ├── screener_cli.py      # Momentum screening CLI
│   │   ├── fscore_cli.py        # F-Score calculation CLI
│   │   └── ticker_cli.py        # Ticker data CLI
│   └── utils/                   # Utility functions
│       └── __init__.py
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_data.py             # Test data and fixtures
│   ├── test_fscore_calculation.py  # F-Score calculation tests
│   └── test_suite.py            # Comprehensive test suite
├── docs/                        # Documentation
│   └── package_structure.md     # This file
├── scripts/                     # Utility scripts
├── annual-reports/              # Downloaded annual reports
├── cache/                       # Cached data (git-ignored)
├── screener.py                  # Entry point for screener CLI
├── fscore.py                    # Entry point for F-Score CLI
├── ticker_data.py               # Entry point for ticker CLI
├── pyproject.toml               # Project configuration
├── README.md                    # Main documentation
├── TODO.md                      # Development tasks
└── .gitignore                   # Git ignore rules
```

## 🏗️ Package Architecture

### Core Module (`core/`)
Contains the main business logic for momentum screening:
- **momentum.py**: Core momentum calculation algorithms
- Handles price data fetching, return calculations, and composite scoring

### Data Module (`data/`)
Handles all data acquisition and processing:
- **models.py**: Data models and schemas (FinancialData, ParseOptions)
- **fetcher.py**: Web scraping from company websites and official sources
- **pdf_parser.py**: AI-powered PDF parsing using OpenAI GPT-4
- **tickers.csv**: Default list of Nordic tickers
- **annual_report_urls.json**: Mapping of companies to their report URLs

### Analysis Module (`analysis/`)
Contains financial analysis and F-Score calculations:
- **parser.py**: Converts raw financial data to F-Score metrics
- **fscore_calculator.py**: Enhanced F-Score calculator with multiple data sources

### CLI Module (`cli/`)
Command-line interfaces for different functionalities:
- **screener_cli.py**: Momentum screening with F-Score integration
- **fscore_cli.py**: Standalone F-Score calculation
- **ticker_cli.py**: Individual ticker data analysis

## 🚀 Usage

### As a Package
```python
from src.screener.core.momentum import momentum_screen
from src.screener.analysis.fscore_calculator import score_company

# Use the functions directly
results = momentum_screen(['VOLV-B.ST', 'SAND.ST'])
f_score = score_company('BIOA-B.ST')
```

### As CLI Tools
```bash
# Momentum screening
python screener.py --ticker-file src/screener/data/tickers.csv --top-n 10

# F-Score calculation
python fscore.py VOLV-B.ST --detailed

# Ticker data
python ticker_data.py SAND.ST --period 1y
```

### As Installed Package
```bash
# Install in development mode
uv pip install -e .

# Use installed commands
screener --help
fscore --help
ticker-data --help
```

## 🔧 Development

### Adding New Features
1. **Core Logic**: Add to `src/screener/core/`
2. **Data Sources**: Add to `src/screener/data/`
3. **Analysis**: Add to `src/screener/analysis/`
4. **CLI**: Add to `src/screener/cli/`
5. **Tests**: Add to `tests/`

### Testing
```bash
# Run all tests
uv run python -m pytest tests/

# Run specific test
uv run python tests/test_suite.py
```

### Building Package
```bash
# Build wheel
uv build

# Install locally
uv pip install dist/screener-*.whl
```

## 📦 Benefits of This Structure

1. **Modularity**: Clear separation of concerns
2. **Testability**: Easy to test individual components
3. **Reusability**: Core logic can be imported and reused
4. **Maintainability**: Easy to find and modify specific functionality
5. **Scalability**: Easy to add new features without breaking existing code
6. **Professional**: Follows Python packaging best practices
7. **Distribution**: Can be packaged and distributed via PyPI
