import React from 'react';
import { useTranslation } from 'react-i18next';
import './ConfirmDialog.css';

const ConfirmDialog = ({ title, message, onConfirm, onCancel }) => {
  const { t } = useTranslation();

  return (
    <div className="confirm-dialog-overlay">
      <div className="confirm-dialog">
        <div className="confirm-dialog-header">
          <h3>{title}</h3>
        </div>
        <div className="confirm-dialog-body">
          <p>{message}</p>
        </div>
        <div className="confirm-dialog-actions">
          <button onClick={onCancel} className="btn btn-secondary">
            {t('profile.confirmDialog.cancel')}
          </button>
          <button onClick={onConfirm} className="btn btn-primary">
            {t('profile.confirmDialog.confirm')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
