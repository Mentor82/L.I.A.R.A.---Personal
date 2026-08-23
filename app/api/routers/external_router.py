"""
🌍 Web Search & Location API Router
Privacy-focused external information retrieval
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from core.database import get_db
from core.dependencies import get_current_user
from api.models.base_models import User
from services.web_search_service import get_web_search_service
from services.location_service import get_location_service


router = APIRouter(prefix="/external", tags=["External Information"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    search_type: str = Field("instant", pattern="^(instant|wikipedia|weather)$")
    language: str = Field("de", pattern="^(de|en)$")


class WebSearchResponse(BaseModel):
    query: str
    search_type: str
    result: dict
    formatted_context: str
    timestamp: str


class LocationDetectionRequest(BaseModel):
    ip_address: Optional[str] = None  # Auto-detect if not provided
    save_with_consent: bool = False


class LocationConsentRequest(BaseModel):
    grant_consent: bool
    allow_llm_usage: bool = True


class PrivacySettingsUpdate(BaseModel):
    allow_location_detection: Optional[bool] = None
    allow_location_storage: Optional[bool] = None
    share_location_with_llm: Optional[bool] = None
    allow_web_search: Optional[bool] = None
    store_search_history: Optional[bool] = None


# ============================================================================
# Web Search Endpoints
# ============================================================================

@router.post("/search", response_model=WebSearchResponse)
async def web_search(
    request: WebSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Web-Suche mit Privacy-First Ansatz
    
    Search Types:
    - **instant**: DuckDuckGo Instant Answer (schnell, präzise)
    - **wikipedia**: Wikipedia Zusammenfassung
    - **weather**: Wetter-Information (Open-Meteo)
    
    Privacy:
    - Keine Speicherung ohne Consent
    - Keine Tracking-Cookies
    - Privacy-focused APIs (DuckDuckGo, Wikipedia, Open-Meteo)
    """
    web_search = get_web_search_service()
    
    # Execute search based on type
    if request.search_type == 'wikipedia':
        result = web_search.search_wikipedia(request.query, request.language)
        formatted = web_search.format_for_llm(result, 'wikipedia')
    
    elif request.search_type == 'weather':
        result = web_search.get_weather_info(request.query)
        formatted = web_search.format_for_llm(result, 'weather')
    
    else:  # instant
        result = await web_search.search_instant_answer(request.query)
        formatted = web_search.format_for_llm(result, 'search')
    
    # TODO: Store in search history if user has consent
    # (Would check user_privacy_settings.store_search_history)
    
    return WebSearchResponse(
        query=request.query,
        search_type=request.search_type,
        result=result,
        formatted_context=formatted,
        timestamp=datetime.utcnow().isoformat()
    )


# ============================================================================
# Location Detection Endpoints
# ============================================================================

