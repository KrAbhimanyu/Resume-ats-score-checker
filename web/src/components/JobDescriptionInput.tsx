import React from 'react';
import { AlertCircle } from 'lucide-react';

interface JobDescriptionInputProps {
  value: string;
  onChange: (val: string) => void;
  error?: string | null;
  disabled?: boolean;
}

export const JobDescriptionInput: React.FC<JobDescriptionInputProps> = ({
  value,
  onChange,
  error,
  disabled = false,
}) => {
  const words = value.trim() ? value.trim().split(/\s+/).length : 0;
  const chars = value.length;

  return (
    <div className="form-group">
      <div className="form-label">
        <label htmlFor="job-description-textarea">Job Description</label>
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          Target position requirements
        </span>
      </div>

      <textarea
        id="job-description-textarea"
        className="textarea-job"
        placeholder="Paste the target job description here (responsibilities, required qualifications, technical skills)..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-invalid={!!error}
        aria-describedby={error ? 'job-desc-error' : undefined}
      />

      <div className="textarea-meta">
        <span>{words} {words === 1 ? 'word' : 'words'} ({chars} characters)</span>
        <span>{words < 5 ? 'Minimum 5 words recommended' : 'Sufficient detail'}</span>
      </div>

      {error && (
        <div
          id="job-desc-error"
          className="alert alert-danger"
          style={{ marginTop: '0.75rem', padding: '0.65rem 0.85rem' }}
        >
          <AlertCircle size={18} style={{ flexShrink: 0 }} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
