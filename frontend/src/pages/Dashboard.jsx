import { useState, useEffect } from 'react';
import { getDashboardStats } from '../api/client';
import StatusBadge from '../components/StatusBadge';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <div>
            <h2>Dashboard</h2>
            <p className="page-header-subtitle">Vista general del outreach engine</p>
          </div>
        </div>
        <div className="stats-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card stat-card">
              <div className="skeleton" style={{ height: 16, width: 100, marginBottom: 12 }} />
              <div className="skeleton" style={{ height: 40, width: 60 }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const nicheEmojis = {
    danza: '💃', futbol: '⚽', pilates: '🧘', gym: '🏋️',
    yoga: '🧘‍♀️', artes_marciales: '🥋', musica: '🎵', otros: '📦',
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p className="page-header-subtitle">Vista general del outreach engine</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary" onClick={() => window.location.reload()}>
            🔄 Refrescar
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="card stat-card">
          <div className="stat-label">Total Leads</div>
          <div className="stat-value">{stats?.total_leads || 0}</div>
          <div className="stat-sub">En la base de datos</div>
        </div>
        <div className="card stat-card">
          <div className="stat-label">DMs Enviados Hoy</div>
          <div className="stat-value">{stats?.dms_sent_today || 0}</div>
          <div className="stat-sub">de 45 máximo</div>
        </div>
        <div className="card stat-card">
          <div className="stat-label">Respuestas Hoy</div>
          <div className="stat-value">{stats?.replies_today || 0}</div>
          <div className="stat-sub">Conversaciones activas</div>
        </div>
        <div className="card stat-card">
          <div className="stat-label">Job Activo</div>
          <div className="stat-value" style={{ fontSize: '1.2rem' }}>
            {stats?.active_job ? `#${stats.active_job.id}` : '—'}
          </div>
          <div className="stat-sub">
            {stats?.active_job ? `${stats.active_job.processed}/${stats.active_job.total_leads} procesados` : 'Sin jobs en ejecución'}
          </div>
        </div>
      </div>

      {/* Status & Niche breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        {/* By Status */}
        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>
            📊 Leads por Estatus
          </h3>
          {stats?.by_status && Object.keys(stats.by_status).length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {Object.entries(stats.by_status).map(([status, count]) => (
                <div
                  key={status}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.5rem 0',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <StatusBadge status={status} />
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                  }}>
                    {count}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>Sin leads aún. ¡Hora de prospectar! 🎯</p>
            </div>
          )}
        </div>

        {/* By Niche */}
        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>
            🎯 Leads por Nicho
          </h3>
          {stats?.by_niche && Object.keys(stats.by_niche).length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {Object.entries(stats.by_niche).map(([niche, count]) => (
                <div
                  key={niche}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.5rem 0',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <span style={{ fontSize: '0.88rem' }}>
                    {nicheEmojis[niche] || '📦'} {niche}
                  </span>
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                  }}>
                    {count}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>Sin datos de nichos</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
