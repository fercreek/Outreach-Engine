import { useState, useEffect } from 'react';
import { getBlacklist, addToBlacklist, removeFromBlacklist } from '../api/client';
import { useToast } from '../components/Toast';

export default function BlacklistPage() {
  const toast = useToast();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ username: '', reason: '' });
  const [search, setSearch] = useState('');

  async function fetchBlacklist() {
    setLoading(true);
    try {
      const data = await getBlacklist({ search });
      setEntries(data);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchBlacklist(); }, [search]);

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      const payload = { ...form, username: form.username.replace('@', '') };
      await addToBlacklist(payload);
      toast(`@${payload.username} agregado a blacklist`, 'success');
      setShowModal(false);
      setForm({ username: '', reason: '' });
      fetchBlacklist();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function handleRemove(id) {
    if (!confirm('¿Quitar de blacklist?')) return;
    try {
      await removeFromBlacklist(id);
      toast('Removido de blacklist', 'info');
      fetchBlacklist();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>🚫 Blacklist</h2>
          <p className="page-header-subtitle">
            Cuentas excluidas del outreach — {entries.length} entradas
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          ➕ Agregar a Blacklist
        </button>
      </div>

      <div className="filters-row">
        <div className="search-bar" style={{ flex: 1, maxWidth: 320 }}>
          <span className="search-bar-icon">🔍</span>
          <input
            className="input"
            placeholder="Buscar usuario..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '2rem' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton" style={{ height: 40, marginBottom: 8 }} />
            ))}
          </div>
        ) : entries.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🚫</div>
            <h3>Blacklist vacía</h3>
            <p>Agrega cuentas que no deben recibir mensajes</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Motivo</th>
                <th>Fecha</th>
                <th style={{ width: 80 }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="username">@{entry.username}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{entry.reason || '—'}</td>
                  <td style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                    {new Date(entry.created_at).toLocaleDateString('es-MX')}
                  </td>
                  <td>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleRemove(entry.id)}
                    >
                      Quitar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Agregar a Blacklist</h3>
              <button className="btn btn-icon btn-secondary" onClick={() => setShowModal(false)}>
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
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                    required
                  />
                </div>
                <div className="input-group">
                  <label>Motivo</label>
                  <input
                    className="input"
                    placeholder="Competencia, cliente actual, rechazó oferta..."
                    value={form.reason}
                    onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary">
                  ⛔ Agregar a Blacklist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
