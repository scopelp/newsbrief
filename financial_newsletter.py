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
from bs4 import BeautifulSoup
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
            'Private Capital Journal': 'https://www.privatecapitaljournal.com/feed/',
            'Private Equity International': 'https://www.privateequityinternational.com/feed/',
            'Reuters Business': 'https://feeds.reuters.com/reuters/businessNews',
            'PE Hub': 'https://www.pehub.com/feed/',
            'PitchBook News': 'https://pitchbook.com/rss/news',
            'TechCrunch Startups': 'https://techcrunch.com/category/startups/feed/'
        }
        
        # PE/VC relevant market indicators (no crypto)
        self.market_symbols = ['SPY', 'QQQ', 'VTEB', 'VTI', 'QUAL', 'MTUM']
        
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
        """Fetch current market data"""
        try:
            # Using Yahoo Finance API (free)
            market_data = {}
            for symbol in self.market_symbols:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                        result = data['chart']['result'][0]
                        meta = result['meta']
                        current_price = meta.get('regularMarketPrice', 0)
                        prev_close = meta.get('previousClose', 0)
                        change = current_price - prev_close if current_price and prev_close else 0
                        change_pct = (change / prev_close * 100) if prev_close else 0
                        
                        market_data[symbol] = {
                            'price': current_price,
                            'change': change,
                            'change_pct': change_pct
                        }
            return market_data
        except Exception as e:
            print(f"Error fetching market data: {e}")
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
            'Wall Street Journal': 'https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml'
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
            'PE Hub': 8,
            'PitchBook News': 8,
            'Reuters Business': 7,
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
        """Categorize articles with PE/VC focus"""
        text_lower = text.lower()
        
        # PE specific categories
        if any(word in text_lower for word in ['buyout', 'lbo', 'leveraged buyout', 'take private', 'private equity']):
            return 'Private Equity'
        elif any(word in text_lower for word in ['venture capital', 'vc', 'startup', 'series a', 'series b', 'series c', 'seed funding']):
            return 'Venture Capital'
        elif any(word in text_lower for word in ['ipo', 'public offering', 'listing', 'debut', 'exit']):
            return 'IPO/Exits'
        elif any(word in text_lower for word in ['m&a', 'merger', 'acquisition', 'takeover', 'deal']):
            return 'M&A'
        elif any(word in text_lower for word in ['fund', 'fundraising', 'capital raise', 'limited partners']):
            return 'Fund News'
        elif any(word in text_lower for word in ['portfolio company', 'portco', 'investment', 'growth capital']):
            return 'Portfolio'
        else:
            return 'Industry News'
    
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
        """Format market data for email (PE/VC relevant indices)"""
        if not market_data:
            return "<p>Market data unavailable</p>"
        
        html = """
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #333; margin: 0 0 15px 0;">📊 Market Snapshot (PE/VC Relevant)</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px;">
        """
        
        # Market labels for PE/VC context
        market_labels = {
            'SPY': 'S&P 500',
            'QQQ': 'Nasdaq',
            'VTEB': 'Tax-Exempt Bonds',
            'VTI': 'Total Stock Market',
            'QUAL': 'Quality Factor',
            'MTUM': 'Momentum Factor'
        }
        
        for symbol, data in market_data.items():
            price = data.get('price', 0)
            change = data.get('change', 0)
            change_pct = data.get('change_pct', 0)
            
            color = "#28a745" if change >= 0 else "#dc3545"
            arrow = "↗" if change >= 0 else "↘"
            display_name = market_labels.get(symbol, symbol)
            
            html += f"""
                <div style="text-align: center; padding: 8px; background: white; border-radius: 4px;">
                    <div style="font-weight: bold; font-size: 12px;">{display_name}</div>
                    <div style="font-size: 14px;">${price:.2f}</div>
                    <div style="color: {color}; font-size: 11px;">{arrow} {change_pct:+.1f}%</div>
                </div>
            """
        
        html += "</div></div>"
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
                    margin-bottom: 25px;
                    padding-bottom: 20px;
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
