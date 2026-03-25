export default function StatusBadge({ status }) {
  const normalized = status?.replace(/_/g, '-') || 'discovered';
  const labels = {
    discovered: '🔵 Discovered',
    qualified: '🟣 Qualified',
    warming: '🟡 Warming',
    interacted: '🟠 Interacted',
    'dm-pending': '🟧 DM Pendiente',
    'dm-sent': '💬 DM Enviado',
    replied: '✅ Respondió',
    converted: '🎉 Convertido',
    excluded: '⛔ Excluido',
  };

  return (
    <span className={`badge badge-${normalized}`}>
      {labels[normalized] || status}
    </span>
  );
}
