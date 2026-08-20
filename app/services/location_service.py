"""
📍 LIARA Location Service
Privacy-conscious user location detection with explicit consent
"""

import requests
from typing import Optional, Dict
import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LocationService:
    """Privacy-focused location detection service"""
    
    def __init__(self):
        # ip-api.com (free, no API key, privacy-focused)
        self.ipapi_url = "http://ip-api.com/json/"
        self.user_agent = "Liara/1.0 (Privacy-focused AI Assistant)"
    
    def get_location_from_ip(self, ip_address: Optional[str] = None) -> Dict:
        """
        Get approximate location from IP address
        
        PRIVACY NOTE: Only uses IP for general location (city/region level)
        Does NOT store IP addresses, only derived location data with user consent
        
        Args:
            ip_address: IP address to check (None = auto-detect from request)
            
        Returns:
            Location information dict
        """
        try:
            url = self.ipapi_url + (ip_address if ip_address else '')
            
            # Request only essential fields to minimize data collection
            params = {
                'fields': 'status,country,countryCode,region,regionName,city,timezone,lat,lon'
            }
            
            response = requests.get(
                url,
                params=params,
                headers={'User-Agent': self.user_agent},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'fail':
                return {'error': 'Location detection failed', 'privacy_note': 'No data collected'}
            
            # Return location WITHOUT storing IP
            return {
                'country': data.get('country'),
                'country_code': data.get('countryCode'),
                'region': data.get('regionName'),
                'region_code': data.get('region'),
                'city': data.get('city'),
                'timezone': data.get('timezone'),
                'latitude': data.get('lat'),
                'longitude': data.get('lon'),
                'detected_at': datetime.utcnow().isoformat(),
                'privacy_note': 'IP address not stored, only derived location data',
                'consent_required': True
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Location detection error: {e}")
            return {'error': str(e), 'privacy_note': 'Detection failed, no data collected'}
    
    def save_user_location(
        self, 
        db: Session, 
        user_id: int, 
        location_data: Dict,
        consent_given: bool = False
    ) -> bool:
        """
        Save user location to database (ONLY if consent given)
        
        Args:
            db: Database session
            user_id: User ID
            location_data: Location data from get_location_from_ip
            consent_given: Explicit user consent required
            
        Returns:
            Success status
        """
        if not consent_given:
            logger.warning(f"Location save blocked for user {user_id}: No consent")
            return False
        
        if 'error' in location_data:
            return False
        
        try:
            # Store in user preferences table
            sql = text("""
            INSERT INTO user_location_preferences
                (user_id, country, country_code, region, city, timezone, 
                 latitude, longitude, consent_given, detected_at, updated_at)
            VALUES
                (:user_id, :country, :country_code, :region, :city, :timezone,
                 :latitude, :longitude, :consent, :detected_at, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id)
            DO UPDATE SET
                country = EXCLUDED.country,
                country_code = EXCLUDED.country_code,
                region = EXCLUDED.region,
                city = EXCLUDED.city,
                timezone = EXCLUDED.timezone,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                consent_given = EXCLUDED.consent_given,
                detected_at = EXCLUDED.detected_at,
                updated_at = CURRENT_TIMESTAMP
            """)
            
            db.execute(sql, {
                'user_id': user_id,
                'country': location_data.get('country'),
                'country_code': location_data.get('country_code'),
                'region': location_data.get('region'),
                'city': location_data.get('city'),
                'timezone': location_data.get('timezone'),
                'latitude': location_data.get('latitude'),
                'longitude': location_data.get('longitude'),
                'consent': consent_given,
                'detected_at': location_data.get('detected_at')
            })
            db.commit()
            
            logger.info(f"Location saved for user {user_id} with consent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save location for user {user_id}: {e}")
            db.rollback()
            return False
    
    def get_user_location(self, db: Session, user_id: int) -> Optional[Dict]:
        """
        Get stored location for user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Stored location data or None
        """
        try:
            sql = text("""
            SELECT country, country_code, region, city, timezone, 
                   latitude, longitude, consent_given, detected_at, updated_at
            FROM user_location_preferences
            WHERE user_id = :user_id AND consent_given = true
            """)
            
            result = db.execute(sql, {'user_id': user_id}).first()
            
            if result:
                return {
                    'country': result.country,
                    'country_code': result.country_code,
                    'region': result.region,
                    'city': result.city,
                    'timezone': result.timezone,
                    'latitude': result.latitude,
                    'longitude': result.longitude,
                    'consent_given': result.consent_given,
                    'detected_at': str(result.detected_at),
                    'updated_at': str(result.updated_at)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get location for user {user_id}: {e}")
            return None
    
    def revoke_location_consent(self, db: Session, user_id: int) -> bool:
        """
        Revoke location consent and delete location data
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Success status
        """
        try:
            sql = text("""
            DELETE FROM user_location_preferences
            WHERE user_id = :user_id
            """)
            
            db.execute(sql, {'user_id': user_id})
            db.commit()
            
            logger.info(f"Location data deleted for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete location for user {user_id}: {e}")
            db.rollback()
            return False
    
    def format_location_for_context(self, location_data: Dict) -> str:
        """
        Format location data for LLM context
        
        Args:
            location_data: Location dictionary
            
        Returns:
            Formatted string for context
        """
        if not location_data or 'error' in location_data:
            return "Standort: Unbekannt"
        
        parts = []
        
        if location_data.get('city'):
            parts.append(f"Stadt: {location_data['city']}")
        
        if location_data.get('region'):
            parts.append(f"Region: {location_data['region']}")
        
        if location_data.get('country'):
            parts.append(f"Land: {location_data['country']}")
        
        if location_data.get('timezone'):
            parts.append(f"Zeitzone: {location_data['timezone']}")
        
        return "Standort-Kontext:\n" + "\n".join(parts)


# Singleton instance
_location_service: Optional[LocationService] = None


def get_location_service() -> LocationService:
    """Get singleton instance of LocationService"""
    global _location_service
    if _location_service is None:
        _location_service = LocationService()
    return _location_service
