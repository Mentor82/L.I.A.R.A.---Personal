import { useState, useEffect } from 'react';
import './LocationConsent.css';

const LocationConsent = ({ onComplete }) => {
  const [showModal, setShowModal] = useState(false);
  const [location, setLocation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  const getToken = () => localStorage.getItem('liara_token') || localStorage.getItem('token');

  useEffect(() => {
    checkLocationStatus();
  }, []);

  const checkLocationStatus = async () => {
    const token = getToken();
    if (!token) return;
    try {
      const response = await fetch('/api/location/current', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      
      // If no location stored, show consent modal
      if (!data.success) {
        detectLocation();
      }
    } catch (err) {
      console.error('Location status check failed:', err);
    }
  };

  const detectLocation = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/location/detect', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (data.success && data.location) {
        setLocation(data.location);
        setShowModal(true);
      } else {
        // Silent fail - location detection is optional
        console.log('Location detection not available');
      }
    } catch (err) {
      console.error('Location detection failed:', err);
      // Silent fail - don't block user
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/location/save', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          consent_given: true,
          location_data: location
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSaved(true);
        setTimeout(() => {
          setShowModal(false);
          if (onComplete) onComplete(true);
        }, 1500);
      } else {
        setError(data.message || 'Failed to save location');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDecline = () => {
    setShowModal(false);
    if (onComplete) onComplete(false);
  };

  if (!showModal) return null;

  return (
    <div className="location-consent-overlay">
      <div className="location-consent-modal">
        {saved ? (
          <div className="location-saved">
            <div className="success-icon">✓</div>
            <h2>Standort gespeichert!</h2>
            <p>Liara kann dir jetzt personalisierte Wetter-Infos geben.</p>
          </div>
        ) : (
          <>
            <div className="modal-header">
              <div className="location-icon">📍</div>
              <h2>Standort speichern?</h2>
            </div>
            
            <div className="modal-body">
              {location && (
                <div className="detected-location">
                  <p className="location-label">Erkannter Standort:</p>
                  <p className="location-value">
                    {location.city}, {location.country}
                  </p>
                </div>
              )}
              
              <div className="info-box">
                <h3>🔒 Deine Privatsphäre ist wichtig</h3>
                <ul>
                  <li>Wir speichern nur Stadt und Land (keine exakte Position)</li>
                  <li>Deine IP-Adresse wird NICHT gespeichert</li>
                  <li>Nur für personalisierte Wetter-Infos</li>
                  <li>Du kannst die Einwilligung jederzeit widerrufen</li>
                </ul>
              </div>
              
              {error && (
                <div className="error-message">{error}</div>
              )}
            </div>
            
            <div className="modal-footer">
              <button 
                className="btn-decline"
                onClick={handleDecline}
                disabled={loading}
              >
                Nein, danke
              </button>
              <button 
                className="btn-accept"
                onClick={handleAccept}
                disabled={loading}
              >
                {loading ? 'Speichere...' : 'Ja, speichern'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default LocationConsent;
