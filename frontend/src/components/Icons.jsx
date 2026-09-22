const base = { width: 22, height: 22, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true };

export const LensMark = (p) => (
  <svg {...base} width="28" height="28" {...p} strokeWidth="2.4"><circle cx="10.5" cy="10.5" r="7" /><line x1="21" y1="21" x2="15.5" y2="15.5" /></svg>
);
export const UploadIcon = (p) => (<svg {...base} {...p}><path d="M12 16V4M12 4 7 9M12 4l5 5" /><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" /></svg>);
export const FileIcon = (p) => (<svg {...base} {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></svg>);
export const CloseIcon = (p) => (<svg {...base} {...p}><path d="M6 6l12 12M18 6 6 18" /></svg>);
export const ChevronDown = (p) => (<svg {...base} {...p}><path d="m6 9 6 6 6-6" /></svg>);
export const CheckCircle = (p) => (<svg {...base} {...p}><path d="M21 11.1V12a9 9 0 1 1-5.3-8.2" /><path d="m9 11 3 3 8-8" /></svg>);
export const AlertIcon = (p) => (<svg {...base} {...p}><path d="M12 9v4M12 17h.01" /><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></svg>);
export const SendIcon = (p) => (<svg {...base} {...p}><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z" /></svg>);
export const SparkleIcon = (p) => (<svg {...base} {...p} fill="currentColor" stroke="none"><path d="M12 2l1.8 5.6L19 9l-5.2 1.4L12 16l-1.8-5.6L5 9l5.2-1.4z" /></svg>);
export const ArrowLeft = (p) => (<svg {...base} {...p}><path d="M19 12H5M5 12l6-6M5 12l6 6" /></svg>);
export const ShieldIcon = (p) => (<svg {...base} {...p}><path d="M12 2 4 5v6c0 5 3.4 8.7 8 11 4.6-2.3 8-6 8-11V5z" /></svg>);
