import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ConfirmDialog from './ConfirmDialog';
import './ProfileEdit.css';

const ProfileEdit = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [errors, setErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validateForm = () => {
    const newErrors = {};

    // Email validation
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = t('profile.errors.invalidEmail');
    }

    // Password validation
    if (formData.newPassword || formData.confirmPassword) {
      if (!formData.currentPassword) {
        newErrors.currentPassword = t('profile.errors.currentRequired');
      }
      if (formData.newPassword && formData.newPassword.length < 8) {
        newErrors.newPassword = t('profile.errors.weakPassword');
      }
      if (formData.newPassword !== formData.confirmPassword) {
        newErrors.confirmPassword = t('profile.errors.passwordMismatch');
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSuccessMessage('');
    
    if (validateForm()) {
      setShowConfirmDialog(true);
    }
  };

  const handleConfirmSave = async () => {
    setShowConfirmDialog(false);
    
    try {
      const token = localStorage.getItem('liara_token');
      const updateData = {};
      
      if (formData.username) updateData.username = formData.username;
      if (formData.email) updateData.email = formData.email;
      
      // Update profile
      const profileResponse = await fetch('/api/user/profile', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
      });

      if (!profileResponse.ok) {
        throw new Error(t('profile.errors.updateFailed'));
      }

      // Update password if provided
      if (formData.newPassword) {
        const passwordResponse = await fetch('/api/user/password', {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            current_password: formData.currentPassword,
            new_password: formData.newPassword
          })
        });

        if (!passwordResponse.ok) {
          throw new Error(t('profile.errors.updateFailed'));
        }
      }

      setSuccessMessage(t('profile.success'));
      // Clear password fields
      setFormData(prev => ({
        ...prev,
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      }));

    } catch (error) {
      setErrors({ general: error.message });
    }
  };

  return (
    <div className="profile-edit-container">
      <div className="profile-edit-card">
        <div className="profile-edit-header">
          <h2>{t('profile.title')}</h2>
          <p>{t('profile.subtitle')}</p>
        </div>

        {successMessage && (
          <div className="success-message">
            ✅ {successMessage}
          </div>
        )}

        {errors.general && (
          <div className="error-message">
            ❌ {errors.general}
          </div>
        )}

        <form onSubmit={handleSubmit} className="profile-edit-form">
          {/* Username */}
          <div className="form-group">
            <label htmlFor="username">{t('profile.username')}</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder={t('profile.username')}
              className={errors.username ? 'error' : ''}
            />
            {errors.username && <span className="field-error">{errors.username}</span>}
          </div>

          {/* Email */}
          <div className="form-group">
            <label htmlFor="email">{t('profile.email')}</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder={t('profile.email')}
              className={errors.email ? 'error' : ''}
            />
            {errors.email && <span className="field-error">{errors.email}</span>}
          </div>

          <div className="form-divider">
            <span>{t('profile.changePassword') || 'Passwort ändern'}</span>
          </div>

          {/* Current Password */}
          <div className="form-group">
            <label htmlFor="currentPassword">{t('profile.currentPassword')}</label>
            <input
              type="password"
              id="currentPassword"
              name="currentPassword"
              value={formData.currentPassword}
              onChange={handleChange}
              placeholder={t('profile.currentPassword')}
              className={errors.currentPassword ? 'error' : ''}
            />
            {errors.currentPassword && <span className="field-error">{errors.currentPassword}</span>}
          </div>

          {/* New Password */}
          <div className="form-group">
            <label htmlFor="newPassword">{t('profile.newPassword')}</label>
            <input
              type="password"
              id="newPassword"
              name="newPassword"
              value={formData.newPassword}
              onChange={handleChange}
              placeholder={t('profile.newPassword')}
              className={errors.newPassword ? 'error' : ''}
            />
            {errors.newPassword && <span className="field-error">{errors.newPassword}</span>}
          </div>

          {/* Confirm Password */}
          <div className="form-group">
            <label htmlFor="confirmPassword">{t('profile.confirmPassword')}</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder={t('profile.confirmPassword')}
              className={errors.confirmPassword ? 'error' : ''}
            />
            {errors.confirmPassword && <span className="field-error">{errors.confirmPassword}</span>}
          </div>

          {/* Actions */}
          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={() => window.history.back()}>
              {t('profile.cancelButton')}
            </button>
            <button type="submit" className="btn btn-primary">
              {t('profile.saveButton')}
            </button>
          </div>
        </form>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <ConfirmDialog
          title={t('profile.confirmDialog.title')}
          message={t('profile.confirmDialog.message')}
          onConfirm={handleConfirmSave}
          onCancel={() => setShowConfirmDialog(false)}
        />
      )}
    </div>
  );
};

export default ProfileEdit;
