"""
🔍 LAYER 2: Domain Reputation & Risk Analyzer
Bewertet URLs nach Sicherheit, SSL, Domain-Alter, Hosting-Land
"""

from typing import Dict, Optional, Tuple, List
from urllib.parse import urlparse
import socket
import ssl
import requests
from datetime import datetime, timedelta
import re


class DomainRiskAnalyzer:
    """
    Layer 2: Domain Reputation Check
    
    Bewertungskriterien:
    - Domain Reputation (Whitelist/Graylist/Blacklist)
    - SSL/HTTPS Validation
    - Domain Age (WHOIS - simuliert, da kein API)
    - Hosting Country
    - Malware/Phishing Listen
    
    Risk Score: 0-100
    - 0-20: Sicher (Wikipedia, NASA, Heise...)
    - 20-40: Brauchbar (Foren, Blogs)
    - 40-60: Unsicher (Unbekannte Domains)
    - 60-80: Kritisch (Nur Sandbox)
    - 80-100: Blockiert (Social Media, Malware, Shops...)
    
    HYBRID SYSTEM (v3.0):
    - Hardcoded lists (fast, always available)
    - Database lists (user-specific + global, runtime configurable)
    """
    
    def __init__(self, db_session=None, user_id: Optional[int] = None):
        """
        Initialize with optional database session for custom lists.
        
        Args:
            db_session: SQLAlchemy Session for DB queries
            user_id: User ID for user-specific lists (None = only global)
        """
        self.db = db_session
        self.user_id = user_id
    
    # 🟢 WHITELIST - Absolut sichere Domains (Risk 0-20)
    SAFE_DOMAINS = {
        # Wissenschaft & Bildung
        'wikipedia.org', 'wikimedia.org', 'wiktionary.org',
        'arxiv.org', 'scholar.google.com', 'researchgate.net',
        'nasa.gov', 'esa.int', 'mpg.de', 'sciencedirect.com',
        
        # Wetter & Geo
        'openweathermap.org', 'open-meteo.com', 'weather.com',
        'dwd.de', 'wetter.de', 'wetter.com',
        
        # === LIARA AI EXTENSIONS ===
        
        # AI/ML Frameworks & Resources
        'huggingface.co', 'paperswithcode.com', 'openai.com',
        'pytorch.org', 'tensorflow.org', 'keras.io',
        'scikit-learn.org', 'fast.ai', 'deeplearning.ai',
        'ai.google', 'ai.meta.com', 'anthropic.com',
        'kaggle.com', 'colab.research.google.com',
        
        # Package Managers & Registries
        'crates.io', 'rubygems.org', 'packagist.org',
        'nuget.org', 'maven.org', 'mvnrepository.com',
        'hub.docker.com', 'docker.com', 'quay.io',
        'conda.io', 'anaconda.org', 'conda-forge.org',
        
        # Dev Documentation & APIs
        'devdocs.io', 'mdn.io', 'developer.apple.com',
        'docs.microsoft.com', 'cloud.google.com', 'aws.amazon.com',
        'azure.microsoft.com', 'digitalocean.com', 'heroku.com',
        'vercel.com', 'netlify.com', 'railway.app',
        
        # Code Quality & CI/CD
        'codecov.io', 'coveralls.io', 'sonarcloud.io',
        'travis-ci.org', 'circleci.com', 'jenkins.io',
        'github.io', 'gitlab.io', 'gitpod.io',
        
        # API Tools & Documentation
        'swagger.io', 'openapis.org', 'graphql.org',
        'postman.com', 'insomnia.rest', 'httpie.io',
        'rapidapi.com', 'apilist.fun', 'public-apis.io',
        
        # Linux/Unix & System
        'kernel.org', 'gnu.org', 'debian.org', 'ubuntu.com',
        'archlinux.org', 'fedoraproject.org', 'redhat.com',
        'alpinelinux.org', 'getfedora.org', 'centos.org',
        
        # Security & Vulnerability
        'owasp.org', 'nvd.nist.gov', 'cve.mitre.org',
        'cert.org', 'sans.org', 'cwe.mitre.org',
        'snyk.io', 'dependabot.com', 'sonatype.com',
        
        # Databases & Data Tools
        'postgresql.org', 'mysql.com', 'mongodb.com',
        'redis.io', 'sqlite.org', 'mariadb.org',
        'neo4j.com', 'influxdata.com', 'timescale.com',
        
        # Web Standards & Browser Docs
        'w3.org', 'whatwg.org', 'caniuse.com',
        'browserlist.dev', 'cssreference.io', 'htmlreference.io',
        
        # News & Medien (seriös)
        'tagesschau.de', 'zeit.de', 'faz.net', 'sueddeutsche.de',
        'spiegel.de', 'heise.de', 'golem.de', 'bbc.com', 'bbc.co.uk',
        'theguardian.com', 'nytimes.com', 'washingtonpost.com',
        
        # Tech & Development
        'github.com', 'gitlab.com', 'stackoverflow.com', 'stackexchange.com',
        'developer.mozilla.org', 'devdocs.io', 'readthedocs.io',
        'python.org', 'nodejs.org', 'reactjs.org', 'vuejs.org',
        
        # Dokumentation
        'docs.python.org', 'docs.microsoft.com', 'docs.github.com',
        'fastapi.tiangolo.com', 'flask.palletsprojects.com',
        
        # Government & Official
        'gov', 'europa.eu', 'bundestag.de', 'bundesregierung.de',
        
        # OpenData
        'data.gov', 'opendata.europa.eu', 'destatis.de',
    }
    
    # 🟠 GRAYLIST - Eingeschränkt nutzbar (Risk 20-40)
    GRAY_DOMAINS = {
        # Foren
        'reddit.com', 'discourse.org', 'forum.', 'board.',
        
        # Blogs & CMS
        'medium.com', 'dev.to', 'hashnode.com', 'substack.com',
        'wordpress.com', 'blogspot.com', 'blogger.com',
        
        # Video (nur Text-Metadaten)
        'youtube.com', 'youtu.be', 'vimeo.com',
        
        # Q&A Platforms
        'quora.com', 'yahoo.com',
        
        # === LIARA AI EXTENSIONS ===
        
        # Educational Platforms (user-generated, quality varies)
        'udemy.com', 'coursera.org', 'edx.org',
        'khanacademy.org', 'codecademy.com', 'freecodecamp.org',
        'pluralsight.com', 'skillshare.com',
        
        # Code Playgrounds (publicly editable)
        'codepen.io', 'jsfiddle.net', 'replit.com',
        'codesandbox.io', 'stackblitz.com', 'glitch.com',
        
        # Wiki/Collaboration (user-edited)
        'fandom.com', 'wikihow.com',
        
        # Design/Assets (mixed quality)
        'dribbble.com', 'behance.net', 'unsplash.com',
        'pexels.com', 'flaticon.com',
        
        # Package Discovery
        'libraries.io', 'bestofjs.org', 'alternativeto.net',
    }
    
    # 🔴 BLACKLIST - Immer blockiert (Risk 80-100)
    BLOCKED_DOMAINS = {
        # Social Media
        'facebook.com', 'fb.com', 'instagram.com', 'tiktok.com',
        'twitter.com', 'x.com', 'linkedin.com', 'snapchat.com',
        'whatsapp.com', 'telegram.org', 't.me', 'discord.com',
        'pinterest.com', 'tumblr.com',
        
        # File Hosting / Cloud Storage (privacy/tracking risks)
        'mega.nz', 'rapidgator.net', 'uploaded.net', 'mediafire.com',
        'dropbox.com', 'drive.google.com', 'onedrive.live.com',
        
        # Torrents / Piracy
        'thepiratebay.org', 'kickass.to', '1337x.to', 'rarbg.to',
        'torrent', 'pirate',
        
        # Shopping (zu dynamisch, Tracking, Werbung)
        'amazon.com', 'amazon.de', 'ebay.com', 'ebay.de',
        'aliexpress.com', 'alibaba.com', 'wish.com',
        'etsy.com', 'walmart.com', 'target.com',
        
        # Adult Content
        'pornhub.com', 'xvideos.com', 'xhamster.com',
        
        # Darknet
        '.onion',
        
        # === LIARA AI EXTENSIONS ===
        
        # Crypto/Trading (volatile, scams)
        'binance.com', 'coinbase.com', 'crypto.com',
        'blockchain.com', 'kraken.com', 'ftx.com',
        'opensea.io', 'rarible.com',
        
        # Gambling/Betting
        'bet365.com', 'pokerstars.com', 'casino.',
        
        # Click Farms / SEO Spam
        'upwork.com', 'fiverr.com', '99designs.com',
        
        # URL Shorteners (Phishing Risk)
        'bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly',
        't.co', 'buff.ly', 'adf.ly',
    }
    
    # Blocked TLDs
    BLOCKED_TLDS = {'.onion', '.tk', '.ml', '.ga', '.cf'}  # Häufig für Spam/Phishing
    
    def analyze_url(self, url: str) -> Dict:
        """
        Analysiert URL und gibt Risk-Score + Details zurück
        
        Returns:
            {
                'url': str,
                'domain': str,
                'risk_score': int (0-100),
                'risk_level': str ('safe', 'gray', 'unsafe', 'critical', 'blocked'),
                'is_safe': bool,
                'has_https': bool,
                'ssl_valid': bool,
                'category': str,
                'blocked_reason': Optional[str],
                'warnings': List[str]
            }
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www.
        if domain.startswith('www.'):
            domain = domain[4:]
        
        result = {
            'url': url,
            'domain': domain,
            'risk_score': 50,  # Default: Unsicher
            'risk_level': 'unsafe',
            'is_safe': False,
            'has_https': parsed.scheme == 'https',
            'ssl_valid': False,
            'category': 'unknown',
            'blocked_reason': None,
            'warnings': []
        }
        
        # 1. Check Blacklist
        if self._is_blocked(domain):
            result['risk_score'] = 100
            result['risk_level'] = 'blocked'
            result['is_safe'] = False
            result['blocked_reason'] = 'Domain on blacklist'
            result['category'] = 'blocked'
            return result
        
        # 2. Check Whitelist
        if self._is_safe(domain):
            result['risk_score'] = 10
            result['risk_level'] = 'safe'
            result['is_safe'] = True
            result['category'] = 'whitelist'
            if not result['has_https']:
                result['warnings'].append('No HTTPS')
                result['risk_score'] += 10
            return result
        
        # 3. Check Graylist
        if self._is_gray(domain):
            result['risk_score'] = 30
            result['risk_level'] = 'gray'
            result['is_safe'] = True  # Mit Einschränkungen
            result['category'] = 'graylist'
            result['warnings'].append('Restricted content - sandbox only')
        
        # 4. HTTPS Check
        if not result['has_https']:
            result['risk_score'] += 30
            result['warnings'].append('No HTTPS encryption')
        else:
            # SSL Validation
            ssl_valid = self._check_ssl(domain)
            result['ssl_valid'] = ssl_valid
            if not ssl_valid:
                result['risk_score'] += 20
                result['warnings'].append('Invalid SSL certificate')
        
        # 5. TLD Check
        tld = self._get_tld(domain)
        if tld in self.BLOCKED_TLDS:
            result['risk_score'] = 100
            result['risk_level'] = 'blocked'
            result['is_safe'] = False
            result['blocked_reason'] = f'Blocked TLD: {tld}'
            result['category'] = 'blocked'
            return result
        
        # 6. Suspicious Patterns
        if self._has_suspicious_patterns(domain):
            result['risk_score'] += 20
            result['warnings'].append('Suspicious domain pattern')
        
        # 7. Final Risk Level Classification
        if result['risk_score'] >= 80:
            result['risk_level'] = 'blocked'
            result['is_safe'] = False
            result['blocked_reason'] = 'Risk score too high'
        elif result['risk_score'] >= 60:
            result['risk_level'] = 'critical'
            result['is_safe'] = False
            result['warnings'].append('Critical risk - blocked')
        elif result['risk_score'] >= 40:
            result['risk_level'] = 'unsafe'
            result['is_safe'] = False
            result['warnings'].append('Unsafe domain - not recommended')
        elif result['risk_score'] >= 20:
            result['risk_level'] = 'gray'
            result['is_safe'] = True
        else:
            result['risk_level'] = 'safe'
            result['is_safe'] = True
        
        return result
    
    def _is_safe(self, domain: str) -> bool:
        """
        Check ob Domain auf Whitelist (Hardcoded + DB)
        Priority: DB user-specific > DB global > Hardcoded
        """
        # 1. Check database lists first (if available)
        if self.db:
            db_result = self._check_db_list(domain, 'whitelist')
            if db_result is not None:
                return db_result
        
        # 2. Check hardcoded whitelist
        # Exact match
        if domain in self.SAFE_DOMAINS:
            return True
        
        # Suffix match (z.B. docs.python.org)
        for safe_domain in self.SAFE_DOMAINS:
            if domain.endswith('.' + safe_domain) or domain == safe_domain:
                return True
        
        # TLD match (z.B. .gov)
        if domain.endswith('.gov') or domain.endswith('.edu'):
            return True
        
        return False
    
    def _is_gray(self, domain: str) -> bool:
        """
        Check ob Domain auf Graylist (Hardcoded + DB)
        """
        # 1. Check database lists first
        if self.db:
            db_result = self._check_db_list(domain, 'graylist')
            if db_result is not None:
                return db_result
        
        # 2. Check hardcoded graylist
        for gray_domain in self.GRAY_DOMAINS:
            if gray_domain in domain:
                return True
        return False
    
    def _is_blocked(self, domain: str) -> bool:
        """
        Check ob Domain auf Blacklist (Hardcoded + DB)
        """
        # 1. Check database lists first
        if self.db:
            db_result = self._check_db_list(domain, 'blacklist')
            if db_result is not None:
                return db_result
        
        # 2. Check hardcoded blacklist
        # Exact match
        if domain in self.BLOCKED_DOMAINS:
            return True
        
        # Substring match
        for blocked in self.BLOCKED_DOMAINS:
            if blocked in domain:
                return True
        
        return False
    
    def _get_tld(self, domain: str) -> str:
        """Extrahiert TLD"""
        parts = domain.split('.')
        if len(parts) >= 2:
            return '.' + parts[-1]
        return ''
    
    def _check_db_list(self, domain: str, list_type: str) -> Optional[bool]:
        """
        Check database for custom domain lists.
        
        Args:
            domain: Domain to check
            list_type: 'whitelist', 'graylist', or 'blacklist'
            
        Returns:
            True if domain is in list (user-specific or global)
            False if domain is explicitly NOT in list
            None if no DB match (fall through to hardcoded)
        """
        from sqlalchemy import text
        
        try:
            # Check user-specific AND global lists
            # Priority: user-specific > global
            query = text("""
                SELECT domain, is_pattern 
                FROM web_safety_lists
                WHERE list_type = :list_type
                  AND (user_id = :user_id OR user_id IS NULL)
                ORDER BY user_id NULLS LAST
            """)
            
            result = self.db.execute(query, {
                'list_type': list_type,
                'user_id': self.user_id
            }).fetchall()
            
            for row in result:
                db_domain = row[0]
                is_pattern = row[1]
                
                if is_pattern:
                    # Wildcard pattern matching (*.example.com)
                    pattern = db_domain.replace('*.', '.*\\.').replace('.', '\\.')
                    if re.match(f'^{pattern}$', domain):
                        return True
                else:
                    # Exact or suffix match
                    if domain == db_domain or domain.endswith('.' + db_domain):
                        return True
            
            # No match found in DB
            return None
            
        except Exception as e:
            # DB error - fall back to hardcoded lists
            print(f"Warning: DB list check failed: {e}")
            return None
    
    def _check_ssl(self, domain: str) -> bool:
        """
        Prüft SSL-Zertifikat
        (Vereinfacht - keine echte Chain-Validation)
        """
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    # Einfacher Check: Zertifikat existiert
                    return cert is not None
        except Exception:
            return False
    
    def _has_suspicious_patterns(self, domain: str) -> bool:
        """
        Erkennt verdächtige Domain-Muster
        - Zu viele Bindestriche
        - Zahlen + Buchstaben gemischt
        - Zu lange Subdomains
        """
        # Zu viele Bindestriche
        if domain.count('-') > 3:
            return True
        
        # Sehr lange Subdomains
        parts = domain.split('.')
        if any(len(part) > 30 for part in parts):
            return True
        
        # Gemischte Zahlen/Buchstaben (z.B. abc123def456.com)
        if re.search(r'[a-z]{2,}\d{2,}[a-z]{2,}', domain):
            return True
        
        return False


# Singleton Instance
_risk_analyzer_instance: Optional[DomainRiskAnalyzer] = None

def get_risk_analyzer(db_session=None, user_id: Optional[int] = None) -> DomainRiskAnalyzer:
    """
    Factory für DomainRiskAnalyzer
    
    Args:
        db_session: Optional SQLAlchemy Session for custom lists
        user_id: Optional User ID for user-specific lists
        
    Returns:
        DomainRiskAnalyzer instance with DB support if session provided
        
    Note: When db_session is provided, returns new instance (not singleton)
          to avoid session conflicts across requests.
    """
    global _risk_analyzer_instance
    
    # If DB session provided, always create new instance (per-request)
    if db_session is not None:
        return DomainRiskAnalyzer(db_session=db_session, user_id=user_id)
    
    # Otherwise use singleton (for backward compatibility)
    if _risk_analyzer_instance is None:
        _risk_analyzer_instance = DomainRiskAnalyzer()
    return _risk_analyzer_instance
