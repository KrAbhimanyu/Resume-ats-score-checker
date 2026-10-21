import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResumeUploader } from '../components/ResumeUploader';

describe('ResumeUploader Component', () => {
  it('renders initial dropzone with browse button and accessible labels', () => {
    const handleFileSelect = vi.fn();
    render(<ResumeUploader selectedFile={null} onFileSelect={handleFileSelect} />);

    expect(screen.getByText(/Drag & drop your resume file here/i)).toBeInTheDocument();
    expect(screen.getByText(/Browse Files/i)).toBeInTheDocument();
    expect(screen.getByText(/Max 5 MB \(\.PDF or \.DOCX\)/i)).toBeInTheDocument();
  });

  it('allows selecting a valid PDF file via file input', () => {
    const handleFileSelect = vi.fn();
    render(<ResumeUploader selectedFile={null} onFileSelect={handleFileSelect} />);

    const input = screen.getByLabelText(/Upload resume file/i) as HTMLInputElement;
    const file = new File(['%PDF-1.4 dummy content'], 'jane_doe_resume.pdf', { type: 'application/pdf' });

    fireEvent.change(input, { target: { files: [file] } });

    expect(handleFileSelect).toHaveBeenCalledTimes(1);
    expect(handleFileSelect).toHaveBeenCalledWith(file);
  });

  it('allows selecting a valid DOCX file', () => {
    const handleFileSelect = vi.fn();
    render(<ResumeUploader selectedFile={null} onFileSelect={handleFileSelect} />);

    const input = screen.getByLabelText(/Upload resume file/i) as HTMLInputElement;
    const file = new File(['PK\x03\x04 dummy content'], 'jane_doe_resume.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(handleFileSelect).toHaveBeenCalledWith(file);
  });

  it('rejects unsupported file formats with error message', () => {
    const handleFileSelect = vi.fn();
    render(<ResumeUploader selectedFile={null} onFileSelect={handleFileSelect} />);

    const input = screen.getByLabelText(/Upload resume file/i) as HTMLInputElement;
    const file = new File(['plain text'], 'resume.txt', { type: 'text/plain' });

    fireEvent.change(input, { target: { files: [file] } });

    expect(handleFileSelect).not.toHaveBeenCalled();
    expect(screen.getByText(/Unsupported file format '\.txt'/i)).toBeInTheDocument();
  });

  it('rejects files larger than 5 MB', () => {
    const handleFileSelect = vi.fn();
    render(<ResumeUploader selectedFile={null} onFileSelect={handleFileSelect} />);

    const input = screen.getByLabelText(/Upload resume file/i) as HTMLInputElement;
    const largeFile = new File(['x'.repeat(6 * 1024 * 1024)], 'large_resume.pdf', { type: 'application/pdf' });
    Object.defineProperty(largeFile, 'size', { value: 6 * 1024 * 1024 });

    fireEvent.change(input, { target: { files: [largeFile] } });

    expect(handleFileSelect).not.toHaveBeenCalled();
    expect(screen.getByText(/exceeds the maximum allowed limit of 5 MB/i)).toBeInTheDocument();
  });

  it('renders selected file card with name, size, and remove button', () => {
    const handleFileSelect = vi.fn();
    const file = new File(['dummy bytes'], 'candidate_cv.pdf', { type: 'application/pdf' });
    Object.defineProperty(file, 'size', { value: 1024 * 50 }); // 50 KB

    render(<ResumeUploader selectedFile={file} onFileSelect={handleFileSelect} />);

    expect(screen.getByText('candidate_cv.pdf')).toBeInTheDocument();
    expect(screen.getByText('50.0 KB')).toBeInTheDocument();

    const removeBtn = screen.getByTitle('Remove file');
    fireEvent.click(removeBtn);

    expect(handleFileSelect).toHaveBeenCalledWith(null);
  });
});

