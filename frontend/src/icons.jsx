const base = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };
const make = (children) => (props) => <svg {...base} {...props}>{children}</svg>;

export const BranchIcon = make(<><circle cx="6" cy="19" r="2.2" /><circle cx="18" cy="6" r="2.2" /><path d="M6 3v13.8" /><path d="M18 8.2c0 5-6 4-11 9" /></>);
export const CubeIcon = make(<><path d="M12 2.5l8.5 4.9v9.2L12 21.5l-8.5-4.9V7.4z" /><path d="M12 8.2l4 2.3v3l-4 2.3-4-2.3v-3z" /><path d="M3.8 7.6L12 12.3l8.2-4.7M12 12.3v9" /></>);
export const HelpIcon = make(<><circle cx="12" cy="12" r="9.5" /><path d="M9.3 9.4a2.8 2.8 0 015.4 1c0 1.8-2.7 2.3-2.7 4" /><path d="M12 17.8h.01" /></>);
export const FileCheckIcon = make(<><path d="M14 2.8H7a2 2 0 00-2 2v14.4a2 2 0 002 2h10a2 2 0 002-2V8z" /><path d="M14 2.8V8h5" /><path d="M9.2 14.2l2 2 3.8-4" /></>);
export const FileIcon = make(<><path d="M14 2.8H7a2 2 0 00-2 2v14.4a2 2 0 002 2h10a2 2 0 002-2V8z" /><path d="M14 2.8V8h5M9 13h6M9 16.5h6" /></>);
export const ArrowRight = make(<><path d="M4 12h16M14 6l6 6-6 6" /></>);
export const ArrowLeft = make(<><path d="M20 12H4M10 6l-6 6 6 6" /></>);
export const CheckIcon = make(<path d="M4.5 12.5l5 5 10-11" />);
export const PulseIcon = make(<path d="M3 12h4l2.5-7 5 14L17 12h4" />);
export const UploadIcon = make(<><path d="M12 15.5V4M7 8.5l5-5 5 5" /><path d="M4 15v3.5A1.5 1.5 0 005.5 20h13a1.5 1.5 0 001.5-1.5V15" /></>);
export const TrashIcon = make(<><path d="M4 7h16M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13M10 11v6M14 11v6" /></>);
export const PlusIcon = make(<path d="M12 4.5v15M4.5 12h15" />);
export const CloseIcon = make(<path d="M6 6l12 12M18 6L6 18" />);
export const AlertIcon = make(<><path d="M12 3.5L2.8 19.5h18.4z" /><path d="M12 10v4.5M12 17.3h.01" /></>);
export const LockIcon = make(<><rect x="5" y="10.5" width="14" height="10" rx="2" /><path d="M8 10.5V8a4 4 0 018 0v2.5" /></>);
export const LinkIcon = make(<><path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1" /><path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1" /></>);
