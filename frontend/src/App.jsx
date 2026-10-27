import { useState } from "react";
import { ResearchApiError, submitResearch } from "./api/client.js";

const asList = (value) => (Array.isArray(value) ? value : []);
const text = (value, fallback = "Unavailable") => {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number") return String(value);
  return fallback;
};
const statusLabel = (status) =>
  ({
    verified: "Verified",
    partially_verified: "Partially verified",
    unverified: "Unverified",
  })[status] || "Verification unavailable";

function Header({ onHome, onMenu, onNew }) {
  return (
    <header className="topbar">
      <button
        className="mobile-menu"
        aria-label="Open workspace navigation"
        onClick={onMenu}
      >
        ≡
      </button>
      <button className="brand" onClick={onHome}>
        <span className="brand-mark">R</span>
        <span>
          <strong>ResearchPilot</strong>
          <small>Evidence workspace</small>
        </span>
      </button>
      <div className="top-actions">
        <span className="top-note">Research Workspace</span>
        <button className="button primary" onClick={onNew}>
          New research
        </button>
      </div>
    </header>
  );
}

function Sidebar({ open, onHome }) {
  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <span className="eyebrow">Workspace</span>
      <nav className="nav">
        <button className="active" onClick={onHome}>
          + &nbsp; New research
        </button>
        <button disabled>◷ &nbsp; Research history</button>
        <button disabled>◇ &nbsp; Saved research</button>
      </nav>
      <div className="sidebar-bottom">
        <button className="nav" disabled>
          ◌ &nbsp; How it works
        </button>
        <button className="nav" disabled>
          ? &nbsp; About ResearchPilot
        </button>
      </div>
    </aside>
  );
}

function EmptyState({ title, children }) {
  return (
    <div className="notice-panel">
      <h3>{title}</h3>
      <p className="detail">{children}</p>
    </div>
  );
}

