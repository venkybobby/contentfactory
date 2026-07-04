import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import './reviewer.css'

const STAGES = ['intake','research','editorial_approval','script','script_approval','preproduction','generation','assembly','qa','final_approval','distribution','analytics']
const ARTIFACTS = ['research','script','preproduction','qa','distribution']

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail?.message || body.detail || `Request failed (${response.status})`)
  }
  if (response.status === 204) return null
  return response.json()
}

function Login({ onLogin }) {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const submit = async (event) => {
    event.preventDefault(); setError('')
    try {
      await api('/api/v1/auth/session', { method: 'POST', body: JSON.stringify({ api_token: token }) })
      onLogin()
    } catch (err) { setError(err.message) }
  }
  return <main className="login-shell">
    <section className="login-panel">
      <div className="eyebrow">THE AI CONFESSION</div>
      <h1>Production Desk</h1>
      <p>Evidence-led documentary production, from case file to final review.</p>
      <form onSubmit={submit}>
        <label>Production API token<input type="password" value={token} onChange={e => setToken(e.target.value)} autoFocus required minLength="16" /></label>
        {error && <div className="error">{error}</div>}
        <button type="submit">Enter production desk <span>→</span></button>
      </form>
    </section>
  </main>
}

function NewEpisode({ onCreated }) {
  const defaultId = useMemo(() => `AIC-${new Date().toISOString().slice(0,10).replaceAll('-','')}-${String(Date.now()).slice(-4)}`, [])
  const [form, setForm] = useState({ case_id: defaultId, title: '', angle: '', target_minutes: 8, provider: 'nvidia', sources: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value })
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    const payload = { ...form, target_minutes: Number(form.target_minutes), sources: form.sources.split('\n').map(x => x.trim()).filter(Boolean) }
    try { await api('/api/v1/episodes', { method: 'POST', body: JSON.stringify(payload) }); onCreated(payload.case_id) }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  return <section className="create-card">
    <div><span className="section-number">01</span><h2>Open a case file</h2><p>Supply primary evidence before the editorial agents begin.</p></div>
    <form onSubmit={submit}>
      <div className="form-grid">
        <label>Case ID<input value={form.case_id} onChange={update('case_id')} required /></label>
        <label>Editorial provider<select value={form.provider} onChange={update('provider')}><option value="nvidia">NVIDIA · GLM-5.2</option><option value="openai">OpenAI</option><option value="demo">Demo preview</option></select></label>
        <label className="wide">Working title<input value={form.title} onChange={update('title')} placeholder="The AI decision nobody verified" required minLength="3" /></label>
        <label className="wide">Editorial angle<textarea value={form.angle} onChange={update('angle')} placeholder="What enduring lesson should the audience take away?" required minLength="10" rows="3" /></label>
        <label>Target duration<select value={form.target_minutes} onChange={update('target_minutes')}><option value="6">6 minutes</option><option value="8">8 minutes</option><option value="10">10 minutes</option><option value="12">12 minutes</option></select></label>
        <label className="wide source-field">Source URLs <small>One HTTPS URL per line</small><textarea value={form.sources} onChange={update('sources')} placeholder={'https://court-or-regulator.example/case\nhttps://company.example/statement'} required rows="4" /></label>
      </div>
      {error && <div className="error">{error}</div>}
      <button className="primary" disabled={busy}>{busy ? 'Opening case…' : 'Begin investigation'} <span>→</span></button>
    </form>
  </section>
}

function StatusPill({ value }) {
  const label = value === 'waiting_for_human' ? 'Review required' : value.replaceAll('_',' ')
  return <span className={`status status-${value}`}>{label}</span>
}

function EpisodeCard({ episode, selected, onSelect, onApprove, onRetry }) {
  const stages = episode.stages || {}
  const complete = Object.values(stages).filter(x => x === 'complete').length
  const waiting = Object.entries(stages).find(([, value]) => value === 'waiting_for_human')
  const state = episode.failed ? 'failed' : waiting ? 'waiting_for_human' : complete === STAGES.length ? 'complete' : 'running'
  return <article className={`episode-card ${selected ? 'selected' : ''}`} onClick={onSelect}>
    <div className="episode-top"><span className="case-id">{episode.case.case_id}</span><StatusPill value={state} /></div>
    <h3>{episode.case.title}</h3>
    <p>{episode.case.angle}</p>
    <div className="progress"><i style={{width: `${Math.round(complete / STAGES.length * 100)}%`}} /></div>
    <div className="episode-meta"><span>{complete}/{STAGES.length} stages</span><span>{episode.provider}</span><span>{episode.case.target_minutes} min</span></div>
    {waiting && <button className="review" onClick={event => { event.stopPropagation(); onApprove(episode.case.case_id, waiting[0]) }}>Approve {waiting[0].replaceAll('_',' ')}</button>}
    {episode.failed && <button className="review" onClick={event => { event.stopPropagation(); onRetry(episode.case.case_id) }}>Retry failed stage</button>}
  </article>
}

