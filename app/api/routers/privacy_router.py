"""
Privacy & Location Consent API Router

Endpoints für Privacy-Einstellungen:
- Location Consent Management
- Privacy Settings (Auto-Delete, Search History)
- Data Export/Delete (DSGVO-konform)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional

from core.database import get_db
from core.dependencies import get_current_user
from api.schemas.user_schemas import UserResponse
from services.location_service import get_location_service

router = APIRouter(prefix="/privacy", tags=["privacy"])


# ============================================================================
# LOCATION CONSENT ENDPOINTS
# ============================================================================

@router.get("/location/consent")
async def get_location_consent_status(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Aktuellen Location-Consent-Status abrufen
    
    Returns:
        - consent_given: bool
        - city, region, country (wenn consent=true)
        - last_updated: timestamp
    """
    location_service = get_location_service()
    location_data = location_service.get_user_location(db, current_user.id)
    
    if not location_data:
        return {
            "consent_given": False,
            "location": None,
            "last_updated": None
        }
    
    return {
        "consent_given": location_data.get("consent_given", False),
        "location": {
            "city": location_data.get("city"),
            "region": location_data.get("region"),
            "country": location_data.get("country"),
            "timezone": location_data.get("timezone")
        } if location_data.get("consent_given") else None,
        "last_updated": location_data.get("detected_at")
    }


