import { useEffect, useState } from 'react'
import './App.css'

const workflowStages = [
  'Research Manager',
  'Search & Authenticity',
  'Critic',
  'Reasoning',
  'Synthesis',
]

const reportArrays = [
  'papers',
  'comparison',
  'missing_information',
  'candidate_gaps',
  'warnings',
  'agent_trace',
]

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isReport(value) {
  return (
    isRecord(value) &&
    typeof value.research_question === 'string' &&
    reportArrays.every((field) => Array.isArray(value[field]))
  )
}

function textValue(value) {
  if (typeof value === 'string' || typeof value === 'number') {
    return String(value) || 'Not reported'
  }

  if (Array.isArray(value)) {
    const values = value
      .filter((item) => typeof item === 'string' || typeof item === 'number')
      .map(String)
    return values.length ? values.join('; ') : 'Not reported'
  }

  return 'Not reported'
}

function displayValues(value) {
  if (Array.isArray(value)) {
    return value.filter(
      (item) =>
        typeof item === 'string' ||
        typeof item === 'number' ||
        isRecord(item),
    )
  }

  return value === null || value === undefined || value === '' ? [] : [value]
}

function errorMessageFrom(payload, fallback) {
  if (typeof payload === 'string' && payload.trim()) {
    return payload
  }

  if (isRecord(payload)) {
    const detail = payload.detail ?? payload.message
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    if (detail !== undefined) {
      return JSON.stringify(detail)
    }
  }

  return fallback
}

async function readJsonResponse(response) {
  const bodyText = await response.text()
  let payload

  try {
    payload = bodyText ? JSON.parse(bodyText) : null
  } catch {
    payload = bodyText
  }

  if (!response.ok) {
    throw new Error(
      errorMessageFrom(payload, `Request failed with status ${response.status}.`),
    )
  }

  return payload
}

function SectionHeading({ eyebrow, title, detail }) {
  return (
    <div className="section-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {detail && <span className="section-detail">{detail}</span>}
    </div>
  )
}

function EmptyNotice({ children }) {
  return <p className="empty-notice">{children}</p>
}

