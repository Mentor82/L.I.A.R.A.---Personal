/**
 * Privacy API Service
 * 
 * Endpoints für Location Consent & Privacy Settings
 */

const API_BASE = '/api'

/**
 * Get current location consent status
 */
export async function getLocationConsent() {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/privacy/location/consent`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to fetch location consent status')
  }
  
  return await response.json()
}

/**
 * Grant location tracking consent
 * Triggers automatic location detection
 */
export async function grantLocationConsent() {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/privacy/location/consent`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to grant consent')
  }
  
  return await response.json()
}

/**
 * Revoke location consent and delete all location data
 */
export async function revokeLocationConsent() {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/privacy/location`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to revoke consent')
  }
  
  return await response.json()
}

/**
 * Get all privacy settings
 */
export async function getPrivacySettings() {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/privacy/settings`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to fetch privacy settings')
  }
  
  return await response.json()
}

/**
 * Update privacy settings
 */
export async function updatePrivacySettings(settings) {
  const token = localStorage.getItem('liara_token')
  
  const params = new URLSearchParams()
  if (settings.web_search_history !== undefined) {
    params.append('web_search_history', settings.web_search_history)
  }
  if (settings.auto_delete_days !== undefined) {
    params.append('auto_delete_days', settings.auto_delete_days)
  }
  
  const response = await fetch(`${API_BASE}/privacy/settings?${params}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to update privacy settings')
  }
  
  return await response.json()
}

/**
 * Export all user data (GDPR)
 */
export async function exportUserData() {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/privacy/export`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to export data')
  }
  
  return await response.json()
}

/**
 * Delete all user data (GDPR Right to be Forgotten)
 */
export async function deleteAllUserData() {
  const token = localStorage.getItem('liara_token')
  
  const response = await fetch(`${API_BASE}/privacy/all-data?confirm=true`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  
  if (!response.ok) {
    throw new Error('Failed to delete data')
  }
  
  return await response.json()
}
