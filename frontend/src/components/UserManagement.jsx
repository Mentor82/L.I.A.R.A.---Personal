import { useState, useEffect } from 'react';
import './UserManagement.css';

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddUser, setShowAddUser] = useState(false);
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: 'user',
    privacy_accepted: true
  });

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/users/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });
      const data = await response.json();
      setUsers(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial data fetch on mount - the effect is the fetch itself (a real
    // external-system side effect), not a render-computable value.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchUsers();
  }, []);

  const handleRoleChange = async (userId, newRole) => {
    try {
      const response = await fetch(`/api/users/${userId}/role?new_role=${newRole}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });
      
      if (!response.ok) {
        const error = await response.json();
        alert(`Fehler: ${error.detail || 'Rolle konnte nicht geändert werden'}`);
        return;
      }
      
      fetchUsers();
    } catch (error) {
      console.error('Failed to update role:', error);
      alert('Fehler beim Ändern der Rolle');
    }
  };

  const handleActivateUser = async (userId) => {
    try {
      const response = await fetch(`/api/users/${userId}/activate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });
      
      if (!response.ok) {
        const error = await response.json();
        alert(`Fehler: ${error.detail || 'Benutzer konnte nicht aktiviert werden'}`);
        return;
      }
      
      fetchUsers();
    } catch (error) {
      console.error('Failed to activate user:', error);
      alert('Fehler beim Aktivieren des Benutzers');
    }
  };

  const handleDeactivateUser = async (userId) => {
    if (!confirm('Möchten Sie diesen Benutzer wirklich deaktivieren?')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/users/${userId}/deactivate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });
      
      if (!response.ok) {
        const error = await response.json();
        alert(`Fehler: ${error.detail || 'Benutzer konnte nicht deaktiviert werden'}`);
        return;
      }
      
      fetchUsers();
    } catch (error) {
      console.error('Failed to deactivate user:', error);
      alert('Fehler beim Deaktivieren des Benutzers');
    }
  };

  const handlePasswordReset = async (userId, username, email) => {
    if (!email) {
      alert('Dieser Benutzer hat keine E-Mail-Adresse hinterlegt!');
      return;
    }

    if (!confirm(
      `Passwort-Reset für ${username}?\n\n` +
      `Liara wird eine personalisierte E-Mail an ${email} senden mit:\n` +
      `• Einem sicheren Reset-Link\n` +
      `• Einer persönlichen Nachricht basierend auf euren Gesprächen\n` +
      `• Anweisungen zum Setzen eines neuen Passworts\n\n` +
      `Fortfahren?`
    )) {
      return;
    }

    try {
      const response = await fetch(`/api/admin/users/${userId}/reset-password`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });

      if (!response.ok) {
        const error = await response.json();
        alert(`Fehler: ${error.detail || 'Passwort-Reset fehlgeschlagen'}`);
        return;
      }

      const data = await response.json();
      
      // Check if email was sent or fallback mode
      if (data.email_sent) {
        alert(
          `✅ Passwort-Reset erfolgreich!\n\n` +
          `E-Mail gesendet an: ${data.email}\n` +
          `Benutzer: ${data.username}\n` +
          `Token gültig für: ${data.token_expires_hours} Stunden\n\n` +
          `Liara hat eine personalisierte Nachricht basierend auf den Erinnerungen generiert! 💜`
        );
      } else {
        // Fallback mode: Show reset link
        const resetInfo = 
          `⚠️ SMTP nicht konfiguriert - Fallback-Modus\n\n` +
          `Reset-Token generiert für: ${data.username}\n` +
          `Token gültig für: ${data.token_expires_hours} Stunden\n\n` +
          `🔗 Reset-Link:\n${data.reset_url}\n\n` +
          `📋 Token:\n${data.reset_token}\n\n` +
          `Sende diesen Link an ${data.email} oder leite den User direkt weiter.\n\n` +
          `💡 Tipp: Konfiguriere SMTP in .env für automatischen E-Mail-Versand!`;
        
        // Copy to clipboard
        if (navigator.clipboard) {
          navigator.clipboard.writeText(data.reset_url);
        }
        
        alert(resetInfo + '\n\n✅ Reset-Link in Zwischenablage kopiert!');
      }
    } catch (error) {
      console.error('Failed to reset password:', error);
      alert('Fehler beim Passwort-Reset. Bitte Backend-Logs prüfen.');
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newUser)
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        alert(`Fehler: ${error.detail || 'Benutzer konnte nicht angelegt werden'}`);
        return;
      }

      const data = await response.json();

      // /auth/register is the public self-signup endpoint and always creates
      // role=user (correct there) - it has no concept of "role" at all, so the
      // dropdown above does nothing unless we promote afterward here.
      if (newUser.role === 'admin' && data.user?.id) {
        const roleResponse = await fetch(`/api/users/${data.user.id}/role?new_role=admin`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
          }
        });
        if (!roleResponse.ok) {
          alert('Benutzer wurde angelegt, aber die Admin-Rolle konnte nicht gesetzt werden. Bitte manuell in der Tabelle ändern.');
        }
      }

      setShowAddUser(false);
      setNewUser({ username: '', email: '', full_name: '', password: '', role: 'user', privacy_accepted: true });
      fetchUsers();
    } catch (error) {
      console.error('Failed to add user:', error);
      alert('Fehler beim Anlegen des Benutzers.');
    }
  };

  if (loading) {
    return (
      <div className="user-management">
        <div className="loading-state">
          <div className="loading-dots"><span></span><span></span><span></span></div>
          <p className="halo-mono">Lade Benutzerdaten...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="user-management">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            👥 Benutzerverwaltung
          </h1>
          <p className="halo-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            {users.length} Benutzer registriert
          </p>
        </div>
        <button 
          onClick={() => setShowAddUser(!showAddUser)} 
          className="halo-button"
        >
          ➕ Neuer Benutzer
        </button>
      </div>

      {/* Add User Form */}
      {showAddUser && (
        <div className="add-user-form halo-panel">
          <h2 className="halo-header" style={{ fontSize: '1.2rem', marginBottom: 'var(--space-lg)' }}>
            Neuen Benutzer anlegen
          </h2>
          <form onSubmit={handleAddUser}>
            <div className="form-grid">
              <div className="form-group">
                <label className="halo-mono">Benutzername</label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                  required
                  className="form-input"
                />
              </div>
              <div className="form-group">
                <label className="halo-mono">E-Mail</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                  required
                  className="form-input"
                />
              </div>
              <div className="form-group">
                <label className="halo-mono">Vollständiger Name</label>
                <input
                  type="text"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser({...newUser, full_name: e.target.value})}
                  required
                  className="form-input"
                />
              </div>
              <div className="form-group">
                <label className="halo-mono">Passwort</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                  required
                  className="form-input"
                />
              </div>
              <div className="form-group">
                <label className="halo-mono">Rolle</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({...newUser, role: e.target.value})}
                  className="form-input"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="halo-button">
                ✅ Benutzer anlegen
              </button>
              <button 
                type="button" 
                onClick={() => setShowAddUser(false)}
                className="halo-button"
                style={{ background: 'transparent', border: '1px solid var(--border-normal)' }}
              >
                Abbrechen
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="users-table-container halo-panel">
        <div className="table-wrapper">
          <table className="users-table">
            <thead>
              <tr>
                <th>Benutzer</th>
                <th>E-Mail</th>
                <th>Rolle</th>
                <th>Status</th>
                <th>Erstellt</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td>
                    <div className="user-cell">
                      <div className="user-avatar">{user.username[0].toUpperCase()}</div>
                      <div className="user-info">
                        <div className="user-name">{user.full_name}</div>
                        <div className="user-username halo-mono">@{user.username}</div>
                      </div>
                    </div>
                  </td>
                  <td className="halo-mono">{user.email}</td>
                  <td>
                    <select
                      value={user.role}
                      onChange={(e) => handleRoleChange(user.id, e.target.value)}
                      className="role-select"
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? '✅ Aktiv' : '⛔ Inaktiv'}
                    </span>
                  </td>
                  <td className="halo-mono">
                    {new Date(user.created_at).toLocaleDateString('de-DE')}
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button
                        onClick={() => handlePasswordReset(user.id, user.username, user.email)}
                        className="action-btn reset-password"
                        title="Passwort zurücksetzen (Liara sendet personalisierte E-Mail)"
                      >
                        🔑
                      </button>
                      {user.is_active ? (
                        <button
                          onClick={() => handleDeactivateUser(user.id)}
                          className="action-btn deactivate"
                          title="Deaktivieren"
                        >
                          🚫
                        </button>
                      ) : (
                        <button
                          onClick={() => handleActivateUser(user.id)}
                          className="action-btn activate"
                          title="Aktivieren"
                        >
                          ✅
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default UserManagement;
