const API_BASE = 'http://localhost:8000/api';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Dashboard ───────────────────────────────────────────────
export const getDashboardStats = () => request('/dashboard/stats');

// ── Leads ───────────────────────────────────────────────────
export const getLeads = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.niche) qs.set('niche', params.niche);
  if (params.search) qs.set('search', params.search);
  if (params.skip) qs.set('skip', params.skip);
  if (params.limit) qs.set('limit', params.limit);
  return request(`/leads/?${qs}`);
};

export const getLead = (id) => request(`/leads/${id}`);
export const createLead = (data) => request('/leads/', { method: 'POST', body: JSON.stringify(data) });
export const updateLead = (id, data) => request(`/leads/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
export const deleteLead = (id) => request(`/leads/${id}`, { method: 'DELETE' });
export const bulkImportLeads = (leads) => request('/leads/bulk', { method: 'POST', body: JSON.stringify({ leads }) });
export const transitionLead = (id, newStatus) =>
  request(`/leads/${id}/transition?new_status=${newStatus}`, { method: 'POST' });

// ── Templates ───────────────────────────────────────────────
export const getTemplates = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.niche) qs.set('niche', params.niche);
  if (params.active_only !== undefined) qs.set('active_only', params.active_only);
  return request(`/templates/?${qs}`);
};

export const createTemplate = (data) => request('/templates/', { method: 'POST', body: JSON.stringify(data) });
export const updateTemplate = (id, data) => request(`/templates/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
export const deleteTemplate = (id) => request(`/templates/${id}`, { method: 'DELETE' });
export const previewSpintax = (templateText, count = 5) =>
  request('/templates/preview', { method: 'POST', body: JSON.stringify({ template_text: templateText, count }) });

// ── Blacklist ───────────────────────────────────────────────
export const getBlacklist = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.search) qs.set('search', params.search);
  return request(`/blacklist/?${qs}`);
};

export const addToBlacklist = (data) => request('/blacklist/', { method: 'POST', body: JSON.stringify(data) });
export const removeFromBlacklist = (id) => request(`/blacklist/${id}`, { method: 'DELETE' });

// ── Logs ────────────────────────────────────────────────────
export const getLogs = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.lead_id) qs.set('lead_id', params.lead_id);
  if (params.action_type) qs.set('action_type', params.action_type);
  if (params.limit) qs.set('limit', params.limit);
  return request(`/logs/?${qs}`);
};

export const LOG_STREAM_URL = `${API_BASE}/logs/stream`;

// ── Jobs ────────────────────────────────────────────────────
export const getJobs = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  return request(`/jobs/?${qs}`);
};

// ── Approval Queue ──────────────────────────────────────────
export const getApprovalQueue = () => request('/leads/approval-queue');
export const approveLeads = (leadIds) =>
  request('/leads/approval-queue/approve', { method: 'POST', body: JSON.stringify({ lead_ids: leadIds }) });
export const rejectLeads = (leadIds, reason) =>
  request('/leads/approval-queue/reject', {
    method: 'POST',
    body: JSON.stringify({ lead_ids: leadIds, reason: reason || 'Rechazado por operador' }),
  });

export const getActiveJob = () => request('/jobs/active');
export const createJob = (data = {}) => request('/jobs/', { method: 'POST', body: JSON.stringify(data) });
export const startJob = (id) => request(`/jobs/${id}/start`, { method: 'POST' });
export const pauseJob = (id) => request(`/jobs/${id}/pause`, { method: 'POST' });
export const cancelJob = (id) => request(`/jobs/${id}/cancel`, { method: 'POST' });

export const getConversationLeads = () => request('/agent/conversations');
export const getConversationMessages = (leadId) =>
  request(`/agent/conversations/${leadId}/messages`);
export const processAgentReply = (leadId, messageText) =>
  request('/agent/process-reply', {
    method: 'POST',
    body: JSON.stringify({ lead_id: leadId, message_text: messageText || null }),
  });