function Home({
  question,
  error,
  loading,
  setQuestion,
  onAnalyze,
  onSuggestion,
}) {
  const suggestions = [
    [
      "Limitations of RAG for factual QA",
      "What are the current limitations of retrieval-augmented generation for factual question answering?",
    ],
    [
      "Multimodal models in diagnosis",
      "How effective are multimodal models in medical diagnosis?",
    ],
    [
      "Open challenges in AI cybersecurity",
      "What are the open challenges in AI cybersecurity?",
    ],
  ];
  return (
    <div className="content">
      <section className="hero">
        <span className="eyebrow">Academic intelligence, made traceable</span>
        <h1>
          Research smarter.
          <br />
          Verify what matters.
        </h1>
        <p>
          ResearchPilot turns a research question into a concise evidence
          review: relevant papers, careful comparisons, missing information, and
          source traceability.
        </p>
        <form
          className="search-box"
          onSubmit={(event) => {
            event.preventDefault();
            onAnalyze();
          }}
        >
          <label htmlFor="question">Research question</label>
          <textarea
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What would you like to research?"
            disabled={loading}
            aria-invalid={Boolean(error)}
          />
          <div className="search-footer">
            <span className="search-hint">
              Start with a question, not a keyword.
            </span>
            <button className="button primary" type="submit" disabled={loading}>
              {loading ? "Analyzing…" : "Analyze research →"}
            </button>
          </div>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
        </form>
      </section>
      <section>
        <div className="section-head">
          <h2>Suggested research</h2>
          <span>Questions to start an analysis</span>
        </div>
        <div className="suggestions">
          {suggestions.map(([label, value]) => (
            <button
              key={value}
              onClick={() => onSuggestion(value)}
              disabled={loading}
            >
              {label}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

import { useState, useEffect, useRef } from "react";

const PIPELINE_STAGES = [
  {
    id: "search",
    icon: "⌕",
    label: "Searching literature",
    detail: "Querying OpenAlex for candidate papers matching your question…",
    durationMs: 2800,
  },
  {
    id: "retrieve",
    icon: "⬇",
    label: "Retrieving papers",
    detail: "Fetching paper records and preparing content for extraction…",
    durationMs: 3500,
  },
  {
    id: "extract",
    icon: "⬡",
    label: "Reading & extracting",
    detail:
      "Downloading PDFs, parsing with pypdf, extracting methods, datasets and metrics via Groq AI…",
    durationMs: 11000,
  },
  {
    id: "verify",
    icon: "✓",
    label: "Verifying authenticity",
    detail:
      "Cross-referencing each paper's bibliographic metadata with OpenAlex…",
    durationMs: 5500,
  },
  {
    id: "compare",
    icon: "⇄",
    label: "Comparing evidence",
    detail:
      "Analysing experimental setups, datasets, metrics, and baselines across papers…",
    durationMs: 3200,
  },
  {
    id: "reason",
    icon: "◎",
    label: "Identifying gaps",
    detail: "Flagging missing structured information in retrieved literature…",
    durationMs: 2500,
  },
  {
    id: "synthesize",
    icon: "✦",
    label: "Synthesising findings",
    detail:
      "Groq AI is generating your executive summary, key findings, and candidate gaps…",
    durationMs: 99999, // stays active until API responds
  },
];

function LoadingState() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [doneIndices, setDoneIndices] = useState(new Set());
  const [visibleIndices, setVisibleIndices] = useState(new Set([0]));
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);
  const elapsedRef = useRef(null);

  useEffect(() => {
    let currentIndex = 0;
    const advance = () => {
      const stage = PIPELINE_STAGES[currentIndex];
      if (!stage || currentIndex >= PIPELINE_STAGES.length - 1) return;
      timerRef.current = setTimeout(() => {
        const next = currentIndex + 1;
        setDoneIndices((prev) => new Set([...prev, currentIndex]));
        setActiveIndex(next);
        setVisibleIndices((prev) => new Set([...prev, next]));
        currentIndex = next;
        advance();
      }, stage.durationMs);
    };
    advance();

    // Elapsed seconds ticker
    elapsedRef.current = setInterval(() => {
      setElapsed((s) => s + 1);
    }, 1000);

    return () => {
      clearTimeout(timerRef.current);
      clearInterval(elapsedRef.current);
    };
  }, []);

  const fmtElapsed = (s) => {
    if (s < 60) return `${s}s`;
    return `${Math.floor(s / 60)}m ${s % 60}s`;
  };

  return (
    <div className="loading-shell">
      <div className="loading-header">
        <span className="eyebrow loading-eyebrow">Research in progress</span>
        <h1 className="loading-title">Following the evidence.</h1>
        <p className="loading-subtitle">
          Each agent is running in sequence. This typically takes 30–60 seconds.
        </p>
        <span className="loading-timer">{fmtElapsed(elapsed)}</span>
      </div>

      <div className="pipeline-track">
        {PIPELINE_STAGES.map((stage, idx) => {
          const isDone = doneIndices.has(idx);
          const isActive = activeIndex === idx;
          const isVisible = visibleIndices.has(idx);
          const stateClass = isDone
            ? "pl-done"
            : isActive
              ? "pl-active"
              : "pl-pending";

          return (
            <div
              key={stage.id}
              className={`pl-row ${stateClass} ${isVisible ? "pl-visible" : ""}`}
              style={{ transitionDelay: `${idx * 40}ms` }}
            >
              {/* Connector line */}
              {idx < PIPELINE_STAGES.length - 1 && (
                <span
                  className={`pl-connector ${isDone ? "pl-connector-done" : ""}`}
                />
              )}

              {/* Icon bubble */}
              <span className="pl-icon-wrap">
                {isDone ? (
                  <span className="pl-icon pl-icon-check">✓</span>
                ) : (
                  <span className="pl-icon">
                    {isActive ? <span className="pl-pulse-dot" /> : stage.icon}
                  </span>
                )}
              </span>

              {/* Content */}
              <div className="pl-content">
                <div className="pl-content-top">
                  <strong className="pl-label">{stage.label}</strong>
                  {isActive && <span className="pl-badge">Running</span>}
                  {isDone && (
                    <span className="pl-badge pl-badge-done">Done</span>
                  )}
                </div>
                {(isActive || isDone) && (
                  <p className="pl-detail">{stage.detail}</p>
                )}
                {isActive && (
                  <div className="pl-scanline">
                    <span className="pl-scanline-bar" />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Warnings({ warnings }) {
  if (!warnings.length) return null;
  return (
    <section className="section">
      <div className="notice-panel warning">
        <div className="section-head">
          <h2>Warnings</h2>
          <span>{warnings.length} returned by the service</span>
        </div>
        <ol>
          {warnings.map((warning, index) => (
            <li key={`${warning}-${index}`}>{text(warning)}</li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function PaperDrawer({ paper, onClose }) {
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Paper evidence"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          className="drawer-close"
          aria-label="Close source panel"
          onClick={onClose}
        >
          ×
        </button>
        <span className="eyebrow">Source record</span>
        <h2>{text(paper.title)}</h2>
        <div className="paper-meta">
          {asList(paper.authors).join(" · ")} ·{" "}
          {text(paper.year, "Year unavailable")}
        </div>
        <span className={`status ${paper.authenticity_status || "unverified"}`}>
          {statusLabel(paper.authenticity_status)}
        </span>
        <div className="drawer-block">
          <h3>Abstract</h3>
          <p>
            {text(
              paper.abstract,
              "Abstract unavailable in the retrieved metadata.",
            )}
          </p>
        </div>
        <div className="drawer-block">
          <h3>Reported metadata</h3>
          <p>
            Methods:{" "}
            {asList(paper.methods).join(", ") ||
              "Not reported in retrieved metadata."}
            <br />
            Datasets:{" "}
            {asList(paper.datasets).join(", ") ||
              "Not reported in retrieved metadata."}
            <br />
            Metrics:{" "}
            {asList(paper.metrics).join(", ") ||
              "Not reported in retrieved metadata."}
            <br />
            Limitations:{" "}
            {asList(paper.limitations).join(", ") ||
              "Not reported in retrieved metadata."}
          </p>
        </div>
        <div className="drawer-block">
          <h3>Verification details</h3>
          <p>
            {asList(paper.authenticity_reasons).join(" ") ||
              "Verification details were not returned by the service."}
          </p>
        </div>
        <div className="drawer-block">
          <h3>Source</h3>
          <p>{text(paper.doi, "DOI unavailable")}</p>
          {paper.url ? (
            <a
              className="button primary"
              href={paper.url}
              target="_blank"
              rel="noreferrer"
            >
              Open original paper ↗
            </a>
          ) : (
            <span className="detail">Source link unavailable.</span>
          )}
        </div>
      </aside>
    </div>
  );
}

function PaperCard({ paper, onOpen }) {
  return (
    <article className="paper-row">
      <div>
        <h3>{text(paper.title, "Untitled paper")}</h3>
        <div className="paper-meta">
          {asList(paper.authors).slice(0, 2).join(" · ") ||
            "Authors unavailable"}{" "}
          · {text(paper.year, "Year unavailable")} ·{" "}
          {text(paper.source, "Source unavailable")}
        </div>
        <p className="paper-abstract">
          {text(
            paper.abstract,
            "Abstract unavailable in the retrieved metadata.",
          )}
        </p>
        <details className="detail">
          <summary>Show metadata</summary>
          <p>
            Methods:{" "}
            {asList(paper.methods).join(", ") ||
              "Not reported in retrieved metadata."}
            <br />
            Datasets:{" "}
            {asList(paper.datasets).join(", ") ||
              "Not reported in retrieved metadata."}
            <br />
            Metrics:{" "}
            {asList(paper.metrics).join(", ") ||
              "Not reported in retrieved metadata."}
            <br />
            DOI: {text(paper.doi, "DOI unavailable")}
          </p>
        </details>
      </div>
      <div className="paper-side">
        <span className={`status ${paper.authenticity_status || "unverified"}`}>
          {statusLabel(paper.authenticity_status)}
        </span>
        <div className="paper-actions">
          <button className="text-button" onClick={() => onOpen(paper)}>
            View evidence →
          </button>
          {paper.url && (
            <a
              className="text-button"
              href={paper.url}
              target="_blank"
              rel="noreferrer"
            >
              Open paper ↗
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

const comparabilityColor = (c) => {
  if (c === "potentially_comparable") return "status";
  if (c === "insufficient_information") return "status partial";
  return "status unverified";
};
const comparabilityLabel = (c) =>
  ({
    potentially_comparable: "Potentially comparable",
    not_directly_comparable: "Not directly comparable",
    insufficient_information: "Insufficient information",
  })[c] || c;

function Comparison({ comparisons, papers = [] }) {
  // Build a map from paper_id → title for display
  const titleMap = papers.reduce((m, p) => {
    if (p.paper_id) m[p.paper_id] = p.title || p.paper_id;
    return m;
  }, {});
  const resolveId = (id) =>
    titleMap[id] ||
    id
      .replace("https://openalex.org/", "Work ")
      .replace("https://doi.org/", "");

  return (
    <section className="section">
      <div className="section-head">
        <h2>Paper comparison</h2>
        <span>
          {comparisons.length} pair{comparisons.length === 1 ? "" : "s"}{" "}
          analysed
        </span>
      </div>
      {comparisons.length ? (
        <div className="comparison">
          {comparisons.map((item, index) => (
            <article
              className="notice-panel"
              key={`${item.paper_ids?.join("-") || "comparison"}-${index}`}
            >
              <div className="section-head">
                <h3>
                  {asList(item.paper_ids).length === 2
                    ? `Pair ${index + 1}`
                    : text(item.dimension, "Comparison")}
                </h3>
                <span className={comparabilityColor(item.comparability)}>
                  {comparabilityLabel(item.comparability)}
                </span>
              </div>
              <p className="detail" style={{ marginTop: 8 }}>
                {text(
                  item.reason || item.finding,
                  "No comparison explanation was returned.",
                )}
              </p>
              {asList(item.paper_ids).length > 0 && (
                <p
                  style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}
                >
                  Papers: {item.paper_ids.map(resolveId).join(" · ")}
                </p>
              )}
              {item.inference && (
                <span
                  className="tag"
                  style={{ marginTop: 8, display: "inline-block" }}
                >
                  Inference
                </span>
              )}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="Comparison unavailable">
          The critic agent did not return comparison items for this report.
        </EmptyState>
      )}
    </section>
  );
}

function KeyFindings({ findings }) {
  return (
    <section className="section">
      <div className="section-head">
        <h2>Key findings</h2>
        <span>{findings.length} returned by Groq</span>
      </div>
      {findings.length ? (
        <div className="findings">
          {findings.map((item, index) => (
            <article
              className="finding"
              key={`${item.finding || "finding"}-${index}`}
            >
              <span className="finding-number">0{index + 1}</span>
              <h3>{text(item.finding || item.title, "Finding unavailable")}</h3>
              <p>
                {text(
                  item.explanation || item.reason,
                  "Explanation unavailable.",
                )}
              </p>
              {asList(item.paper_ids).length > 0 && (
                <span className="evidence-count">
                  Sources: {item.paper_ids.join(", ")}
                </span>
              )}
              {asList(item.conflicting_paper_ids).length > 0 && (
                <span className="detail">
                  Conflicting sources: {item.conflicting_paper_ids.join(", ")}
                </span>
              )}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="Key findings unavailable">
          Ollama did not return structured findings for this report.
        </EmptyState>
      )}
    </section>
  );
}

function MissingInformation({ items }) {
  // Group items by paper_id so the display isn't one giant flat list
  const grouped = items.reduce((acc, item) => {
    const key = item.paper_id || "unknown";
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});
  const groups = Object.entries(grouped);

  return (
    <section className="section">
      <div className="section-head">
        <h2>Missing information</h2>
        <span>
          {items.length} field{items.length === 1 ? "" : "s"} not in retrieved
          metadata
        </span>
      </div>
      {groups.length ? (
        <div className="gap-list">
          {groups.map(([paperId, groupItems]) => {
            // Use the paper_title field the backend now sends directly
            const displayTitle =
              groupItems[0]?.paper_title ||
              paperId.replace("https://openalex.org/", "");
            return (
              <article
                className="notice-panel"
                key={paperId}
                style={{ marginBottom: 0 }}
              >
                <p style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>
                  {displayTitle}
                </p>
                <div className="ledger">
                  {groupItems.map((item, idx) => (
                    <div className="ledger-item" key={`${item.field}-${idx}`}>
                      <span className="ledger-dot" />
                      <div>
                        <span className="ledger-label">
                          {text(item.field, "Unknown field")}
                        </span>
                        <p>
                          {text(
                            item.follow_up_action,
                            "No suggestion available.",
                          )}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <EmptyState title="No missing-information items returned">
          All retrieved papers had complete structured metadata.
        </EmptyState>
      )}
      <p className="detail" style={{ marginTop: 12 }}>
        These gaps reflect what the OpenAlex metadata API returned, not the
        actual paper content.
      </p>
    </section>
  );
}

function CandidateGaps({ gaps }) {
  const validGaps = gaps.filter(
    (gap) => gap && typeof gap === "object" && (gap.title || gap.description),
  );
  return (
    <section className="section">
      <div className="section-head">
        <h2>Candidate research gaps</h2>
        <span>{validGaps.length} returned</span>
      </div>
      {validGaps.length ? (
        <div className="gap-list">
          {validGaps.map((gap, index) => (
            <article className="gap-card" key={`${gap.title}-${index}`}>
              <span className="gap-number">0{index + 1}</span>
              <div>
                <h3>{text(gap.title)}</h3>
                <p>
                  {text(
                    gap.description || gap.explanation,
                    "Explanation unavailable.",
                  )}
                </p>
              </div>
              {gap.confidence && (
                <span className="tag">Candidate · {gap.confidence}</span>
              )}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="Candidate gaps unavailable">
          The current API does not return distinct candidate-gap objects. The
          reasoning items above describe missing extracted information instead.
        </EmptyState>
      )}
      <p className="detail">
        Candidate gaps, when returned, describe the retrieved literature and do
        not establish that no prior research exists.
      </p>
    </section>
  );
}

function AgentTrace({ trace }) {
  return (
    <section className="section">
      <div className="section-head">
        <h2>Agent execution</h2>
        <span>{trace.length} entries returned</span>
      </div>
      {trace.length ? (
        <div className="trace">
          {trace.map((entry, index) => {
            const agent = typeof entry === "string" ? entry : entry.agent_name;
            return (
              <div className="trace-row" key={`${agent}-${index}`}>
                <strong>{text(agent, "Agent")}</strong>
                <span>
                  {typeof entry === "string"
                    ? "Returned"
                    : `${text(entry.status, "Status unavailable")} · ${text(entry.summary, "No summary returned.")}`}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState title="Agent trace unavailable">
          The API did not return execution details for this report.
        </EmptyState>
      )}
    </section>
  );
}

function Results({ report, onPaper }) {
  const papers = asList(report.papers);
  const comparisons = asList(report.comparison);
  const missing = asList(report.missing_information);
  const gaps = asList(report.candidate_gaps);
  const trace = asList(report.agent_trace);
  const warnings = asList(report.warnings);
  return (
    <div className="content">
      <div className="view-header">
        <div>
          <span className="eyebrow">Research results</span>
          <h2 style={{ marginTop: 8 }}>Evidence review</h2>
          <p>“{text(report.research_question)}”</p>
        </div>
        <span className="status">Live API response</span>
      </div>
      <section className="summary">
        <div className="summary-copy">
          <span className="eyebrow">Executive summary</span>
          {report.summary ? (
            <p>{report.summary}</p>
          ) : (
            <EmptyState title="Summary unavailable">
              Groq did not return an executive summary for this report.
            </EmptyState>
          )}
        </div>
        <div className="evidence-overview">
          <span className="eyebrow">Report scope</span>
          <strong>
            {papers.length} paper record{papers.length === 1 ? "" : "s"}{" "}
            returned.
          </strong>
          <p className="detail">
            Counts and evidence strength are shown only when the API supplies
            them.
          </p>
        </div>
      </section>
      <KeyFindings findings={asList(report.key_findings)} />
      <section className="section">
        <div className="section-head">
          <h2>Evidence ledger</h2>
          <span>Retrieved source records</span>
        </div>
        {papers.length ? (
          <div className="papers">
            {papers.map((paper) => (
              <PaperCard
                key={paper.paper_id || paper.url || paper.title}
                paper={paper}
                onOpen={onPaper}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="No paper evidence returned">
            The discovery agent returned no paper records.
          </EmptyState>
        )}
      </section>
      <Comparison comparisons={comparisons} papers={papers} />
      <MissingInformation items={missing} />
      <CandidateGaps gaps={gaps} />
      <AgentTrace trace={trace} />
      <Warnings warnings={warnings} />
    </div>
  );
}

export default function App() {
  const [view, setView] = useState("home");
  const [question, setQuestion] = useState("");
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [drawerPaper, setDrawerPaper] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  async function analyze() {
    const asked = question.trim();
    if (!asked) {
      setError("Enter a research question before analyzing.");
      return;
    }
    setError("");
    setView("loading");
    try {
      setReport(await submitResearch(asked));
      setView("results");
    } catch (requestError) {
      const message =
        requestError instanceof ResearchApiError
          ? requestError.message
          : "The research request failed. Try again.";
      setError(message);
      setView("home");
    }
  }
  function home() {
    setView("home");
    setReport(null);
    setDrawerPaper(null);
    setSidebarOpen(false);
  }
  return (
    <div className="app">
      <Header
        onHome={home}
        onNew={home}
        onMenu={() => setSidebarOpen((open) => !open)}
      />
      <div className="layout">
        <Sidebar open={sidebarOpen} onHome={home} />
        <main className="main">
          {view === "home" && (
            <Home
              question={question}
              error={error}
              loading={false}
              setQuestion={setQuestion}
              onAnalyze={analyze}
              onSuggestion={(value) => {
                setError("");
                setQuestion(value);
              }}
            />
          )}
          {view === "loading" && <LoadingState />}
          {view === "results" && report && (
            <Results report={report} onPaper={setDrawerPaper} />
          )}
        </main>
      </div>
      {drawerPaper && (
        <PaperDrawer paper={drawerPaper} onClose={() => setDrawerPaper(null)} />
      )}
    </div>
  );
}
