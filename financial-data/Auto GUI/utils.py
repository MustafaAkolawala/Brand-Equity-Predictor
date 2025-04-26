import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Cache configuration
# Simple in-memory cache with expiration
cache = {}
CACHE_EXPIRY = 300  # 5 minutes in seconds

def get_from_cache(key):
    """Get item from cache if it exists and is not expired"""
    if key in cache:
        timestamp, data = cache[key]
        if time.time() - timestamp < CACHE_EXPIRY:
            return data
    return None

def set_in_cache(key, data):
    """Set item in cache with current timestamp"""
    cache[key] = (time.time(), data)
    return data

def fetch_stock_data(symbol, period='1mo', interval='1d'):
    """
    Fetch historical stock data for a given symbol
    
    Args:
        symbol (str): Stock symbol
        period (str): Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval (str): Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    
    Returns:
        pandas.DataFrame: Historical stock data
    """
    cache_key = f"hist_{symbol}_{period}_{interval}"
    cached_data = get_from_cache(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    try:
        stock = yf.Ticker(symbol)
        hist_data = stock.history(period=period, interval=interval)
        
        if hist_data.empty:
            return pd.DataFrame()
        
        return set_in_cache(cache_key, hist_data)
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return pd.DataFrame()

def fetch_stock_info(symbol):
    """
    Fetch general information about a stock
    
    Args:
        symbol (str): Stock symbol
    
    Returns:
        dict: Stock information
    """
    cache_key = f"info_{symbol}"
    cached_data = get_from_cache(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        if not info:
            return {}
        
        return set_in_cache(cache_key, info)
    except Exception as e:
        print(f"Error fetching stock info: {e}")
        return {}

def fetch_financial_data(symbol):
    """
    Fetch financial data for a given stock
    
    Args:
        symbol (str): Stock symbol
    
    Returns:
        dict: Financial data
    """
    cache_key = f"financials_{symbol}"
    cached_data = get_from_cache(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    try:
        stock = yf.Ticker(symbol)
        
        # Get income statement, balance sheet and cash flow data
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        if income_stmt.empty and balance_sheet.empty and cash_flow.empty:
            return {}
        
        # Extract the most recent annual data
        financials = {}
        
        # Income statement data
        if not income_stmt.empty:
            recent_income = income_stmt.iloc[:, 0]  # Most recent column
            financials.update({
                'totalRevenue': recent_income.get('Total Revenue', None),
                'grossProfit': recent_income.get('Gross Profit', None),
                'operatingIncome': recent_income.get('Operating Income', None),
                'netIncome': recent_income.get('Net Income', None),
                'eps': stock.info.get('trailingEps', None)
            })
        
        # Balance sheet data
        if not balance_sheet.empty:
            recent_balance = balance_sheet.iloc[:, 0]  # Most recent column
            financials.update({
                'totalAssets': recent_balance.get('Total Assets', None),
                'totalLiab': recent_balance.get('Total Liabilities Net Minority Interest', None),
                'totalStockholderEquity': recent_balance.get('Stockholders Equity', None),
                'totalCash': recent_balance.get('Cash And Cash Equivalents', None),
                'totalDebt': recent_balance.get('Total Debt', None)
            })
        
        # Cash flow data
        if not cash_flow.empty:
            recent_cash = cash_flow.iloc[:, 0]  # Most recent column
            financials.update({
                'operatingCashFlow': recent_cash.get('Operating Cash Flow', None),
                'capitalExpenditures': recent_cash.get('Capital Expenditure', None),
                'freeCashFlow': recent_cash.get('Free Cash Flow', None)
            })
        
        return set_in_cache(cache_key, financials)
    except Exception as e:
        print(f"Error fetching financial data: {e}")
        return {}

def calculate_financial_ratios(symbol):
    """
    Calculate financial ratios for a given stock
    
    Args:
        symbol (str): Stock symbol
    
    Returns:
        dict: Financial ratios
    """
    cache_key = f"ratios_{symbol}"
    cached_data = get_from_cache(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Get financial data
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        
        ratios = {}
        
        # Valuation ratios
        ratios['pe_ratio'] = round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 'N/A'
        ratios['ps_ratio'] = round(info.get('priceToSalesTrailing12Months', 0), 2) if info.get('priceToSalesTrailing12Months') else 'N/A'
        ratios['pb_ratio'] = round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 'N/A'
        ratios['ev_to_ebitda'] = round(info.get('enterpriseToEbitda', 0), 2) if info.get('enterpriseToEbitda') else 'N/A'
        
        # Profitability ratios
        if not income_stmt.empty:
            recent_income = income_stmt.iloc[:, 0]  # Most recent column
            
            # Handle the data safely
            revenue = 0
            gross_profit = 0
            operating_income = 0
            net_income = 0
            
            # Check if values exist and are numeric
            if 'Total Revenue' in recent_income:
                revenue = recent_income['Total Revenue']
            if 'Gross Profit' in recent_income:
                gross_profit = recent_income['Gross Profit']
            if 'Operating Income' in recent_income:
                operating_income = recent_income['Operating Income']
            if 'Net Income' in recent_income:
                net_income = recent_income['Net Income']
            
            if revenue and revenue > 0:
                ratios['gross_margin'] = round((gross_profit / revenue) * 100, 2) if gross_profit else 'N/A'
                ratios['operating_margin'] = round((operating_income / revenue) * 100, 2) if operating_income else 'N/A'
                ratios['net_margin'] = round((net_income / revenue) * 100, 2) if net_income else 'N/A'
            else:
                ratios['gross_margin'] = 'N/A'
                ratios['operating_margin'] = 'N/A'
                ratios['net_margin'] = 'N/A'
        else:
            ratios['gross_margin'] = 'N/A'
            ratios['operating_margin'] = 'N/A'
            ratios['net_margin'] = 'N/A'
        
        # ROE and ROA
        if not balance_sheet.empty and not income_stmt.empty:
            recent_balance = balance_sheet.iloc[:, 0]  # Most recent column
            
            equity = 0
            assets = 0
            net_income = 0
            
            if 'Stockholders Equity' in recent_balance:
                equity = recent_balance['Stockholders Equity']
            if 'Total Assets' in recent_balance:
                assets = recent_balance['Total Assets']
            if 'Net Income' in income_stmt.iloc[:, 0]:
                net_income = income_stmt.iloc[:, 0]['Net Income']
            
            if equity and equity > 0:
                ratios['roe'] = round((net_income / equity) * 100, 2)
            else:
                ratios['roe'] = 'N/A'
                
            if assets and assets > 0:
                ratios['roa'] = round((net_income / assets) * 100, 2)
            else:
                ratios['roa'] = 'N/A'
        else:
            ratios['roe'] = 'N/A'
            ratios['roa'] = 'N/A'
        
        # Growth metrics - if we have multiple periods
        if not income_stmt.empty and income_stmt.shape[1] >= 2:
            current_revenue = 0
            prev_revenue = 0
            current_net_income = 0
            prev_net_income = 0
            
            if 'Total Revenue' in income_stmt.iloc[:, 0]:
                current_revenue = income_stmt.iloc[:, 0]['Total Revenue']
            if 'Total Revenue' in income_stmt.iloc[:, 1]:
                prev_revenue = income_stmt.iloc[:, 1]['Total Revenue']
            if 'Net Income' in income_stmt.iloc[:, 0]:
                current_net_income = income_stmt.iloc[:, 0]['Net Income']
            if 'Net Income' in income_stmt.iloc[:, 1]:
                prev_net_income = income_stmt.iloc[:, 1]['Net Income']
            
            if current_revenue and prev_revenue and prev_revenue > 0:
                ratios['revenue_growth'] = round(((current_revenue - prev_revenue) / prev_revenue) * 100, 2)
            else:
                ratios['revenue_growth'] = 'N/A'
                
            if current_net_income and prev_net_income and prev_net_income > 0:
                ratios['eps_growth'] = round(((current_net_income - prev_net_income) / prev_net_income) * 100, 2)
            else:
                ratios['eps_growth'] = 'N/A'
        else:
            ratios['revenue_growth'] = 'N/A'
            ratios['eps_growth'] = 'N/A'
        
        # Dividend metrics
        ratios['dividend_yield'] = round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 'N/A'
        ratios['payout_ratio'] = round(info.get('payoutRatio', 0) * 100, 2) if info.get('payoutRatio') else 'N/A'
        
        return set_in_cache(cache_key, ratios)
    except Exception as e:
        print(f"Error calculating financial ratios: {e}")
        return {}

def fetch_company_news(symbol, max_news=5):
    """
    Fetch recent news for a company
    
    Args:
        symbol (str): Stock symbol
        max_news (int): Maximum number of news articles to return
    
    Returns:
        list: Recent news articles
    """
    cache_key = f"news_{symbol}"
    cached_data = get_from_cache(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    try:
        stock = yf.Ticker(symbol)
        news_data = []
        
        # Yahoo Finance API provides news through the info property
        if hasattr(stock, 'news') and stock.news:
            for i, article in enumerate(stock.news):
                if i >= max_news:
                    break
                    
                news_item = {
                    'title': article["content"]["title"],
                    #article.get('title', 'No title'),
                    'summary': article["content"]["summary"],
                    #article.get('summary', 'No summary available'),
                    'link': article["content"]["canonicalUrl"]["url"],
                    #article.get('link', ''),
                    'date': article["content"]["pubDate"][:10]
                    #datetime.fromtimestamp(article.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M')
                }
                news_data.append(news_item)
        
        return set_in_cache(cache_key, news_data)
    except Exception as e:
        print(f"Error fetching company news: {e}")
        return []

def format_large_number(num):
    """
    Format large numbers to be more readable
    
    Args:
        num: Number to format
    
    Returns:
        str: Formatted number
    """
    if num == 'N/A' or num is None:
        return 'N/A'
    
    try:
        num = float(num)
        if num >= 1e12:  # Trillion
            return f"₹{num/1e12:.2f}T"
        elif num >= 1e9:  # Billion
            return f"₹{num/1e9:.2f}B"
        elif num >= 1e6:  # Million
            return f"₹{num/1e6:.2f}M"
        elif num >= 1e3:  # Thousand
            return f"₹{num/1e3:.2f}K"
        else:
            return f"₹{num:.2f}"
    except (ValueError, TypeError):
        return 'N/A'
        
def calculate_brand_equity_index(symbol):
    """
    Calculate Brand Equity Index (BEI) for a given stock with enhanced metrics
    
    The Brand Equity Index is a comprehensive score that quantifies a company's brand value
    based on multiple dimensions:
    1. Market Position (40%):
       - Market Cap to Revenue Ratio
       - Enterprise Value to EBITDA
       - Price to Sales Ratio
    2. Financial Strength (30%):
       - Gross Margin
       - Operating Margin
       - Net Profit Margin
    3. Growth & Momentum (20%):
       - Revenue Growth Rate
       - Earnings Growth Rate
       - Price Momentum
    4. Brand Stability (10%):
       - Operating History
       - Dividend History
       - Volatility Score
    
    Args:
        symbol (str): Stock symbol
    
    Returns:
        dict: Enhanced brand equity metrics and analysis
    """
    cache_key = f"bei_{symbol}"
    cached_data = get_from_cache(cache_key)
    
    if cached_data is not None:
        return cached_data
        
    try:
        # Get required data
        stock = yf.Ticker(symbol)
        info = stock.info
        financial_data = fetch_financial_data(symbol)
        income_stmt = stock.income_stmt
        hist_data = stock.history(period="2y")  # Get 2 years of history for momentum and volatility
        
        bei_data = {
            'bei_score': 'N/A',
            'components': {},
            'market_position': {},
            'financial_strength': {},
            'growth_momentum': {},
            'brand_stability': {},
            'market_dominance': 'N/A',
            # 'comparable_companies': [],
            'analysis': {},
            # 'recommendations': []
        }

        # 1. Market Position Components (40% weight)
        market_cap = info.get('marketCap', 0)
        revenue = financial_data.get('totalRevenue', 0)
        ev_to_ebitda = info.get('enterpriseToEbitda', 0)
        price_to_sales = info.get('priceToSalesTrailing12Months', 0)

        if revenue and revenue > 0:
            market_to_revenue = market_cap / revenue
            bei_data['market_position']['market_to_revenue'] = round(market_to_revenue, 2)
            bei_data['market_position']['ev_to_ebitda'] = round(ev_to_ebitda, 2) if ev_to_ebitda else 'N/A'
            bei_data['market_position']['price_to_sales'] = round(price_to_sales, 2) if price_to_sales else 'N/A'
            
            # Calculate market position score (0-40)
            market_score = 0
            if market_to_revenue > 0:
                market_score += min(20, market_to_revenue * 2)  # Up to 20 points
            if ev_to_ebitda and ev_to_ebitda > 0:
                market_score += min(10, ev_to_ebitda)  # Up to 10 points
            if price_to_sales and price_to_sales > 0:
                market_score += min(10, price_to_sales * 2)  # Up to 10 points
            
            bei_data['components']['market_position_score'] = round(market_score, 2)

        # 2. Financial Strength Components (30% weight)
        if revenue > 0:
            gross_profit = financial_data.get('grossProfit', 0)
            operating_income = financial_data.get('operatingIncome', 0)
            net_income = financial_data.get('netIncome', 0)
            
            gross_margin = (gross_profit / revenue) if gross_profit else 0
            operating_margin = (operating_income / revenue) if operating_income else 0
            net_margin = (net_income / revenue) if net_income else 0
            
            bei_data['financial_strength']['gross_margin'] = round(gross_margin * 100, 2)
            bei_data['financial_strength']['operating_margin'] = round(operating_margin * 100, 2)
            bei_data['financial_strength']['net_margin'] = round(net_margin * 100, 2)
            
            # Calculate financial strength score (0-30)
            financial_score = (
                min(15, gross_margin * 100) +  # Up to 15 points
                min(10, operating_margin * 100) +  # Up to 10 points
                min(5, net_margin * 100)  # Up to 5 points
            )
            bei_data['components']['financial_strength_score'] = round(financial_score, 2)

        # 3. Growth & Momentum Components (20% weight)
        growth_score = 0
        
        # Calculate revenue growth
        if not income_stmt.empty and income_stmt.shape[1] >= 2:
            current_revenue = income_stmt.iloc[:, 0].get('Total Revenue', 0)
            prev_revenue = income_stmt.iloc[:, 1].get('Total Revenue', 0)
            if current_revenue and prev_revenue and prev_revenue > 0:
                revenue_growth = ((current_revenue - prev_revenue) / prev_revenue)
                bei_data['growth_momentum']['revenue_growth'] = round(revenue_growth * 100, 2)
                growth_score += min(10, max(0, revenue_growth * 100))  # Up to 10 points

        # Calculate price momentum
        if not hist_data.empty:
            recent_price = hist_data['Close'].iloc[-1]
            year_ago_price = hist_data['Close'].iloc[min(len(hist_data)-1, max(0, len(hist_data)-252))]
            if recent_price and year_ago_price and year_ago_price > 0:
                price_momentum = ((recent_price - year_ago_price) / year_ago_price)
                bei_data['growth_momentum']['price_momentum'] = round(price_momentum * 100, 2)
                growth_score += min(10, max(0, price_momentum * 50))  # Up to 10 points
        
        bei_data['components']['growth_momentum_score'] = round(growth_score, 2)

        # 4. Brand Stability Components (10% weight)
        stability_score = 0
        
        # Operating history
        years_listed = info.get('yearFounded', 0)
        current_year = datetime.now().year
        if years_listed:
            company_age = current_year - years_listed
            bei_data['brand_stability']['company_age'] = company_age
            stability_score += min(4, company_age / 10)  # Up to 4 points
        
        # Dividend history
        dividend_yield = info.get('dividendYield', 0)
        if dividend_yield:
            bei_data['brand_stability']['dividend_yield'] = round(dividend_yield * 100, 2)
            stability_score += min(3, dividend_yield * 100)  # Up to 3 points
        
        # Volatility score
        if not hist_data.empty:
            daily_returns = hist_data['Close'].pct_change()
            volatility = daily_returns.std() * np.sqrt(252)  # Annualized volatility
            bei_data['brand_stability']['volatility'] = round(volatility * 100, 2)
            stability_score += min(3, (1 - volatility) * 3)  # Up to 3 points for low volatility
        
        bei_data['components']['brand_stability_score'] = round(stability_score, 2)

        # Calculate final BEI score (0-100 scale)
        total_score = (
            bei_data['components'].get('market_position_score', 0) +
            bei_data['components'].get('financial_strength_score', 0) +
            bei_data['components'].get('growth_momentum_score', 0) +
            bei_data['components'].get('brand_stability_score', 0)
        )
        
        bei_data['bei_score'] = round(total_score, 2)
        
        # Categorize market dominance based on enhanced BEI score
        if total_score >= 80:
            bei_data['market_dominance'] = "Elite Brand Value"
        elif total_score >= 60:
            bei_data['market_dominance'] = "Premium Brand Value"
        elif total_score >= 40:
            bei_data['market_dominance'] = "Strong Brand Value"
        elif total_score >= 20:
            bei_data['market_dominance'] = "Moderate Brand Value"
        else:
            bei_data['market_dominance'] = "Developing Brand Value"

        # Generate analysis and recommendations
        bei_data['analysis'] = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': []
        }
        
        # Analyze strengths
        if bei_data['components'].get('market_position_score', 0) > 30:
            bei_data['analysis']['strengths'].append("Strong market position with high brand value relative to revenue")
        if bei_data['components'].get('financial_strength_score', 0) > 20:
            bei_data['analysis']['strengths'].append("Excellent financial performance with strong margins")
        if bei_data['growth_momentum'].get('revenue_growth', 0) > 15:
            bei_data['analysis']['strengths'].append("Strong revenue growth trajectory")
        
        # Analyze weaknesses
        if bei_data['components'].get('market_position_score', 0) < 20:
            bei_data['analysis']['weaknesses'].append("Market position could be improved")
        if bei_data['components'].get('financial_strength_score', 0) < 15:
            bei_data['analysis']['weaknesses'].append("Margins below industry standards")
        
        # Analyze opportunities and threats
        if bei_data['growth_momentum'].get('revenue_growth', 0) > 0:
            bei_data['analysis']['opportunities'].append("Potential for market expansion given positive growth trends")
        if bei_data['brand_stability'].get('volatility', 0) > 30:
            bei_data['analysis']['threats'].append("High price volatility may indicate market uncertainty")

        # Generate recommendations
        # if bei_data['components'].get('market_position_score', 0) < 20:
        #     bei_data['recommendations'].append("Focus on improving market position through brand development")
        # if bei_data['components'].get('financial_strength_score', 0) < 15:
        #     bei_data['recommendations'].append("Implement cost optimization strategies to improve margins")
        # if bei_data['brand_stability'].get('volatility', 0) > 30:
        #     bei_data['recommendations'].append("Consider strategies to reduce market volatility and strengthen brand stability")
                
        # Find and add comparable companies
        # try:
        #     peers = stock.info.get('peerSet', [])
        #     if peers:
        #         bei_data['comparable_companies'] = peers[:5]
        #     else:
        #         # Fallback to sector-based peers
        #         sector = info.get('sector', '')
        #         sector_peers = {
        #             "Technology": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        #             "Financial Services": ["JPM", "BAC", "WFC", "C", "GS"],
        #             "Consumer Cyclical": ["WMT", "TGT", "COST", "HD", "LOW"],
        #             "Healthcare": ["JNJ", "PFE", "MRK", "UNH", "ABBV"],
        #             "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
        #             "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "T"],
        #             "Industrial": ["GE", "HON", "UPS", "CAT", "BA"]
        #         }
        #         bei_data['comparable_companies'] = [c for c in sector_peers.get(sector, [])[:5] if c != symbol]
        # except Exception:
        #     pass
        
        return set_in_cache(cache_key, bei_data)
        
    except Exception as e:
        print(f"Error calculating Brand Equity Index: {e}")
        return {
            'bei_score': 'N/A',
            'components': {},
            'market_position': {},
            'financial_strength': {},
            'growth_momentum': {},
            'brand_stability': {},
            'market_dominance': 'N/A',
            # 'comparable_companies': [],
            'analysis': {},
            # 'recommendations': []
        }
