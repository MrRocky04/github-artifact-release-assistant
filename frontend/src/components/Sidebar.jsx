import { BranchIcon, CubeIcon, HelpIcon } from "../icons.jsx";

export default function Sidebar({ view, onNavigate, status, onRecheck }) {
  const state = !status ? "checking" : !status.gh_installed ? "missing" : !status.authenticated ? "login" : "ok";
  const text = {
    checking: "Checking GitHub CLI…",
    missing: "GitHub CLI (gh) not found",
    login: "Not signed in — run gh auth login",
    ok: "GitHub CLI connected",
  }[state];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"><BranchIcon width={26} height={26} strokeWidth={1.6} /></div>
        <div className="brand-name">Release Assistant</div>
      </div>

      <nav className="nav" aria-label="Workspace">
        <div className="nav-label">WORKSPACE</div>
        <button className={`nav-item ${view === "release" || view === "home" ? "active" : ""}`} onClick={() => onNavigate("home")}>
          <CubeIcon width={26} height={26} strokeWidth={1.6} /> Artifact Release
        </button>
        <button className={`nav-item ${view === "questions" ? "active" : ""}`} onClick={() => onNavigate("questions")}>
          <HelpIcon width={26} height={26} strokeWidth={1.6} /> Manage Questions
        </button>
      </nav>

      <button className={`cli-status ${state}`} onClick={onRecheck} title="Click to check again">
        <span className="dot" /> {text}
      </button>
    </aside>
  );
}