function DataList({ items, emptyText }) {
  const values = displayValues(items)

  if (!values.length) {
    return <EmptyNotice>{emptyText}</EmptyNotice>
  }

  return (
    <ul className="data-list">
      {values.map((item, index) => (
        <li key={`${index}-${typeof item === 'string' ? item : 'record'}`}>
          {isRecord(item) ? (
            <dl className="record-details">
              {Object.entries(item).map(([field, value]) => (
                <div key={field}>
                  <dt>{field.replaceAll('_', ' ')}</dt>
                  <dd>{textValue(value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            textValue(item)
          )}
        </li>
      ))}
    </ul>
  )
}

function safeWebUrl(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value)
}

function getPaperTitle(paper) {
  return typeof paper.title === 'string' && paper.title.trim()
    ? paper.title
    : 'Title not reported'
}

function comparisonPapers(comparison, papers) {
  const ids = Array.isArray(comparison.paper_ids)
    ? comparison.paper_ids.map(String)
    : []

  return papers.filter((paper) => ids.includes(String(paper.paper_id)))
}

function App() {
  const [question, setQuestion] = useState('')
  const [paperCount, setPaperCount] = useState('5')
  const [status, setStatus] = useState('idle')
  const [report, setReport] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [apiStatus, setApiStatus] = useState('checking')

  async function checkApiHealth() {
    setApiStatus('checking')
    try {
      const response = await fetch('/api/health')
      const payload = await readJsonResponse(response)
      setApiStatus(isRecord(payload) && payload.status === 'ok' ? 'online' : 'unverified')
    } catch {
      setApiStatus('unverified')
    }
  }

  useEffect(() => {
    void checkApiHealth()
  }, [])

  async function submitResearch() {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) {
      setStatus('empty')
      setErrorMessage('')
      return
    }

    setStatus('loading')
    setReport(null)
    setErrorMessage('')

    try {
      const response = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: trimmedQuestion,
          max_papers: Number(paperCount),
        }),
      })
      const payload = await readJsonResponse(response)

      if (!isReport(payload)) {
        throw new Error(
          'The API response did not match the expected research report structure.',
        )
      }

      setReport(payload)
      setStatus('success')
      setApiStatus('online')
    } catch (error) {
      setStatus('error')
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'An unexpected error occurred while requesting research.',
      )
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    void submitResearch()
  }

  const missingInformation = report?.missing_information ?? []
  const followUpQuestions = missingInformation.flatMap((item) => {
    if (!isRecord(item)) return []
    return displayValues(item.follow_up_action)
  })

  const apiStatusLabel = {
    checking: 'Checking API',
    online: 'API reachable',
    unverified: 'API not verified',
  }[apiStatus]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#workspace" aria-label="ResearchPilot AI home">
          <span className="brand-mark" aria-hidden="true">R</span>
          <span className="brand-copy">
            <strong>ResearchPilot</strong>
            <span>AI RESEARCH ASSISTANT</span>
          </span>
        </a>

        <div className="sidebar-divider" />
        <p className="sidebar-label">WORKSPACE</p>
        <nav className="sidebar-nav" aria-label="Research workspace">
          <a className="nav-link active" href="#workspace">
            <span aria-hidden="true">⌂</span>
            Research workspace
          </a>
          <a className="nav-link" href="#workflow">
            <span aria-hidden="true">◇</span>
            Agent workflow
          </a>
          <a className="nav-link" href="#results">
            <span aria-hidden="true">▤</span>
            Evidence & report
          </a>
        </nav>

        <div className="sidebar-spacer" />
        <div className="integrity-note">
          <span className="integrity-icon" aria-hidden="true">i</span>
          <div>
            <strong>Research integrity</strong>
            <p>Metadata checks do not establish scientific truth or prove novelty.</p>
          </div>
        </div>
        <div className="sidebar-footer">
          <span className={`health-dot ${apiStatus}`} aria-hidden="true" />
          <span>{apiStatusLabel}</span>
          <button
            className="icon-button"
            type="button"
            onClick={() => void checkApiHealth()}
            aria-label="Check API health again"
            title="Check API health again"
          >
            ↻
          </button>
        </div>
      </aside>

      <main className="main-content" id="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Research workspace</span>
            <span aria-hidden="true">/</span>
            <strong>New inquiry</strong>
          </div>
          <span className="prototype-badge">
            <span aria-hidden="true" />
            Research prototype
          </span>
        </header>

        <div className="content-wrap">
          <section className="welcome">
            <p className="eyebrow">EVIDENCE-LED DISCOVERY</p>
            <h1>Turn research questions into evidence.</h1>
            <p>
              Search the literature, inspect the limits of available evidence,
              and follow every result back to its source.
            </p>
          </section>

          <section className="research-card" aria-labelledby="research-heading">
            <div className="card-topline">
              <span className="input-step">01</span>
              <span>RESEARCH INQUIRY</span>
            </div>
            <h2 id="research-heading">What would you like to investigate?</h2>
            <p className="card-description">
              Phrase a focused question. The response will reflect only the
              information returned by the research service.
            </p>

            <form onSubmit={handleSubmit}>
              <label htmlFor="research-question">Research question</label>
              <textarea
                id="research-question"
                name="question"
                placeholder="e.g. How do transformer models compare for detecting misinformation?"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                aria-invalid={status === 'empty'}
                aria-describedby={status === 'empty' ? 'question-error' : undefined}
                disabled={status === 'loading'}
              />

              <div className="form-bottom">
                <div className="paper-select">
                  <label htmlFor="paper-count">Maximum papers</label>
                  <select
                    id="paper-count"
                    name="max_papers"
                    value={paperCount}
                    onChange={(event) => setPaperCount(event.target.value)}
                    disabled={status === 'loading'}
                  >
                    <option value="3">3 papers</option>
                    <option value="5">5 papers</option>
                    <option value="10">10 papers</option>
                  </select>
                </div>
                <button
                  className="primary-button"
                  type="submit"
                  disabled={status === 'loading'}
                >
                  {status === 'loading' ? (
                    <>
                      <span className="button-spinner" aria-hidden="true" />
                      Requesting research
                    </>
                  ) : status === 'error' ? (
                    'Retry research request'
                  ) : (
                    <>
                      Begin research
                      <span aria-hidden="true">→</span>
                    </>
                  )}
                </button>
              </div>
            </form>

            {status === 'empty' && (
              <p
                className="inline-message error-message"
                id="question-error"
                role="alert"
              >
                Enter a research question before submitting.
              </p>
            )}
            {status === 'loading' && (
              <p className="inline-message" role="status">
                Waiting for a response from the research service. No agent
                progress is shown unless it is returned by the API.
              </p>
            )}
          </section>

          <section className="workflow-section" id="workflow">
            <SectionHeading
              eyebrow="RESEARCH PROCESS"
              title="A traceable agent workflow"
              detail="Five stages"
            />
            <p className="section-intro">
              These are the project workflow stages. Their status is shown only
              when the research response includes an agent trace.
            </p>
            <div className="workflow-grid">
              {workflowStages.map((stage, index) => {
                const trace = report?.agent_trace.find(
                  (item) => isRecord(item) && item.agent_name === stage,
                )
                return (
                  <article className="workflow-card" key={stage}>
                    <div className="workflow-card-top">
                      <span className="workflow-number">0{index + 1}</span>
                      <span className={`trace-status ${trace ? 'reported' : ''}`}>
                        {trace ? textValue(trace.status) : 'Not reported'}
                      </span>
                    </div>
                    <h3>{stage}</h3>
                    {trace && typeof trace.summary === 'string' ? (
                      <p>{trace.summary}</p>
                    ) : (
                      <p className="muted-copy">Awaiting returned trace data.</p>
                    )}
                  </article>
                )
              })}
            </div>
          </section>

          <section className="results-section" id="results">
            <SectionHeading
              eyebrow="EVIDENCE REVIEW"
              title="Research results"
              detail={
                status === 'success'
                  ? 'Returned by the research API'
                  : 'No live results displayed'
              }
            />

            {status === 'loading' && (
              <div className="state-panel" role="status">
                <span className="large-spinner" aria-hidden="true" />
                <div>
                  <h3>Research request in progress</h3>
                  <p>Waiting for the service to return evidence.</p>
                </div>
              </div>
            )}

            {status === 'error' && (
              <div className="state-panel error-panel" role="alert">
                <span className="state-symbol" aria-hidden="true">!</span>
                <div>
                  <h3>Research request failed</h3>
                  <p>{errorMessage}</p>
                  <p className="muted-copy">
                    Check that the API is available and that the frontend is
                    configured to reach it, then retry.
                  </p>
                </div>
              </div>
            )}

            {status === 'idle' && (
              <div className="state-panel">
                <span className="state-symbol" aria-hidden="true">↳</span>
                <div>
                  <h3>No research report yet</h3>
                  <p>
                    Submit a question to request papers and structured evidence
                    from the API. Nothing here is sample research data.
                  </p>
                </div>
              </div>
            )}

            {status === 'empty' && (
              <div className="state-panel">
                <span className="state-symbol" aria-hidden="true">↳</span>
                <div>
                  <h3>Waiting for a research question</h3>
                  <p>Enter a question above to request an evidence report.</p>
                </div>
              </div>
            )}

            {status === 'success' && report && (
              <>
                <div className="question-received">
                  <span>RESEARCH QUESTION</span>
                  <p>{report.research_question}</p>
                </div>

                <div className="result-card">
                  <SectionHeading
                    eyebrow="LITERATURE"
                    title="Research papers"
                    detail={`${report.papers.length} returned`}
                  />
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th scope="col">Source</th>
                          <th scope="col">Publication details</th>
                          <th scope="col">Authenticity status</th>
                          <th scope="col">Status explanation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.papers.length ? (
                          report.papers.map((paper, index) => {
                            const title = getPaperTitle(paper)
                            const authors = textValue(paper.authors)
                            const year = textValue(paper.year)
                            const authenticityReasons = displayValues(
                              paper.authenticity_reasons,
                            )
                            return (
                              <tr key={paper.paper_id ?? `${title}-${index}`}>
                                <td>
                                  {safeWebUrl(paper.url) ? (
                                    <a
                                      className="paper-link"
                                      href={paper.url}
                                      target="_blank"
                                      rel="noreferrer"
                                    >
                                      {title}
                                      <span aria-hidden="true">↗</span>
                                    </a>
                                  ) : (
                                    <strong>{title}</strong>
                                  )}
                                  {typeof paper.abstract === 'string' &&
                                    paper.abstract && (
                                      <details className="abstract-details">
                                        <summary>View returned abstract</summary>
                                        <p>{paper.abstract}</p>
                                      </details>
                                    )}
                                </td>
                                <td>
                                  <span>{authors}</span>
                                  <span className="table-secondary">
                                    {year}
                                    {paper.source
                                      ? ` · ${textValue(paper.source)}`
                                      : ''}
                                  </span>
                                  {paper.doi && (
                                    <span className="table-secondary">
                                      DOI: {textValue(paper.doi)}
                                    </span>
                                  )}
                                </td>
                                <td>
                                  <span className="authenticity-label">
                                    {textValue(paper.authenticity_status)}
                                  </span>
                                </td>
                                <td>
                                  {authenticityReasons.length ? (
                                    <DataList
                                      items={authenticityReasons}
                                      emptyText=""
                                    />
                                  ) : (
                                    'No explanation returned.'
                                  )}
                                </td>
                              </tr>
                            )
                          })
                        ) : (
                          <tr>
                            <td colSpan="4">The API returned no paper records.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="result-card">
                  <SectionHeading
                    eyebrow="CRITICAL COMPARISON"
                    title="Comparison matrix"
                    detail={`${report.comparison.length} returned`}
                  />
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th scope="col">Paper pair</th>
                          <th scope="col">Method</th>
                          <th scope="col">Dataset</th>
                          <th scope="col">Metric</th>
                          <th scope="col">Reported result</th>
                          <th scope="col">Comparability warning</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.comparison.length ? (
                          report.comparison.map((comparison, index) => {
                            const pairPapers = comparisonPapers(
                              comparison,
                              report.papers,
                            )
                            const pairNames = pairPapers.length
                              ? pairPapers.map(getPaperTitle).join(' / ')
                              : textValue(comparison.paper_ids)
                            return (
                              <tr key={`${pairNames}-${index}`}>
                                <td>{pairNames}</td>
                                <td>
                                  {pairPapers
                                    .map((paper) => textValue(paper.methods))
                                    .join(' / ') || 'Not reported'}
                                </td>
                                <td>
                                  {pairPapers
                                    .map((paper) => textValue(paper.datasets))
                                    .join(' / ') || 'Not reported'}
                                </td>
                                <td>
                                  {pairPapers
                                    .map((paper) => textValue(paper.metrics))
                                    .join(' / ') || 'Not reported'}
                                </td>
                                <td>
                                  {pairPapers
                                    .map((paper) =>
                                      textValue(paper.reported_results),
                                    )
                                    .join(' / ') || 'Not reported'}
                                </td>
                                <td>
                                  <span className="comparability-label">
                                    {textValue(comparison.comparability)}
                                  </span>
                                  <p className="table-note">
                                    {textValue(
                                      comparison.reason ?? comparison.finding,
                                    )}
                                  </p>
                                </td>
                              </tr>
                            )
                          })
                        ) : (
                          <tr>
                            <td colSpan="6">
                              No comparison records were returned. This is not
                              evidence that the studies are comparable.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="result-columns">
                  <div className="result-card">
                    <SectionHeading
                      eyebrow="EVIDENCE LIMITS"
                      title="Missing information"
                    />
                    <DataList
                      items={report.missing_information}
                      emptyText="No missing-information items were returned."
                    />
                  </div>
                  <div className="result-card">
                    <SectionHeading
                      eyebrow="NEXT INQUIRY"
                      title="Follow-up questions"
                    />
                    <DataList
                      items={followUpQuestions}
                      emptyText="No follow-up actions were returned."
                    />
                  </div>
                </div>

                <div className="result-card">
                  <SectionHeading
                    eyebrow="POSSIBLE DIRECTIONS"
                    title="Candidate research directions"
                  />
                  <p className="section-intro">
                    These are candidate directions in the returned data, not
                    claims of novelty. Preserve uncertainty labels exactly as
                    provided by the service.
                  </p>
                  <DataList
                    items={report.candidate_gaps}
                    emptyText="No candidate research directions were returned."
                  />
                </div>

                <div className="result-card">
                  <SectionHeading
                    eyebrow="CAUTIONS"
                    title="Warnings"
                    detail={`${report.warnings.length} returned`}
                  />
                  <DataList
                    items={report.warnings}
                    emptyText="No warnings were returned by the API."
                  />
                </div>

                <div className="result-card cited-report">
                  <SectionHeading
                    eyebrow="TRACEABLE OUTPUT"
                    title="Final cited report"
                    detail="Source register"
                  />
                  <p className="section-intro">
                    The API response is presented as structured evidence. The
                    sources below are only the paper records returned by the
                    service; no citations or findings have been added.
                  </p>
                  <ol className="citation-list">
                    {report.papers.length ? (
                      report.papers.map((paper, index) => (
                        <li key={paper.paper_id ?? `${paper.title}-${index}`}>
                          <span className="citation-number">[{index + 1}]</span>
                          <span>
                            <strong>{getPaperTitle(paper)}</strong>
                            <span className="citation-meta">
                              {textValue(paper.authors)} · {textValue(paper.year)}
                            </span>
                          </span>
                          {safeWebUrl(paper.url) && (
                            <a
                              href={paper.url}
                              target="_blank"
                              rel="noreferrer"
                              aria-label={`Open source for ${getPaperTitle(paper)}`}
                            >
                              Open source ↗
                            </a>
                          )}
                        </li>
                      ))
                    ) : (
                      <li>No cited paper records were returned.</li>
                    )}
                  </ol>
                  <div className="trace-register">
                    <h3>Returned agent trace</h3>
                    <DataList
                      items={report.agent_trace}
                      emptyText="The API did not return agent trace records."
                    />
                  </div>
                </div>
              </>
            )}
          </section>

          <footer className="page-footer">
            <span>ResearchPilot AI</span>
            <span>
              Retrieved evidence is limited by the available literature and
              metadata. It does not establish scientific truth or novelty.
            </span>
          </footer>
        </div>
      </main>
    </div>
  )
}

export default App
