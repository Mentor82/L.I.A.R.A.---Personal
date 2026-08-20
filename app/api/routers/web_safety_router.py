"""
🌐 Web Safety API Router - 4-Layer Security System
User → Intent → Risk → Sandbox → Filter → LLM → Response Filter → User
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from core.database import get_db
from core.dependencies import get_current_user
from api.models.base_models import User
from services.web_safety import (
    get_intent_checker,
    get_risk_analyzer,
    get_proxy_sandbox,
    get_content_filter,
    get_response_filter
)
from sqlalchemy import text


router = APIRouter(prefix="/web", tags=["Web Safety"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(10, ge=1, le=50)


class WebFetchRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2000)
    extract_text: bool = True
    allow_redirects: bool = True


class RiskCheckRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2000)


class LogsRequest(BaseModel):
    limit: int = Field(50, ge=1, le=500)
    blocked_only: bool = False
    min_risk_score: Optional[int] = None


# ============================================================================
# Helper Functions
# ============================================================================

def log_web_access(
    db: Session,
    user_id: int,
    query: str,
    final_url: Optional[str],
    request_type: str,
    intent_risk: int,
    domain_risk: int,
    content_risk: int,
    response_risk: int,
    blocked: bool,
    blocked_reason: Optional[str],
    blocked_layer: Optional[str],
    status_code: Optional[int] = None,
    content_type: Optional[str] = None,
    response_time_ms: Optional[int] = None,
    ip_address: Optional[str] = None
) -> int:
    """
    Loggt Web-Zugriff in Database (Audit Trail)
    
    Returns:
        log_id
    """
    final_risk = max(intent_risk, domain_risk, content_risk, response_risk)
    
    # Risk Level
    if final_risk >= 80:
        risk_level = 'blocked'
    elif final_risk >= 60:
        risk_level = 'critical'
    elif final_risk >= 40:
        risk_level = 'unsafe'
    elif final_risk >= 20:
        risk_level = 'gray'
    else:
        risk_level = 'safe'
    
    sql = text("""
    INSERT INTO web_access_logs (
        user_id, query, final_url, request_type,
        intent_risk_score, domain_risk_score, content_risk_score, response_risk_score,
        final_risk_score, risk_level,
        blocked, blocked_reason, blocked_layer,
        status_code, content_type, response_time_ms, ip_address
    ) VALUES (
        :user_id, :query, :final_url, :request_type,
        :intent_risk, :domain_risk, :content_risk, :response_risk,
        :final_risk, :risk_level,
        :blocked, :blocked_reason, :blocked_layer,
        :status_code, :content_type, :response_time_ms, :ip_address
    ) RETURNING id
    """)
    
    result = db.execute(sql, {
        'user_id': user_id,
        'query': query,
        'final_url': final_url,
        'request_type': request_type,
        'intent_risk': intent_risk,
        'domain_risk': domain_risk,
        'content_risk': content_risk,
        'response_risk': response_risk,
        'final_risk': final_risk,
        'risk_level': risk_level,
        'blocked': blocked,
        'blocked_reason': blocked_reason,
        'blocked_layer': blocked_layer,
        'status_code': status_code,
        'content_type': content_type,
        'response_time_ms': response_time_ms,
        'ip_address': ip_address
    })
    db.commit()
    
    log_id = result.scalar()
    return log_id


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/fetch")
async def fetch_url_safe(
    request: WebFetchRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🧊 Sicherer URL-Abruf (4-Layer Security)
    
    **Flow**:
    1. Intent Check (Query Safety)
    2. Domain Risk Analysis
    3. Proxy Sandbox (HTML Extraction)
    4. Content Filter
    
    **Safety**:
    - Kein JavaScript
    - Keine Cookies
    - Keine POST Requests
    - Nur Safe Domains
    - Content Filtering
    """
    start_time = datetime.utcnow()
    
    # Extract User IP
    client_ip = http_request.client.host
    x_forwarded = http_request.headers.get('X-Forwarded-For')
    if x_forwarded:
        client_ip = x_forwarded.split(',')[0].strip()
    
    # LAYER 1: Intent Check (Query statt URL)
    intent_checker = get_intent_checker()
    query_safe, blocked_reason, intent_risk = intent_checker.check_query_safety(
        current_user.id, 
        f"fetch {request.url}"
    )
    
    if not query_safe:
        log_web_access(
            db, current_user.id, request.url, request.url, 'fetch',
            intent_risk, 0, 0, 0, True, blocked_reason, 'Layer1_Intent',
            ip_address=client_ip
        )
        raise HTTPException(status_code=403, detail={
            'blocked': True,
            'reason': blocked_reason,
            'layer': 'Intent Check (Layer 1)',
            'risk_score': intent_risk
        })
    
    # LAYER 2: Domain Risk Analysis
    risk_analyzer = get_risk_analyzer()
    domain_analysis = risk_analyzer.analyze_url(request.url)
    
    if not domain_analysis['is_safe']:
        log_web_access(
            db, current_user.id, request.url, request.url, 'fetch',
            intent_risk, domain_analysis['risk_score'], 0, 0,
            True, domain_analysis['blocked_reason'], 'Layer2_Domain',
            ip_address=client_ip
        )
        raise HTTPException(status_code=403, detail={
            'blocked': True,
            'reason': domain_analysis['blocked_reason'],
            'layer': 'Domain Risk Analysis (Layer 2)',
            'risk_score': domain_analysis['risk_score'],
            'domain': domain_analysis['domain'],
            'warnings': domain_analysis['warnings']
        })
    
    # LAYER 3: Proxy Sandbox (Safe Fetch)
    sandbox = get_proxy_sandbox()
    fetch_result = sandbox.fetch_safe(request.url, request.allow_redirects)
    
    if fetch_result['error']:
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        log_web_access(
            db, current_user.id, request.url, fetch_result.get('final_url'), 'fetch',
            intent_risk, domain_analysis['risk_score'], 0, 0,
            True, f"Fetch error: {fetch_result['error']}", 'Layer3_Sandbox',
            status_code=fetch_result.get('status_code'),
            response_time_ms=response_time,
            ip_address=client_ip
        )
        raise HTTPException(status_code=502, detail={
            'blocked': True,
            'reason': fetch_result['error'],
            'layer': 'Proxy Sandbox (Layer 3)'
        })
    
    # LAYER 4: Content Filter
    content_filter = get_content_filter()
    filtered_html = content_filter.filter_html(fetch_result['raw_html'])
    filtered_text = content_filter.filter_text(fetch_result['text_content'])
    
    content_risk = 0
    if filtered_text['toxic_content_found']:
        content_risk = 60
    if filtered_text['affiliate_links_removed'] > 5:
        content_risk += 20
    
    # Calculate response time
    response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    # Log successful fetch
    log_web_access(
        db, current_user.id, request.url, fetch_result['final_url'], 'fetch',
        intent_risk, domain_analysis['risk_score'], content_risk, 0,
        False, None, None,
        status_code=fetch_result['status_code'],
        content_type=fetch_result['content_type'],
        response_time_ms=response_time,
        ip_address=client_ip
    )
    
    return {
        'url': request.url,
        'final_url': fetch_result['final_url'],
        'status_code': fetch_result['status_code'],
        'title': fetch_result['title'],
        'meta_description': fetch_result['meta_description'],
        'headings': fetch_result['headings'][:10],
        'paragraphs': fetch_result['paragraphs'][:20] if request.extract_text else [],
        'text_content': filtered_text['filtered_text'][:5000] if request.extract_text else '',
        'links': fetch_result['links'][:50],
        'images': fetch_result['images'][:20],
        'risk_analysis': {
            'intent_risk': intent_risk,
            'domain_risk': domain_analysis['risk_score'],
            'content_risk': content_risk,
            'domain_category': domain_analysis['category'],
            'toxic_content_found': filtered_text['toxic_content_found'],
            'affiliate_links_removed': filtered_text['affiliate_links_removed']
        },
        'response_time_ms': response_time,
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/risk")
async def check_url_risk(
    request: RiskCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 URL Risk-Check (ohne Abruf)
    
    Prüft nur Domain Reputation, kein Content-Fetch
    """
    risk_analyzer = get_risk_analyzer()
    analysis = risk_analyzer.analyze_url(request.url)
    
    return {
        'url': request.url,
        'domain': analysis['domain'],
        'risk_score': analysis['risk_score'],
        'risk_level': analysis['risk_level'],
        'is_safe': analysis['is_safe'],
        'category': analysis['category'],
        'has_https': analysis['has_https'],
        'ssl_valid': analysis['ssl_valid'],
        'blocked_reason': analysis['blocked_reason'],
        'warnings': analysis['warnings'],
        'timestamp': datetime.utcnow().isoformat()
    }


@router.get("/logs")
async def get_web_access_logs(
    limit: int = 50,
    blocked_only: bool = False,
    min_risk_score: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Web Access Logs (Audit Trail)
    
    Zeigt alle Web-Zugriffe des Users mit Risk-Scores
    """
    sql = text("""
    SELECT 
        id, query, final_url, request_type,
        intent_risk_score, domain_risk_score, content_risk_score, response_risk_score,
        final_risk_score, risk_level,
        blocked, blocked_reason, blocked_layer,
        status_code, created_at
    FROM web_access_logs
    WHERE user_id = :user_id
        AND (:blocked_only = false OR blocked = true)
        AND (:min_risk IS NULL OR final_risk_score >= :min_risk)
    ORDER BY created_at DESC
    LIMIT :limit
    """)
    
    result = db.execute(sql, {
        'user_id': current_user.id,
        'blocked_only': blocked_only,
        'min_risk': min_risk_score,
        'limit': limit
    })
    
    logs = []
    for row in result:
        logs.append({
            'id': row.id,
            'query': row.query,
            'final_url': row.final_url,
            'request_type': row.request_type,
            'risk_scores': {
                'intent': row.intent_risk_score,
                'domain': row.domain_risk_score,
                'content': row.content_risk_score,
                'response': row.response_risk_score,
                'final': row.final_risk_score,
                'level': row.risk_level
            },
            'blocked': row.blocked,
            'blocked_reason': row.blocked_reason,
            'blocked_layer': row.blocked_layer,
            'status_code': row.status_code,
            'created_at': str(row.created_at)
        })
    
    return {
        'logs': logs,
        'count': len(logs),
        'user_id': current_user.id
    }


@router.get("/stats")
async def get_web_safety_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📈 Web Safety Statistiken
    """
    sql = text("""
    SELECT 
        COUNT(*) as total_requests,
        COUNT(*) FILTER (WHERE blocked = true) as blocked_requests,
        COUNT(*) FILTER (WHERE blocked = false) as successful_requests,
        AVG(final_risk_score) as avg_risk_score,
        COUNT(*) FILTER (WHERE blocked_layer = 'Layer1_Intent') as blocked_layer1,
        COUNT(*) FILTER (WHERE blocked_layer = 'Layer2_Domain') as blocked_layer2,
        COUNT(*) FILTER (WHERE blocked_layer = 'Layer3_Sandbox') as blocked_layer3,
        AVG(response_time_ms) as avg_response_time_ms
    FROM web_access_logs
    WHERE user_id = :user_id
        AND created_at > NOW() - INTERVAL '30 days'
    """)
    
    result = db.execute(sql, {'user_id': current_user.id}).first()
    
    # Rate Limit Status
    intent_checker = get_intent_checker()
    rate_status = intent_checker.get_rate_limit_status(current_user.id)
    
    return {
        'total_requests': result.total_requests or 0,
        'blocked_requests': result.blocked_requests or 0,
        'successful_requests': result.successful_requests or 0,
        'avg_risk_score': round(result.avg_risk_score or 0, 2),
        'blocks_by_layer': {
            'layer1_intent': result.blocked_layer1 or 0,
            'layer2_domain': result.blocked_layer2 or 0,
            'layer3_sandbox': result.blocked_layer3 or 0
        },
        'avg_response_time_ms': round(result.avg_response_time_ms or 0, 2),
        'rate_limit': rate_status,
        'period': 'last_30_days'
    }


@router.get("/rate-limit")
async def get_rate_limit_status(
    current_user: User = Depends(get_current_user)
):
    """
    ⏱️ Rate-Limit Status
    """
    intent_checker = get_intent_checker()
    status = intent_checker.get_rate_limit_status(current_user.id)
    return status


# ============================================================================
# 🛡️ Custom Lists Management (Whitelist/Graylist/Blacklist)
# ============================================================================

class DomainListRequest(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)
    list_type: str = Field(..., pattern="^(whitelist|graylist|blacklist)$")
    reason: Optional[str] = Field(None, max_length=500)
    is_pattern: bool = False  # TRUE for *.example.com wildcards


class DomainListResponse(BaseModel):
    id: int
    user_id: Optional[int]
    domain: str
    list_type: str
    reason: Optional[str]
    is_pattern: bool
    is_global: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime


@router.get("/lists")
async def get_custom_lists(
    list_type: Optional[str] = None,
    include_global: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📋 Get Custom Domain Lists
    
    Returns user-specific and optionally global lists.
    Filter by list_type: whitelist, graylist, blacklist
    """
    query = """
        SELECT 
            id, user_id, domain, list_type, reason, is_pattern,
            (user_id IS NULL) as is_global,
            created_by, created_at, updated_at
        FROM web_safety_lists
        WHERE (user_id = :user_id OR (user_id IS NULL AND :include_global))
    """
    
    params = {'user_id': current_user.id, 'include_global': include_global}
    
    if list_type:
        query += " AND list_type = :list_type"
        params['list_type'] = list_type
    
    query += " ORDER BY list_type, domain"
    
    result = db.execute(text(query), params).fetchall()
    
    return {
        'total': len(result),
        'lists': [dict(row._mapping) for row in result]
    }


@router.post("/lists")
async def add_to_list(
    request: DomainListRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ➕ Add Domain to Custom List
    
    Adds domain to user-specific whitelist/graylist/blacklist.
    """
    # Normalize domain (lowercase, remove www)
    domain = request.domain.lower().strip()
    if domain.startswith('www.'):
        domain = domain[4:]
    
    try:
        result = db.execute(text("""
            INSERT INTO web_safety_lists 
                (user_id, domain, list_type, reason, is_pattern, created_by)
            VALUES 
                (:user_id, :domain, :list_type, :reason, :is_pattern, :created_by)
            RETURNING id, created_at
        """), {
            'user_id': current_user.id,
            'domain': domain,
            'list_type': request.list_type,
            'reason': request.reason,
            'is_pattern': request.is_pattern,
            'created_by': current_user.id
        })
        db.commit()
        
        row = result.fetchone()
        
        return {
            'success': True,
            'id': row[0],
            'domain': domain,
            'list_type': request.list_type,
            'created_at': row[1]
        }
        
    except Exception as e:
        db.rollback()
        if 'unique_user_domain_list' in str(e):
            raise HTTPException(status_code=409, detail=f"Domain already in {request.list_type}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/lists/{list_id}")
async def remove_from_list(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ❌ Remove Domain from Custom List
    
    Only allows deletion of own entries (or admin for global entries).
    """
    # Check ownership
    check = db.execute(text("""
        SELECT user_id, domain, list_type 
        FROM web_safety_lists 
        WHERE id = :id
    """), {'id': list_id}).fetchone()
    
    if not check:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # User can only delete own entries (user_id match)
    # TODO: Add admin check for global entries (user_id IS NULL)
    if check[0] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this entry")
    
    db.execute(text("DELETE FROM web_safety_lists WHERE id = :id"), {'id': list_id})
    db.commit()
    
    return {
        'success': True,
        'deleted': {
            'id': list_id,
            'domain': check[1],
            'list_type': check[2]
        }
    }


@router.post("/lists/bulk")
async def bulk_import_lists(
    lists: List[DomainListRequest],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📦 Bulk Import Domain Lists
    
    Import multiple domains at once. Skips duplicates.
    """
    imported = 0
    skipped = 0
    errors = []
    
    for item in lists:
        domain = item.domain.lower().strip()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        try:
            db.execute(text("""
                INSERT INTO web_safety_lists 
                    (user_id, domain, list_type, reason, is_pattern, created_by)
                VALUES 
                    (:user_id, :domain, :list_type, :reason, :is_pattern, :created_by)
                ON CONFLICT (user_id, domain, list_type) DO NOTHING
            """), {
                'user_id': current_user.id,
                'domain': domain,
                'list_type': item.list_type,
                'reason': item.reason,
                'is_pattern': item.is_pattern,
                'created_by': current_user.id
            })
            
            if db.execute(text("SELECT * FROM web_safety_lists WHERE user_id = :user_id AND domain = :domain AND list_type = :list_type"), 
                         {'user_id': current_user.id, 'domain': domain, 'list_type': item.list_type}).fetchone():
                imported += 1
            else:
                skipped += 1
                
        except Exception as e:
            errors.append({'domain': domain, 'error': str(e)})
    
    db.commit()
    
    return {
        'success': True,
        'imported': imported,
        'skipped': skipped,
        'errors': errors
    }
