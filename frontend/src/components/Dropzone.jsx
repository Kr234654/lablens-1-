import { useCallback, useRef, useState } from 'react';
import { CloseIcon, FileIcon, UploadIcon } from './Icons';

const MAX_MB = 5;

export default function Dropzone({ file, onFile, error }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const validate = useCallback((f) => {
    if (!f) return;
    if (f.type !== 'application/pdf') {
      onFile(null, 'Please choose a PDF file.');
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      onFile(null, `That file is larger than ${MAX_MB} MB.`);
      return;
    }
    onFile(f, null);
  }, [onFile]);

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    validate(e.dataTransfer.files?.[0]);
  };

  if (file) {
    return (
      <div className="picked-file">
        <FileIcon />
        <div className="picked-file-info">
          <strong>{file.name}</strong>
          <span>{(file.size / 1024).toFixed(0)} KB</span>
        </div>
        <button type="button" className="icon-btn" onClick={() => onFile(null, null)} aria-label="Remove file">
          <CloseIcon width={18} height={18} />
        </button>
      </div>
    );
  }

  return (
    <div
      className={`dropzone ${dragOver ? 'is-over' : ''} ${error ? 'has-error' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
    >
      <UploadIcon width={30} height={30} />
      <p><strong>Click to upload</strong> or drag a PDF here</p>
      <span>Lab report as PDF, up to {MAX_MB} MB</span>
      <input
        ref={inputRef} type="file" accept="application/pdf" hidden
        onChange={(e) => validate(e.target.files?.[0])}
      />
    </div>
  );
}
