import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './styles.css';

const API_BASE = 'http://127.0.0.1:8000';

// =====================
// 🔹 EXPLAIN API HELPER
// =====================
async function explainDecision(payload) {
  const res = await axios.post(`${API_BASE}/explain`, payload);
  return res.data; // { explanation }
}

// --- Components ---

function Badge({ band, value }) {
  if (value == null) return <span className="badge">N/A</span>;
  return <span className={`badge ${band}`}>PCS {value.toFixed(1)} ({band})</span>;
}

function DriftChip({ bucket }) {
  if (!bucket) return <span className="chip">Drift N/A</span>;
  return <span className={`chip drift-${bucket.toLowerCase()}`}>Drift: {bucket}</span>;
}

function ProgressBar({ value, max = 100, color = '#4caf50' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div style={{ background: '#eee', borderRadius: '4px', height: '10px', width: '100%' }}>
      <div style={{ background: color, width: `${pct}%`, height: '100%', borderRadius: '4px' }} />
    </div>
  );
}

function Dashboard({ stats, manualReviewCount }) {
  if (!stats) return <div>Loading stats...</div>;
  
  const { latest_run, avg_pcs, drift_distribution, pcs_distribution, trend } = stats;

  const maxDrift = Math.max(...Object.values(drift_distribution), 1);
  const maxPCS = Math.max(...Object.values(pcs_distribution || {}), 1);

  return (
    <div className="dashboard-container">
      <div className="card stats-summary">
        <h2>🚀 System Status</h2>
        <div className="stat-row">
          <div className="stat-item">
            <h3>Last Run</h3>
            <p>{latest_run.started_at ? new Date(latest_run.started_at).toLocaleString() : 'Never'}</p>
            <small>{latest_run.type} Batch</small>
          </div>
          <div className="stat-item">
            <h3>Processed</h3>
            <p>{latest_run.count_processed}</p>
          </div>
          <div className="stat-item">
            <h3>Auto-Updated</h3>
            <p className="text-success">{latest_run.auto_updates}</p>
          </div>
          <div className="stat-item">
            <h3>Manual Review</h3>
            <p className="text-warning">{manualReviewCount || 0}</p>
          </div>
          <div className="stat-item">
            <h3>Avg PCS</h3>
            <p>{avg_pcs ? avg_pcs.toFixed(1) : 'N/A'}</p>
          </div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="card">
          <h3>📉 Drift Distribution</h3>
          <div className="chart-bar-container">
            {Object.entries(drift_distribution).map(([key, val]) => (
              <div key={key} className="chart-bar-row">
                <span className="label">{key}</span>
                <div className="bar-wrapper">
                  <div className={`bar drift-${key.toLowerCase()}`} style={{ width: `${(val / maxDrift) * 100}%` }} />
                  <span className="count">{val}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>📊 PCS Distribution</h3>
          <div className="chart-bar-container">
            {Object.entries(pcs_distribution || {}).map(([key, val]) => (
              <div key={key} className="chart-bar-row">
                <span className="label">{key}</span>
                <div className="bar-wrapper">
                  <div className="bar pcs-bar" style={{ width: `${(val / maxPCS) * 100}%`, background: '#2196f3' }} />
                  <span className="count">{val}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3>📈 Trend (Last 5 Runs)</h3>
          <table className="trend-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Auto</th>
                <th>Manual</th>
              </tr>
            </thead>
            <tbody>
              {(trend || []).map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.auto_updates}</td>
                  <td>{t.manual_reviews}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* =====================
   PROVIDER LIST
   ===================== */

function ProviderList({ providers, onSelect }) {
  return (
    <div className="card">
      <h2>🏥 Provider Directory</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Specialty</th>
            <th>Phone</th>
            <th>PCS Score</th>
            <th>Drift Risk</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {providers.map((p) => (
            <tr key={p.id} onClick={() => onSelect(p.id)} className="clickable-row">
              <td>{p.id}</td>
              <td>{p.name}</td>
              <td>{p.specialty}</td>
              <td>{p.phone}</td>
              <td><Badge band={p.pcs_band} value={p.pcs} /></td>
              <td><DriftChip bucket={p.drift_bucket} /></td>
              <td><button className="btn-small">View Details</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* =====================
   PROVIDER DETAIL
   ===================== */

function ProviderDetail({ providerId, onBack }) {
  const [data, setData] = useState(null);
  const [ocr, setOcr] = useState(null);
  const [qaHistory, setQaHistory] = useState([]);

  // 🔹 EXPLAIN STATE
  const [explanations, setExplanations] = useState({});
  const [loadingField, setLoadingField] = useState(null);
  const [explainError, setExplainError] = useState(null);

  useEffect(() => {
    if (!providerId) return;
    axios.get(`/providers/${providerId}/details`).then(res => setData(res.data));
    axios.get(`/providers/${providerId}/ocr`).then(res => setOcr(res.data));
    axios.get(`/providers/${providerId}/qa`).then(res => setQaHistory(res.data));
  }, [providerId]);

  if (!data) return <div>Loading details...</div>;

  const { provider, validation, pcs, drift, enrichment } = data;

  // 🔹 EXPLAIN HANDLER
  const handleExplain = async (field, info) => {
    setLoadingField(field);
    setExplainError(null);

    try {
      const payload = {
        field,
        current_value: provider[field],
        candidates: (info.sources || []).map(s => ({
          source: s.source,
          value: s.value,
        })),
        chosen_value: provider[field],
        confidence: info.confidence,
        decision: info.confidence >= 0.7 ? 'auto_update' : 'manual_review',
      };

      const res = await explainDecision(payload);

      setExplanations(prev => ({ ...prev, [field]: res.explanation }));
    } catch (err) {
      setExplainError(
        err.response?.status === 429
          ? 'Rate limit exceeded. Please wait.'
          : 'Failed to generate explanation.'
      );
    } finally {
      setLoadingField(null);
    }
  };

  return (
    <div className="detail-container">
      <button onClick={onBack} className="btn-back">← Back to Directory</button>

      <div className="header-card card">
        <div className="header-info">
          <h1>{provider.name}</h1>
          <p>{provider.specialty} | {provider.address}</p>
          <div className="badges">
            <Badge band={pcs?.band} value={pcs?.score} />
            <DriftChip bucket={drift?.bucket} />
          </div>
        </div>
        <div className="drift-explanation">
          <strong>Drift Analysis:</strong> {drift?.explanation}
        </div>
      </div>

      <div className="detail-grid">
        <div className="left-col">
          <div className="card">
            <h3>✅ Validated Data & Confidence</h3>

            {explainError && <div className="error-banner">{explainError}</div>}

            <table className="validation-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>Confidence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(validation).map(([field, info]) => (
                  <React.Fragment key={field}>
                    <tr>
                      <td>{field}</td>
                      <td>{provider[field]}</td>
                      <td>
                        <div className="confidence-wrapper">
                          <ProgressBar
                            value={info.confidence * 100}
                            color={info.confidence >= 0.7 ? '#4caf50' : '#ff9800'}
                          />
                          <span>{(info.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                      <td>
                        {info.confidence >= 0.7
                          ? <span className="badge-green">Auto-Updated</span>
                          : <span className="badge-red">Manual Review</span>}

                        <div style={{ marginTop: '6px' }}>
                          <button
                            className="btn-small"
                            disabled={loadingField === field}
                            onClick={() => handleExplain(field, info)}
                          >
                            {loadingField === field ? 'Explaining…' : 'Explain'}
                          </button>
                        </div>
                      </td>
                    </tr>

                    {explanations[field] && (
                      <tr>
                        <td colSpan="4">
                          <div className="explanation-box">
                            {explanations[field]}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {/* OCR PANEL */}
          <div className="card">
            <h3>📄 Document Extraction Panel (OCR)</h3>
            {ocr && ocr.exists ? (
              <div className="ocr-panel">
                <div className="ocr-meta">
                  <span><strong>Type:</strong> {ocr.doc_type}</span>
                  <span><strong>Confidence:</strong> {(ocr.ocr_confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="ocr-preview">
                  <pre>{ocr.ocr_text}</pre>
                </div>
              </div>
            ) : (
              <p>No documents found for this provider.</p>
            )}
          </div>

          <div className="card">
            <h3>📊 Confidence History</h3>
            {qaHistory.length === 0 ? (
              <p>No validation history available.</p>
            ) : (
              <table className="qa-history-table">
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Confidence</th>
                    <th>Sources</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {qaHistory.slice(0, 10).map((qa, idx) => (
                    <tr key={idx}>
                      <td>{qa.field_name}</td>
                      <td>
                        <ProgressBar value={qa.confidence * 100} max={100} color={qa.confidence >= 0.7 ? '#4caf50' : '#ff9800'} />
                        <span style={{fontSize: '0.8rem', marginLeft: '0.5rem'}}>{(qa.confidence * 100).toFixed(0)}%</span>
                      </td>
                      <td>{qa.sources ? qa.sources.join(', ') : 'N/A'}</td>
                      <td>{qa.created_at ? new Date(qa.created_at).toLocaleDateString() : 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="right-col">
          <div className="card">
            <h3>🛡️ PCS Breakdown</h3>
            <div className="pcs-grid">
              {Object.entries(pcs?.components || {}).map(([key, val]) => (
                <div key={key} className="pcs-item">
                  <span className="pcs-label">{key.toUpperCase()}</span>
                  <ProgressBar value={val} max={100} color="#2196f3" />
                  <span className="pcs-val">{val.toFixed(0)}</span>
                </div>
              ))}
            </div>
            <div className="pcs-legend">
              <small>SRM: Source Reliability | FR: Freshness | ST: Stability | MB: Mismatch Burden</small>
              <small>DQ: Doc Quality | RP: Responsiveness | LH: License Health | HA: History</small>
            </div>
          </div>
{/* 
          {enrichment && (
            <div className="card">
              <h3>🧠 Enrichment Summary</h3>
              <p>{enrichment.summary || "No summary available (LLM disabled or no data)."}</p>
              <div className="enrich-grid">
                {enrichment.certifications && (
                  <div>
                    <strong>Certifications</strong>
                    <ul>
                      {enrichment.certifications.map((c, idx) => <li key={idx}>{c}</li>)}
                    </ul>
                  </div>
                )}
                {enrichment.affiliations && (
                  <div>
                    <strong>Affiliations</strong>
                    <ul>
                      {enrichment.affiliations.map((a, idx) => <li key={idx}>{a}</li>)}
                    </ul>
                  </div>
                )}
                {enrichment.education && (
                  <div>
                    <strong>Education</strong>
                    <p>{enrichment.education}</p>
                  </div>
                )}
                {enrichment.secondary_specialties && enrichment.secondary_specialties.length > 0 && (
                  <div>
                    <strong>Secondary Specialties</strong>
                    <ul>
                      {enrichment.secondary_specialties.map((s, idx) => <li key={idx}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )} */}
        </div>
      </div>
    </div>
  );
}

/* =====================
   MANUAL REVIEW
   ===================== */

function ManualReview({ items, onAction }) {
  const [explanations, setExplanations] = useState({});
  const [loadingExplanation, setLoadingExplanation] = useState({});

  const getAIExplanation = async (item) => {
    setLoadingExplanation({ ...loadingExplanation, [item.id]: true });
    try {
      const response = await axios.post('/explain', {
        field: item.field_name,
        current_value: item.current_value,
        candidates: [], // Could be enhanced with actual candidates
        chosen_value: item.suggested_value,
        confidence: 0.5, // Default confidence for manual review items
        decision: 'manual_review'
      });
      setExplanations({ ...explanations, [item.id]: response.data.explanation });
    } catch (err) {
      if (err.response?.status === 429) {
        alert('Rate limit exceeded. Please wait before requesting more explanations.');
      } else {
        alert('Failed to get AI explanation');
      }
    } finally {
      setLoadingExplanation({ ...loadingExplanation, [item.id]: false });
    }
  };

  return (
    <div className="card">
      <h2>📝 Manual Review Queue</h2>
      {items.length === 0 ? <p>No items pending review.</p> : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Provider ID</th>
              <th>Field</th>
              <th>Current Value</th>
              <th>Suggested Value</th>
              <th>Reason</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <React.Fragment key={i.id}>
                <tr>
                  <td>{i.id}</td>
                  <td>{i.provider_id}</td>
                  <td>{i.field_name}</td>
                  <td className="text-strike">{i.current_value}</td>
                  <td className="text-highlight">{i.suggested_value}</td>
                  <td>{i.reason}</td>
                  <td className="actions-cell">
                    <button className="btn-approve" onClick={() => onAction(i.id, 'approve')}>Approve</button>
                    <button className="btn-override" onClick={() => {
                      const val = window.prompt('Enter override value:', i.suggested_value);
                      if (val) onAction(i.id, 'override', val);
                    }}>Override</button>
                    <button className="btn-reject" onClick={() => onAction(i.id, 'reject')}>Reject</button>
                    <button 
                      className="btn-explain" 
                      onClick={() => getAIExplanation(i)}
                      disabled={loadingExplanation[i.id]}
                    >
                      {loadingExplanation[i.id] ? '...' : '🤖 Explain'}
                    </button>
                  </td>
                </tr>
                {explanations[i.id] && (
                  <tr>
                    <td colSpan="7" className="explanation-row">
                      <div className="ai-explanation">
                        <strong>🤖 AI Analysis:</strong> {explanations[i.id]}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* =====================
   MAIN APP
   ===================== */

export default function App() {
  const [view, setView] = useState('dashboard');
  const [selectedProviderId, setSelectedProviderId] = useState(null);

  const [stats, setStats] = useState(null);
  const [providers, setProviders] = useState([]);
  const [manualItems, setManualItems] = useState([]);

  const loadData = async () => {
    try {
      const [s, p, m] = await Promise.all([
        axios.get('/stats'),
        axios.get('/providers'),
        axios.get('/manual-review'),
      ]);
      setStats(s.data);
      setProviders(p.data);
      setManualItems(m.data.filter(i => i.status === 'pending'));
    } catch (err) {
      console.error('Error loading data', err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const runBatch = async () => {
    if (window.confirm('Run daily batch process? This may take a moment.')) {
      await axios.post('/run-batch?type=daily');
      await loadData();
      alert('Batch run complete!');
    }
  };

  const downloadReport = async () => {
    try {
      const response = await axios.get('/reports/latest', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `validation_report_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to download report');
    }
  };

  const handleManualAction = async (id, action, value) => {
    try {
      if (action === 'approve') {
        await axios.post(`/manual-review/${id}/approve`);
      } else if (action === 'reject') {
        await axios.post(`/manual-review/${id}/reject`);
      } else {
        await axios.post(`/manual-review/${id}/override?value=${encodeURIComponent(value)}`);
      }
      await loadData();
    } catch {
      alert('Action failed');
    }
  };

  const navigateToDetail = (id) => {
    setSelectedProviderId(id);
    setView('detail');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <h2>EY Agentic AI</h2>
          <p>Provider Directory</p>
        </div>
        <nav>
          <button className={view === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}>Dashboard</button>
          <button className={view === 'providers' ? 'active' : ''} onClick={() => setView('providers')}>Providers</button>
          <button className={view === 'manual' ? 'active' : ''} onClick={() => setView('manual')}>
            Manual Review
            {manualItems.length > 0 && <span className="badge-count">{manualItems.length}</span>}
          </button>
        </nav>
        <div className="sidebar-footer">
          <button className="btn-primary" onClick={runBatch}>Run Daily Batch</button>
          <button className="btn-secondary" onClick={downloadReport}>📄 Download Report</button>
        </div>
      </aside>

      <main className="content">
        {view === 'dashboard' && <Dashboard stats={stats} manualReviewCount={manualItems.length} />}
        {view === 'providers' && <ProviderList providers={providers} onSelect={navigateToDetail} />}
        {view === 'detail' && <ProviderDetail providerId={selectedProviderId} onBack={() => setView('providers')} />}
        {view === 'manual' && <ManualReview items={manualItems} onAction={handleManualAction} />}
      </main>
    </div>
  );
}
