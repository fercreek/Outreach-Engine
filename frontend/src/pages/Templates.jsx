import { useState, useEffect } from 'react';
import { getTemplates, createTemplate, updateTemplate, deleteTemplate, previewSpintax } from '../api/client';
import { useToast } from '../components/Toast';

const NICHES = [null, 'danza', 'futbol', 'pilates', 'gym', 'yoga', 'artes_marciales', 'musica', 'otros'];

export default function Templates() {
  const toast = useToast();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editTpl, setEditTpl] = useState(null);
  const [previews, setPreviews] = useState({});
  const [form, setForm] = useState({
    name: '', niche: '', template_text: '', spintax_enabled: true,
  });

  async function fetchTemplates() {
    setLoading(true);
    try {
      const data = await getTemplates({ active_only: false });
      setTemplates(data);
    } catch (e) {
      toast('Error cargando templates: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchTemplates(); }, []);

  async function handlePreview(tpl) {
    try {
      const data = await previewSpintax(tpl.template_text, 5);
      setPreviews((p) => ({ ...p, [tpl.id]: data.variations }));
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  function openCreate() {
    setEditTpl(null);
    setForm({ name: '', niche: '', template_text: '', spintax_enabled: true });
    setShowModal(true);
  }

  function openEdit(tpl) {
    setEditTpl(tpl);
    setForm({
      name: tpl.name,
      niche: tpl.niche || '',
      template_text: tpl.template_text,
      spintax_enabled: tpl.spintax_enabled,
    });
    setShowModal(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      const payload = { ...form };
      if (!payload.niche) payload.niche = null;

      if (editTpl) {
        await updateTemplate(editTpl.id, payload);
        toast('Template actualizado ✅', 'success');
      } else {
        await createTemplate(payload);
        toast('Template creado ✅', 'success');
      }
      setShowModal(false);
      fetchTemplates();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async function handleDelete(id) {
    if (!confirm('¿Eliminar este template?')) return;
    try {
      await deleteTemplate(id);
      toast('Template eliminado', 'info');
      fetchTemplates();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  function highlightSpintax(text) {
    return text.replace(
      /\{([^{}]+)\}/g,
      '<span class="spintax-highlight">{$1}</span>'
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>✍️ Templates</h2>
          <p className="page-header-subtitle">
            Copys con variaciones Spintax para mensajes artesanales
          </p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          ➕ Nuevo Template
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton" style={{ height: 120, borderRadius: 16 }} />
          ))}
        </div>
      ) : templates.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">✍️</div>
            <h3>Sin templates</h3>
            <p>Crea tu primer template de mensaje para comenzar</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {templates.map((tpl) => (
            <div key={tpl.id} className="template-card">
              <div className="template-card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <h3>{tpl.name}</h3>
                  {tpl.niche && (
                    <span className="filter-chip active" style={{ cursor: 'default' }}>
                      {tpl.niche}
                    </span>
                  )}
                  {tpl.spintax_enabled && (
                    <span className="badge" style={{
                      background: 'rgba(139,92,246,0.15)',
                      color: 'var(--accent-light)',
                    }}>
                      🎲 Spintax
                    </span>
                  )}
                  {!tpl.is_active && (
                    <span className="badge badge-excluded">Inactivo</span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => handlePreview(tpl)}>
                    👁️ Preview
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => openEdit(tpl)}>
                    ✏️ Editar
                  </button>
                </div>
              </div>

              <div className="template-card-body">
                <div
                  style={{
                    fontSize: '0.88rem',
                    lineHeight: 1.7,
                    color: 'var(--text-secondary)',
                  }}
                  dangerouslySetInnerHTML={{ __html: highlightSpintax(tpl.template_text) }}
                />

                {previews[tpl.id] && (
                  <div className="template-preview">
                    <h4>🎲 Variaciones generadas ({previews[tpl.id].length})</h4>
                    {previews[tpl.id].map((variation, idx) => (
                      <div key={idx} className="template-preview-item">
                        <span style={{ color: 'var(--text-muted)', marginRight: '0.5rem' }}>
                          {idx + 1}.
                        </span>
                        {variation}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editTpl ? 'Editar Template' : 'Nuevo Template'}</h3>
              <button className="btn btn-icon btn-secondary" onClick={() => setShowModal(false)}>
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="input-group">
                  <label>Nombre</label>
                  <input
                    className="input"
                    placeholder="Copy Maestro — Danza"
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    required
                  />
                </div>
                <div className="input-group">
                  <label>Nicho (opcional)</label>
                  <select
                    className="select"
                    value={form.niche}
                    onChange={(e) => setForm((f) => ({ ...f, niche: e.target.value }))}
                  >
                    <option value="">General (todos los nichos)</option>
                    {NICHES.filter(Boolean).map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </div>
                <div className="input-group">
                  <label>
                    Texto del Template
                    <span style={{ fontWeight: 400, fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 8 }}>
                      Usa {'{opción1|opción2}'} para Spintax
                    </span>
                  </label>
                  <textarea
                    className="textarea"
                    style={{ minHeight: 160 }}
                    placeholder="¡{Hola|Hey}! Como programador y bailarín 🕺..."
                    value={form.template_text}
                    onChange={(e) => setForm((f) => ({ ...f, template_text: e.target.value }))}
                    required
                  />
                </div>
                <label style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  fontSize: '0.85rem', cursor: 'pointer',
                }}>
                  <input
                    type="checkbox"
                    checked={form.spintax_enabled}
                    onChange={(e) => setForm((f) => ({ ...f, spintax_enabled: e.target.checked }))}
                  />
                  Activar variaciones Spintax
                </label>
              </div>
              <div className="modal-footer">
                {editTpl && (
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => { handleDelete(editTpl.id); setShowModal(false); }}
                    style={{ marginRight: 'auto' }}
                  >
                    🗑️ Eliminar
                  </button>
                )}
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary">
                  {editTpl ? 'Guardar' : 'Crear Template'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
