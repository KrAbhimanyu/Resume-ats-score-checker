import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
  code?: string;
  onRetry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, code, onRetry }) => {
  return (
    <div className="alert alert-danger" role="alert" style={{ flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', width: '100%' }}>
        <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '2px' }} aria-hidden="true" />
        <div style={{ flex: 1 }}>
          <strong style={{ display: 'block', marginBottom: '0.2rem' }}>Analysis Error</strong>
          <span>{message}</span>
          {code && (
            <span style={{ display: 'block', fontSize: '0.75rem', marginTop: '0.35rem', opacity: 0.85 }}>
              Error code: <code>{code}</code>
            </span>
          )}
        </div>
      </div>

      {onRetry && (
        <div style={{ marginTop: '0.75rem', alignSelf: 'flex-start' }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem' }}
            onClick={onRetry}
          >
            <RefreshCw size={14} aria-hidden="true" />
            <span>Try Again</span>
          </button>
        </div>
      )}
    </div>
  );
};
