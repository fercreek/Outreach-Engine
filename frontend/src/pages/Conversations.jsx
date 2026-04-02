import { useState, useEffect } from 'react';
import {
  getConversationLeads,
  getConversationMessages,
  processAgentReply,
} from '../api/client';
import { useToast } from '../components/Toast';

export default function Conversations() {
  const toast = useToast();
  const [leads, setLeads] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msgsLoading, setMsgsLoading] = useState(false);
  const [manualText, setManualText] = useState('');
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getConversationLeads()
      .then((data) => {
        if (cancelled) return;
        setLeads(data);
        if (data.length) {
          setSelectedId((prev) => (prev != null ? prev : data[0].lead_id));
        }
      })
      .catch((e) => toast(e.message, 'error'))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [toast]);

  useEffect(() => {
    if (!selectedId) return;
    setMsgsLoading(true);
    getConversationMessages(selectedId)
      .then(setMessages)
      .catch((e) => toast(e.message, 'error'))
      .finally(() => setMsgsLoading(false));
  }, [selectedId, toast]);

  async function handleRunAgent() {
    if (!selectedId) return;
    setRunning(true);
    try {
      const res = await processAgentReply(
        selectedId,
        manualText.trim() || null
      );
      toast('Agente ejecutado', 'success');
      setManualText('');
      const [msgs, listAgain] = await Promise.all([
        getConversationMessages(selectedId),
        getConversationLeads(),
      ]);
      setMessages(msgs);
      setLeads(listAgain);
      if (res.assistant_text) {
        toast(res.assistant_text.slice(0, 120) + '…', 'info');
      }
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>💬 Conversaciones (agente)</h2>
          <p className="page-header-subtitle">
            Historial guardado por lead. Dispara el agente manualmente si
            ANTHROPIC_API_KEY está configurada.
          </p>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '280px 1fr',
          gap: '1rem',
          minHeight: '420px',
        }}
      >
        <div
          className="panel"
          style={{
            padding: 0,
            overflow: 'auto',
            maxHeight: '70vh',
          }}
        >
          {loading ? (
            <p style={{ padding: '1rem' }}>Cargando…</p>
          ) : leads.length === 0 ? (
            <p style={{ padding: '1rem', color: 'var(--text-muted)' }}>
              Aún no hay mensajes del agente. Cuando el monitor detecte una
              respuesta y el agente corra, aparecerán aquí.
            </p>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {leads.map((l) => (
                <li key={l.lead_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(l.lead_id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '0.75rem 1rem',
                      border: 'none',
                      borderBottom: '1px solid var(--border-subtle)',
                      background:
                        selectedId === l.lead_id
                          ? 'var(--surface-elevated)'
                          : 'transparent',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>@{l.username}</div>
                    <div
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {l.status} ·{' '}
                      {l.last_message_at
                        ? new Date(l.last_message_at).toLocaleString()
                        : ''}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="panel" style={{ padding: '1rem' }}>
          {!selectedId ? (
            <p style={{ color: 'var(--text-muted)' }}>
              Selecciona un lead con historial.
            </p>
          ) : msgsLoading ? (
            <p>Cargando mensajes…</p>
          ) : (
            <>
              <div
                style={{
                  maxHeight: '48vh',
                  overflow: 'auto',
                  marginBottom: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                }}
              >
                {messages.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      alignSelf:
                        m.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '92%',
                      padding: '0.65rem 0.85rem',
                      borderRadius: '10px',
                      background:
                        m.role === 'user'
                          ? 'var(--accent-soft)'
                          : 'var(--surface-elevated)',
                      border: '1px solid var(--border-subtle)',
                      fontSize: '0.9rem',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '0.65rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        color: 'var(--text-muted)',
                        marginBottom: '0.25rem',
                      }}
                    >
                      {m.role}
                    </div>
                    {m.content}
                  </div>
                ))}
              </div>

              <div
                style={{
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '1rem',
                }}
              >
                <label
                  style={{
                    display: 'block',
                    fontSize: '0.8rem',
                    marginBottom: '0.35rem',
                    color: 'var(--text-muted)',
                  }}
                >
                  Texto entrante opcional (si vacío, el agente usa un
                  placeholder)
                </label>
                <textarea
                  value={manualText}
                  onChange={(e) => setManualText(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%',
                    marginBottom: '0.75rem',
                    padding: '0.5rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    resize: 'vertical',
                  }}
                  placeholder="Pega aquí el último mensaje del lead…"
                />
                <button
                  type="button"
                  className="btn-primary"
                  disabled={running}
                  onClick={handleRunAgent}
                >
                  {running ? 'Ejecutando…' : 'Ejecutar agente'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
