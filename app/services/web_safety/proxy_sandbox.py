"""
🧊 LAYER 3: Proxy-Sandbox (HTML Extractor)
Serverseitiger sicherer HTML-Abruf ohne JS, Cookies, Sessions
"""

from typing import Dict, Optional
import ipaddress
import socket
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
from datetime import datetime


class SSRFError(Exception):
    """Raised when a target URL resolves to a non-public address, or uses
    a non-HTTP(S) scheme - see ProxySandbox._check_target_is_public."""
    pass


class ProxySandbox:
    """
    Layer 3: Safe HTML Extraction
    
    Sicherheits-Features:
    - ❌ Kein JavaScript
    - ❌ Keine Cookies
    - ❌ Keine Sessions
    - ❌ Keine POST Requests
    - ❌ Nur GET → HTML/Text
    - ❌ Keine Frames/iFrames
    - ❌ Keine Downloads
    - ❌ Keine Weiterleitungen auf fremde Domains
    
    Extrahiert:
    - ✅ Überschriften (h1-h6)
    - ✅ Artikel-Texte (article, main, p)
    - ✅ Tabellen
    - ✅ Listen (ul, ol)
    - ✅ Metadaten (title, description)
    """
    
    # Safe User-Agent
    USER_AGENT = "Liara/1.0 (Privacy-focused AI Assistant; +https://liara.ai)"
    
    # Timeout für Requests
    TIMEOUT = 10  # Sekunden
    
    # Max Content Size (10 MB)
    MAX_CONTENT_SIZE = 10 * 1024 * 1024
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'de,en;q=0.9',
            'DNT': '1',  # Do Not Track
        })
        
        # Disable cookies
        self.session.cookies.clear()

    def _check_target_is_public(self, url: str) -> None:
        """
        Rejects non-http(s) schemes and any hostname that resolves to a
        private/loopback/link-local/reserved/multicast address - closes an
        SSRF gap that existed regardless of the same-domain redirect check
        below (that only compares hostname strings, never resolves DNS).
        Without this, a model deciding which URL to fetch based on search
        results could be steered (via page content, or a malicious/rebound
        DNS entry) into requesting http://127.0.0.1:..., an internal
        service, or a cloud metadata endpoint (169.254.169.254).

        Raises SSRFError if the target isn't safe to fetch.
        """
        parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            raise SSRFError(f'Unsupported scheme: {parsed.scheme or "(none)"}')

        hostname = parsed.hostname
        if not hostname:
            raise SSRFError('URL has no hostname')

        try:
            addresses = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
        except socket.gaierror as e:
            raise SSRFError(f'Could not resolve host: {hostname}') from e

        for addr in addresses:
            ip = ipaddress.ip_address(addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise SSRFError(f'Host "{hostname}" resolves to a non-public address ({addr})')


    def fetch_safe(self, url: str, allow_redirects: bool = True) -> Dict:
        """
        Sicherer HTML-Abruf
        
        Args:
            url: Target URL
            allow_redirects: Erlaube Weiterleitungen (nur same-domain)
        
        Returns:
            {
                'url': str,
                'final_url': str,
                'status_code': int,
                'content_type': str,
                'title': str,
                'headings': List[str],
                'paragraphs': List[str],
                'lists': List[str],
                'tables': List[Dict],
                'meta_description': str,
                'links': List[str],
                'images': List[str],
                'raw_html': str,
                'text_content': str,
                'timestamp': str,
                'error': Optional[str]
            }
        """
        result = {
            'url': url,
            'final_url': None,
            'status_code': None,
            'content_type': None,
            'title': '',
            'headings': [],
            'paragraphs': [],
            'lists': [],
            'tables': [],
            'meta_description': '',
            'links': [],
            'images': [],
            'raw_html': '',
            'text_content': '',
            'timestamp': datetime.utcnow().isoformat(),
            'error': None
        }
        
        try:
            # SSRF check: reject non-http(s) schemes and any hostname that
            # resolves to a private/loopback/link-local/reserved address
            # (127.0.0.1, RFC1918 ranges, 169.254.169.254 cloud metadata,
            # etc.) - previously unchecked entirely. Must happen before the
            # request is ever made, not just on the response.
            self._check_target_is_public(url)

            # Safe GET request
            response = self.session.get(
                url,
                timeout=self.TIMEOUT,
                allow_redirects=allow_redirects,
                stream=True  # Für Size-Check
            )

            result['status_code'] = response.status_code
            result['final_url'] = response.url
            result['content_type'] = response.headers.get('Content-Type', '')

            # Check redirect safety (same domain only)
            if allow_redirects and response.url != url:
                original_domain = urlparse(url).netloc
                final_domain = urlparse(response.url).netloc

                if original_domain != final_domain:
                    result['error'] = f'Cross-domain redirect blocked: {original_domain} → {final_domain}'
                    return result

                # Same-domain redirects still need the same SSRF check -
                # DNS for that domain could differ per-request (rebinding)
                # or simply not have been resolved yet if this is the
                # first time we've seen it redirect anywhere.
                self._check_target_is_public(response.url)
            
            # Check Content-Type (nur HTML)
            if 'text/html' not in result['content_type']:
                result['error'] = f'Invalid content type: {result["content_type"]}'
                return result
            
            # Check Content-Length (max 10 MB)
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > self.MAX_CONTENT_SIZE:
                result['error'] = f'Content too large: {content_length} bytes'
                return result
            
            # Read content (with size limit)
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.MAX_CONTENT_SIZE:
                    result['error'] = 'Content size limit exceeded'
                    return result
            
            html = content.decode('utf-8', errors='ignore')
            result['raw_html'] = html
            
            # Parse mit BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove scripts, styles, iframes
            for tag in soup(['script', 'style', 'iframe', 'noscript']):
                tag.decompose()
            
            # Extract data
            result['title'] = self._extract_title(soup)
            result['meta_description'] = self._extract_meta_description(soup)
            result['headings'] = self._extract_headings(soup)
            result['paragraphs'] = self._extract_paragraphs(soup)
            result['lists'] = self._extract_lists(soup)
            result['tables'] = self._extract_tables(soup)
            result['links'] = self._extract_links(soup, url)
            result['images'] = self._extract_images(soup, url)
            result['text_content'] = self._extract_text_content(soup)
            
        except SSRFError as e:
            result['error'] = f'Blocked: {str(e)}'
        except requests.exceptions.Timeout:
            result['error'] = f'Request timeout after {self.TIMEOUT}s'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Connection error'
        except requests.exceptions.TooManyRedirects:
            result['error'] = 'Too many redirects'
        except Exception as e:
            result['error'] = f'Fetch error: {str(e)}'
        
        return result
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrahiert Title"""
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else ''
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extrahiert Meta Description"""
        meta = soup.find('meta', attrs={'name': 'description'})
        return meta.get('content', '') if meta else ''
    
    def _extract_headings(self, soup: BeautifulSoup) -> list:
        """Extrahiert alle Headings (h1-h6)"""
        headings = []
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text(strip=True)
                if text:
                    headings.append(f'H{i}: {text}')
        return headings[:50]  # Max 50 headings
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> list:
        """Extrahiert Paragraphen"""
        paragraphs = []
        
        # Prioritize article/main content
        main_content = soup.find('article') or soup.find('main') or soup
        
        for p in main_content.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 30:  # Nur substanzielle Paragraphen
                paragraphs.append(text)
        
        return paragraphs[:100]  # Max 100 paragraphs
    
    def _extract_lists(self, soup: BeautifulSoup) -> list:
        """Extrahiert Listen (ul, ol)"""
        lists = []
        for ul in soup.find_all(['ul', 'ol']):
            items = [li.get_text(strip=True) for li in ul.find_all('li', recursive=False)]
            if items:
                lists.append(items)
        return lists[:20]  # Max 20 listen
    
    def _extract_tables(self, soup: BeautifulSoup) -> list:
        """Extrahiert Tabellen"""
        tables = []
        for table in soup.find_all('table')[:10]:  # Max 10 tables
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append({'rows': rows})
        return tables
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extrahiert Links (absolut)"""
        links = []
        for a in soup.find_all('a', href=True)[:100]:  # Max 100 links
            href = a['href']
            # Make absolute
            abs_url = urljoin(base_url, href)
            links.append(abs_url)
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extrahiert Image URLs"""
        images = []
        for img in soup.find_all('img', src=True)[:50]:  # Max 50 images
            src = img['src']
            abs_url = urljoin(base_url, src)
            images.append(abs_url)
        return images
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extrahiert gesamten Text (clean)"""
        # Prioritize main content areas
        main = soup.find('article') or soup.find('main') or soup.find('body') or soup
        
        text = main.get_text(separator='\n', strip=True)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Limit size
        max_chars = 50000
        if len(text) > max_chars:
            text = text[:max_chars] + '...[truncated]'
        
        return text


# Singleton Instance
_proxy_sandbox_instance: Optional[ProxySandbox] = None

def get_proxy_sandbox() -> ProxySandbox:
    """Factory für ProxySandbox (Singleton)"""
    global _proxy_sandbox_instance
    if _proxy_sandbox_instance is None:
        _proxy_sandbox_instance = ProxySandbox()
    return _proxy_sandbox_instance
