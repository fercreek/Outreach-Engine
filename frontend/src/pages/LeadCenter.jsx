import { useState, useEffect, useCallback } from 'react';
import {
  getLeads, createLead, updateLead, deleteLead,
  transitionLead, bulkImportLeads,
} from '../api/client';
import { useToast } from '../components/Toast';
import StatusBadge from '../components/StatusBadge';

const STATUSES = [
  'discovered', 'qualified', 'warming', 'interacted',
  'dm_pending', 'dm_sent', 'replied', 'converted', 'excluded',
];

const NICHES = [
  'danza', 'futbol', 'pilates', 'gym',
  'yoga', 'artes_marciales', 'musica', 'otros',
];

export default function LeadCenter() {
  const toast = useToast();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', niche: '', search: '' });
  const [showModal, setShowModal] = useState(false);
  const [editLead, setEditLead] = useState(null);
  const [form, setForm] = useState({
    username: '', business_name: '', profile_url: '', niche: 'otros',
    follower_count: '', bio: '', custom_message: '', notes: '',
  });

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.niche) params.niche = filters.niche;
      if (filters.search) params.search = filters.search;
      params.limit = 100;
      const data = await getLeads(params);
      setLeads(data);
    } catch (e) {
      toast('Error cargando leads: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [filters, toast]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  function openCreate() {
    setEditLead(null);
    setForm({
      username: '', business_name: '', profile_url: '', niche: 'otros',
      follower_count: '', bio: '', custom_message: '', notes: '',
    });
    setShowModal(true);
  }

  function openEdit(lead) {
    setEditLead(lead);
    setForm({
      username: lead.username,
      business_name: lead.business_name || '',
      profile_url: lead.profile_url,
      niche: lead.niche,
      follower_count: lead.follower_count || '',
      bio: lead.bio || '',
      custom_message: lead.custom_message || '',
      notes: lead.notes || '',
    });
    setShowModal(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      const payload = { ...form };
      if (payload.follower_count === '') delete payload.follower_count;
      else payload.follower_count = parseInt(payload.follower_count);

      if (!payload.profile_url && payload.username) {
        payload.profile_url = `https://www.tiktok.com/@${payload.username}`;
      }

      if (editLead) {
        await updateLead(editLead.id, payload);
        toast('Lead actualizado ✅', 'success');
      } else {
        await createLead(payload);
        toast('Lead creado ✅', 'success');
      }
      setShowModal(false);
      fetchLeads();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function handleDelete(id) {
    if (!confirm('¿Eliminar este lead?')) return;
    try {
      await deleteLead(id);
      toast('Lead eliminado', 'info');
      fetchLeads();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function handleTransition(id, newStatus) {
    try {
      await transitionLead(id, newStatus);
      toast(`Status cambiado a ${newStatus}`, 'success');
      fetchLeads();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  function formatCount(n) {
    if (!n) return '—';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Lead Center</h2>
          <p className="page-header-subtitle">{leads.length} leads encontrados</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          ➕ Agregar Lead
        </button>
      </div>

      {/* Filters */}
      <div className="filters-row">
        <div className="search-bar" style={{ flex: 1, maxWidth: 320 }}>
          <span className="search-bar-icon">🔍</span>
          <input
            className="input"
            placeholder="Buscar por usuario o negocio..."
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          />
        </div>

        <select
          className="select"
          style={{ width: 160 }}
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
        >
          <option value="">Todos los status</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select
          className="select"
          style={{ width: 140 }}
          value={filters.niche}
          onChange={(e) => setFilters((f) => ({ ...f, niche: e.target.value }))}
        >
          <option value="">Todos los nichos</option>
          {NICHES.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '2rem' }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton" style={{ height: 48, marginBottom: 8, borderRadius: 6 }} />
            ))}
          </div>
        ) : leads.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">👥</div>
            <h3>Sin leads</h3>
            <p>Agrega tu primer lead o ejecuta una sesión de discovery</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Negocio</th>
                  <th>Nicho</th>
                  <th>Seguidores</th>
                  <th>Estatus</th>
                  <th>Último contacto</th>
                  <th style={{ width: 100 }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <a
                        href={lead.profile_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="username"
                      >
                        @{lead.username}
                      </a>
                    </td>
                    <td className="business">{lead.business_name || '—'}</td>
                    <td>
                      <span className="filter-chip active" style={{ cursor: 'default' }}>
                        {lead.niche}
                      </span>
                    </td>
                    <td className="count">{formatCount(lead.follower_count)}</td>
                    <td><StatusBadge status={lead.status} /></td>
                    <td style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      {lead.last_interaction_at
                        ? new Date(lead.last_interaction_at).toLocaleDateString('es-MX')
                        : '—'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.35rem' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          title="Editar"
                          onClick={() => openEdit(lead)}
                        >
                          ✏️
                        </button>
                        <select
                          className="select"
                          style={{ width: 100, padding: '0.25rem 0.4rem', fontSize: '0.72rem' }}
                          value=""
                          onChange={(e) => {
                            if (e.target.value) handleTransition(lead.id, e.target.value);
                          }}
                        >
                          <option value="">Mover a...</option>
                          {STATUSES.filter((s) => s !== lead.status).map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editLead ? 'Editar Lead' : 'Nuevo Lead'}</h3>
              <button
                className="btn btn-icon btn-secondary"
                onClick={() => setShowModal(false)}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="input-group">
                  <label>Username de TikTok</label>
                  <input
                    className="input"
                    placeholder="@usuario"
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value.replace('@', '') }))}
                    disabled={!!editLead}
                    required
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="input-group">
                    <label>Nombre del negocio</label>
                    <input
                      className="input"
                      placeholder="Salsa MTY"
                      value={form.business_name}
                      onChange={(e) => setForm((f) => ({ ...f, business_name: e.target.value }))}
                    />
                  </div>
                  <div className="input-group">
                    <label>Nicho</label>
                    <select
                      className="select"
                      value={form.niche}
                      onChange={(e) => setForm((f) => ({ ...f, niche: e.target.value }))}
                    >
                      {NICHES.map((n) => (
                        <option key={n} value={n}>{n}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="input-group">
                  <label>URL del Perfil</label>
                  <input
                    className="input"
                    placeholder="https://www.tiktok.com/@usuario"
                    value={form.profile_url}
                    onChange={(e) => setForm((f) => ({ ...f, profile_url: e.target.value }))}
                  />
                </div>
                <div className="input-group">
                  <label>Seguidores</label>
                  <input
                    className="input"
                    type="number"
                    placeholder="12000"
                    value={form.follower_count}
                    onChange={(e) => setForm((f) => ({ ...f, follower_count: e.target.value }))}
                  />
                </div>
                <div className="input-group">
                  <label>Mensaje Personalizado (opcional)</label>
                  <textarea
                    className="textarea"
                    placeholder="Un mensaje artesanal para este lead..."
                    value={form.custom_message}
                    onChange={(e) => setForm((f) => ({ ...f, custom_message: e.target.value }))}
                  />
                </div>
                <div className="input-group">
                  <label>Notas</label>
                  <input
                    className="input"
                    placeholder="Notas internas..."
                    value={form.notes}
                    onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  />
                </div>
              </div>
              <div className="modal-footer">
                {editLead && (
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => { handleDelete(editLead.id); setShowModal(false); }}
                    style={{ marginRight: 'auto' }}
                  >
                    🗑️ Eliminar
                  </button>
                )}
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary">
                  {editLead ? 'Guardar Cambios' : 'Crear Lead'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
