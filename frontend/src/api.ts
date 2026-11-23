import type {
  FingerprintDetail,
  FingerprintPage,
  Stats,
  VerificationLogItem,
  VerificationResult,
} from "./types";

const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

function headers(): Record<string, string> {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

function errorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  if (status === 0) return "Cannot reach the API server. Is the backend running?";
  return `Request failed (${status})`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers: { ...headers(), ...init.headers } });
  } catch {
    throw new ApiError(errorMessage(0, null), 0);
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(errorMessage(res.status, body), res.status);
  return body as T;
}

/** POST multipart form data with upload progress (fetch cannot report upload progress). */
function upload<T>(path: string, form: FormData, onProgress?: (pct: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}${path}`);
    Object.entries(headers()).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* non-JSON error page */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as T);
      else reject(new ApiError(errorMessage(xhr.status, body), xhr.status));
    };
    xhr.onerror = () => reject(new ApiError(errorMessage(0, null), 0));
    xhr.send(form);
  });
}

export interface RegisterInput {
  file: File;
  claim_reference: string;
  policy_number?: string;
  vehicle_plate?: string;
  notes?: string;
}

export const api = {
  health: () => request<{ status: string; version: string }>("/api/health"),
  stats: () => request<Stats>("/api/stats"),

  listFingerprints: (q = "", limit = 20, offset = 0) =>
    request<FingerprintPage>(
      `/api/fingerprints?${new URLSearchParams({ q, limit: String(limit), offset: String(offset) })}`,
    ),
  getFingerprint: (id: string) =>
    request<FingerprintDetail>(`/api/fingerprints/${encodeURIComponent(id)}`),
  deleteFingerprint: (id: string) =>
    request<void>(`/api/fingerprints/${encodeURIComponent(id)}`, { method: "DELETE" }),

  register(input: RegisterInput, onProgress?: (pct: number) => void) {
    const form = new FormData();
    form.append("file", input.file);
    form.append("claim_reference", input.claim_reference);
    if (input.policy_number) form.append("policy_number", input.policy_number);
    if (input.vehicle_plate) form.append("vehicle_plate", input.vehicle_plate);
    if (input.notes) form.append("notes", input.notes);
    return upload<FingerprintDetail>("/api/fingerprints", form, onProgress);
  },

  verify(
    file: File,
    target: { fingerprint_id?: string; claim_reference?: string },
    onProgress?: (pct: number) => void,
  ) {
    const form = new FormData();
    form.append("file", file);
    if (target.fingerprint_id) form.append("fingerprint_id", target.fingerprint_id);
    if (target.claim_reference) form.append("claim_reference", target.claim_reference);
    return upload<VerificationResult>("/api/verify", form, onProgress);
  },

  verifications: (fingerprintId?: string, limit = 20) =>
    request<VerificationLogItem[]>(
      `/api/verifications?${new URLSearchParams({
        limit: String(limit),
        ...(fingerprintId ? { fingerprint_id: fingerprintId } : {}),
      })}`,
    ),
};
