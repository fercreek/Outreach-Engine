import { useState, useEffect, useRef } from 'react';
import { getLogs, LOG_STREAM_URL } from '../api/client';

export default function ActivityLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const logEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  // Initial load
  useEffect(() => {
    getLogs({ limit: 100 })
      .then((data) => setLogs(data.reverse()))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // SSE streaming
  function toggleStream() {
    if (streaming) {
      eventSourceRef.current?.close();
      setStreaming(false);
      return;
    }

    const es = new EventSource(LOG_STREAM_URL);
    es.addEventListener('log', (event) => {
      const log = JSON.parse(event.data);
      setLogs((prev) => [...prev, log]);
    });
    es.onerror = () => {
      es.close();
      setStreaming(false);
    };
    eventSourceRef.current = es;
    setStreaming(true);
  }

  useEffect(() => {
    return () => eventSourceRef.current?.close();
  }, []);

  // Auto-scroll
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const actionEmojis = {
    discovered: '🔵',
    qualified: '🟣',
    profile_visited: '👁️',
    video_watched: '🎬',
    liked: '❤️',
    dm_sent: '✉️',
    reply_detected: '💬',
    excluded: '⛔',
    error: '❌',
    agent_reply: '🤖',
    escalation: '📣',
  };

  function formatTime(isoString) {
    return new Date(isoString).toLocaleTimeString('es-MX', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>📋 Activity Log</h2>
          <p className="page-header-subtitle">
            Registro en tiempo real de todas las operaciones
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className={`btn ${streaming ? 'btn-danger' : 'btn-primary'}`}
            onClick={toggleStream}
          >
            {streaming ? '⏹️ Detener Stream' : '📡 Live Stream'}
          </button>
        </div>
      </div>

      <div className="log-console">
        <div className="log-console-header">
          <h3>
            {streaming && <span className="log-console-dot" />}
            Terminal de Actividad
          </h3>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            {logs.length} entradas
          </span>
        </div>
        <div className="log-console-body">
          {loading ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Cargando logs...
            </div>
          ) : logs.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Sin actividad registrada. Inicia un job para ver logs aquí.
            </div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className={`log-entry ${log.level}`}>
                <span className="log-time">{formatTime(log.created_at)}</span>
                <span className={`log-action ${log.action_type}`}>
                  {actionEmojis[log.action_type] || '📌'} {log.action_type}
                </span>
                {log.job_id && <span className="log-job-badge">#{log.job_id}</span>}
                <span className="log-message">{log.message}</span>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
