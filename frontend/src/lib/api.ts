const BASE_URL = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export const api = {
  config: {
    getStatus: () => fetchJSON<any>('/config/status'),
    getModels: () => fetchJSON<{ models: string[] }>('/config/available-models'),
    update: (data: any) =>
      fetchJSON('/config/update', { method: 'POST', body: JSON.stringify(data) }),
  },
  flows: {
    list: (contextType?: string) =>
      fetchJSON<any[]>(`/flows${contextType ? `?context_type=${contextType}` : ''}`),
    get: (id: string) => fetchJSON<any>(`/flows/${id}`),
    create: (data: any) => fetchJSON('/flows', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: any) =>
      fetchJSON(`/flows/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => fetchJSON(`/flows/${id}`, { method: 'DELETE' }),
    createVersion: (id: string, data: any) =>
      fetchJSON(`/flows/${id}/versions`, { method: 'POST', body: JSON.stringify(data) }),
    getTransitionGuide: (id: string, versionId?: string) =>
      fetchJSON<any>(`/flows/${id}/transition-guide${versionId ? `?version_id=${versionId}` : ''}`),
    generateTransitionGuide: (id: string, data: any) =>
      fetchJSON(`/flows/${id}/transition-guide`, { method: 'POST', body: JSON.stringify(data) }),
    deleteTransitionGuide: (id: string) =>
      fetchJSON(`/flows/${id}/transition-guide`, { method: 'DELETE' }),
  },
  poses: {
    list: (params?: {
      category?: string;
      level?: string;
      search_query?: string;
      limit?: number;
    }) => {
      const query = new URLSearchParams(params as any).toString();
      return fetchJSON<any[]>(`/poses${query ? `?${query}` : ''}`);
    },
    get: (id: string) => fetchJSON<any>(`/poses/${id}`),
    getCategories: () => fetchJSON<string[]>('/poses/categories'),
    getNameOverrides: () =>
      fetchJSON<{ overrides: Record<string, string> }>('/poses/name-overrides'),
    setNameOverrides: (overrides: Record<string, string>) =>
      fetchJSON('/poses/name-overrides', { method: 'PUT', body: JSON.stringify({ overrides }) }),
  },
  sessions: {
    list: (upcoming?: boolean) => fetchJSON<any[]>(`/sessions${upcoming ? '?upcoming=true' : ''}`),
    get: (id: string) => fetchJSON<any>(`/sessions/${id}`),
    create: (data: any) => fetchJSON('/sessions', { method: 'POST', body: JSON.stringify(data) }),
    submitAssessment: (id: string, data: any) =>
      fetchJSON(`/sessions/${id}/assessment`, { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => fetchJSON(`/sessions/${id}`, { method: 'DELETE' }),
  },
  library: {
    getThemes: (search?: string) =>
      fetchJSON<any[]>(`/library/themes${search ? `?search_query=${search}` : ''}`),
    createTheme: (data: any) =>
      fetchJSON('/library/themes', { method: 'POST', body: JSON.stringify(data) }),
    getTalkingPoints: (themeId?: string) =>
      fetchJSON<any[]>(`/library/talking-points${themeId ? `?theme_id=${themeId}` : ''}`),
    createTalkingPoint: (data: any) =>
      fetchJSON('/library/talking-points', { method: 'POST', body: JSON.stringify(data) }),
    getSutras: (book?: number) => fetchJSON<any[]>(`/library/sutras${book ? `?book=${book}` : ''}`),
  },
  spotify: {
    getStatus: () => fetchJSON<any>('/spotify/status'),
    getAuthUrl: () => fetchJSON<{ auth_url: string }>('/spotify/auth'),
    createPlaylist: (data: any) =>
      fetchJSON('/spotify/playlist', { method: 'POST', body: JSON.stringify(data) }),
    getPlaylists: () => fetchJSON<any[]>('/spotify/playlists'),
    disconnect: () => fetchJSON('/spotify/disconnect', { method: 'DELETE' }),
  },
  schedule: {
    getUpcoming: (days?: number) =>
      fetchJSON<any[]>(`/schedule/upcoming${days ? `?days=${days}` : ''}`),
    getNeedsAssessment: () => fetchJSON<any[]>('/schedule/needs-assessment'),
    getStats: () => fetchJSON<any>('/schedule/stats'),
  },
};

// Trigger a browser download of the full data export ZIP. Not wrapped in
// fetchJSON because the response is binary and the browser keys download
// behavior off the response's Content-Disposition header.
export function downloadExport(): void {
  window.location.href = `${BASE_URL}/admin/export`;
}

// Upload an export ZIP and apply it. Returns the import summary
// ({applied, warnings}); throws if the backend reports an error.
export async function uploadImport(
  file: File,
): Promise<{ applied: Record<string, number>; warnings: string[] }> {
  const form = new FormData();
  form.append('bundle', file);
  const response = await fetch(`${BASE_URL}/admin/import`, {
    method: 'POST',
    body: form,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body && typeof body.detail === 'string') {
        detail = body.detail;
      }
    } catch (parseErr) {
      // Body wasn't JSON; fall back to status-only detail.
      console.debug('import error body not JSON:', parseErr);
    }
    throw new Error(detail);
  }
  return response.json();
}

// Schema-validated parser for chat WS events. Backend sends one of a small,
// fixed set of message shapes — this narrows ``unknown`` to a known type
// before handing it to consumers, satisfying the
// json-parse-without-schema-validation guardrail.
type ChatEvent = { type: string; [field: string]: unknown };

function parseChatEvent(raw: string): ChatEvent | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    console.error('chat WS message parse failed:', err);
    return null;
  }
  if (
    parsed === null ||
    typeof parsed !== 'object' ||
    Array.isArray(parsed) ||
    !('type' in parsed) ||
    typeof (parsed as { type: unknown }).type !== 'string'
  ) {
    return null;
  }
  return parsed as ChatEvent;
}

export function createChatSocket(onMessage: (data: any) => void) {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const wsBase = `${wsProtocol}://${window.location.host}`;
  const ws = new WebSocket(`${wsBase}${BASE_URL}/chat/ws`);
  ws.onmessage = (event) => {
    if (typeof event.data !== 'string') return;
    const data = parseChatEvent(event.data);
    if (data !== null) {
      onMessage(data);
    }
  };
  return {
    send: (data: any) => ws.send(JSON.stringify(data)),
    close: () => ws.close(),
    ws,
  };
}