@router.post("/location/detect")
async def detect_location(
    request: LocationDetectionRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📍 Standort-Erkennung (Privacy-Conscious)
    
    WICHTIG - Privacy:
    - IP-Adresse wird NICHT gespeichert
    - Nur abgeleitete Location-Daten (Stadt/Region Ebene)
    - Speicherung NUR mit expliziter Zustimmung
    - Jederzeit widerrufbar
    
    Detection:
    - Automatisch aus Request IP (wenn ip_address=None)
    - Oder manuell angegebene IP
    
    Args:
        save_with_consent: Speichere Ergebnis (benötigt Zustimmung)
    """
    location_service = get_location_service()
    
    # Get IP from request if not provided
    client_ip = request.ip_address
    if not client_ip:
        # Extract from request headers (considering proxy)
        client_ip = http_request.client.host
        x_forwarded_for = http_request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0].strip()
    
    # Detect location (IP NOT stored)
    location_data = location_service.get_location_from_ip(client_ip)
    
    # Save if consent given
    if request.save_with_consent and 'error' not in location_data:
        saved = location_service.save_user_location(
            db=db,
            user_id=current_user.id,
            location_data=location_data,
            consent_given=True
        )
        location_data['saved'] = saved
    else:
        location_data['saved'] = False
    
    return location_data


@router.get("/location/current")
async def get_current_location(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📍 Gespeicherten Standort abrufen
    
    Gibt nur Daten zurück wenn:
    - Consent wurde gegeben
    - Daten wurden gespeichert
    """
    location_service = get_location_service()
    location = location_service.get_user_location(db, current_user.id)
    
    if not location:
        raise HTTPException(
            status_code=404, 
            detail="Kein Standort gespeichert oder Consent nicht gegeben"
        )
    
    return location


@router.post("/location/consent")
async def update_location_consent(
    request: LocationConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ✅ Location Consent verwalten
    
    Args:
        grant_consent: true = Erlaube Location-Speicherung, false = Widerrufe
        allow_llm_usage: Erlaube Verwendung in LLM Context
    """
    location_service = get_location_service()
    
    from sqlalchemy import text
    
    if request.grant_consent:
        # Update privacy settings to allow location
        sql = text("""
        UPDATE user_privacy_settings
        SET allow_location_detection = true,
            allow_location_storage = true,
            share_location_with_llm = :allow_llm,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = :user_id
        """)
        
        db.execute(sql, {
            'user_id': current_user.id,
            'allow_llm': request.allow_llm_usage
        })
        db.commit()
        
        return {
            'status': 'consent_granted',
            'message': 'Standort-Erkennung aktiviert',
            'allow_llm_usage': request.allow_llm_usage
        }
    
    else:
        # Revoke consent and delete location data
        location_service.revoke_location_consent(db, current_user.id)
        
        sql = text("""
        UPDATE user_privacy_settings
        SET allow_location_detection = false,
            allow_location_storage = false,
            share_location_with_llm = false,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = :user_id
        """)
        
        db.execute(sql, {'user_id': current_user.id})
        db.commit()
        
        return {
            'status': 'consent_revoked',
            'message': 'Standort-Daten gelöscht, Consent widerrufen'
        }


# ============================================================================
# Privacy Settings Endpoints
# ============================================================================

@router.get("/privacy/settings")
async def get_privacy_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔒 Privacy-Einstellungen abrufen
    """
    from sqlalchemy import text
    
    sql = text("""
    SELECT * FROM user_privacy_settings
    WHERE user_id = :user_id
    """)
    
    result = db.execute(sql, {'user_id': current_user.id}).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Privacy settings not found")
    
    return {
        'allow_location_detection': result.allow_location_detection,
        'allow_location_storage': result.allow_location_storage,
        'share_location_with_llm': result.share_location_with_llm,
        'allow_web_search': result.allow_web_search,
        'store_search_history': result.store_search_history,
        'allow_search_for_training': result.allow_search_for_training,
        'auto_delete_location_after_days': result.auto_delete_location_after_days,
        'auto_delete_searches_after_days': result.auto_delete_searches_after_days,
        'updated_at': str(result.updated_at)
    }


@router.patch("/privacy/settings")
async def update_privacy_settings(
    request: PrivacySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔒 Privacy-Einstellungen aktualisieren
    
    Granulare Kontrolle über:
    - Location Detection & Storage
    - Web Search
    - Search History
    - Data Retention
    """
    from sqlalchemy import text
    
    update_fields = []
    params = {'user_id': current_user.id}
    
    if request.allow_location_detection is not None:
        update_fields.append("allow_location_detection = :loc_detect")
        params['loc_detect'] = request.allow_location_detection
    
    if request.allow_location_storage is not None:
        update_fields.append("allow_location_storage = :loc_storage")
        params['loc_storage'] = request.allow_location_storage
    
    if request.share_location_with_llm is not None:
        update_fields.append("share_location_with_llm = :loc_llm")
        params['loc_llm'] = request.share_location_with_llm
    
    if request.allow_web_search is not None:
        update_fields.append("allow_web_search = :web_search")
        params['web_search'] = request.allow_web_search
    
    if request.store_search_history is not None:
        update_fields.append("store_search_history = :search_hist")
        params['search_hist'] = request.store_search_history
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    sql = text(f"""
    UPDATE user_privacy_settings
    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
    WHERE user_id = :user_id
    """)
    
    db.execute(sql, params)
    db.commit()
    
    return {
        'status': 'updated',
        'message': 'Privacy-Einstellungen aktualisiert'
    }


@router.delete("/privacy/delete-all-data")
async def delete_all_external_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🗑️ Alle externen Daten löschen
    
    WARNUNG: Löscht unwiderruflich:
    - Standort-Daten
    - Such-Historie
    - Alle externen Informationen
    """
    from sqlalchemy import text
    
    # Delete location data
    db.execute(
        text("DELETE FROM user_location_preferences WHERE user_id = :user_id"),
        {'user_id': current_user.id}
    )
    
    # Delete search history
    db.execute(
        text("DELETE FROM user_search_history WHERE user_id = :user_id"),
        {'user_id': current_user.id}
    )
    
    # Reset privacy settings to defaults
    db.execute(text("""
    UPDATE user_privacy_settings
    SET allow_location_detection = false,
        allow_location_storage = false,
        share_location_with_llm = false,
        store_search_history = false,
        allow_search_for_training = false,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = :user_id
    """), {'user_id': current_user.id})
    
    db.commit()
    
    return {
        'status': 'deleted',
        'message': 'Alle externen Daten wurden gelöscht',
        'timestamp': datetime.utcnow().isoformat()
    }