function EpisodeDetail({ episode }) {
  const [artifact, setArtifact] = useState(null)
  const [content, setContent] = useState(null)
  const inspect = async (name) => { setArtifact(name); setContent(null); try { setContent(await api(`/api/v1/episodes/${episode.case.case_id}/artifacts/${name}`)) } catch (err) { setContent({ error: err.message }) } }
  return <aside className="detail-panel">
    <span className="section-number">03</span><h2>Case inspection</h2>
    <div className="stage-list">{STAGES.map(stage => <div key={stage}><span>{stage.replaceAll('_',' ')}</span><StatusPill value={episode.stages[stage]} /></div>)}</div>
    <div className="artifact-tabs">{ARTIFACTS.map(name => <button key={name} onClick={() => inspect(name)} className={artifact === name ? 'active' : ''}>{name}</button>)}</div>
    {content && <pre>{JSON.stringify(content, null, 2)}</pre>}
    {episode.video_ready && <a className="video-link" href={`/api/v1/episodes/${episode.case.case_id}/video`} target="_blank">Open final video ↗</a>}
  </aside>
}

function Dashboard({ onLogout }) {
  const [episodes, setEpisodes] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [notice, setNotice] = useState('')
  const [reviewer, setReviewer] = useState('Venky')
  const load = async () => { try { const data = await api('/api/v1/episodes'); setEpisodes(data); if (!selectedId && data[0]) setSelectedId(data[0].case.case_id) } catch {} }
  useEffect(() => { load(); const timer = setInterval(load, 5000); return () => clearInterval(timer) }, [selectedId])
  const created = (id) => { setNotice(`${id} accepted. Research is starting.`); setSelectedId(id); setTimeout(load, 800) }
  const approve = async (id, stage) => { if (!reviewer.trim()) { setNotice('Enter a reviewer name before approving.'); return } await api(`/api/v1/episodes/${id}/approvals/${stage}`, { method: 'POST', body: JSON.stringify({ approved_by: reviewer.trim() }) }); setNotice(`${stage.replaceAll('_',' ')} approved by ${reviewer.trim()}.`); setTimeout(load, 500) }
  const retry = async (id) => { try { await api(`/api/v1/episodes/${id}/retry`, { method: 'POST' }); setNotice(`${id} retry started.`); setTimeout(load, 500) } catch (err) { setNotice(err.message) } }
  const logout = async () => { await api('/api/v1/auth/session', { method: 'DELETE' }); onLogout() }
  const selected = episodes.find(x => x.case.case_id === selectedId)
  return <div className="app-shell">
    <header><div><span className="mark">AIC</span><div><strong>The AI Confession</strong><small>Production Desk</small></div></div><nav><span className="live-dot" /> Factory online<input className="reviewer-input" aria-label="Reviewer name" value={reviewer} onChange={event => setReviewer(event.target.value)} /><button onClick={logout}>Sign out</button></nav></header>
    <main>
      <section className="hero"><div className="eyebrow">AGENTIC DOCUMENTARY SYSTEM</div><h1>Every case begins<br/>with <em>evidence.</em></h1><p>Research, write, review, render and distribute from one controlled production line.</p></section>
      {notice && <div className="notice">{notice}<button onClick={() => setNotice('')}>×</button></div>}
      <NewEpisode onCreated={created} />
      <section className="production"><div className="section-heading"><div><span className="section-number">02</span><h2>Production queue</h2></div><span>{episodes.length} case{episodes.length === 1 ? '' : 's'}</span></div>
        <div className="production-grid"><div className="episode-list">{episodes.length ? episodes.map(item => <EpisodeCard key={item.case.case_id} episode={item} selected={item.case.case_id === selectedId} onSelect={() => setSelectedId(item.case.case_id)} onApprove={approve} onRetry={retry} />) : <div className="empty">No cases yet. Open the first case file above.</div>}</div>{selected && <EpisodeDetail episode={selected} />}</div>
      </section>
    </main>
    <footer><span>REAL STORIES.</span><span>REAL EVIDENCE.</span><span>REAL LESSONS.</span></footer>
  </div>
}

function App() {
  const [auth, setAuth] = useState(null)
  useEffect(() => { api('/api/v1/auth/session').then(() => setAuth(true)).catch(() => setAuth(false)) }, [])
  if (auth === null) return <div className="loading">Loading production desk…</div>
  return auth ? <Dashboard onLogout={() => setAuth(false)} /> : <Login onLogin={() => setAuth(true)} />
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
