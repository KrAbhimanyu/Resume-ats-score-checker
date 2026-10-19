import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, X, AlertCircle } from 'lucide-react';

interface ResumeUploaderProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  error?: string | null;
  disabled?: boolean;
}

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

export const ResumeUploader: React.FC<ResumeUploaderProps> = ({
  selectedFile,
  onFileSelect,
  error,
  disabled = false,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const validateAndSelectFile = (file: File) => {
    setLocalError(null);

    const ext = `.${file.name.split('.').pop()?.toLowerCase()}`;
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setLocalError(`Unsupported file format '${ext}'. Please upload a .pdf or .docx resume.`);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setLocalError(
        `File size (${formatFileSize(file.size)}) exceeds the maximum allowed limit of 5 MB.`
      );
      return;
    }

    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelectFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelectFile(e.target.files[0]);
    }
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null);
    setLocalError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const displayError = error || localError;

  return (
    <div className="form-group">
      <div className="form-label">
        <span>Resume Document</span>
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          Max 5 MB (.PDF or .DOCX)
        </span>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        id="resume-file-input"
        aria-label="Upload resume file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={handleInputChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />

      {!selectedFile ? (
        <div
          role="button"
          tabIndex={disabled ? -1 : 0}
          aria-label="Drag and drop your resume file here or click to browse files"
          className={`dropzone ${isDragOver ? 'active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
        >
          <UploadCloud className="dropzone-icon" aria-hidden="true" />
          <p className="dropzone-text">Drag & drop your resume file here</p>
          <p className="dropzone-hint">or click to browse your computer</p>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ marginTop: '1rem', padding: '0.5rem 1.25rem', fontSize: '0.85rem' }}
            disabled={disabled}
            onClick={(e) => {
              e.stopPropagation();
              fileInputRef.current?.click();
            }}
          >
            Browse Files
          </button>
        </div>
      ) : (
        <div className="selected-file-card">
          <div className="file-info">
            <div className="file-icon-badge" aria-hidden="true">
              <FileText size={22} />
            </div>
            <div className="file-details">
              <span className="file-name" title={selectedFile.name}>
                {selectedFile.name}
              </span>
              <span className="file-size">{formatFileSize(selectedFile.size)}</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
            >
              Replace
            </button>
            <button
              type="button"
              className="btn-remove-file"
              onClick={handleRemove}
              aria-label="Remove selected resume"
              title="Remove file"
              disabled={disabled}
            >
              <X size={20} />
            </button>
          </div>
        </div>
      )}

      {displayError && (
        <div className="alert alert-danger" style={{ marginTop: '0.75rem', padding: '0.65rem 0.85rem' }}>
          <AlertCircle size={18} style={{ flexShrink: 0 }} aria-hidden="true" />
          <span>{displayError}</span>
        </div>
      )}
    </div>
  );
};
