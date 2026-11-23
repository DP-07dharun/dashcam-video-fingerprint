import { useEffect, useId, useRef, useState } from "react";
import { formatBytes } from "../format";

const ACCEPT = ".mp4,.mov,.avi,.mkv,.webm,.m4v,.ts,.3gp,video/*";

interface Props {
  file: File | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
  label?: string;
}

export function FileDrop({ file, onChange, disabled, label = "Dashcam video" }: Props) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function pick(files: FileList | null) {
    const f = files?.[0];
    if (f) onChange(f);
  }

  return (
    <div className="field">
      <label htmlFor={inputId}>{label}</label>
      <div
        className={`drop ${dragging ? "drop--active" : ""} ${file ? "drop--filled" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) pick(e.dataTransfer.files);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !disabled) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        aria-disabled={disabled}
      >
        <input
          id={inputId}
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          hidden
          disabled={disabled}
          onChange={(e) => {
            pick(e.target.files);
            e.target.value = "";
          }}
        />
        {file && preview ? (
          <div className="drop__file" onClick={(e) => e.stopPropagation()}>
            <video src={preview} controls muted className="drop__video" />
            <div className="drop__meta">
              <strong className="truncate" title={file.name}>
                {file.name}
              </strong>
              <span className="muted">{formatBytes(file.size)}</span>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={disabled}
                onClick={() => onChange(null)}
              >
                Remove
              </button>
            </div>
          </div>
        ) : (
          <div className="drop__empty">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M4 7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7Zm12 3 4-2.5v9L16 14"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
            </svg>
            <strong>Drop a video here or click to browse</strong>
            <span className="muted">MP4, MOV, AVI, MKV, WebM · processed for its fingerprint, never stored</span>
          </div>
        )}
      </div>
    </div>
  );
}
