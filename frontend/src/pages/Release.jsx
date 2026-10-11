import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";
import QuestionField from "../components/QuestionField.jsx";
import { AlertIcon, ArrowLeft, ArrowRight, BranchIcon, CheckIcon, FileCheckIcon, HelpIcon, LinkIcon, UploadIcon } from "../icons.jsx";

const PURPOSES = [
  { id: "1", section: "internal", title: "Internal Testing", text: "Artifact used for internal testing builds." },
  { id: "2", section: "personal", title: "Personal Testing", text: "Artifact tested personally or for experimentation." },
  { id: "3", section: "production", title: "Production", text: "Artifact considered for production release." },
];
const STEPPER = ["Upload", "Artifact info", "Action", "Questions", "Branch", "Review", "Done"];
const STEP_OF = { upload: 0, artifact: 1, action: 2, release: 3, purpose: 3, verify: 3, uploadinfo: 3, branch: 4, review: 5, done: 6 };

const formatSize = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(2)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);
const normalizeRepo = (r) => r.trim().replace(/\\/g, "/");
const REPO_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]*\/[A-Za-z0-9_.-]+$/;

export default function Release({ status, onRecheck, qVersion, onExit, onRestart }) {
  const [screen, setScreen] = useState("upload");
  const [qs, setQs] = useState(null);
  const [artifact, setArtifact] = useState(null);
  const [answers, setAnswers] = useState({ artifact: {}, release: {}, internal: {}, personal: {}, production: {}, upload: {} });
  const [purpose, setPurpose] = useState("");
  const [action, setAction] = useState("");
  const [branchMode, setBranchMode] = useState("");
  const [branchName, setBranchName] = useState("");
  const [review, setReview] = useState(null);
  const [prTitle, setPrTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [errors, setErrors] = useState({});
  const topRef = useRef(null);

  const loadQuestions = () => api.questions().then(setQs).catch((e) => setError(e.message));
  useEffect(() => { loadQuestions(); }, [qVersion]);
  useEffect(() => { topRef.current?.scrollIntoView({ block: "start" }); }, [screen]);

  const sectionQs = (section) => (qs ? qs.questions.filter((q) => q.section === section) : []);
  const val = (section, q) => answers[section][q.key] ?? q.default ?? "";
  const setVal = (section, q, v) => {
    setAnswers((a) => ({ ...a, [section]: { ...a[section], [q.key]: v } }));
    setErrors((e) => { const n = { ...e }; delete n[q.id]; return n; });
  };
  const visible = (section, q) => !q.depends_on || val(section, { key: q.depends_on.key }) === q.depends_on.value;
  const visibleQs = (section) => sectionQs(section).filter((q) => visible(section, q));

  // Flat answers exactly like the CLI dict: only current, visible questions.
  const flatAnswers = () => {
    const out = {};
    const sections = ["artifact", ...(action === "release" ? ["release", PURPOSES.find((p) => p.id === purpose)?.section] : [])];
    sections.filter(Boolean).forEach((s) => visibleQs(s).forEach((q) => { out[q.key] = val(s, q); }));
    if (action === "release") out.testing_purpose = purpose;
    if (action === "upload") qs.upload_questions.forEach((q) => { out[q.key] = answers.upload[q.key] ?? ""; });
    return out;
  };
  const payload = () => ({ action, artifact_id: artifact.artifact_id, answers: flatAnswers(), branch_mode: branchMode, branch_name: branchName.trim() });

  const validate = (section) => {
    const errs = {};
    visibleQs(section).forEach((q) => {
      const v = String(val(section, q)).trim();
      if (q.required && !v) errs[q.id] = "This question is required.";
      else if (q.key === "repository" && v && !REPO_RE.test(normalizeRepo(v))) errs[q.id] = "Please enter the repository in OWNER/REPO format.";
      else if (q.key === "current_version" && v && (/\s/.test(v) || v.startsWith("-"))) errs[q.id] = "The version cannot contain spaces or start with '-'.";
    });
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const flow = action === "upload" ? ["upload", "artifact", "action", "uploadinfo", "branch", "review", "done"]
    : ["upload", "artifact", "action", "release", "purpose", "verify", "branch", "review", "done"];
  const go = (s) => { setError(""); setErrors({}); setScreen(s); };
  const step = (delta) => go(flow[Math.max(0, flow.indexOf(screen) + delta)]);

  const run = async (label, fn) => {
    setBusy(label); setError("");
    try { return await fn(); } catch (e) { setError(e.message); return null; } finally { setBusy(""); }
  };

  // ------------------------------------------------------------------ actions
  const next = async () => {
    if (screen === "upload") { if (artifact) go("artifact"); return; }
    if (screen === "artifact") { if (validate("artifact")) go("action"); return; }
    if (screen === "action") { if (!action) return setError("Please choose what you would like to do."); go(action === "upload" ? "uploadinfo" : "release"); return; }
    if (screen === "release") { if (validate("release")) go("purpose"); return; }
    if (screen === "purpose") {
      if (!purpose) return setError("Please select the purpose of the artifact.");
      if (validate(PURPOSES.find((p) => p.id === purpose).section)) {
        const r = await run("Preparing the answer summary…", () => api.summary(payload()));
        if (r) { setSummary(r.text); go("verify"); }
      }
      return;
    }
    if (screen === "uploadinfo") { go("branch"); return; }
    if (screen === "branch") {
      if (!branchMode) return setError("Please choose how to handle the release branch.");
      if (!branchName.trim()) return setError("Please enter the branch name.");
      const r = await run("Preparing the repository with GitHub CLI… the first clone can take a moment.", () => api.prepare(payload()));
      if (r) { setReview(r); setPrTitle(r.default_pr_title); go("review"); }
    }
  };

  const confirm = async () => {
    const r = await run("Committing and pushing with GitHub CLI…", () => api.confirm({ pr_title: prTitle }));
    if (r) { setResult(r); go("done"); }
  };
  const discard = async () => {
    await run("Discarding changes…", () => api.cancel());
    setReview(null); go("branch");
  };
  const back = async () => {
    if (screen === "review") return discard();
    step(-1);
  };

  const showBack = !["upload", "done"].includes(screen);
  const ghProblem = status && (!status.gh_installed || !status.authenticated);

  // ------------------------------------------------------------------- render
  return (
    <div className="wizard" ref={topRef}>
      <header className="page-head">
        <div className="eyebrow">ARTIFACT RELEASE</div>
        <h1 className="h-page">Start a release</h1>
      </header>

      <ol className="stepper" aria-label="Progress">
        {STEPPER.map((label, i) => (
          <li key={label} className={i < STEP_OF[screen] ? "done" : i === STEP_OF[screen] ? "current" : ""}>
            <span className="num">{i < STEP_OF[screen] ? <CheckIcon width={14} height={14} strokeWidth={2.6} /> : i + 1}</span>
            <span className="lbl">{label}</span>
          </li>
        ))}
      </ol>

      <section className="panel">
        {!qs && !error && <p className="muted">Loading…</p>}

        {qs && screen === "upload" && (
          <UploadStep artifact={artifact} setArtifact={setArtifact} ghProblem={ghProblem} status={status} onRecheck={onRecheck} />
        )}

        {qs && screen === "artifact" && (
          <QuestionStep title="Artifact information" intro="Tell us about the artifact you uploaded."
            file={artifact} questions={visibleQs("artifact")} section="artifact" val={val} setVal={setVal} errors={errors} />
        )}

        {qs && screen === "action" && (
          <>
            <h2>What would you like to do?</h2>
            <p className="muted">Choose one operation for <b>{artifact?.name}</b>.</p>
            <div className="choice-grid two">
              <ChoiceCard on={action === "upload"} onClick={() => setAction("upload")} icon={<UploadIcon width={22} height={22} />}
                title="Upload Artifact" text="Add the AAR to a release branch only. No release/tag or Pull Request is created." />
              <ChoiceCard on={action === "release"} onClick={() => setAction("release")} icon={<HelpIcon width={22} height={22} />}
                title="Release / Questionnaire Information" text="Answer the release and testing questions, update README.md, then create the release/tag and Pull Request." />
            </div>
          </>
        )}

        {qs && screen === "release" && (
          <QuestionStep title="Release information" intro="Skipped questions are left out of the README and Pull Request."
            questions={visibleQs("release")} section="release" val={val} setVal={setVal} errors={errors} />
        )}

        {qs && screen === "purpose" && (
          <>
            <h2>Purpose of the artifact</h2>
            <p className="muted">Which purpose best describes this artifact?</p>
            <div className="choice-grid three">
              {PURPOSES.map((p) => (
                <ChoiceCard key={p.id} on={purpose === p.id} onClick={() => { setPurpose(p.id); setErrors({}); }} title={p.title} text={p.text} />
              ))}
            </div>
            {purpose && (
              <div className="sub-block">
                <h3>{PURPOSES.find((p) => p.id === purpose).title}</h3>
                <div className="fields">
                  {visibleQs(PURPOSES.find((p) => p.id === purpose).section).map((q) => (
                    <QuestionField key={q.id} question={q} value={val(PURPOSES.find((p) => p.id === purpose).section, q)}
                      onChange={(v) => setVal(PURPOSES.find((p) => p.id === purpose).section, q, v)} error={errors[q.id]} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {qs && screen === "verify" && (
          <>
            <h2>Questionnaire answer verification</h2>
            <p className="muted">This is what will be written to the README and the Pull Request description. Skipped questions are omitted.</p>
            <pre className="code-block">{summary}</pre>
            <p><b>Are these answers correct?</b></p>
          </>
        )}

        {qs && screen === "uploadinfo" && (
          <>
            <h2>Artifact upload</h2>
            <p className="muted">Optional details for this upload.</p>
            <div className="fields">
              {qs.upload_questions.map((q) => (
                <QuestionField key={q.key} question={{ ...q, id: q.key }} value={answers.upload[q.key] ?? ""}
                  onChange={(v) => setAnswers((a) => ({ ...a, upload: { ...a.upload, [q.key]: v } }))} />
              ))}
            </div>
          </>
        )}

        {qs && screen === "branch" && (
          <>
            <h2>Release / Pull Request branch</h2>
            <p className="muted">Base (source) branch: <b>{String(val("artifact", { key: "source_branch", default: "main" }))}</b></p>
            <div className="choice-grid two">
              <ChoiceCard on={branchMode === "new"} onClick={() => setBranchMode("new")} icon={<BranchIcon width={22} height={22} />}
                title="Create a new branch" text="A new branch is created from the source branch. It must not exist yet." />
              <ChoiceCard on={branchMode === "existing"} onClick={() => setBranchMode("existing")} icon={<BranchIcon width={22} height={22} />}
                title="Use an existing branch" text="The branch must exist on GitHub and have no open Pull Request yet." />
            </div>
            <div className="field" style={{ marginTop: 20 }}>
              <label htmlFor="branch">What branch name should be used? <span className="req">*</span></label>
              <input id="branch" value={branchName} onChange={(e) => setBranchName(e.target.value)} placeholder="e.g. release/1.2.0" spellCheck="false" autoComplete="off" />
            </div>
          </>
        )}

        {qs && screen === "review" && review && (
          <ReviewStep review={review} prTitle={prTitle} setPrTitle={setPrTitle} />
        )}

        {qs && screen === "done" && result && <DoneStep result={result} onRestart={onRestart} onExit={onExit} />}

        {error && <div className="alert error" role="alert"><AlertIcon width={18} height={18} /> <span style={{ whiteSpace: "pre-wrap" }}>{error}</span></div>}
        {busy && <div className="alert info" role="status"><span className="spinner" /> {busy}</div>}

        {qs && screen !== "done" && (
          <footer className="actions">
            {showBack ? <button className="btn ghost" onClick={back} disabled={!!busy}><ArrowLeft width={18} height={18} /> {screen === "review" ? "Discard & go back" : "Back"}</button> : <span />}
            <div className="right">
              {screen === "verify" && <button className="btn ghost" onClick={() => go("release")}>No, edit answers</button>}
              {screen === "verify" && <button className="btn primary" onClick={() => go("branch")}>Yes, continue <ArrowRight width={18} height={18} /></button>}
              {screen === "review" && !review?.no_changes && (
                <button className="btn primary" onClick={confirm} disabled={!!busy || (action === "release" && !prTitle.trim())}>
                  {action === "release" ? "Commit, push & create Pull Request" : "Commit & push"}
                </button>
              )}
              {screen === "review" && review?.no_changes && <button className="btn primary" onClick={onExit}>Finish</button>}
              {!["verify", "review"].includes(screen) && (
                <button className="btn primary" onClick={next} disabled={!!busy || (screen === "upload" && !artifact)}>
                  {screen === "branch" ? "Review changes" : "Continue"} <ArrowRight width={18} height={18} />
                </button>
              )}
            </div>
          </footer>
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
function QuestionStep({ title, intro, file, questions, section, val, setVal, errors }) {
  return (
    <>
      <h2>{title}</h2>
      <p className="muted">{intro}</p>
      {file && <div className="file-pill"><FileCheckIcon width={18} height={18} /> {file.name} <span>· {formatSize(file.size)}</span></div>}
      <div className="fields">
        {questions.map((q) => (
          <QuestionField key={q.id} question={q} value={val(section, q)} onChange={(v) => setVal(section, q, v)} error={errors[q.id]} />
        ))}
      </div>
    </>
  );
}

function ChoiceCard({ on, onClick, icon, title, text }) {
  return (
    <button type="button" className={`choice ${on ? "on" : ""}`} onClick={onClick} aria-pressed={on}>
      {icon && <span className="choice-icon">{icon}</span>}
      <span className="choice-title">{title}</span>
      <span className="choice-text">{text}</span>
      {on && <span className="choice-check"><CheckIcon width={14} height={14} strokeWidth={2.8} /></span>}
    </button>
  );
}

function UploadStep({ artifact, setArtifact, ghProblem, status, onRecheck }) {
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState(null);
  const [err, setErr] = useState("");
  const input = useRef(null);

  const pick = async (file) => {
    setErr("");
    if (!file) return;
    if (!/\.aar$/i.test(file.name) || file.name.length <= 4) {
      setErr(`"${file.name}" is not an artifact. Only .aar (Android library) files can be uploaded.`);
      return;
    }
    setProgress(0);
    try {
      const r = await api.uploadArtifact(file, setProgress);
      setArtifact(r);
    } catch (e) { setErr(e.message); } finally { setProgress(null); }
  };

  return (
    <>
      <h2>Select and upload your AAR</h2>
      <p className="muted">Choose the artifact from your computer. Only <b>.aar</b> files are accepted.</p>

      {ghProblem && (
        <div className="alert warn" role="alert">
          <AlertIcon width={18} height={18} />
          <span>
            {!status.gh_installed ? "GitHub CLI (gh) was not found on this computer. Install it from cli.github.com, then run " : "GitHub CLI is not signed in. Open a terminal and run "}
            <code>gh auth login</code>. <button className="link" onClick={onRecheck}>Check again</button>
          </span>
        </div>
      )}

      {!artifact ? (
        <div className={`dropzone ${drag ? "drag" : ""} ${err ? "bad" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}>
          <div className="dz-icon"><UploadIcon width={30} height={30} /></div>
          <div className="dz-title">{progress !== null ? `Uploading… ${progress}%` : "Drag & drop your .aar file here"}</div>
          {progress !== null ? <div className="bar"><i style={{ width: `${progress}%` }} /></div> : (
            <>
              <div className="muted">or</div>
              <button className="btn secondary" onClick={() => input.current.click()}>Browse files</button>
            </>
          )}
          <input ref={input} type="file" accept=".aar" hidden onChange={(e) => { pick(e.target.files[0]); e.target.value = ""; }} />
        </div>
      ) : (
        <div className="uploaded">
          <div className="uploaded-icon"><FileCheckIcon width={26} height={26} /></div>
          <div className="uploaded-info"><b>{artifact.name}</b><span>{formatSize(artifact.size)} · AAR validated</span></div>
          <button className="btn ghost" onClick={() => setArtifact(null)}>Choose a different file</button>
        </div>
      )}

      {err && <div className="alert error" role="alert"><AlertIcon width={18} height={18} /> {err}</div>}
    </>
  );
}

function ReviewStep({ review, prTitle, setPrTitle }) {
  return (
    <>
      <h2>Review changes</h2>
      {review.no_changes ? (
        <div className="alert info"><CheckIcon width={18} height={18} /> {review.message}</div>
      ) : (
        <p className="muted">Nothing is committed until you confirm. The AAR is a binary file, so Git shows it as added/modified rather than a line-by-line diff.</p>
      )}

      <dl className="facts">
        <div><dt>Repository</dt><dd>{review.repository}</dd></div>
        <div><dt>Branch</dt><dd>{review.branch} <small>({review.branch_mode === "new" ? "new" : "existing"}, base {review.source_branch})</small></dd></div>
        <div><dt>Artifact</dt><dd>{review.artifact_name}</dd></div>
        <div><dt>Version</dt><dd>{review.version}</dd></div>
        <div><dt>Size</dt><dd>{review.size}</dd></div>
      </dl>
      <p className="muted">{review.artifact_message}</p>

      {review.status && (<><h3>Changed files</h3><pre className="code-block">{review.status}</pre></>)}
      {review.readme_section && (
        <details open><summary>README.md section that will be added</summary><pre className="code-block">{review.readme_section}</pre></details>
      )}
      {review.readme_diff && <details><summary>README.md git diff</summary><pre className="code-block">{review.readme_diff}</pre></details>}

      {!review.no_changes && review.action === "release" && (
        <div className="field" style={{ marginTop: 20 }}>
          <label htmlFor="prt">What should the Pull Request title be? <span className="req">*</span></label>
          <input id="prt" value={prTitle} onChange={(e) => setPrTitle(e.target.value)} />
        </div>
      )}
    </>
  );
}

function DoneStep({ result, onRestart, onExit }) {
  return (
    <>
      <div className={`done-badge ${result.ok ? "ok" : "fail"}`}>{result.ok ? <CheckIcon width={30} height={30} strokeWidth={2.4} /> : <AlertIcon width={30} height={30} />}</div>
      <h2 style={{ textAlign: "center" }}>{result.ok ? "All done" : "Something went wrong"}</h2>
      <ul className="results">
        {result.steps.map((s, i) => (
          <li key={i} className={s.ok ? "ok" : "fail"}>
            <span className="r-icon">{s.ok ? <CheckIcon width={14} height={14} strokeWidth={3} /> : <AlertIcon width={14} height={14} />}</span>
            <div><b>{s.label}</b>{s.detail && <div className="detail">{s.detail}</div>}</div>
          </li>
        ))}
      </ul>
      {result.pr_url && <a className="btn secondary pr-link" href={result.pr_url} target="_blank" rel="noreferrer"><LinkIcon width={18} height={18} /> Open Pull Request</a>}
      <div className="actions center">
        <button className="btn ghost" onClick={onExit}>Back to home</button>
        <button className="btn primary" onClick={onRestart}>Start another release</button>
      </div>
    </>
  );
}
