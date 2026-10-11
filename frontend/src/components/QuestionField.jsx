const SHORT_KEYS = new Set(["current_version", "previous_version", "repository", "source_branch", "code_reviewer", "approved_by"]);
const PLACEHOLDERS = { repository: "OWNER/REPO  (e.g. my-org/my-sdk)", current_version: "e.g. v1.2.0", previous_version: "e.g. v1.1.0" };

export default function QuestionField({ question, value, onChange, error }) {
  const { key, label, type, required } = question;
  const id = `q-${question.id}`;

  return (
    <div className={`field ${error ? "has-error" : ""} ${question.depends_on ? "followup" : ""}`}>
      <label htmlFor={id}>
        {label.replace(/\s*\(optional\)\s*$/i, "")}
        {required ? <span className="req" title="Required"> *</span> : <span className="opt"> optional</span>}
      </label>

      {type === "binary" ? (
        <div className="segmented" role="radiogroup" aria-label={label} id={id}>
          {[["1", "Yes"], ["0", "No"], ...(required ? [] : [["", "Skip"]])].map(([v, text]) => (
            <button type="button" key={v || "skip"} role="radio" aria-checked={(value ?? "") === v}
              className={(value ?? "") === v ? "on" : ""} onClick={() => onChange(v)}>{text}</button>
          ))}
        </div>
      ) : SHORT_KEYS.has(key) ? (
        <input id={id} type="text" value={value ?? ""} placeholder={PLACEHOLDERS[key] || ""}
          onChange={(e) => onChange(e.target.value)} autoComplete="off" spellCheck="false" />
      ) : (
        <textarea id={id} rows={2} value={value ?? ""} placeholder={required ? "Required" : "Leave empty to skip"}
          onChange={(e) => onChange(e.target.value)} />
      )}

      {error && <div className="field-error">{error}</div>}
    </div>
  );
}
