"""
♻️ LAYER 4: Content Filter
Entfernt Werbung, Tracking, toxische Inhalte, Affiliate Links
"""

from typing import Dict, List, Optional
import re
from bs4 import BeautifulSoup


class ContentFilter:
    """
    Layer 4: Content Filtering
    
    Entfernt:
    - Werbung (ads, sponsored)
    - Social Buttons (Share, Like, Follow)
    - Affiliate Links
    - Cookie Consent Banners
    - Personalisierte Abschnitte
    - Tracking Scripts
    - Gefährliche Inhalte (toxisch, illegal)
    
    Kürzt:
    - Extrem lange Texte
    - Repetitive Inhalte
    """
    
    # Ad/Tracking Patterns
    AD_PATTERNS = [
        r'advertisement',
        r'sponsored',
        r'anzeige',
        r'werbung',
        r'ad-container',
        r'google-ad',
        r'doubleclick',
        r'adsbygoogle',
    ]
    
    # Social Media Patterns
    SOCIAL_PATTERNS = [
        r'share-button',
        r'social-share',
        r'follow-us',
        r'like-button',
        r'tweet-button',
        r'facebook-like',
    ]
    
    # Cookie/Privacy Patterns
    COOKIE_PATTERNS = [
        r'accept.*cookie',
        r'cookie.*consent',
        r'privacy.*policy',
        r'gdpr.*notice',
        r'we use cookies',
        r'diese.*website.*cookies',
    ]
    
    # Affiliate Link Domains
    AFFILIATE_DOMAINS = {
        'amzn.to', 'amazon.de/dp', 'ebay.com',
        'awin1.com', 'shareasale.com', 'clickbank.net',
    }
    
    # Toxic/Dangerous Keywords
    TOXIC_KEYWORDS = {
        # Hate Speech
        'nazi', 'hitler', 'holocaust denial',
        
        # Violence
        'how to kill', 'murder tutorial', 'bomb making',
        
        # Explicit Content
        'porn', 'xxx', 'nsfw',
        
        # Drugs
        'buy cocaine', 'buy heroin', 'drug dealer',
    }
    
    def filter_html(self, html: str) -> Dict:
        """
        Filtert HTML Content
        
        Returns:
            {
                'filtered_html': str,
                'removed_elements': int,
                'removed_ads': int,
                'removed_social': int,
                'removed_cookies': int,
                'toxic_content_found': bool,
                'warnings': List[str]
            }
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        stats = {
            'filtered_html': '',
            'removed_elements': 0,
            'removed_ads': 0,
            'removed_social': 0,
            'removed_cookies': 0,
            'toxic_content_found': False,
            'warnings': []
        }
        
        # 1. Remove Ads
        for pattern in self.AD_PATTERNS:
            for element in soup.find_all(class_=re.compile(pattern, re.I)):
                element.decompose()
                stats['removed_ads'] += 1
            for element in soup.find_all(id=re.compile(pattern, re.I)):
                element.decompose()
                stats['removed_ads'] += 1
        
        # 2. Remove Social Buttons
        for pattern in self.SOCIAL_PATTERNS:
            for element in soup.find_all(class_=re.compile(pattern, re.I)):
                element.decompose()
                stats['removed_social'] += 1
        
        # 3. Remove Cookie Banners
        for pattern in self.COOKIE_PATTERNS:
            for element in soup.find_all(string=re.compile(pattern, re.I)):
                if element.parent:
                    element.parent.decompose()
                    stats['removed_cookies'] += 1
        
        # 4. Remove known noise elements
        noise_tags = ['aside', 'nav', 'footer', 'header']
        for tag in noise_tags:
            for element in soup.find_all(tag):
                element.decompose()
                stats['removed_elements'] += 1
        
        stats['filtered_html'] = str(soup)
        
        return stats
    
    def filter_text(self, text: str, max_length: int = 10000) -> Dict:
        """
        Filtert Text Content
        
        Args:
            text: Rohtext
            max_length: Max Zeichen (default 10k)
        
        Returns:
            {
                'filtered_text': str,
                'original_length': int,
                'filtered_length': int,
                'toxic_content_found': bool,
                'toxic_keywords': List[str],
                'affiliate_links_removed': int,
                'truncated': bool,
                'warnings': List[str]
            }
        """
        result = {
            'filtered_text': text,
            'original_length': len(text),
            'filtered_length': 0,
            'toxic_content_found': False,
            'toxic_keywords': [],
            'affiliate_links_removed': 0,
            'truncated': False,
            'warnings': []
        }
        
        # 1. Check for toxic content
        text_lower = text.lower()
        for keyword in self.TOXIC_KEYWORDS:
            if keyword in text_lower:
                result['toxic_content_found'] = True
                result['toxic_keywords'].append(keyword)
        
        if result['toxic_content_found']:
            result['warnings'].append('Toxic content detected')
            # Option: Text komplett blockieren
            # return result
        
        # 2. Remove Affiliate Links
        filtered = text
        for domain in self.AFFILIATE_DOMAINS:
            pattern = r'https?://[^\s]*' + re.escape(domain) + r'[^\s]*'
            matches = re.findall(pattern, filtered, re.I)
            result['affiliate_links_removed'] += len(matches)
            filtered = re.sub(pattern, '[affiliate link removed]', filtered, flags=re.I)
        
        # 3. Remove Cookie Notices
        for pattern in self.COOKIE_PATTERNS:
            filtered = re.sub(
                r'.{0,50}' + pattern + r'.{0,100}',
                '',
                filtered,
                flags=re.I
            )
        
        # 4. Remove excessive whitespace
        filtered = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered)
        filtered = re.sub(r'  +', ' ', filtered)
        
        # 5. Remove repetitive lines (spam-detection)
        lines = filtered.split('\n')
        unique_lines = []
        seen = set()
        for line in lines:
            line_clean = line.strip().lower()
            if line_clean and line_clean not in seen:
                unique_lines.append(line)
                seen.add(line_clean)
        filtered = '\n'.join(unique_lines)
        
        # 6. Truncate if too long
        if len(filtered) > max_length:
            filtered = filtered[:max_length] + '\n\n[Content truncated...]'
            result['truncated'] = True
            result['warnings'].append(f'Content truncated to {max_length} characters')
        
        result['filtered_text'] = filtered
        result['filtered_length'] = len(filtered)
        
        return result
    
    def filter_links(self, links: List[str]) -> Dict:
        """
        Filtert Link-Liste
        
        Returns:
            {
                'safe_links': List[str],
                'removed_links': List[str],
                'removed_count': int
            }
        """
        safe = []
        removed = []
        
        for link in links:
            # Check für Affiliate Domains
            is_affiliate = any(domain in link.lower() for domain in self.AFFILIATE_DOMAINS)
            
            # Check für Tracking Parameter
            has_tracking = any(
                param in link.lower() 
                for param in ['utm_', 'fbclid=', 'gclid=', 'ref=']
            )
            
            if is_affiliate or has_tracking:
                removed.append(link)
            else:
                safe.append(link)
        
        return {
            'safe_links': safe,
            'removed_links': removed,
            'removed_count': len(removed)
        }
    
    def check_toxicity(self, text: str) -> Dict:
        """
        Dedizierter Toxicity-Check
        
        Returns:
            {
                'is_toxic': bool,
                'toxic_score': int (0-100),
                'found_keywords': List[str],
                'category': str  # 'safe', 'warning', 'toxic', 'illegal'
            }
        """
        text_lower = text.lower()
        found = []
        
        for keyword in self.TOXIC_KEYWORDS:
            if keyword in text_lower:
                found.append(keyword)
        
        toxic_score = min(100, len(found) * 30)
        
        # Kategorisierung
        if toxic_score == 0:
            category = 'safe'
        elif toxic_score < 30:
            category = 'warning'
        elif toxic_score < 60:
            category = 'toxic'
        else:
            category = 'illegal'
        
        return {
            'is_toxic': toxic_score > 0,
            'toxic_score': toxic_score,
            'found_keywords': found,
            'category': category
        }


# Singleton Instance
_content_filter_instance: Optional[ContentFilter] = None

def get_content_filter() -> ContentFilter:
    """Factory für ContentFilter (Singleton)"""
    global _content_filter_instance
    if _content_filter_instance is None:
        _content_filter_instance = ContentFilter()
    return _content_filter_instance
