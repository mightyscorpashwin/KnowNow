import type { DraftSummary, Me, PageDoc, RunStatus, Topic, TopicSummary } from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (res.status === 401) {
    window.location.href = `/.auth/login/aad?post_login_redirect_uri=${encodeURIComponent(window.location.pathname)}`;
    throw new ApiError(401, "Signing you in");
  }
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, body?.error ?? `Request failed (${res.status})`);
  return body as T;
}

const enc = encodeURIComponent;

export const api = {
  me: () => request<Me>("me"),
  topics: () => request<TopicSummary[]>("topics"),
  topic: (topicId: string) => request<Topic>(`topics/${enc(topicId)}`),
  page: (topicId: string, pageId: string) => request<PageDoc>(`topics/${enc(topicId)}/pages/${enc(pageId)}`),

  drafts: () => request<DraftSummary[]>("admin/drafts"),
  draft: (topicId: string, pageId: string) => request<PageDoc>(`admin/drafts/${enc(topicId)}/${enc(pageId)}`),
  approve: (topicId: string, pageId: string) =>
    request<{ status: string }>(`admin/drafts/${enc(topicId)}/${enc(pageId)}/approve`, { method: "POST" }),
  reject: (topicId: string, pageId: string, comment: string) =>
    request<{ status: string }>(`admin/drafts/${enc(topicId)}/${enc(pageId)}/reject`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  generate: (scope: { topicId?: string; subtopicId?: string; areaId?: string }) =>
    request<{ instanceId: string }>("admin/generate", { method: "POST", body: JSON.stringify(scope) }),
  runStatus: (instanceId: string) => request<RunStatus>(`admin/generate/${enc(instanceId)}`),
  syncCatalog: () => request<{ topics: number }>("admin/catalog/sync", { method: "POST" }),
};
