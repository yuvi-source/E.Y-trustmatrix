import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend
} from 'recharts';
import './styles.css';

const API_BASE = 'http://127.0.0.1:8000';

// =====================
// 🔹 EXPLAIN API HELPER
// =====================
async function explainDecision(payload) {
  const res = await axios.post(`${API_BASE}/explain`, payload);
  return res.data;
}

// --- Helper Components ---

function Badge({ band, value }) {
  if (value == null) return <span className="badge">N/A</span>;
  return <span className={`badge ${band}`}>PCS {value.toFixed(1)} ({band})</span>;
}

function DriftChip({ bucket }) {
  if (!bucket) return <span className="chip">Drift N/A</span>;
  return <span className={`chip drift-${bucket.toLowerCase()}`}>Drift: {bucket}</span>;
}

function ProgressBar({ value, max = 100, color = '#3fb950' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="progress-bar-bg">
      <div className="progress-bar-fill" style={{ background: color, width: `${pct}%` }} />
    </div>
  );
}

// =====================
// PIE CHART COLORS
// =====================
const DRIFT_COLORS = {
  High: '#ef4444',
  Medium: '#f59e0b',
  Low: '#10b981'
};

const PCS_COLORS = ['#6366f1', '#7c3aed', '#8b5cf6', '#06b6d4', '#3b82f6'];

// =====================
// DASHBOARD COMPONENT
// =====================
function Dashboard({ stats, onRunBatch, onDownloadReport }) {
  if (!stats) return <div className="dashboard-content">Loading stats...</div>;
  
  const { latest_run, avg_pcs, drift_distribution, pcs_distribution, trend } = stats;

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  // Prepare pie chart data
  const driftData = Object.entries(drift_distribution || {}).map(([name, value]) => ({
    name,
    value: value || 0
  })).filter(d => d.value > 0);

  // Prepare bar chart data
  const pcsData = Object.entries(pcs_distribution || {}).map(([range, count]) => ({
    range,
    count: count || 0
  }));

  // Prepare trend data
  const trendData = (trend || []).map(t => ({
    date: t.date,
    autoUpdates: t.auto_updates || 0,
    manualReviews: t.manual_reviews || 0
  }));

  // Calculate totals
  const totalProcessed = latest_run?.count_processed || 0;
  const autoUpdates = latest_run?.auto_updates || 0;
  const manualReviews = latest_run?.manual_reviews || 0;
  const autoPercent = totalProcessed > 0 ? ((autoUpdates / totalProcessed) * 100).toFixed(1) : 0;

  return (
    <div className="dashboard-content">
      {/* Stats Row */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Last Run</div>
          <div className="stat-value">{formatDate(latest_run?.started_at)}</div>
          <div className="stat-subtitle">({latest_run?.type || 'Daily'})</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-label">Processed</div>
          <div className="stat-value">{totalProcessed} Providers</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-label">Auto-Updated</div>
          <div className="stat-value success">
            {autoUpdates} Fields ({autoPercent}%)
            <span className="icon-up">↑</span>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-label">Manual Review</div>
          <div className="stat-value">
            {manualReviews} Pending
            <span className="icon-warning">⚠️</span>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="charts-row">
        {/* Drift Risk Pie Chart */}
        <div className="chart-card">
          <div className="chart-title">
            <span className="icon">🛡️</span>
            Drift Risk Distribution
          </div>
          <div className="pie-chart-container">
            <ResponsiveContainer width={200} height={200}>
              <PieChart>
                <Pie
                  data={driftData.length > 0 ? driftData : [{ name: 'No Data', value: 1 }]}
                  cx="50%"
                  cy="50%"
                  innerRadius={0}
                  outerRadius={80}
                  dataKey="value"
                >
                  {driftData.length > 0 ? (
                    driftData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={DRIFT_COLORS[entry.name] || '#666'} />
                    ))
                  ) : (
                    <Cell fill="#30363d" />
                  )}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pie-legend">
              <div className="legend-item">
                <span className="legend-dot high"></span>
                High Risk
              </div>
              <div className="legend-item">
                <span className="legend-dot medium"></span>
                Medium
              </div>
              <div className="legend-item">
                <span className="legend-dot low"></span>
                Low
              </div>
            </div>
          </div>
        </div>

        {/* PCS Distribution Bar Chart */}
        <div className="chart-card">
          <div className="chart-title">
            <span className="icon">📊</span>
            PCS Distribution
          </div>
          <div className="bar-chart-container">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={pcsData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="range" stroke="#8b949e" fontSize={12} />
                <YAxis stroke="#8b949e" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    background: '#161b22', 
                    border: '1px solid #30363d',
                    borderRadius: '8px',
                    color: '#fff'
                  }} 
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {pcsData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PCS_COLORS[index % PCS_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Trend Chart */}
      <div className="trend-card">
        <div className="chart-title">
          <span className="icon">📈</span>
          Automation Trend (Last 5 Runs)
        </div>
        <div className="trend-legend">
          <div className="trend-legend-item">
            <span className="trend-legend-box auto"></span>
            Auto-Updates
          </div>
          <div className="trend-legend-item">
            <span className="trend-legend-box manual"></span>
            Manual Reviews
          </div>
        </div>
        <div className="trend-chart-container">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={trendData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
              <XAxis dataKey="date" stroke="#8b949e" fontSize={12} />
              <YAxis stroke="#8b949e" fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  background: '#161b22', 
                  border: '1px solid #30363d',
                  borderRadius: '8px',
                  color: '#fff'
                }} 
              />
              <Line 
                type="monotone" 
                dataKey="autoUpdates" 
                stroke="#3fb950" 
                strokeWidth={3}
                dot={{ fill: '#3fb950', strokeWidth: 2, r: 4 }}
                name="Auto-Updates"
              />
              <Line 
                type="monotone" 
                dataKey="manualReviews" 
                stroke="#d29922" 
                strokeWidth={3}
                dot={{ fill: '#d29922', strokeWidth: 2, r: 4 }}
                name="Manual Reviews"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

