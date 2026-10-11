import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import Modal from "../components/Modal.jsx";
import { AlertIcon, CheckIcon, LockIcon, PlusIcon, TrashIcon } from "../icons.jsx";

const TABS = [
  { id: "artifact", label: "Artifact information" },
  { id: "release", label: "Release information" },
  { id: "purpose", label: "Purpose of the artifact" },
];
const PURPOSE_TABS = [
  { id: "internal", label: "Internal testing" },
  { id: "personal", label: "Personal testing" },
  { id: "production", label: "Production" },
];

export default function ManageQuestions({ onChanged }) {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("artifact");
  const [purposeTab, setPurposeTab] = useState("internal");
  const [adding, setAdding] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const load = useCallback(() => api.questions().then(setData).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(""), 3500); return () => clearTimeout(t); }, [toast]);

  const section = tab === "purpose" ? purposeTab : tab;
  const list = data ? data.questions.filter((q) => q.section === section) : [];
  const sectionTitle = (id) => data?.sections.find((s) => s.id === id)?.title ?? id;
  const followUps = (q) => list.filter((x) => x.depends_on && x.depends_on.key === q.key);

  const remove = async () => {
    try {
      const r = await api.deleteQuestion(deleting.id);
      setToast(r.removed.length > 1 ? `Question and ${r.removed.length - 1} follow-up removed.` : "Question removed.");
      setDeleting(null); await load(); onChanged();
    } catch (e) { setError(e.message); setDeleting(null); }
  };

  return (
    <div className="wizard">
      <header className="page-head row">
        <div>
          <div className="eyebrow">WORKSPACE</div>
          <h1 className="h-page">Manage Questions</h1>
          <p className="muted">Add or remove the questions asked during a release. Changes apply to the next release you start.</p>
        </div>
        <button className="btn primary" onClick={() => setAdding(true)}><PlusIcon width={18} height={18} /> Add question</button>
      </header>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "on" : ""} onClick={() => setTab(t.id)}>{t.label}</button>
        ))}
      </div>
      {tab === "purpose" && (
        <div className="tabs sub" role="tablist">
          {PURPOSE_TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={purposeTab === t.id} className={purposeTab === t.id ? "on" : ""} onClick={() => setPurposeTab(t.id)}>{t.label}</button>
          ))}
        </div>
      )}

      {error && <div className="alert error" role="alert"><AlertIcon width={18} height={18} /> {error}</div>}

      <section className="panel q-list">
        {!data && !error && <p className="muted">Loading…</p>}
        {data && list.length === 0 && <p className="muted">No questions in this section yet. Use “Add question” to create one.</p>}
        {list.map((q, i) => (
          <div className={`q-row ${q.depends_on ? "followup" : ""}`} key={q.id}>
            <span className="q-index">{i + 1}</span>
            <div className="q-main">
              <div className="q-text">{q.label}</div>
              <div className="badges">
                <span className="badge">{q.type === "binary" ? "Yes / No" : "Text"}</span>
                <span className={`badge ${q.required ? "strong" : ""}`}>{q.required ? "Required" : "Optional"}</span>
                {q.depends_on && <span className="badge">Follow-up</span>}
                {!q.builtin && <span className="badge accent">Added by you</span>}
              </div>
            </div>
            {q.locked ? (
              <span className="locked" title="Needed to create the branch, release and Pull Request"><LockIcon width={16} height={16} /> Required by workflow</span>
            ) : (
              <button className="icon-btn danger" onClick={() => setDeleting(q)} aria-label={`Delete question: ${q.label}`} title="Delete question"><TrashIcon width={18} height={18} /></button>
            )}
          </div>
        ))}
      </section>

      {adding && data && (
        <AddQuestion sections={data.sections} initial={section} onClose={() => setAdding(false)}
          onAdded={async (q) => {
            setAdding(false); setToast(`Question added to ${sectionTitle(q.section)}.`);
            if (["internal", "personal", "production"].includes(q.section)) { setTab("purpose"); setPurposeTab(q.section); } else setTab(q.section);
            await load(); onChanged();
          }} />
      )}

      {deleting && (
        <Modal title="Delete this question?" onClose={() => setDeleting(null)} width={480}
          footer={<><button className="btn ghost" onClick={() => setDeleting(null)}>Cancel</button><button className="btn danger" onClick={remove}>Delete question</button></>}>
          <div className="alert warn"><AlertIcon width={18} height={18} /> This cannot be undone.</div>
          <p className="confirm-q">“{deleting.label}”</p>
          <p className="muted">Section: {sectionTitle(deleting.section)}</p>
          {followUps(deleting).length > 0 && (
            <p className="muted">Its {followUps(deleting).length} follow-up question{followUps(deleting).length > 1 ? "s" : ""} will be deleted as well.</p>
          )}
        </Modal>
      )}

      {toast && <div className="toast" role="status"><CheckIcon width={16} height={16} strokeWidth={2.6} /> {toast}</div>}
    </div>
  );
}

function AddQuestion({ sections, initial, onClose, onAdded }) {
  const [section, setSection] = useState(initial);
  const [label, setLabel] = useState("");
  const [type, setType] = useState("text");
  const [required, setRequired] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!label.trim()) return setError("Please enter the question.");
    setBusy(true); setError("");
    try { const r = await api.addQuestion({ section, label: label.trim(), type, required }); onAdded(r.question); }
    catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <Modal title="Add a question" onClose={onClose} width={600}
      footer={<><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn primary" onClick={submit} disabled={busy}>Add question</button></>}>
      <div className="field">
        <label>Where should this question appear?</label>
        <div className="sec-options">
          {sections.filter((s) => s.group !== "Purpose of the artifact").map((s) => (
            <button type="button" key={s.id} className={`sec-option ${section === s.id ? "on" : ""}`} onClick={() => setSection(s.id)} aria-pressed={section === s.id}>{s.title}</button>
          ))}
        </div>
        <div className="sec-group">
          <div className="sec-group-title">Purpose of the artifact</div>
          <div className="sec-options">
            {sections.filter((s) => s.group === "Purpose of the artifact").map((s) => (
              <button type="button" key={s.id} className={`sec-option ${section === s.id ? "on" : ""}`} onClick={() => setSection(s.id)} aria-pressed={section === s.id}>{s.title}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="field">
        <label htmlFor="newq">Question <span className="req">*</span></label>
        <textarea id="newq" rows={3} value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Has the release been tested on Android 14?" autoFocus />
      </div>

      <div className="field">
        <label>Answer type</label>
        <div className="segmented">
          <button type="button" className={type === "text" ? "on" : ""} onClick={() => setType("text")}>Text answer</button>
          <button type="button" className={type === "binary" ? "on" : ""} onClick={() => setType("binary")}>Yes / No</button>
        </div>
      </div>

      <div className="field">
        <label>Is answering this question important?</label>
        <div className="segmented">
          <button type="button" className={required ? "on" : ""} onClick={() => setRequired(true)}>Yes — required</button>
          <button type="button" className={!required ? "on" : ""} onClick={() => setRequired(false)}>No — can be skipped</button>
        </div>
      </div>

      {error && <div className="alert error"><AlertIcon width={18} height={18} /> {error}</div>}
    </Modal>
  );
}
