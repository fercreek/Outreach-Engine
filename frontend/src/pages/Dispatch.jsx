import { useState, useEffect } from 'react';
import { getActiveJob, getJobs, createJob, startJob, pauseJob, cancelJob } from '../api/client';
import { useToast } from '../components/Toast';

export default function Dispatch() {
  const toast = useToast();
  const [activeJob, setActiveJob] = useState(null);
  const [pastJobs, setPastJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [countdown, setCountdown] = useState(null);

  async function fetchJobs() {
    try {
      const [active, all] = await Promise.all([getActiveJob(), getJobs()]);
      setActiveJob(active);
      setPastJobs(all.filter((j) => j.id !== active?.id));
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchJobs(); }, []);

  // Countdown simulation
  useEffect(() => {
    if (!activeJob || activeJob.status !== 'running') {
      setCountdown(null);
      return;
    }
    // Simulate countdown between leads
    let seconds = Math.floor(Math.random() * 600) + 300; // 5-15 min
    setCountdown(seconds);
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          // Reset to new random countdown
          return Math.floor(Math.random() * 600) + 300;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [activeJob]);

  function formatCountdown(totalSeconds) {
    if (!totalSeconds) return '00:00';
    const min = Math.floor(totalSeconds / 60);
    const sec = totalSeconds % 60;
    return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  }

  async function handleCreate() {
    try {
      const job = await createJob({ job_type: 'outreach' });
      toast(`Job #${job.id} creado con ${job.total_leads} leads`, 'success');
      fetchJobs();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function handleStart(id) {
    try {
      await startJob(id);
      toast('🚀 Job iniciado', 'success');
      fetchJobs();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function handlePause(id) {
    try {
      await pauseJob(id);
      toast('⏸️ Job pausado', 'info');
      fetchJobs();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function handleCancel(id) {
    if (!confirm('¿Cancelar este job?')) return;
    try {
      await cancelJob(id);
      toast('Job cancelado', 'info');
      fetchJobs();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  const statusConfig = {
    pending: { emoji: '⏳', color: 'var(--text-muted)', label: 'Pendiente' },
    running: { emoji: '🟢', color: 'var(--success)', label: 'En ejecución' },
    paused: { emoji: '⏸️', color: 'var(--warning)', label: 'Pausado' },
    completed: { emoji: '✅', color: 'var(--success)', label: 'Completado' },
    failed: { emoji: '❌', color: 'var(--error)', label: 'Fallido' },
    cancelled: { emoji: '🚫', color: 'var(--text-muted)', label: 'Cancelado' },
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>🚀 Dispatch Center</h2>
          <p className="page-header-subtitle">Control de envío masivo de mensajes</p>
        </div>
      </div>

      {/* Active Job Panel */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        {activeJob ? (
          <div className="dispatch-panel">
            <div className="dispatch-status running">
              <span style={{ fontSize: '1.5rem' }}>🟢</span>
              Job #{activeJob.id} — {statusConfig[activeJob.status]?.label}
            </div>

            {/* Progress */}
            <div className="dispatch-progress">
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.5rem',
              }}>
                <span>{activeJob.processed} procesados</span>
                <span>{activeJob.total_leads} total</span>
              </div>
              <div className="dispatch-progress-bar">
                <div
                  className="dispatch-progress-fill"
                  style={{
                    width: `${activeJob.total_leads ? (activeJob.processed / activeJob.total_leads) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>

            {/* Countdown */}
            {activeJob.status === 'running' && countdown && (
              <div>
                <div style={{
                  fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.1em',
                  color: 'var(--text-muted)', marginBottom: '0.5rem',
                }}>
                  Siguiente envío en
                </div>
                <div className="dispatch-countdown">
                  <span>{formatCountdown(countdown)}</span>
                </div>
              </div>
            )}

            {/* Controls */}
            <div style={{ display: 'flex', gap: '1rem' }}>
              {activeJob.status === 'pending' && (
                <button className="btn btn-play" onClick={() => handleStart(activeJob.id)}>
                  ▶️ Iniciar Envío
                </button>
              )}
              {activeJob.status === 'running' && (
                <button className="btn btn-stop" onClick={() => handlePause(activeJob.id)}>
                  ⏸️ Pausar
                </button>
              )}
              {activeJob.status === 'paused' && (
                <button className="btn btn-play" onClick={() => handleStart(activeJob.id)}>
                  ▶️ Reanudar
                </button>
              )}
              {['pending', 'running', 'paused'].includes(activeJob.status) && (
                <button className="btn btn-danger" onClick={() => handleCancel(activeJob.id)}>
                  🛑 Cancelar
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="dispatch-panel">
            <div style={{ fontSize: '4rem', opacity: 0.3 }}>🚀</div>
            <div className="dispatch-status idle">
              Sin jobs activos
            </div>
            <p style={{ color: 'var(--text-muted)', maxWidth: 400, textAlign: 'center' }}>
              Crea un nuevo job para comenzar a enviar mensajes a leads con status "dm_pending".
              Los mensajes se enviarán con intervalos de 15-20 minutos entre cada uno.
            </p>
            <button className="btn btn-play" onClick={handleCreate}>
              ⚡ Crear Nuevo Job
            </button>
          </div>
        )}
      </div>

      {/* Safety Info */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>
          🛡️ Protocolos de Seguridad Activos
        </h3>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
        }}>
          {[
            { icon: '⏱️', title: 'Delay entre DMs', value: '15-20 min' },
            { icon: '📊', title: 'Máximo diario', value: '45 DMs' },
            { icon: '🎲', title: 'Gaussian Jitter', value: 'Activo' },
            { icon: '⌨️', title: 'Keystroke Dynamics', value: '50-180ms' },
            { icon: '🖥️', title: 'Modo Navegador', value: 'Visible' },
            { icon: '👤', title: 'Human-in-Loop', value: 'Activado' },
          ].map((item, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: '0.75rem',
              padding: '0.75rem', borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-elevated)',
            }}>
              <span style={{ fontSize: '1.3rem' }}>{item.icon}</span>
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  {item.title}
                </div>
                <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{item.value}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Past Jobs */}
      {pastJobs.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--border-subtle)',
            fontSize: '0.95rem', fontWeight: 600,
          }}>
            📜 Historial de Jobs
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Procesados</th>
                <th>Fallidos</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {pastJobs.map((job) => {
                const cfg = statusConfig[job.status] || statusConfig.pending;
                return (
                  <tr key={job.id}>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>#{job.id}</td>
                    <td>{job.job_type}</td>
                    <td>
                      <span style={{ color: cfg.color }}>
                        {cfg.emoji} {cfg.label}
                      </span>
                    </td>
                    <td className="count">{job.processed}/{job.total_leads}</td>
                    <td className="count" style={{ color: job.failed > 0 ? 'var(--error)' : undefined }}>
                      {job.failed}
                    </td>
                    <td style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      {new Date(job.created_at).toLocaleDateString('es-MX')}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