// =====================
// PROVIDER LIST
// =====================
function ProviderList({ providers, onSelect }) {
  return (
    <div className="provider-list-container">
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
            <tr key={p.id} onClick={() => onSelect(p.id)}>
              <td>{p.id}</td>
              <td>{p.name}</td>
              <td>{p.specialty || '—'}</td>
              <td>{p.phone || '—'}</td>
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

// =====================
// PROVIDER DETAIL
// =====================
function ProviderDetail({ providerId, onBack }) {
  const [data, setData] = useState(null);
  const [ocr, setOcr] = useState(null);
  const [explanations, setExplanations] = useState({});
  const [loadingField, setLoadingField] = useState(null);
  const [explainError, setExplainError] = useState(null);

  useEffect(() => {
    if (!providerId) return;
    axios.get(`/providers/${providerId}/details`).then(res => setData(res.data));
    axios.get(`/providers/${providerId}/ocr`).then(res => setOcr(res.data));
  }, [providerId]);

  if (!data) return <div className="detail-container">Loading details...</div>;

  const { provider, validation, pcs, drift } = data;

  const handleExplain = async (field, info) => {
    setLoadingField(field);
    setExplainError(null);
    try {
      const payload = {
        field,
        current_value: provider[field],
        candidates: (info.sources || []).map(s => ({ source: s.source, value: s.value })),
        chosen_value: provider[field],
        confidence: info.confidence,
        decision: info.confidence >= 0.7 ? 'auto_update' : 'manual_review',
      };
      const res = await explainDecision(payload);
      setExplanations(prev => ({ ...prev, [field]: res.explanation }));
    } catch (err) {
      setExplainError(err.response?.status === 429 ? 'Rate limit exceeded.' : 'Failed to explain.');
    } finally {
      setLoadingField(null);
    }
  };

  return (
    <div className="detail-container">
      <button onClick={onBack} className="btn-back">← Back to Directory</button>

      <div className="header-card">
        <h1>{provider.name}</h1>
        <p>{provider.specialty} | {provider.address}</p>
        <div className="badges">
          <Badge band={pcs?.band} value={pcs?.score} />
          <DriftChip bucket={drift?.bucket} />
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
                          <ProgressBar value={info.confidence * 100} color={info.confidence >= 0.7 ? '#3fb950' : '#d29922'} />
                          <span>{(info.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                      <td>
                        {info.confidence >= 0.7 ? <span className="badge-green">Auto-Updated</span> : <span className="badge-red">Manual Review</span>}
                        <div style={{ marginTop: '6px' }}>
                          <button className="btn-small" disabled={loadingField === field} onClick={() => handleExplain(field, info)}>
                            {loadingField === field ? 'Explaining…' : 'Explain'}
                          </button>
                        </div>
                      </td>
                    </tr>
                    {explanations[field] && (
                      <tr>
                        <td colSpan="4">
                          <div className="explanation-box">{explanations[field]}</div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>📄 Document Extraction Panel (OCR)</h3>
            {ocr && ocr.exists ? (
              <div className="ocr-panel">
                <div className="ocr-meta">
                  <span><strong>Type:</strong> {ocr.doc_type}</span>
                  <span><strong>Confidence:</strong> {(ocr.ocr_confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="ocr-preview"><pre>{ocr.ocr_text}</pre></div>
              </div>
            ) : (
              <p style={{ color: '#8b949e' }}>No documents found for this provider.</p>
            )}
          </div>

          <div className="card">
            <h3>🔍 Source Comparison</h3>
            <p style={{ color: '#8b949e', marginBottom: '1rem', fontSize: '0.85rem' }}>
              Reliability: NPI (High), State Board (High), Hospital (Med), Maps (Low)
            </p>
            <table className="source-table">
              <thead>
                <tr><th>Field</th><th>Source</th><th>Value Found</th></tr>
              </thead>
              <tbody>
                {Object.entries(validation).map(([field, info]) => (
                  (info.sources || []).map((src, idx) => (
                    <tr key={`${field}-${idx}`}>
                      <td>{field}</td>
                      <td>{typeof src === 'string' ? src : (src?.source ?? 'unknown')}</td>
                      <td>{typeof src === 'object' && src !== null ? (src.value ?? '—') : '—'}</td>
                    </tr>
                  ))
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="right-col">
          <div className="card">
            <h3>🛡️ PCS Breakdown</h3>
            <div className="pcs-grid">
              {Object.entries(pcs?.components || {}).map(([key, val]) => (
                <div key={key} className="pcs-item">
                  <span className="pcs-label">{key.toUpperCase()}</span>
                  <ProgressBar value={val} max={100} color="#58a6ff" />
                  <span className="pcs-val">{val.toFixed(0)}</span>
                </div>
              ))}
            </div>
            <div className="pcs-legend">
              <small>SRM: Source Reliability | FR: Freshness | ST: Stability | MB: Mismatch Burden</small>
              <small>DQ: Doc Quality | RP: Responsiveness | LH: License Health | HA: History</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// =====================
// MANUAL REVIEW
// =====================
function ManualReview({ items, onAction }) {
  return (
    <div className="manual-review-container">
      <div className="card">
        <h3>📝 Manual Review Queue</h3>
        {items.length === 0 ? (
          <p style={{ color: '#8b949e' }}>No items pending review.</p>
        ) : (
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
                <tr key={i.id}>
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// =====================
// MAIN APP
// =====================
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
      const response = await axios.get('/reports/pdf', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'provider_report.pdf');
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
      {/* Left Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="ey-logo">EY</span>
          <div className="sidebar-title">
            <span>Agentic AI</span>
            <small>Provider Directory</small>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button className={`nav-item ${view === 'dashboard' ? 'active' : ''}`} onClick={() => setView('dashboard')}>
            <span className="nav-icon">📊</span>
            Dashboard
          </button>
          <button className={`nav-item ${view === 'providers' ? 'active' : ''}`} onClick={() => setView('providers')}>
            <span className="nav-icon">🏥</span>
            Providers
          </button>
          <button className={`nav-item ${view === 'manual' ? 'active' : ''}`} onClick={() => setView('manual')}>
            <span className="nav-icon">📝</span>
            Manual Review
            {manualItems.length > 0 && <span className="badge-count">{manualItems.length}</span>}
          </button>
        </nav>

        <div className="sidebar-footer">
          <button className="btn-run-batch-sidebar" onClick={runBatch}>
            ▷ Run Daily Batch
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-area">
        {/* Top Header */}
        <header className="top-header">
          <h1 className="page-title">
            {view === 'dashboard' && 'Provider Data Command Center'}
            {view === 'providers' && 'Provider Directory'}
            {view === 'detail' && 'Provider Details'}
            {view === 'manual' && 'Manual Review Queue'}
          </h1>
          <div className="header-actions">
            <button className="btn-download" onClick={downloadReport}>
              ↓ Download Report
            </button>
          </div>
        </header>

        {/* Main Content */}
        <main className="content-area">
          {view === 'dashboard' && <Dashboard stats={stats} onRunBatch={runBatch} onDownloadReport={downloadReport} />}
          {view === 'providers' && <ProviderList providers={providers} onSelect={navigateToDetail} />}
          {view === 'detail' && <ProviderDetail providerId={selectedProviderId} onBack={() => setView('providers')} />}
          {view === 'manual' && <ManualReview items={manualItems} onAction={handleManualAction} />}
        </main>
      </div>
    </div>
  );
}
