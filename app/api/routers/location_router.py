"""
📍 Location API Router
IP-based location detection with privacy consent
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict
from sqlalchemy.orm import Session
import logging

from core.database import get_db
from core.dependencies import require_active_user
from api.models.base_models import User
from services.location_service import get_location_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/location", tags=["location"])


class LocationDetectResponse(BaseModel):
    """Response for location detection"""
    success: bool
    location: Optional[Dict] = None
    message: str
    consent_required: bool = True


class LocationConsentRequest(BaseModel):
    """Request to save location with consent"""
    consent_given: bool
    location_data: Optional[Dict] = None


@router.post("/detect", response_model=LocationDetectResponse)
async def detect_location(
    request: Request,
    current_user: User = Depends(require_active_user)
) -> LocationDetectResponse:
    """
    Detect user location from IP address.
    
    Returns location data but does NOT store it until user gives consent.
    """
    try:
        location_service = get_location_service()
        
        # Get client IP
        client_ip = request.client.host
        
        # Check for forwarded IP (behind proxy/nginx)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        logger.info(f"Detecting location for user {current_user.id} from IP: {client_ip}")
        
        # Detect location (does not store yet)
        location_data = location_service.get_location_from_ip(client_ip)
        
        if 'error' in location_data:
            return LocationDetectResponse(
                success=False,
                location=None,
                message=f"Location detection failed: {location_data.get('error')}",
                consent_required=False
            )
        
        return LocationDetectResponse(
            success=True,
            location=location_data,
            message="Location detected successfully. Please provide consent to save.",
            consent_required=True
        )
        
    except Exception as e:
        logger.error(f"Location detection error for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_location_with_consent(
    consent_request: LocationConsentRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Save user location with explicit consent.
    
    Only saves if consent_given=true and valid location_data provided.
    """
    try:
        if not consent_request.consent_given:
            return {
                "success": False,
                "message": "Consent not given. Location not saved."
            }
        
        if not consent_request.location_data:
            raise HTTPException(status_code=400, detail="No location data provided")
        
        location_service = get_location_service()
        
        # Save location with consent
        success = location_service.save_user_location(
            db=db,
            user_id=current_user.id,
            location_data=consent_request.location_data,
            consent_given=True
        )
        
        if success:
            logger.info(f"Location saved for user {current_user.id} with consent")
            return {
                "success": True,
                "message": f"Location ({consent_request.location_data.get('city')}) saved successfully with your consent."
            }
        else:
            return {
                "success": False,
                "message": "Failed to save location."
            }
            
    except Exception as e:
        logger.error(f"Save location error for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_location(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get user's stored location (if consent was given).
    """
    try:
        location_service = get_location_service()
        location = location_service.get_user_location(db, current_user.id)
        
        if location:
            return {
                "success": True,
                "location": location
            }
        else:
            return {
                "success": False,
                "message": "No location stored (or consent not given)"
            }
            
    except Exception as e:
        logger.error(f"Get location error for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/revoke")
async def revoke_location_consent(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Revoke location consent and delete stored location data.
    """
    try:
        location_service = get_location_service()
        success = location_service.revoke_location_consent(db, current_user.id)
        
        if success:
            return {
                "success": True,
                "message": "Location consent revoked and data deleted."
            }
        else:
            return {
                "success": False,
                "message": "Failed to revoke consent."
            }
            
    except Exception as e:
        logger.error(f"Revoke location error for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
