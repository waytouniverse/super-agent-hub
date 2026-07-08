const BASE = '';

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    cache: 'no-store',
    ...(options || {}),
  });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      message = data.detail || message;
    } catch {
      // Keep the status fallback when the response is not JSON.
    }
    throw new Error(message);
  }
  return res.json();
}

export async function fetchEngines() {
  return request('/api/engines');
}

export async function fetchSessions(limit = 50, offset = 0, engine = '') {
  const params = new URLSearchParams({ limit, offset });
  if (engine) params.set('engine', engine);
  return request(`/api/sessions?${params}`);
}

export async function fetchSession(id) {
  return request(`/api/sessions/${id}`);
}

export async function fetchCurrentProject() {
  return request('/api/projects/current');
}

export async function chooseProjectFolder() {
  return request('/api/projects/choose', { method: 'POST' });
}

export async function validateProject(path) {
  return request('/api/projects/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
}

export async function deleteSession(id) {
  const res = await fetch(`${BASE}/api/sessions/${id}`, { method: 'DELETE' });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  try {
    return await res.json();
  } catch {
    return { ok: true };
  }
}

export async function fetchStats(days = 7) {
  return request(`/api/stats?days=${days}`);
}

export async function fetchDailyStats(days = 30) {
  return request(`/api/stats/daily?days=${days}`);
}

export function createChatSocket(engine) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${location.host}/ws/chat/${engine}`;
  return new WebSocket(url);
}