@router.post("/location/consent")
async def grant_location_consent(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Location-Tracking Consent erteilen
    
    Führt automatisch Location-Detection durch und speichert Ergebnis
    
    Returns:
        - success: bool
        - location: detected location data
    """
    location_service = get_location_service()
    
    try:
        # Detect location (IP-based)
        location_data = location_service.get_location_from_ip()
        
        if "error" in location_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Location detection failed: {location_data['error']}"
            )
        
        # Save location with consent
        success = location_service.save_user_location(
            db=db,
            user_id=current_user.id,
            location_data=location_data,
            consent_given=True
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save location data"
            )
        
        return {
            "success": True,
            "message": "Location consent granted",
            "location": {
                "city": location_data.get("city"),
                "region": location_data.get("region"),
                "country": location_data.get("country"),
                "timezone": location_data.get("timezone")
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process consent: {str(e)}"
        )


@router.delete("/location")
async def revoke_location_consent(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Location-Consent widerrufen und alle Location-Daten löschen
    
    DSGVO-konform: Sofortige Löschung aller Standort-Daten
    """
    try:
        # Delete location data from database
        db.execute(
            text("DELETE FROM user_location_preferences WHERE user_id = :user_id"),
            {"user_id": current_user.id}
        )
        db.commit()
        
        return {
            "success": True,
            "message": "Location data deleted and consent revoked"
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke consent: {str(e)}"
        )


# ============================================================================
# PRIVACY SETTINGS
# ============================================================================

@router.get("/settings")
async def get_privacy_settings(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Privacy-Einstellungen des Users abrufen
    
    Returns:
        - location_tracking: bool
        - web_search_history: bool
        - auto_delete_days: int (0 = disabled)
        - data_export_available: bool
    """
    # Check location consent
    location_result = db.execute(
        text("SELECT consent_given FROM user_location_preferences WHERE user_id = :user_id ORDER BY detected_at DESC LIMIT 1"),
        {"user_id": current_user.id}
    ).fetchone()
    
    location_tracking = location_result[0] if location_result else False
    
    # Get privacy settings from database
    privacy_settings = db.execute(
        text("SELECT store_search_history, auto_delete_searches_after_days FROM user_privacy_settings WHERE user_id = :user_id"),
        {"user_id": current_user.id}
    ).fetchone()
    
    if privacy_settings:
        web_search_history = privacy_settings[0]
        # Use the actual DB value, don't override with default
        auto_delete_days = privacy_settings[1] if privacy_settings[1] is not None else 30
    else:
        # Create default settings if not exists
        db.execute(
            text("""
            INSERT INTO user_privacy_settings (user_id, allow_web_search, store_search_history, auto_delete_searches_after_days)
            VALUES (:user_id, true, true, 30)
            """),
            {"user_id": current_user.id}
        )
        db.commit()
        web_search_history = True
        auto_delete_days = 30
    
    return {
        "location_tracking": location_tracking,
        "web_search_history": web_search_history,
        "auto_delete_days": auto_delete_days,
        "data_export_available": True
    }


@router.post("/settings")
async def update_privacy_settings(
    web_search_history: Optional[bool] = None,
    auto_delete_days: Optional[int] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Privacy-Einstellungen aktualisieren
    
    Args:
        web_search_history: Web-Search-History aktivieren/deaktivieren
        auto_delete_days: Auto-Delete nach X Tagen (0 = disabled)
    """
    try:
        # Check if settings exist
        existing = db.execute(
            text("SELECT id FROM user_privacy_settings WHERE user_id = :user_id"),
            {"user_id": current_user.id}
        ).fetchone()
        
        if existing:
            # Update existing settings
            update_parts = []
            params = {"user_id": current_user.id}
            
            if web_search_history is not None:
                update_parts.append("store_search_history = :web_search_history")
                params["web_search_history"] = web_search_history
            
            if auto_delete_days is not None:
                update_parts.append("auto_delete_searches_after_days = :auto_delete_days")
                params["auto_delete_days"] = auto_delete_days
            
            if update_parts:
                update_parts.append("updated_at = CURRENT_TIMESTAMP")
                sql = f"UPDATE user_privacy_settings SET {', '.join(update_parts)} WHERE user_id = :user_id"
                db.execute(text(sql), params)
                db.commit()
        else:
            # Create new settings
            db.execute(
                text("""
                INSERT INTO user_privacy_settings 
                (user_id, allow_web_search, store_search_history, auto_delete_searches_after_days)
                VALUES (:user_id, true, :web_search_history, :auto_delete_days)
                """),
                {
                    "user_id": current_user.id,
                    "web_search_history": web_search_history if web_search_history is not None else True,
                    "auto_delete_days": auto_delete_days if auto_delete_days is not None else 30
                }
            )
            db.commit()
        
        return {
            "success": True,
            "message": "Privacy settings updated successfully",
            "settings": {
                "web_search_history": web_search_history,
                "auto_delete_days": auto_delete_days
            }
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


# ============================================================================
# DATA EXPORT & DELETE (DSGVO)
# ============================================================================

@router.get("/export")
async def export_user_data(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    DSGVO-konformer Daten-Export
    
    Returns:
        JSON mit allen gespeicherten User-Daten:
        - Location data
        - Web access logs
        - Chat history
        - Tasks, Notes, Calendar
    """
    export_data = {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role
        },
        "export_timestamp": datetime.now().isoformat(),
        "data": {}
    }
    
    # Location data
    location_result = db.execute(
        text("SELECT * FROM user_location_preferences WHERE user_id = :user_id"),
        {"user_id": current_user.id}
    ).fetchall()
    
    export_data["data"]["locations"] = [dict(row._mapping) for row in location_result]
    
    # Web access logs
    web_logs = db.execute(
        text("SELECT * FROM web_access_logs WHERE user_id = :user_id ORDER BY created_at DESC LIMIT 1000"),
        {"user_id": current_user.id}
    ).fetchall()
    
    export_data["data"]["web_access_logs"] = [dict(row._mapping) for row in web_logs]
    
    # TODO: Add chat history, tasks, notes, calendar events
    
    return export_data


@router.delete("/all-data")
async def delete_all_user_data(
    confirm: bool = False,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    DSGVO "Recht auf Vergessenwerden"
    
    Löscht ALLE User-Daten (außer Account selbst)
    
    Args:
        confirm: Muss true sein zur Bestätigung
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set confirm=true"
        )
    
    try:
        # Delete location data
        db.execute(text("DELETE FROM user_location_preferences WHERE user_id = :user_id"), {"user_id": current_user.id})

        # Delete web access logs
        db.execute(text("DELETE FROM web_access_logs WHERE user_id = :user_id"), {"user_id": current_user.id})

        # Delete chat history - messages first (FK references chat_sessions),
        # matched via session ownership so assistant replies (which carry no
        # user_id of their own) in the user's own sessions are removed too.
        db.execute(
            text("DELETE FROM chat_messages WHERE session_id IN "
                 "(SELECT id FROM chat_sessions WHERE user_id = :user_id)"),
            {"user_id": current_user.id}
        )
        db.execute(text("DELETE FROM chat_sessions WHERE user_id = :user_id"), {"user_id": current_user.id})

        # Delete tasks, notes, calendar events
        db.execute(text("DELETE FROM tasks WHERE user_id = :user_id"), {"user_id": current_user.id})
        db.execute(text("DELETE FROM notes WHERE user_id = :user_id"), {"user_id": current_user.id})
        db.execute(text("DELETE FROM calendar_events WHERE user_id = :user_id"), {"user_id": current_user.id})

        db.commit()
        
        return {
            "success": True,
            "message": "All user data deleted successfully"
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete data: {str(e)}"
        )
