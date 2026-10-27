import { useEffect, useMemo, useState } from 'react'
import './App.css'

const checkpoints = ['Discover', 'Verify', 'Compare', 'Find gaps', 'Synthesize']

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function text(value, fallback = 'Not reported') {
  if (typeof value === 'string' || typeof value === 'number') {
    return String(value) || fallback
  }
  if (Array.isArray(value)) {
    const values = value.filter((item) => typeof item === 'string' || typeof item === 'number')
    return values.length ? values.join(', ') : fallback
  }
  return fallback
}

function list(value) {
  return Array.isArray(value) ? value.filter(Boolean) : []
}

function safeUrl(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value)
}

function errorMessage(payload, fallback) {
  if (isRecord(payload)) {
    const detail = payload.detail ?? payload.message
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  return fallback
}

async function jsonResponse(response) {
  const body = await response.text()
  let payload
  try {
    payload = body ? JSON.parse(body) : null
  } catch {
    payload = body
  }
  if (!response.ok) {
    throw new Error(errorMessage(payload, `Request failed (${response.status}).`))
  }
  return payload
}

function SectionTitle({ kicker, title, action }) {
  return (
    <div className="section-title">
      <div>
        <p className="kicker">{kicker}</p>
        <h2>{title}</h2>
      </div>
      {action && <span className="section-action">{action}</span>}
    </div>
  )
}

function StatusPill({ children, tone = 'neutral' }) {
  return <span className={`status-pill ${tone}`}>{children}</span>
}

function App() {
  const [question, setQuestion] = useState('')
  const [paperCount, setPaperCount] = useState('5')
  const [status, setStatus] = useState('idle')
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const [apiOnline, setApiOnline] = useState(false)
  const [checkpoint, setCheckpoint] = useState(0)

  useEffect(() => {
    fetch('/api/health')
      .then(jsonResponse)
      .then((payload) => setApiOnline(payload?.status === 'ok'))
      .catch(() => setApiOnline(false))
  }, [])

  useEffect(() => {
    if (status !== 'loading') {
      setCheckpoint(0)
      return undefined
    }
    const timer = window.setInterval(() => {
      setCheckpoint((current) => Math.min(current + 1, checkpoints.length - 1))
    }, 850)
    return () => window.clearInterval(timer)
  }, [status])

  async function submitResearch(event) {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed) {
      setStatus('empty')
      return
    }
    setStatus('loading')
    setError('')
    try {
      const response = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed, max_papers: Number(paperCount) }),
      })
      const payload = await jsonResponse(response)
      if (!isRecord(payload) || !Array.isArray(payload.papers)) {
        throw new Error('The research service returned an unexpected report.')
      }
      setReport(payload)
      setStatus('success')
      setApiOnline(true)
    } catch (requestError) {
      setStatus('error')
      setError(requestError instanceof Error ? requestError.message : 'Research request failed.')
    }
  }

  const papers = list(report?.papers)
  const comparisons = list(report?.comparison)
  const gaps = list(report?.missing_information)
  const warnings = list(report?.warnings)
  const verifiedCount = papers.filter((paper) => paper.authenticity_status === 'verified').length
  const summary = useMemo(() => {
    if (!report) return ''
    if (!papers.length) return 'No source records were returned. Try a more specific question.'
    if (comparisons.some((item) => item.comparability === 'not_directly_comparable')) {
      return 'The literature is relevant, but the studies should not be ranked as if they were one experiment.'
    }
    return `${papers.length} source${papers.length === 1 ? '' : 's'} found. Review the evidence and its limits before drawing a conclusion.`
  }, [comparisons, papers, report])

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top">
          <span className="brand-mark">R</span>
          <span><strong>ResearchPilot</strong><small>evidence, without the noise</small></span>
        </a>
        <div className="topbar-meta">
          <span className={`connection ${apiOnline ? 'online' : ''}`}><i /> {apiOnline ? 'Research service online' : 'Checking service'}</span>
          <span className="trust-badge">● Metadata-first</span>
        </div>
      </header>

      <main className="page" id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="kicker">RESEARCH BRIEF</p>
            <h1>From a question<br /><em>to a defensible starting point.</em></h1>
            <p className="hero-subtitle">Search the literature, see what is actually supported, and spot the gaps before they become assumptions.</p>
          </div>
          <div className="hero-orbit" aria-hidden="true"><span>R</span><i /><b /></div>
        </section>

        <section className="query-card">
          <div className="query-label"><span>01</span><p>ASK YOUR QUESTION</p></div>
          <form onSubmit={submitResearch}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Compare deepfake detection methods, datasets, metrics and limitations."
              aria-label="Research question"
              rows={2}
              disabled={status === 'loading'}
            />
            <div className="query-controls">
              <label>
                <span>Sources</span>
                <select value={paperCount} onChange={(event) => setPaperCount(event.target.value)} disabled={status === 'loading'}>
                  <option value="3">3 papers</option>
                  <option value="5">5 papers</option>
                  <option value="10">10 papers</option>
                </select>
              </label>
              <button type="submit" disabled={status === 'loading'}>
                {status === 'loading' ? 'Researching…' : 'Build my brief'} <span>↗</span>
              </button>
            </div>
          </form>
          {status === 'empty' && <p className="form-message error-text">Add a research question to begin.</p>}
          {status === 'error' && <p className="form-message error-text">{error}</p>}
          {status === 'loading' && (
            <div className="checkpoints" role="status">
              {checkpoints.map((item, index) => <span className={index <= checkpoint ? 'active' : ''} key={item}><b>{index < checkpoint ? '✓' : index + 1}</b>{item}</span>)}
            </div>
          )}
        </section>

        {status === 'idle' && (
          <section className="starter-grid">
            <div className="starter-card featured"><span className="starter-icon">✦</span><p className="kicker">TRY A FOCUSED BRIEF</p><h3>Compare deepfake detection methods</h3><button onClick={() => setQuestion('Compare deepfake detection methods, datasets, metrics and limitations.')}>Use this question <span>→</span></button></div>
            <div className="starter-card"><span className="starter-number">01</span><h3>Find the signal</h3><p>Relevant papers, ranked and linked to their source.</p></div>
            <div className="starter-card"><span className="starter-number">02</span><h3>See the limits</h3><p>Missing fields and unfair comparisons stay visible.</p></div>
          </section>
        )}

        {status === 'success' && report && (
          <div className="report">
            <section className="brief-header">
              <div><p className="kicker">YOUR RESEARCH BRIEF</p><h2>{report.research_question}</h2></div>
              <StatusPill tone={warnings.length ? 'caution' : 'good'}>{warnings.length ? 'Read with context' : 'Ready to review'}</StatusPill>
            </section>

            <section className="insight-card">
              <div className="insight-icon">✦</div>
              <div><p className="kicker">THE SHORT VERSION</p><h2>{summary}</h2><p>ResearchPilot separates what a source reports from what the evidence can safely support.</p></div>
            </section>

            <div className="stat-row">
              <div><strong>{papers.length}</strong><span>sources found</span></div>
              <div><strong>{verifiedCount}<small>/{papers.length}</small></strong><span>metadata verified</span></div>
              <div><strong>{comparisons.length}</strong><span>pair checks</span></div>
              <div><strong>{gaps.length}</strong><span>evidence gaps</span></div>
            </div>

            <section className="content-section">
              <SectionTitle kicker="EVIDENCE LEDGER" title="Start with the sources" action="Open links to inspect" />
              <div className="source-list">
                {papers.length ? papers.map((paper, index) => (
                  <article className="source-card" key={paper.paper_id ?? index}>
                    <span className="source-index">0{index + 1}</span>
                    <div className="source-main">
                      <div className="source-heading">
                        <h3>{text(paper.title, 'Untitled source')}</h3>
                        <StatusPill tone={paper.authenticity_status === 'verified' ? 'good' : 'caution'}>{paper.authenticity_status === 'verified' ? 'Verified metadata' : 'Unverified metadata'}</StatusPill>
                      </div>
                      <p className="source-meta">{text(paper.year)} · {text(paper.authors, 'Authors not reported')}</p>
                      {paper.abstract && <p className="source-abstract">{text(paper.abstract)}</p>}
                      <div className="source-footer">
                        {safeUrl(paper.url) ? <a href={paper.url} target="_blank" rel="noreferrer">Read source ↗</a> : <span>Source link unavailable</span>}
                        <details><summary>Why this status?</summary><p>{text(paper.authenticity_reasons, 'No verification explanation returned.')}</p></details>
                      </div>
                    </div>
                  </article>
                )) : <div className="empty-state">No source records were returned for this question.</div>}
              </div>
            </section>

            {comparisons.length > 0 && (
              <section className="content-section">
                <SectionTitle kicker="CRITIC'S NOTE" title="Can these studies be compared?" />
                <div className="comparison-callout">
                  <span className="callout-icon">!</span>
                  <div><strong>{comparisons[0].comparability === 'potentially_comparable' ? 'Potentially comparable, not proven equivalent.' : 'Do not rank these results directly.'}</strong><p>{text(comparisons[0].reason || comparisons[0].finding)}</p></div>
                </div>
              </section>
            )}

            <section className="bottom-grid">
              <div className="mini-panel"><SectionTitle kicker="WHAT IS MISSING" title="Evidence gaps" action={`${gaps.length} found`} />{gaps.length ? <ul>{gaps.slice(0, 4).map((gap, index) => <li key={`${gap.paper_id}-${gap.field}-${index}`}><b>{text(gap.field).replaceAll('_', ' ')}</b><span>{text(gap.follow_up_action, 'Needs verification')}</span></li>)}</ul> : <p>No evidence gaps were returned.</p>}</div>
              <div className="mini-panel"><SectionTitle kicker="BOUNDARIES" title="Read this honestly" /><p>Authenticity checks confirm bibliographic metadata only. They do not prove scientific claims, quality, or novelty.</p>{warnings.length > 0 && <details className="warnings"><summary>{warnings.length} context notes</summary><ul>{warnings.slice(0, 5).map((warning) => <li key={warning}>{warning}</li>)}</ul></details>}</div>
            </section>
          </div>
        )}
      </main>
      <footer><span>ResearchPilot AI</span><span>Evidence is a starting point, not a verdict.</span></footer>
    </div>
  )
}

export default App
