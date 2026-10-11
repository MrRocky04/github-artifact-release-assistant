import { useCallback, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Home from "./pages/Home.jsx";
import Release from "./pages/Release.jsx";
import ManageQuestions from "./pages/ManageQuestions.jsx";
import { api } from "./api.js";

export default function App() {
  const [view, setView] = useState("home");          // home | release | questions
  const [status, setStatus] = useState(null);
  const [qVersion, setQVersion] = useState(0);        // bumps when questions are added/removed
  const [releaseKey, setReleaseKey] = useState(0);    // changing it starts a fresh release
  const [releaseActive, setReleaseActive] = useState(false);

  const checkStatus = useCallback(() => {
    setStatus(null);
    api.status().then(setStatus).catch(() => setStatus({ gh_installed: false, git_installed: false, authenticated: false }));
  }, []);
  useEffect(checkStatus, [checkStatus]);

  const startRelease = () => { setReleaseKey((k) => k + 1); setReleaseActive(true); setView("release"); };
  const exitRelease = () => { setReleaseActive(false); setView("home"); };
  // "Artifact Release" returns to a release that is in progress, otherwise to the start page
  const navigate = (v) => setView(v === "home" && releaseActive ? "release" : v);

  return (
    <div className="page">
      <div className="shell">
        <Sidebar view={view} onNavigate={navigate} status={status} onRecheck={checkStatus} />
        <main className="main">
          {view === "home" && <Home onStart={startRelease} />}
          {releaseActive && (
            <div hidden={view !== "release"}>
              <Release key={releaseKey} status={status} onRecheck={checkStatus} qVersion={qVersion}
                onExit={exitRelease} onRestart={startRelease} />
            </div>
          )}
          {view === "questions" && <ManageQuestions onChanged={() => setQVersion((v) => v + 1)} />}
        </main>
      </div>
    </div>
  );
}
