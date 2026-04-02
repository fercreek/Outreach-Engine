import { useState, useEffect, useCallback } from 'react';
import { getApprovalQueue, approveLeads, rejectLeads } from '../api/client';
import { useToast } from '../components/Toast';

const NICHE_EMOJI = {
  danza: '💃', futbol: '⚽', pilates: '🧘', gym: '💪',
  yoga: '🌿', artes_marciales: '🥋', musica: '🎵', otros: '📌',
};

export default function ApprovalQueue() {
  const toast = useToast();
  const [leads, setLeads] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  const fetchQueue = useCallback(async () => {
    try {
      const data = await getApprovalQueue();
      setLeads(data);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  function toggleSelect(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === leads.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(leads.map((l) => l.id)));
    }
  }

  async function handleApprove(ids) {
    try {
      const res = await approveLeads(ids);
      toast(`✅ ${res.count} lead(s) aprobados para DM`, 'success');
      setSelected(new Set());
      fetchQueue();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function handleReject(ids) {
    try {
      const res = await rejectLeads(ids);
      toast(`🚫 ${res.count} lead(s) excluidos`, 'info');
      setSelected(new Set());
      fetchQueue();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  const selectedIds = [...selected];

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>✅ Cola de Aprobación</h2>
          <p className="page-header-subtitle">
            Revisa el mensaje que se enviará a cada lead antes de aprobarlos para DM
          </p>
        </div>
        {leads.length > 0 && (
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              {selected.size}/{leads.length} seleccionados
            </span>
            <button
              className="btn"
              onClick={() => handleReject(selectedIds)}
              disabled={selected.size === 0}
              style={{ opacity: selected.size === 0 ? 0.4 : 1 }}
            >
              🚫 Rechazar
            </button>
            <button
              className="btn btn-play"
              onClick={() => handleApprove(selectedIds)}
              disabled={selected.size === 0}
              style={{ opacity: selected.size === 0 ? 0.4 : 1 }}
            >
              ✅ Aprobar seleccionados
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Cargando cola...
        </div>
      ) : leads.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
          <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Cola vacía</div>
          <p style={{ color: 'var(--text-muted)', maxWidth: 360, margin: '0 auto' }}>
            No hay leads en estado "qualified" o "warming". Importa leads y
            califícalos para que aparezcan aquí.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {/* Select all header */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.75rem',
            padding: '0.5rem 1rem',
            fontSize: '0.82rem', color: 'var(--text-muted)',
          }}>
            <input
              type="checkbox"
              checked={selected.size === leads.length && leads.length > 0}
              onChange={toggleAll}
              style={{ cursor: 'pointer', width: 16, height: 16 }}
            />
            <span>Seleccionar todos ({leads.length})</span>
          </div>

          {leads.map((lead) => {
            const isSelected = selected.has(lead.id);
            const isExpanded = expanded === lead.id;

            return (
              <div
                key={lead.id}
                className="card"
                style={{
                  padding: '1rem 1.25rem',
                  borderLeft: isSelected ? '3px solid var(--accent)' : '3px solid transparent',
                  transition: 'border-color 0.15s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(lead.id)}
                    style={{ cursor: 'pointer', width: 16, height: 16, marginTop: 3, flexShrink: 0 }}
                  />

                  {/* Lead info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 600 }}>@{lead.username}</span>
                      {lead.business_name && (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                          · {lead.business_name}
                        </span>
                      )}
                      <span style={{ fontSize: '0.82rem' }}>
                        {NICHE_EMOJI[lead.niche] || '📌'} {lead.niche}
                      </span>
                      {lead.follower_count && (
                        <span style={{
                          fontSize: '0.78rem', background: 'var(--bg-elevated)',
                          padding: '0.1rem 0.5rem', borderRadius: 999,
                          color: 'var(--text-secondary)',
                        }}>
                          {lead.follower_count.toLocaleString()} seguidores
                        </span>
                      )}
                    </div>

                    {lead.bio && (
                      <p style={{
                        fontSize: '0.82rem', color: 'var(--text-muted)',
                        margin: '0.35rem 0 0', overflow: 'hidden',
                        display: '-webkit-box', WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                      }}>
                        {lead.bio}
                      </p>
                    )}

                    {/* Message preview toggle */}
                    <button
                      onClick={() => setExpanded(isExpanded ? null : lead.id)}
                      style={{
                        marginTop: '0.6rem',
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--accent)', fontSize: '0.82rem', padding: 0,
                      }}
                    >
                      {isExpanded ? '▲ Ocultar mensaje' : '▼ Ver mensaje a enviar'}
                    </button>

                    {isExpanded && (
                      <div style={{
                        marginTop: '0.75rem',
                        padding: '0.75rem 1rem',
                        background: 'var(--bg-elevated)',
                        borderRadius: 'var(--radius-sm)',
                        borderLeft: '3px solid var(--accent)',
                        fontSize: '0.88rem',
                        whiteSpace: 'pre-wrap',
                        lineHeight: 1.6,
                      }}>
                        {lead.message_preview || (
                          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Sin plantilla activa configurada
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Per-row actions */}
                  <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                    <button
                      className="btn"
                      onClick={() => handleReject([lead.id])}
                      style={{ padding: '0.35rem 0.75rem', fontSize: '0.82rem' }}
                    >
                      🚫
                    </button>
                    <button
                      className="btn btn-play"
                      onClick={() => handleApprove([lead.id])}
                      style={{ padding: '0.35rem 0.75rem', fontSize: '0.82rem' }}
                    >
                      ✅
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
