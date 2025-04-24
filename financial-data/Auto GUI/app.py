import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils import (
    fetch_stock_data,
    fetch_stock_info,
    fetch_financial_data,
    calculate_financial_ratios,
    fetch_company_news,
    format_large_number,
    calculate_brand_equity_index,
    cache
)
# Set page configuration
st.set_page_config(
    page_title="Stock Analysis Tool",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# hide_streamlit_style = """
# <style>
# .css-hi6a2p {padding-top: 0rem;}
# </style>

# """
# st.markdown(hide_streamlit_style, unsafe_allow_html=True)
hide_streamlit_style2 = """
<style>
.stAppHeader {visibility: hidden;}
.stMainBlockContainer {padding-top: 50px}
.st-emotion-cache-kgpedg {padding:0;padding-top:5px;}
</style>

"""
st.markdown(hide_streamlit_style2, unsafe_allow_html=True) 

# Sidebar
with st.sidebar:
    st.header("Stock Selection")
    
    # Default popular stocks
    popular_stocks = {
        "Apple": "AAPL",
        "Microsoft": "MSFT", 
        "Google": "GOOGL",
        "Amazon": "AMZN",
        "Tesla": "TSLA",
        "Meta": "META",
        "Nvidia": "NVDA"
    }
    
    # Stock selection options
    selection_method = st.radio(
        "Choose selection method",
        ["Popular Stocks", "Enter Symbol"]
    )
    
    if selection_method == "Popular Stocks":
        selected_company = st.selectbox(
            "Select a company",
            list(popular_stocks.keys())
        )
        stock_symbol = popular_stocks[selected_company]
    else:
        stock_symbol = st.text_input(
            "Enter stock symbol",
            value="AAPL",
            help="Enter the stock symbol (e.g., AAPL for Apple)"
        ).upper()
    
    # Time period selection
    st.subheader("Time Period")
    period_options = {
        "1 Week": "1wk",
        "1 Month": "1mo",
        "3 Months": "3mo",
        "6 Months": "6mo", 
        "1 Year": "1y",
        "2 Years": "2y",
        "5 Years": "5y"
    }
    
    selected_period = st.select_slider(
        "Select time period",
        options=list(period_options.keys()),
        value="3 Months"
    )
    
    period = period_options[selected_period]
    
    # Chart type selection
    st.subheader("Chart Settings")
    chart_type = st.selectbox(
        "Chart type",
        ["Candlestick", "Line", "OHLC"],
        index=0
    )
    
    # Technical indicators
    st.subheader("Technical Indicators")
    show_ma = st.checkbox("Moving Averages", value=True)
    if show_ma:
        ma_periods = st.multiselect(
            "MA Periods",
            [5, 10, 20, 50, 100, 200],
            default=[20, 50]
        )
    
    show_volume = st.checkbox("Volume", value=True)
    show_rsi = st.checkbox("RSI", value=False)


















def save_to_csv(stock_symbol, stock_info, financial_data, financial_ratios, brand_equity_data, hist_data):
    """
    Save all collected stock data to a single CSV file, appending new data as new rows
    """
    try:
        # Prepare data dictionary
        data = {
            "Symbol": stock_symbol,
            "Company Name": stock_info.get('shortName', 'N/A'),
            "Exchange": stock_info.get('exchange', 'N/A'),
            "Currency": stock_info.get('currency', 'N/A'),
            "Sector": stock_info.get('sector', 'N/A'),
            "Industry": stock_info.get('industry', 'N/A'),
            
            # Price Data
            "Current Price": stock_info.get('currentPrice', hist_data['Close'].iloc[-1] if not hist_data.empty else 'N/A'),
            "Previous Close": stock_info.get('previousClose', 'N/A'),
            "52W High": stock_info.get('fiftyTwoWeekHigh', 'N/A'),
            "52W Low": stock_info.get('fiftyTwoWeekLow', 'N/A'),
            
            # Market Data
            "Market Cap": stock_info.get('marketCap', 'N/A'),
            "Volume": stock_info.get('volume', 'N/A'),
            "Avg Volume": stock_info.get('averageVolume', 'N/A'),
            
            # Financial Metrics
            "Revenue": financial_data.get('totalRevenue', 'N/A'),
            "Gross Profit": financial_data.get('grossProfit', 'N/A'),
            "Operating Income": financial_data.get('operatingIncome', 'N/A'),
            "Net Income": financial_data.get('netIncome', 'N/A'),
            "EPS": financial_data.get('eps', 'N/A'),
            "Total Assets": financial_data.get('totalAssets', 'N/A'),
            "Total Debt": financial_data.get('totalDebt', 'N/A'),
            "Total Cash": financial_data.get('totalCash', 'N/A'),
            
            # Financial Ratios
            "P/E Ratio": financial_ratios.get('pe_ratio', 'N/A'),
            "P/B Ratio": financial_ratios.get('pb_ratio', 'N/A'),
            "P/S Ratio": financial_ratios.get('ps_ratio', 'N/A'),
            "Gross Margin": financial_ratios.get('gross_margin', 'N/A'),
            "Operating Margin": financial_ratios.get('operating_margin', 'N/A'),
            "Net Margin": financial_ratios.get('net_margin', 'N/A'),
            "ROE": financial_ratios.get('roe', 'N/A'),
            "ROA": financial_ratios.get('roa', 'N/A'),
            "Revenue Growth": financial_ratios.get('revenue_growth', 'N/A'),
            "EPS Growth": financial_ratios.get('eps_growth', 'N/A'),
            "Dividend Yield": financial_ratios.get('dividend_yield', 'N/A'),
            
            # Brand Equity Metrics
            "BEI Score": brand_equity_data.get('bei_score', 'N/A'),
            "Market Dominance": brand_equity_data.get('market_dominance', 'N/A'),
            "Market Position Score": brand_equity_data.get('components', {}).get('market_position_score', 'N/A'),
            "Financial Strength Score": brand_equity_data.get('components', {}).get('financial_strength_score', 'N/A'),
            "Growth Momentum Score": brand_equity_data.get('components', {}).get('growth_momentum_score', 'N/A'),
            "Brand Stability Score": brand_equity_data.get('components', {}).get('brand_stability_score', 'N/A')
        }
        
        # Create DataFrame from the new data
        new_data_df = pd.DataFrame([data])
        
        # Define the filename
        filename = 'stock_analysis_data.csv'
        
        try:
            # Try to read existing CSV file
            existing_df = pd.read_csv(filename)
            # Append new data
            updated_df = pd.concat([existing_df, new_data_df], ignore_index=True)
        except FileNotFoundError:
            # If file doesn't exist, use new data
            updated_df = new_data_df
        
        # Save to CSV
        updated_df.to_csv(filename, index=False)
        
        # Show success message with download button
        st.success(f"Data saved to {filename}")
        
        # Create download button
        with open(filename, 'rb') as f:
            st.download_button(
                label="Download Stock Analysis Data",
                data=f,
                file_name=filename,
                mime='text/csv'
            )
            
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")












# Main content
try:
    with st.spinner(f"Loading data for {stock_symbol}..."):
        # Fetch stock data
        hist_data = fetch_stock_data(stock_symbol, period)
        
        if hist_data.empty:
            st.error(f"No data found for symbol {stock_symbol}. Please verify the stock symbol.")
            st.stop()
        
        # Get stock info
        stock_info = fetch_stock_info(stock_symbol)
        
        # Get financial data
        financial_data = fetch_financial_data(stock_symbol)
        
        # Calculate financial ratios
        financial_ratios = calculate_financial_ratios(stock_symbol)
        
        # Calculate Brand Equity Index
        brand_equity_data = calculate_brand_equity_index(stock_symbol)

        save_to_csv(stock_symbol, stock_info, financial_data, financial_ratios, brand_equity_data, hist_data)

    print(cache)
    
    # Company Header Section
    # st.header("Stock Analysis Tool")
    col1, col2 = st.columns([2, 3])

    with col1:
        # st.header("Stock Analysis Tool")

        # Company name and current price
        company_name = stock_info.get('shortName', stock_symbol)
        st.header(company_name)
        
        # Current price and daily change
        current_price = stock_info.get('currentPrice', hist_data['Close'].iloc[-1])
        previous_close = stock_info.get('previousClose', 0)
        price_change = current_price - previous_close
        price_change_pct = (price_change / previous_close) * 100 if previous_close else 0
        
        change_color = "green" if price_change >= 0 else "red"
        change_icon = "↑" if price_change >= 0 else "↓"
        
        st.markdown(f"""
        <h2 style='margin-bottom:0;'>₹{current_price:.2f}</h2>
        <p style='color:{change_color};font-size:1.2rem;margin-top:0;'>
            {change_icon} ₹{abs(price_change):.2f} ({price_change_pct:.2f}%)
        </p>
        """, unsafe_allow_html=True)
        
        # Exchange and currency
        exchange = stock_info.get('exchange', 'N/A')
        currency = stock_info.get('currency', 'USD')
        st.markdown(f"**Exchange:** {exchange} • Currency: {currency}")
    
    with col2:
        st.header("")
        # st.header("")
        # Key metrics table
        metrics_data = {
            "Market Cap": format_large_number(stock_info.get('marketCap', 'N/A')),
            "52W High": f"₹{stock_info.get('fiftyTwoWeekHigh', 'N/A')}",
            "52W Low": f"₹{stock_info.get('fiftyTwoWeekLow', 'N/A')}",
            "P/E Ratio": f"{stock_info.get('trailingPE', 'N/A'):.2f}" if stock_info.get('trailingPE') else 'N/A',
            "EPS": f"₹{stock_info.get('trailingEps', 'N/A'):.2f}" if stock_info.get('trailingEps') else 'N/A',
            "Dividend Yield": f"{stock_info.get('dividendYield', 0) * 100:.2f}%" if stock_info.get('dividendYield') else 'N/A',
            "Volume": format_large_number(stock_info.get('volume', 'N/A')),
            "Avg Volume": format_large_number(stock_info.get('averageVolume', 'N/A'))
        }
        
        # Create a 2x4 layout for metrics
        metrics_cols = st.columns(4)
        idx = 0
        for metric, value in metrics_data.items():
            with metrics_cols[idx % 4]:
                st.metric(metric, value)
            idx += 1
    
    # st.markdown("---")
    
    # Price Chart
    # st.subheader(f"{chart_type} Chart - {selected_period}")
    
    # Create the base figure
    if chart_type == "Candlestick":
        fig = go.Figure(data=[go.Candlestick(
            x=hist_data.index,
            open=hist_data['Open'],
            high=hist_data['High'],
            low=hist_data['Low'],
            close=hist_data['Close'],
            name='Price'
        )])
    elif chart_type == "OHLC":
        fig = go.Figure(data=[go.Ohlc(
            x=hist_data.index,
            open=hist_data['Open'],
            high=hist_data['High'],
            low=hist_data['Low'],
            close=hist_data['Close'],
            name='Price'
        )])
    else:  # Line chart
        fig = go.Figure(data=[go.Scatter(
            x=hist_data.index,
            y=hist_data['Close'],
            mode='lines',
            name='Close Price',
            line=dict(color='#00BFFF', width=2)
        )])
    
    # Add Moving Averages if selected
    if show_ma:
        for period in ma_periods:
            ma_col = f'MA_{period}'
            hist_data[ma_col] = hist_data['Close'].rolling(window=period).mean()
            fig.add_trace(go.Scatter(
                x=hist_data.index,
                y=hist_data[ma_col],
                mode='lines',
                name=f'{period}-day MA',
                line=dict(width=1)
            ))
    
    # Add RSI if selected
    if show_rsi:
        delta = hist_data['Close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = ema_up / ema_down
        hist_data['RSI'] = 100 - (100 / (1 + rs))
        
        # Create a secondary y-axis for RSI
        fig.add_trace(go.Scatter(
            x=hist_data.index,
            y=hist_data['RSI'],
            mode='lines',
            name='RSI',
            line=dict(color='yellow', width=1),
            yaxis='y2'
        ))
        
        # Add RSI reference lines (30 and 70)
        fig.add_shape(type="line", x0=hist_data.index[0], x1=hist_data.index[-1], y0=30, y1=30,
                     line=dict(color="red", width=1, dash="dash"), yref='y2')
        fig.add_shape(type="line", x0=hist_data.index[0], x1=hist_data.index[-1], y0=70, y1=70,
                     line=dict(color="red", width=1, dash="dash"), yref='y2')
    
    # Update layout based on selected options
    layout_dict = dict(
        title=f"{company_name} ({stock_symbol}) Stock Price",
        xaxis=dict(title="Date", rangeslider=dict(visible=False)),
        yaxis=dict(title="Price (₹)", side="left"),
        template="plotly_dark",
        height=600,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        autosize=True
    )
    
    # Add RSI axis if selected
    if show_rsi:
        layout_dict.update({
            "yaxis2": dict(
                title="RSI",
                range=[0, 100],
                side="right",
                overlaying="y",
                showgrid=False,
                title_standoff=15
            )
        })
    
    fig.update_layout(**layout_dict)
    
    # Create main content sections
    # st.markdown("---")
    
    # Create main tabs
    tabs = st.tabs([
        "📊 Price Analysis",
        "💰 Financials",
        "📈 Brand Equity Index",
        "ℹ️ Company Info"
    ])
    
    with tabs[0]:  # Price Analysis
        st.plotly_chart(fig, use_container_width=True)
        
        # Volume Chart if selected
        if show_volume:
            st.subheader("Volume")
            volume_fig = px.bar(
                hist_data,
                x=hist_data.index,
                y='Volume',
                color_discrete_sequence=['rgba(0, 191, 255, 0.7)']
            )
            volume_fig.update_layout(
                template="plotly_dark",
                height=300,
                margin=dict(l=50, r=50, t=20, b=50),
                yaxis=dict(title="Volume"),
                autosize=True
            )
            st.plotly_chart(volume_fig, use_container_width=True)
    
    with tabs[1]:  # Financials
        fin_tabs = st.tabs(["Key Financials", "Ratios & Metrics"])
        
        with fin_tabs[0]:
            # Key financial data
            if financial_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Income Statement Highlights")
                    income_data = {
                        "Revenue": format_large_number(financial_data.get('totalRevenue', 'N/A')),
                        "Gross Profit": format_large_number(financial_data.get('grossProfit', 'N/A')),
                        "Operating Income": format_large_number(financial_data.get('operatingIncome', 'N/A')),
                        "Net Income": format_large_number(financial_data.get('netIncome', 'N/A')),
                        "EPS": f"₹{financial_data.get('eps', 'N/A')}"
                    }
                    income_df = pd.DataFrame(list(income_data.items()), columns=['Metric', 'Value'])
                    st.table(income_df)
                
                with col2:
                    st.markdown("### Balance Sheet Highlights")
                    balance_data = {
                        "Total Assets": format_large_number(financial_data.get('totalAssets', 'N/A')),
                        "Total Debt": format_large_number(financial_data.get('totalDebt', 'N/A')),
                        "Cash & Equivalents": format_large_number(financial_data.get('totalCash', 'N/A')),
                        "Total Liabilities": format_large_number(financial_data.get('totalLiab', 'N/A')),
                        "Stockholders' Equity": format_large_number(financial_data.get('totalStockholderEquity', 'N/A'))
                    }
                    balance_df = pd.DataFrame(list(balance_data.items()), columns=['Metric', 'Value'])
                    st.table(balance_df)
            else:
                st.info("Financial data not available for this stock.")
        
        with fin_tabs[1]:
            # Financial ratios and metrics
            if financial_ratios:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("### Valuation Metrics")
                    valuation_data = {
                        "P/E Ratio": f"{financial_ratios.get('pe_ratio', 'N/A')}",
                        "P/B Ratio": f"{financial_ratios.get('pb_ratio', 'N/A')}",
                        "P/S Ratio": f"{financial_ratios.get('ps_ratio', 'N/A')}",
                        "EV/EBITDA": f"{financial_ratios.get('ev_to_ebitda', 'N/A')}"
                    }
                    valuation_df = pd.DataFrame(list(valuation_data.items()), columns=['Metric', 'Value'])
                    st.table(valuation_df)
                
                with col2:
                    st.markdown("### Profitability Metrics")
                    profit_data = {
                        "Gross Margin": f"{financial_ratios.get('gross_margin', 'N/A')}%",
                        "Operating Margin": f"{financial_ratios.get('operating_margin', 'N/A')}%",
                        "Net Profit Margin": f"{financial_ratios.get('net_margin', 'N/A')}%",
                        "ROE": f"{financial_ratios.get('roe', 'N/A')}%",
                        "ROA": f"{financial_ratios.get('roa', 'N/A')}%"
                    }
                    profit_df = pd.DataFrame(list(profit_data.items()), columns=['Metric', 'Value'])
                    st.table(profit_df)
                
                with col3:
                    st.markdown("### Growth & Dividend")
                    growth_data = {
                        "Revenue Growth (YoY)": f"{financial_ratios.get('revenue_growth', 'N/A')}%",
                        "EPS Growth (YoY)": f"{financial_ratios.get('eps_growth', 'N/A')}%",
                        "Dividend Yield": f"{financial_ratios.get('dividend_yield', 'N/A')}%",
                        "Payout Ratio": f"{financial_ratios.get('payout_ratio', 'N/A')}%"
                    }
                    growth_df = pd.DataFrame(list(growth_data.items()), columns=['Metric', 'Value'])
                    st.table(growth_df)
            else:
                st.info("Financial ratios not available for this stock.")
    
    with tabs[2]:  # Brand Equity Index
        st.markdown("### Brand Equity Index (BEI)")
        st.markdown("""
        The Brand Equity Index is a comprehensive metric that evaluates a company's brand strength 
        across four key dimensions:
        1. **Market Position (40%)**: How the market values the company relative to its fundamentals
        2. **Financial Strength (30%)**: Company's operational efficiency and profitability
        3. **Growth & Momentum (20%)**: Growth trajectory and market momentum
        4. **Brand Stability (10%)**: Long-term stability and market presence
        """)
        
        # Show BEI Score with gauge chart
        if brand_equity_data and brand_equity_data.get('bei_score', 'N/A') != 'N/A':
            bei_score = brand_equity_data.get('bei_score', 0)
            market_dominance = brand_equity_data.get('market_dominance', 'N/A')
            
            # Create a gauge chart for BEI score
            gauge_fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=bei_score,
                title={'text': "Brand Equity Index"},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1},
                    'bar': {'color': '#00BFFF'},
                    'steps': [
                        {'range': [0, 20], 'color': '#FF9999'},
                        {'range': [20, 40], 'color': '#FFCC99'},
                        {'range': [40, 60], 'color': '#FFFF99'},
                        {'range': [60, 80], 'color': '#99FF99'},
                        {'range': [80, 100], 'color': '#99FFFF'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 3},
                        'thickness': 0.8,
                        'value': bei_score
                    }
                }
            ))
            gauge_fig.update_layout(
                template="plotly_dark",
                height=300,
                margin=dict(l=30, r=30, t=50, b=30),
                autosize=True
            )
            
            # Create columns for the main content
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("### Overall Brand Assessment")
                st.markdown(f"**Brand Strength:** {market_dominance}")
                st.markdown(f"**BEI Score:** {bei_score}/100")
                
                # Show component scores
                st.markdown("### Component Scores")
                components = brand_equity_data.get('components', {})
                
                # Create component score bars
                components_fig = go.Figure()
                
                component_names = {
                    'market_position_score': 'Market Position (40%)',
                    'financial_strength_score': 'Financial Strength (30%)',
                    'growth_momentum_score': 'Growth & Momentum (20%)',
                    'brand_stability_score': 'Brand Stability (10%)'
                }
                
                max_scores = {
                    'market_position_score': 40,
                    'financial_strength_score': 30,
                    'growth_momentum_score': 20,
                    'brand_stability_score': 10
                }
                
                for comp_key, comp_name in component_names.items():
                    score = components.get(comp_key, 0)
                    max_score = max_scores[comp_key]
                    components_fig.add_trace(go.Bar(
                        x=[score],
                        y=[comp_name],
                        orientation='h',
                        name=comp_name,
                        text=[f"{score:.1f}/{max_score}"],
                        textposition='auto',
                    ))
                
                components_fig.update_layout(
                    template="plotly_dark",
                    height=200,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False,
                    xaxis_title="Score",
                    yaxis_title="",
                    bargap=0.15,
                    xaxis=dict(range=[0, 40])  # Max component score is 40
                )
                
                st.plotly_chart(components_fig, use_container_width=True)
            
            # with col2:
                st.plotly_chart(gauge_fig, use_container_width=True)
                
                # SWOT Analysis
                st.markdown("### SWOT Analysis")
                analysis = brand_equity_data.get('analysis', {})
                
                swot_cols = st.columns(3)
                
                with swot_cols[0]:
                    st.markdown("**💪 Strengths**")
                    if len(analysis.get('strengths', [])) > 0:
                        for strength in analysis.get('strengths', []):
                            st.markdown(f"- {strength}")
                    else:
                        st.markdown(f"None")
                    
                    st.markdown("**🎯 Opportunities**")
                    if len(analysis.get('opportunities', [])) > 0:
                        for opportunity in analysis.get('opportunities', []):
                            st.markdown(f"- {opportunity}")
                    else:
                        st.markdown(f"None")
                
                with swot_cols[2]:
                    st.markdown("**⚠️ Weaknesses**")
                    if len(analysis.get('weaknesses', [])) > 0:
                        for weakness in analysis.get('weaknesses', []):
                            st.markdown(f"- {weakness}")
                    else:
                        st.markdown(f"None")
                    
                    st.markdown("**⚡ Threats**")
                    if len(analysis.get('threats', [])) > 0:
                        for threat in analysis.get('threats', []):
                            st.markdown(f"- {threat}")
                    else:
                        st.markdown(f"None")
            
            # Detailed Metrics
            st.markdown("### Detailed Metrics")
            
            # Create tabs for different metric categories
            metric_tabs = st.tabs([
                "Market Position", 
                "Financial Strength",
                "Growth & Momentum",
                "Brand Stability"
            ])
            
            with metric_tabs[0]:
                market_position = brand_equity_data.get('market_position', {})
                st.markdown("#### Market Position Metrics")
                market_metrics = {
                    "Market-to-Revenue Ratio": market_position.get('market_to_revenue', 'N/A'),
                    "EV/EBITDA": market_position.get('ev_to_ebitda', 'N/A'),
                    "Price-to-Sales": market_position.get('price_to_sales', 'N/A')
                }
                market_df = pd.DataFrame(list(market_metrics.items()), columns=['Metric', 'Value'])
                st.table(market_df)
            
            with metric_tabs[1]:
                financial_strength = brand_equity_data.get('financial_strength', {})
                st.markdown("#### Financial Strength Metrics")
                financial_metrics = {
                    "Gross Margin": f"{financial_strength.get('gross_margin', 'N/A')}%",
                    "Operating Margin": f"{financial_strength.get('operating_margin', 'N/A')}%",
                    "Net Margin": f"{financial_strength.get('net_margin', 'N/A')}%"
                }
                financial_df = pd.DataFrame(list(financial_metrics.items()), columns=['Metric', 'Value'])
                st.table(financial_df)
            
            with metric_tabs[2]:
                growth_momentum = brand_equity_data.get('growth_momentum', {})
                st.markdown("#### Growth & Momentum Metrics")
                growth_metrics = {
                    "Revenue Growth": f"{growth_momentum.get('revenue_growth', 'N/A')}%",
                    "Price Momentum": f"{growth_momentum.get('price_momentum', 'N/A')}%"
                }
                growth_df = pd.DataFrame(list(growth_metrics.items()), columns=['Metric', 'Value'])
                st.table(growth_df)
            
            with metric_tabs[3]:
                brand_stability = brand_equity_data.get('brand_stability', {})
                st.markdown("#### Brand Stability Metrics")
                stability_metrics = {
                    "Company Age (Years)": brand_stability.get('company_age', 'N/A'),
                    "Dividend Yield": f"{brand_stability.get('dividend_yield', 'N/A')}%",
                    "Price Volatility": f"{brand_stability.get('volatility', 'N/A')}%"
                }
                stability_df = pd.DataFrame(list(stability_metrics.items()), columns=['Metric', 'Value'])
                st.table(stability_df)
            
            # Strategic Recommendations
            # st.markdown("### Strategic Recommendations")
            # recommendations = brand_equity_data.get('recommendations', [])
            # for i, rec in enumerate(recommendations, 1):
            #     st.markdown(f"{i}. {rec}")
            
            # Comparable Companies
            # st.markdown("### Industry Peers")
            # comparable_companies = brand_equity_data.get('comparable_companies', [])
            # if comparable_companies:
                # st.markdown("Compare brand equity with these industry peers:")
                # peers_cols = st.columns(min(5, len(comparable_companies)))
                # for i, symbol in enumerate(comparable_companies):
                    # with peers_cols[i]:
                        # st.markdown(f"**{symbol}**")
                        # try:
                            # peer_info = yf.Ticker(symbol).info
                            # st.markdown(f"_{peer_info.get('shortName', symbol)}_")
                        # except:
                            # pass
        else:
            st.info("Brand Equity data not available for this stock.")
    
    with tabs[3]:  # Company Info
        st.markdown("### Company Profile")
        st.markdown(f"**Sector:** {stock_info.get('sector', 'N/A')}")
        st.markdown(f"**Industry:** {stock_info.get('industry', 'N/A')}")
        st.markdown(f"**Website:** {stock_info.get('website', 'N/A')}")
        st.markdown(f"**Full-Time Employees:** {format_large_number(stock_info.get('fullTimeEmployees', 'N/A'))}")
        
        business_summary = stock_info.get('longBusinessSummary', 'No information available.')
        st.markdown("#### Business Summary")
        st.markdown(business_summary)
        
        # Get company news
        news = fetch_company_news(stock_symbol)
        if news:
            st.markdown("### Recent News")
            for article in news:
                st.markdown(f"**{article['title']}** - {article['date']}")
                st.markdown(f"{article['summary'][:200]}...")
                if article.get('link'):
                    st.markdown(f"[Read more]({article['link']})")
                st.markdown("---")
        else:
            st.info("No recent news available.")
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.markdown("Please try a different stock symbol or check back later.")
