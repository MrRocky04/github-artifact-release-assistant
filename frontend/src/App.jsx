import { useCallback, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Home from "./pages/Home.jsx";
import Release from "./pages/Release.jsx";
import ManageQuestions from "./pages/ManageQuestions.jsx";
import { api } from "./api.js";

export default function App() {
  const [view, setView] = useState("home");
  const [status, setStatus] = useState(null);
  const [qVersion, setQVersion] = useState(0);
  const [releaseKey, setReleaseKey] = useState(0);
  const [releaseActive, setReleaseActive] = useState(false);

  const checkStatus = useCallback(() => {
    setStatus(null);

    api.status()
      .then(setStatus)
      .catch(() =>
        setStatus({
          gh_installed: false,
          git_installed: false,
          authenticated: false,
        }),
      );
  }, []);

  useEffect(checkStatus, [checkStatus]);

  const startRelease = () => {
    setReleaseKey((key) => key + 1);
    setReleaseActive(true);
    setView("release");
  };

  const exitRelease = () => {
    setReleaseActive(false);
    setView("home");
  };

  // Return to an in-progress release when the user selects Artifact Release.
  const navigate = (nextView) =>
    setView(nextView === "home" && releaseActive ? "release" : nextView);

  return (
    <div className="page">
      <div className="shell">
        <Sidebar
          view={view}
          onNavigate={navigate}
          status={status}
          onRecheck={checkStatus}
        />

        <main className="main">
          {view === "home" && <Home onStart={startRelease} />}

          {releaseActive && (
            <div hidden={view !== "release"}>
              <Release
                key={releaseKey}
                status={status}
                onRecheck={checkStatus}
                qVersion={qVersion}
                onExit={exitRelease}
                onRestart={startRelease}
              />
            </div>
          )}

          {view === "questions" && (
            <ManageQuestions onChanged={() => setQVersion((version) => version + 1)} />
          )}
        </main>
      </div>
    </div>
  );
}
