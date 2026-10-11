import { ArrowRight, BranchIcon, CheckIcon, FileCheckIcon, FileIcon, HelpIcon, PulseIcon } from "../icons.jsx";

const STEPS = [
  { icon: <FileIcon width={22} height={22} />, tag: "01 · ARTIFACT UPLOAD", title: "Select and upload your AAR",
    text: "Choose an .aar file from your computer, specify the target repository and version, and upload it to the corresponding GitHub Release. Existing assets with the same filename are not overwritten." },
  { icon: <HelpIcon width={22} height={22} />, tag: "02 · RELEASE INFORMATION", title: "Complete release details",
    text: "Answer questions about the artifact, release changes, testing, and deployment. Relevant follow-up questions appear automatically. Choose a new branch or an existing branch associated with your pull request." },
  { icon: <BranchIcon width={22} height={22} />, tag: "03 · REVIEW & PULL REQUEST", title: "Review and submit changes",
    text: "Preview the proposed README.md changes before confirming. The application commits and pushes the update, then creates a new pull request or updates the matching open pull request through GitHub CLI." },
];

export default function Home({ onStart }) {
  return (
    <div className="home">
      <section className="hero">
        <div className="hero-copy">
          <h1>Simplify Your SDK Release <span>Workflow</span></h1>
          <p>Upload AAR artifacts, collect release and testing details, and manage release documentation through GitHub pull requests—all in one place with the GitHub CLI.</p>
          <button className="btn primary" onClick={onStart}>Start a release <ArrowRight width={20} height={20} /></button>
        </div>

        <div className="hero-art" aria-hidden="true">
          <svg className="rings" viewBox="0 0 460 330" fill="none">
            <ellipse cx="230" cy="165" rx="170" ry="150" transform="rotate(-18 230 165)" />
            <ellipse cx="230" cy="165" rx="205" ry="120" transform="rotate(12 230 165)" />
          </svg>
          <div className="art-core"><FileCheckIcon width={54} height={54} strokeWidth={1.5} /></div>
          <div className="chip c1"><CheckIcon width={18} height={18} /> AAR validated</div>
          <div className="chip c2"><BranchIcon width={18} height={18} /> gh CLI</div>
          <div className="chip c3"><PulseIcon width={18} height={18} /> Release flow</div>
        </div>
      </section>

      <section className="workflow">
        <div className="eyebrow">YOUR WORKFLOW</div>
        <h2>Upload your AAR &amp; document your release, with a clear review process for every README update.</h2>
        <div className="step-cards">
          {STEPS.map((s) => (
            <article className="step-card" key={s.tag}>
              <div className="step-icon">{s.icon}</div>
              <div className="eyebrow sm">{s.tag}</div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
