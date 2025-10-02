# 📋 Analysis TODO List

## 🚨 **High Priority Investigations**

### 1. **BIOA-B.ST F-Score Analysis** 🔍
**Issue**: BioArctic shows 0/9 F-Score - investigate fundamental problems or data extraction errors

**Investigation Tasks:**
- [ ] **Enhanced F-Score Analysis**: Run `uv run python fscore.py BIOA-B.ST --detailed`
- [ ] **Financial Data Verification**: Check if Yahoo Finance data is complete/accurate
- [ ] **Industry Context**: Understand biotech industry-specific financial patterns
- [ ] **Cash Flow Analysis**: Biotech companies often have different cash flow patterns (R&D heavy)
- [ ] **Revenue Recognition**: Investigate if revenue/cost patterns are industry-typical
- [ ] **Comparison with Peers**: Compare with other Nordic biotech companies

**Expected Outcome**: Understand if 0/9 score reflects:
- Real fundamental weaknesses (poor profitability, high debt, declining efficiency)
- Data extraction issues (missing financial periods, incorrect field mapping)
- Industry-specific patterns not captured by standard F-Score criteria

### 2. **Momentum Calculation Validation** 📈
**Issue**: Verify momentum scoring logic and identify discrepancies in results

**Investigation Tasks:**
- [ ] **Manual Calculation Check**: Pick 2-3 stocks, manually verify 3m/6m/12m returns
- [ ] **Data Quality Audit**: Ensure Yahoo Finance historical data is accurate and complete
- [ ] **Return Calculation Logic**: Verify `(current_price / historical_price - 1) * 100` formula
- [ ] **Date Range Validation**: Confirm lookback periods are correctly calculated (450-day default adequate?)
- [ ] **Price Adjustment**: Check if dividend-adjusted vs unadjusted prices are used consistently
- [ ] **Outlier Detection**: Identify stocks with suspicious return patterns (potential data errors)

**Comparison Framework**:
- Calculate manual returns for: `VOLV-B.ST`, `SAND.ST`, `INT.ST`
- Cross-reference with official exchange data if available
- Validate against other financial data sources

**Expected Outcome**: Confirm momentum calculations are mathematically correct and data-driven

### 3. **F-Score vs Market Performance Correlation** 📊
**Investigation Tasks:**
- [ ] **Backtesting**: Compare F-Score ranking vs actual stock performance over last 12 months
- [ ] **Quality Threshold**: Determine if F-Score ≥ 6 stocks consistently outperform
- [ ] **Risk-Adjusted Returns**: Check if high F-Score stocks have better risk/reward profiles
- [ ] **Market Cap Analysis**: See if F-Score effectiveness varies by company size

## 🔧 **Technical Improvements**

### 4. **Data Robustness** 
- [ ] **Error Handling**: Improve graceful handling of missing Yahoo Finance data
- [ ] **Field Mapping**: Add more robust financial statement field name variations
- [ ] **Data Validation**: Add sanity checks for extracted financial metrics
- [ ] **Retry Logic**: Implement retry mechanism for failed API calls

### 5. **Performance & Caching**
- [ ] **Cache Optimization**: Review current 7-day cache duration (optimal for Nordic market updates?)
- [ ] **Parallel Processing**: Implement concurrent F-Score calculations for batch analysis
- [ ] **Data Compression**: Optimize cache storage format

### 6. **User Experience** 
- [ ] **Configuration File**: Add YAML config file for default parameters
- [ ] **Better Error Messages**: More descriptive error messages for common issues
- [ ] **Progress Indicators**: Add progress bars for long-running analyses
- [ ] **Export Formats**: Support JSON output for F-Score results

## 📚 **Documentation & Analysis**

### 7. **Enhanced Documentation**
- [ ] **Case Studies**: Add real-world analysis examples (Volvo, Sandvik deep-dives)
- [ ] **Market Commentary**: Document typical F-Score distributions for Nordic markets
- [ ] **Industry Insights**: Sector-specific F-Score patterns (finance, tech, industrial, biotech)

### 8. **Additional Features**
- [ ] **Peer Comparison**: Add sector-based peer group analysis
- [ ] **Historical Trends**: Track F-Score changes over time for individual stocks
- [ ] **Market-wide Screening**: Expand beyond current ticker list to full Nordic market
- [ ] **Real-time Updates**: Integration with real-time price feeds

## 🎯 **Quick Analysis Commands**

**Immediate Investigation**:
```bash
# Deep dive BioArctic F-Score
uv run python fscore.py BIOA-B.ST --detailed --no-cache

# Validate momentum for SAND.ST  
uv run python ticker_data.py SAND.ST
uv run python fscore.py SAND.ST --detailed

# Check recent screener output
uv run python screener.py --ticker-file tickers.csv --verbose
```

---

## 📝 **Notes**
- **Priority Order**: BIOA-B.ST analysis → Momentum validation → Correlation study
- **Time Estimate**: BIOA-B.ST investigation ~2-3 hours, Momentum validation ~1-2 hours
- **Success Criteria**: Clear understanding of why scores differ from expectations
- **Next Steps**: After addressing these tasks, consider expanding ticker universe and adding more sophisticated analysis features
