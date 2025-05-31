import feedparser
import requests
import smtplib
import schedule
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
import re
import json

class FinancialNewsletterBot:
    def __init__(self):
        # Email configuration
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('EMAIL_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        
        # Premium PE/VC focused news sources
        self.financial_feeds = {
            'Private Equity Wire': 'https://www.privateequitywire.co.uk/feed/',
            'Financial Times': 'https://www.ft.com/rss/home/us',
            'Wall Street Journal': 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
            'Bloomberg Markets': 'https://feeds.bloomberg.com/markets/news.rss',
            'Bloomberg Business': 'https://feeds.bloomberg.com/politics/news.rss',
            'Private Capital Journal': 'https://www.privatecapitaljournal.com/feed/',
            'Private Equity International': 'https://www.privateequityinternational.com/feed/',
            'Reuters Business': 'https://feeds.reuters.com/reuters/businessNews',
            'Reuters Markets': 'https://feeds.reuters.com/reuters/marketsNews',
            'PE Hub': 'https://www.pehub.com/feed/',
            'PitchBook News': 'https://pitchbook.com/rss/news',
            'TechCrunch Startups': 'https://techcrunch.com/category/startups/feed/',
            'CNBC': 'https://www.cnbc.com/id/100003114/device/rss/rss.html'
        }
        
        # PE/VC relevant market indicators (enhanced for global view)
        self.market_symbols = ['SPY', 'QQQ', 'VTI', 'EFA', 'EEM', 'VNQ', 'TNX', 'GLD', 'DXY', 'CL=F']
        
        # Comprehensive PE/VC keywords for better filtering
        self.pe_vc_keywords = [
            # Private Equity
            'private equity', 'pe firm', 'buyout', 'lbo', 'leveraged buyout',
            'management buyout', 'mbo', 'secondary buyout', 'take private',
            'financial sponsor', 'sponsor', 'portfolio company', 'portco',
            
            # Venture Capital
            'venture capital', 'vc', 'startup', 'funding round', 'series a', 'series b', 'series c',
            'seed funding', 'pre-seed', 'bridge round', 'down round', 'up round',
            'unicorn', 'decacorn', 'venture funding', 'early stage', 'late stage',
            
            # Growth & Capital
            'growth capital', 'growth equity', 'mezzanine', 'expansion capital',
            'recapitalization', 'dividend recap', 'refinancing',
            
            # Fund Operations
            'fund raising', 'fundraising', 'capital raise', 'fund size', 'first close',
            'final close', 'limited partners', 'lp', 'gp', 'general partner',
            'management fee', 'carried interest', 'carry', 'hurdle rate',
            'dry powder', 'deployment', 'vintage year',
            
            # Exits & Returns
            'exit strategy', 'ipo', 'acquisition', 'merger', 'm&a', 'deal', 'investment',
            'trade sale', 'strategic sale', 'secondary sale', 'continuation fund',
            'irr', 'multiple', 'tvpi', 'dpi', 'rvpi',
            
            # Major PE/VC Firms (ScopeLP Focus)
            '26north', 'abry', 'accel kkr', 'adia', 'advent', 'aea', 'american industrial partners',
            'alpine', 'american securities', 'antin infra', 'apax', 'apollo', 'ares',
            'arlington capital', 'arcline', 'bain', 'baypine', 'bc partners', 'bdt', 'msd',
            'berkshire partners', 'blackstone', 'brightstar', 'butterfly equity', 'calera',
            'carlyle', 'ccmp', 'cd&r', 'centerbridge', 'cerberus', 'charlesbank', 'cinven',
            'clearlake', 'cornell capital', 'court square', 'cvc', 'elliott', 'eqt',
            'fairfax', 'fortress', 'francisco', 'gamut', 'general atlantic', 'genstar',
            'gi partners', 'golden gate', 'greenbriar', 'gsam', 'gtcr', 'h&f', 'haveli',
            'harvest partners', 'hg', 'hig', 'hps', 'insight partners', 'kelso', 'kkr',
            'kohlberg', 'kps', 'l catterton', 'leonard green', 'lindsay goldberg', 'littlejohn',
            'lone star', 'madison dearborn', 'mubadala', 'new mountain', 'oak hill', 'oaktree',
            'odyssey', 'olympus', 'omers', 'one rock', 'onex', 'pai', 'parthenon',
            'partners group', 'patient square', 'permira', 'platinum', 'pritzker private capital',
            'providence', 'reverence', 'rhône group', 'roark', 'searchlight', 'silver lake',
            'siris capital', 'sk capital', 'stone canyon', 'stone point', 'stonepeak',
            'summit partners', 'svp capital', 'symphony', 'ta associates', 'thoma bravo',
            'thl', 'tjc', 'towerbrook', 'tpg', 'tpg real estate', 'truelink', 'tsg consumer',
            'veritas', 'vista', 'warburg pincus', 'welsh carson'
        ]
    
    def get_market_data(self):
        """Fetch closing prices from the last trading date with YTD performance"""
        try:
            market_data = {}
            print("📊 Fetching closing prices and YTD performance...")
            
            for symbol in self.market_symbols:
                try:
                    # Get 1 year of data to calculate YTD performance accurately
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = requests.get(url, headers=headers, timeout=15)
                    print(f"📈 Fetching {symbol}: Status {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                            result = data['chart']['result'][0]
                            
                            # Get trading timestamps and closing prices
                            timestamps = result.get('timestamp', [])
                            prices_data = result.get('indicators', {}).get('quote', [{}])[0]
                            close_prices = prices_data.get('close', [])
                            
                            if timestamps and close_prices:
                                # Find the last two valid trading days for comparison
                                last_close = None
                                previous_close = None
                                last_trading_date = None
                                ytd_start_price = None
                                
                                # Work backwards to find the most recent closing prices
                                for i in range(len(close_prices) - 1, -1, -1):
                                    if close_prices[i] is not None:
                                        if last_close is None:
                                            last_close = close_prices[i]
                                            last_trading_date = datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d')
                                        elif previous_close is None:
                                            previous_close = close_prices[i]
                                            break
                                
                                # Find YTD start price (first trading day of current year)
                                current_year = datetime.now().year
                                jan_1_timestamp = datetime(current_year, 1, 1).timestamp()
                                
                                # Look for first trading day in January
                                for i, ts in enumerate(timestamps):
                                    if ts >= jan_1_timestamp and close_prices[i] is not None:
                                        ytd_start_price = close_prices[i]
                                        ytd_start_date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                                        break
                                
                                if last_close and previous_close:
                                    change = last_close - previous_close
                                    change_pct = (change / previous_close * 100) if previous_close != 0 else 0
                                    
                                    # Calculate YTD performance
                                    ytd_pct = 0
                                    if ytd_start_price and last_close:
                                        ytd_pct = ((last_close - ytd_start_price) / ytd_start_price * 100)
                                        print(f"📊 {symbol} YTD: ${ytd_start_price:.2f} → ${last_close:.2f} = {ytd_pct:+.1f}%")
                                    
                                    market_data[symbol] = {
                                        'price': float(last_close),
                                        'change': float(change),
                                        'change_pct': float(change_pct),
                                        'ytd_pct': float(ytd_pct),
                                        'trading_date': last_trading_date
                                    }
                                    print(f"✅ {symbol}: ${last_close:.2f} ({change_pct:+.1f}% daily, {ytd_pct:+.1f}% YTD) - Close {last_trading_date}")
                                else:
                                    print(f"⚠️ {symbol}: Could not find valid closing prices")
                            else:
                                print(f"⚠️ {symbol}: No price history available")
                        else:
                            print(f"⚠️ {symbol}: Invalid response structure")
                    else:
                        print(f"❌ {symbol}: HTTP {response.status_code}")
                    
                    time.sleep(0.4)  # Slightly longer delay for larger data requests
                    
                except Exception as e:
                    print(f"❌ Error fetching {symbol}: {e}")
                    continue
            
            print(f"📊 Successfully fetched closing data with YTD for {len(market_data)} symbols")
            return market_data
            
        except Exception as e:
            print(f"❌ Error in get_market_data: {e}")
            return {}
    

    
    def fetch_financial_news(self, max_articles=30):
        """Fetch PE/VC focused financial news from premium sources"""
        all_articles = []
        
        for source_name, feed_url in self.financial_feeds.items():
            try:
                # Add user agent to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Parse RSS with custom headers
                feed = feedparser.parse(feed_url, request_headers=headers)
                
                if feed.entries:
                    print(f"✅ Fetched {len(feed.entries)} articles from {source_name}")
                    
                    for entry in feed.entries[:10]:  # More articles for better filtering
                        # Clean and format the summary
                        summary = self.clean_summary(entry.get('summary', entry.title))
                        
                        # Filter for PE/VC relevance (more lenient for specialized sources)
                        if self.is_pe_vc_relevant(entry.title + ' ' + summary, source_name):
                            article = {
                                'title': entry.title,
                                'summary': summary,
                                'link': entry.link,
                                'source': source_name,
                                'published': entry.get('published', 'Recent'),
                                'category': self.categorize_article(entry.title + ' ' + summary),
                                'priority': self.get_source_priority(source_name)
                            }
                            all_articles.append(article)
                else:
                    print(f"⚠️ No articles found from {source_name}")
                    
                time.sleep(0.8)  # Slightly longer delay for premium sources
                
            except Exception as e:
                print(f"❌ Error fetching from {source_name}: {e}")
                # Try alternative RSS paths for some sources
                alternative_url = self.get_alternative_rss(source_name, feed_url)
                if alternative_url:
                    try:
                        feed = feedparser.parse(alternative_url, request_headers=headers)
                        print(f"✅ Using alternative RSS for {source_name}")
                        # Process alternative feed...
                    except:
                        print(f"❌ Alternative RSS also failed for {source_name}")
        
        # Sort by priority and PE/VC relevance, remove duplicates
        unique_articles = self.remove_duplicates(all_articles)
        pe_vc_articles = self.prioritize_pe_vc_content(unique_articles)
        categorized_articles = self.organize_by_category(pe_vc_articles[:max_articles])
        
        return categorized_articles
    
    def get_alternative_rss(self, source_name, original_url):
        """Get alternative RSS URLs for sources that might have different paths"""
        alternatives = {
            'Private Equity Wire': 'https://www.privateequitywire.co.uk/rss',
            'Private Capital Journal': 'https://privatecapitaljournal.com/rss',
            'Private Equity International': 'https://privateequityinternational.com/rss',
            'Financial Times': 'https://www.ft.com/rss/companies',
            'Wall Street Journal': 'https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml',
            'Bloomberg Markets': 'https://feeds.bloomberg.com/bpolitics/news.rss',
            'Bloomberg Business': 'https://feeds.bloomberg.com/technology/news.rss',
            'Reuters Business': 'https://feeds.reuters.com/reuters/companyNews',
            'Reuters Markets': 'https://feeds.reuters.com/reuters/JPbusiness',
            'CNBC': 'https://www.cnbc.com/id/100727362/device/rss/rss.html'
        }
        return alternatives.get(source_name)
    
    def get_source_priority(self, source_name):
        """Assign priority scores to sources (higher = more important)"""
        priority_map = {
            'Private Equity Wire': 10,
            'Private Equity International': 10,
            'Private Capital Journal': 10,
            'Financial Times': 9,
            'Wall Street Journal': 9,
            'Bloomberg Markets': 9,
            'Bloomberg Business': 9,
            'Reuters Business': 8,
            'Reuters Markets': 8,
            'PE Hub': 8,
            'PitchBook News': 8,
            'CNBC': 7,
            'TechCrunch Startups': 6
        }
        return priority_map.get(source_name, 5)
    
    def clean_summary(self, summary):
        """Clean HTML tags and format summary"""
        if not summary:
            return ""
        
        # Remove HTML tags
        clean = re.sub('<.*?>', '', summary)
        # Remove extra whitespace
        clean = ' '.join(clean.split())
        # Limit length
        if len(clean) > 300:
            clean = clean[:300] + "..."
        
        return clean
    
    def is_pe_vc_relevant(self, text, source_name):
        """Check if article is relevant to PE/VC (more lenient for specialized sources)"""
        text_lower = text.lower()
        
        # Specialized PE/VC sources are always relevant
        specialized_sources = ['Private Equity Wire', 'Private Equity International', 'Private Capital Journal', 'PE Hub']
        if source_name in specialized_sources:
            return True
        
        # For general sources, must contain PE/VC keywords
        pe_vc_match = any(keyword in text_lower for keyword in self.pe_vc_keywords)
        
        # Additional PE/VC terms for broader matching
        additional_terms = [
            'portfolio company', 'portco', 'growth capital', 'growth equity',
            'limited partners', 'lp', 'gp', 'general partner', 'fund manager',
            'dry powder', 'carried interest', 'management fee', 'irr',
            'sponsor', 'financial sponsor', 'buyout firm', 'investment firm'
        ]
        additional_match = any(term in text_lower for term in additional_terms)
        
        # Exclude hedge fund and crypto content
        exclude_keywords = [
            'hedge fund', 'hedge funds', 'cryptocurrency', 'crypto', 'bitcoin', 'ethereum',
            'forex', 'currency trading', 'commodity trading', 'derivatives', 'short selling'
        ]
        exclude_match = any(keyword in text_lower for keyword in exclude_keywords)
        
        return (pe_vc_match or additional_match) and not exclude_match
    
    def categorize_article(self, text):
        """Categorize articles with enhanced structure"""
        text_lower = text.lower()
        
        # Global Markets (broad financial markets, not PE/VC specific)
        if any(word in text_lower for word in ['stock market', 'trading', 'index', 'bond market', 'commodity', 'currency', 'forex', 'fed', 'federal reserve', 'central bank', 'interest rate', 'inflation', 'gdp', 'economic data', 'treasury', 'yields']):
            return 'Global Markets'
        
        # Private Equity deals and buyouts
        elif any(word in text_lower for word in ['buyout', 'lbo', 'leveraged buyout', 'take private', 'private equity', 'pe firm', 'portfolio company acquisition']):
            return 'Private Equity'
        
        # Venture Capital funding rounds
        elif any(word in text_lower for word in ['venture capital', 'vc', 'startup funding', 'series a', 'series b', 'series c', 'seed funding', 'pre-seed', 'growth round']):
            return 'Venture Capital'
        
        # Private Credit and direct lending
        elif any(word in text_lower for word in ['private credit', 'direct lending', 'credit fund', 'debt fund', 'mezzanine', 'bdc', 'business development company', 'private debt', 'credit strategy']):
            return 'Private Credit'
        
        # IPOs and public offerings
        elif any(word in text_lower for word in ['ipo', 'public offering', 'listing', 'debut', 'going public', 'spac']):
            return 'IPOs'
        
        # Fund raising (PE/VC/Credit fund raises, NOT company fundraising)
        elif any(word in text_lower for word in ['fund raising', 'fund close', 'limited partners', 'lp', 'fund launch', 'first close', 'final close', 'fund of funds', 'pension fund', 'endowment', 'sovereign wealth']) and not any(word in text_lower for word in ['startup', 'company raises', 'series', 'funding round']):
            return 'Fundraising'
        
        # Bankruptcy and distressed situations
        elif any(word in text_lower for word in ['bankruptcy', 'chapter 11', 'distressed', 'restructuring', 'liquidation', 'insolvency', 'creditor', 'debtor']):
            return 'Bankruptcy'
        
        # PE Secondaries market
        elif any(word in text_lower for word in ['secondary', 'secondaries', 'continuation fund', 'gp-led', 'lp-led', 'process sale', 'portfolio sale']):
            return 'PE Secondaries'
        
        # General deal activity defaults to PE
        elif any(word in text_lower for word in ['m&a', 'merger', 'acquisition', 'takeover', 'deal']):
            return 'Private Equity'
        
        else:
            return 'Global Markets'  # Default to markets section
    
    def remove_duplicates(self, articles):
        """Remove duplicate articles based on title similarity"""
        unique_articles = []
        seen_titles = set()
        
        for article in articles:
            # Create a simplified title for comparison
            simple_title = re.sub(r'[^\w\s]', '', article['title'].lower())
            simple_title = ' '.join(simple_title.split()[:5])  # First 5 words
            
            if simple_title not in seen_titles:
                seen_titles.add(simple_title)
                unique_articles.append(article)
        
        return unique_articles
    
    def organize_by_category(self, articles):
        """Organize articles by category"""
        categories = {}
        for article in articles:
            category = article['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(article)
        
        return categories
    
    def prioritize_pe_vc_content(self, articles):
        """Sort articles by PE/VC relevance score and source priority"""
        def pe_vc_score(article):
            text = (article['title'] + ' ' + article['summary']).lower()
            score = 0
            
            # Source priority weight
            score += article.get('priority', 5) * 2
            
            # High priority keywords
            high_priority = [
                'private equity', 'venture capital', 'buyout', 'funding round', 'ipo', 'acquisition',
                'series a', 'series b', 'series c', 'growth capital', 'lbo'
            ]
            score += sum(8 for keyword in high_priority if keyword in text)
            
            # Medium priority keywords  
            medium_priority = [
                'investment', 'startup', 'portfolio', 'exit', 'valuation', 'fund', 'sponsor'
            ]
            score += sum(4 for keyword in medium_priority if keyword in text)
            
            # PE/VC firm names (ScopeLP monitoring list)
            scopelp_firms = [
                '26north', 'abry', 'accel kkr', 'adia', 'advent', 'aea', 'american industrial partners',
                'alpine', 'american securities', 'antin infra', 'apax', 'apollo', 'ares',
                'arlington capital', 'arcline', 'bain', 'baypine', 'bc partners', 'bdt', 'msd',
                'berkshire partners', 'blackstone', 'brightstar', 'butterfly equity', 'calera',
                'carlyle', 'ccmp', 'cd&r', 'centerbridge', 'cerberus', 'charlesbank', 'cinven',
                'clearlake', 'cornell capital', 'court square', 'cvc', 'elliott', 'eqt',
                'fairfax', 'fortress', 'francisco', 'gamut', 'general atlantic', 'genstar',
                'gi partners', 'golden gate', 'greenbriar', 'gsam', 'gtcr', 'h&f', 'haveli',
                'harvest partners', 'hg', 'hig', 'hps', 'insight partners', 'kelso', 'kkr',
                'kohlberg', 'kps', 'l catterton', 'leonard green', 'lindsay goldberg', 'littlejohn',
                'lone star', 'madison dearborn', 'mubadala', 'new mountain', 'oak hill', 'oaktree',
                'odyssey', 'olympus', 'omers', 'one rock', 'onex', 'pai', 'parthenon',
                'partners group', 'patient square', 'permira', 'platinum', 'pritzker private capital',
                'providence', 'reverence', 'rhône group', 'roark', 'searchlight', 'silver lake',
                'siris capital', 'sk capital', 'stone canyon', 'stone point', 'stonepeak',
                'summit partners', 'svp capital', 'symphony', 'ta associates', 'thoma bravo',
                'thl', 'tjc', 'towerbrook', 'tpg', 'tpg real estate', 'truelink', 'tsg consumer',
                'veritas', 'vista', 'warburg pincus', 'welsh carson'
            ]
            score += sum(15 for firm in scopelp_firms if firm in text)
            
            # Deal size indicators
            deal_indicators = ['billion', 'million', '$', 'valuation', 'fund size']
            score += sum(3 for indicator in deal_indicators if indicator in text)
            
            return score
        
        return sorted(articles, key=pe_vc_score, reverse=True)
    
    def format_market_data(self, market_data):
        """Format market data or show unavailable message"""
        if not market_data or len(market_data) == 0:
            print("⚠️ No live market data available")
            return """
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #333; margin: 0 0 15px 0;">🌍 Global Markets Overview</h3>
                <div style="text-align: center; padding: 30px; background: white; border-radius: 8px; border: 2px dashed #ddd;">
                    <p style="color: #666; font-size: 16px; margin: 0; font-style: italic;">
                        📊 Market data temporarily unavailable
                    </p>
                    <p style="color: #999; font-size: 14px; margin: 10px 0 0 0;">
                        Please check financial news sources for current market information
                    </p>
                </div>
            </div>
            """
        
        print(f"📊 Formatting live market data for {len(market_data)} symbols")
        
        # Get the trading date from any symbol (they should all be the same)
        trading_date = None
        for symbol_data in market_data.values():
            if 'trading_date' in symbol_data:
                trading_date = symbol_data['trading_date']
                break
        
        html = f"""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #333; margin: 0 0 5px 0;">🌍 Global Markets Overview</h3>
            {f'<p style="color: #666; font-size: 12px; margin: 0 0 15px 0;">Closing prices from {trading_date}</p>' if trading_date else ''}
            <div style="display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between;">
        """
        
        # Enhanced market labels for global view
        market_labels = {
            'SPY': 'S&P 500',
            'QQQ': 'Nasdaq',
            'VTI': 'US Total Market',
            'EFA': 'Developed Markets',
            'EEM': 'Emerging Markets',
            'VNQ': 'US REITs',
            'TNX': '10-Year Treasury',
            'GLD': 'Gold',
            'DXY': 'US Dollar Index',
            'CL=F': 'Oil (WTI)'
        }
        
        # Define order for consistent display
        symbol_order = ['SPY', 'QQQ', 'VTI', 'EFA', 'EEM', 'VNQ', 'TNX', 'GLD', 'DXY', 'CL=F']
        
        for symbol in symbol_order:
            if symbol in market_data:
                data = market_data[symbol]
                price = data.get('price', 0)
                change = data.get('change', 0)
                change_pct = data.get('change_pct', 0)
                ytd_pct = data.get('ytd_pct', 0)
                
                # Color coding for daily change
                daily_color = "#28a745" if change >= 0 else "#dc3545"
                daily_arrow = "↗" if change >= 0 else "↘"
                
                # Color coding for YTD performance
                ytd_color = "#28a745" if ytd_pct >= 0 else "#dc3545"
                
                display_name = market_labels.get(symbol, symbol)
                
                # Format price based on symbol type
                if symbol == 'TNX':
                    price_display = f"{price:.2f}%"
                elif symbol in ['DXY']:
                    price_display = f"{price:.2f}"
                else:
                    price_display = f"${price:.2f}"
                
                html += f"""
                    <div style="flex: 1; min-width: 120px; max-width: 150px; text-align: center; padding: 12px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-weight: bold; font-size: 11px; color: #666; margin-bottom: 6px; line-height: 1.2;">{display_name}</div>
                        <div style="font-size: 16px; font-weight: 700; margin-bottom: 4px; color: #1a1a1a;">{price_display}</div>
                        <div style="color: {daily_color}; font-size: 12px; font-weight: 500; margin-bottom: 4px;">{daily_arrow} {change_pct:+.1f}%</div>
                        <div style="color: {ytd_color}; font-size: 10px; font-weight: 500;">YTD: {ytd_pct:+.1f}%</div>
                    </div>
                """
            else:
                # Show placeholder for missing symbols
                display_name = market_labels.get(symbol, symbol)
                html += f"""
                    <div style="flex: 1; min-width: 120px; max-width: 150px; text-align: center; padding: 12px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); opacity: 0.5;">
                        <div style="font-weight: bold; font-size: 11px; color: #666; margin-bottom: 6px; line-height: 1.2;">{display_name}</div>
                        <div style="font-size: 14px; color: #999;">N/A</div>
                    </div>
                """
        
        html += "</div></div>"
        print("✅ Market data formatted successfully")
        return html
    
    def create_newsletter_html(self, categorized_articles, market_data):
        """Create ExecSum-style HTML newsletter"""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Count total articles
        total_articles = sum(len(articles) for articles in categorized_articles.values())
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 680px; 
                    margin: 0 auto; 
                    background: #ffffff;
                    color: #333;
                    line-height: 1.6;
                }}
                .header {{
                    text-align: center;
                    padding: 30px 20px;
                    border-bottom: 1px solid #e1e8ed;
                }}
                .header h1 {{
                    font-size: 28px;
                    color: #1a1a1a;
                    margin: 0 0 10px 0;
                    font-weight: 700;
                }}
                .date {{
                    color: #657786;
                    font-size: 14px;
                }}
                .greeting {{
                    padding: 20px;
                    background: #f8f9fa;
                    margin: 0;
                    font-size: 16px;
                }}
                .section {{
                    margin: 30px 20px;
                }}
                .section h2 {{
                    color: #1a1a1a;
                    font-size: 20px;
                    margin: 0 0 20px 0;
                    font-weight: 600;
                    border-bottom: 2px solid #1d9bf0;
                    padding-bottom: 8px;
                }}
                .article {{
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 1px solid #f1f3f4;
                }}
                .article:last-child {{
                    border-bottom: none;
                }}
                .article-title {{
                    font-weight: 600;
                    font-size: 16px;
                    margin: 0 0 8px 0;
                    color: #1a1a1a;
                }}
                .article-summary {{
                    color: #536471;
                    margin: 8px 0 12px 0;
                    font-size: 14px;
                }}
                .article-meta {{
                    font-size: 12px;
                    color: #8b98a5;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .read-more {{
                    color: #1d9bf0;
                    text-decoration: none;
                    font-weight: 500;
                    font-size: 13px;
                }}
                .read-more:hover {{
                    text-decoration: underline;
                }}
                .footer {{
                    text-align: center;
                    padding: 30px 20px;
                    border-top: 1px solid #e1e8ed;
                    color: #8b98a5;
                    font-size: 12px;
                }}
                .category-divider {{
                    margin: 40px 0 30px 0;
                    text-align: center;
                }}
                .category-divider::before {{
                    content: '';
                    display: inline-block;
                    width: 50px;
                    height: 1px;
                    background: #e1e8ed;
                    margin-right: 15px;
                    vertical-align: middle;
                }}
                .category-divider::after {{
                    content: '';
                    display: inline-block;
                    width: 50px;
                    height: 1px;
                    background: #e1e8ed;
                    margin-left: 15px;
                    vertical-align: middle;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 NewsBrief by ScopeLP</h1>
                <div class="date">{current_date}</div>
            </div>
            
            <div class="greeting">
                <strong>Good Morning,</strong><br><br>
                Today's brief covers {total_articles} key stories across global markets and private capital deals. 
                Market data reflects closing prices from the most recent trading session.
            </div>
            
            {self.format_market_data(market_data)}
        """
        
        # Add categorized content in new structure
        category_order = ['Global Markets', 'Private Equity', 'Venture Capital', 'Private Credit', 'IPOs', 'Fundraising', 'Bankruptcy', 'PE Secondaries']
        
        for category in category_order:
            if category in categorized_articles and categorized_articles[category]:
                # Special handling for Global Markets section
                if category == 'Global Markets':
                    article_limit = 8  # More articles for markets overview
                    section_description = "Global financial markets news, economic indicators, and macro trends"
                elif category == 'Fundraising':
                    article_limit = 6
                    section_description = "PE/VC/Credit fund closes, LP activity, and institutional fundraising"
                else:
                    article_limit = 6  # Standard limit for deal sections
                    section_description = ""
                
                html_content += f"""
                <div class="section">
                    <h2>{self.get_category_emoji(category)} {category}</h2>
                """
                
                # Add section description for specific sections
                if section_description:
                    html_content += f"""
                    <p style="color: #666; font-size: 14px; margin: 0 0 20px 0; font-style: italic;">{section_description}</p>
                    """
                
                for article in categorized_articles[category][:article_limit]:
                    html_content += f"""
                    <div class="article">
                        <div class="article-title">{article['title']}</div>
                        <div class="article-summary">{article['summary']}</div>
                        <div class="article-meta">
                            <span>📍 {article['source']}</span>
                            <a href="{article['link']}" class="read-more" target="_blank">Read more →</a>
                        </div>
                    </div>
                    """
                
                html_content += "</div>"
                
                # Add divider between categories (except last one)
                if category != category_order[-1] and category_order.index(category) < len(category_order) - 1:
                    html_content += '<div class="category-divider"></div>'
        
        html_content += """
            <div class="footer">
                <p>📊 NewsBrief by ScopeLP - Private Equity Intelligence<br>
                Automated monitoring and analysis for PE professionals.</p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def get_category_emoji(self, category):
        """Get emoji for deal-focused categories"""
        emojis = {
            'Global Markets': '🌍',
            'Private Equity': '🏢',
            'Venture Capital': '🚀',
            'Private Credit': '💳',
            'IPOs': '📈',
            'Fundraising': '💰',
            'Bankruptcy': '⚠️',
            'PE Secondaries': '🔄'
        }
        return emojis.get(category, '📰')
    
    def send_email(self, html_content):
        """Send the newsletter email via PrivateEmail.com"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📊 NewsBrief by ScopeLP - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            
            # Create HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Try multiple PrivateEmail.com SMTP configurations
            smtp_configs = [
                ('mail.privateemail.com', 587, True),    # STARTTLS (most common)
                ('mail.privateemail.com', 465, False),   # SSL
                ('smtp.privateemail.com', 587, True),    # Alternative server
                ('smtp.privateemail.com', 465, False),   # Alternative server SSL
            ]
            
            for server, port, use_starttls in smtp_configs:
                try:
                    if use_starttls:
                        # STARTTLS configuration
                        with smtplib.SMTP(server, port) as smtp_server:
                            smtp_server.starttls()
                            smtp_server.login(self.sender_email, self.sender_password)
                            smtp_server.send_message(msg)
                    else:
                        # SSL configuration
                        with smtplib.SMTP_SSL(server, port) as smtp_server:
                            smtp_server.login(self.sender_email, self.sender_password)
                            smtp_server.send_message(msg)
                    
                    print(f"✅ NewsBrief sent successfully via {server}:{port} at {datetime.now()}")
                    return
                    
                except Exception as e:
                    print(f"❌ Failed with {server}:{port} - {e}")
                    continue
            
            print("❌ All PrivateEmail.com SMTP configurations failed")
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
    
    def generate_and_send_newsletter(self):
        """Main function to create and send newsletter"""
        print("📊 Generating NewsBrief by ScopeLP...")
        
        # Fetch market data
        market_data = self.get_market_data()
        
        # Fetch financial news
        categorized_articles = self.fetch_financial_news()
        
        if categorized_articles:
            html_content = self.create_newsletter_html(categorized_articles, market_data)
            self.send_email(html_content)
        else:
            print("⚠️ No articles found. Newsletter not sent.")

def main():
    newsletter_bot = FinancialNewsletterBot()
    
    # For GitHub Actions - run once
    if os.getenv('GITHUB_ACTIONS'):
        newsletter_bot.generate_and_send_newsletter()
    else:
        # For local development - schedule daily
        schedule.every().day.at("07:00").do(newsletter_bot.generate_and_send_newsletter)
        
        print("🚀 NewsBrief by ScopeLP started. Next newsletter: 7:00 AM daily")
        
        # Uncomment to test immediately:
        # newsletter_bot.generate_and_send_newsletter()
        
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    main()
