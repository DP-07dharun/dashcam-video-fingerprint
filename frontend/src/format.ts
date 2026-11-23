import type { Verdict } from "./types";

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit++;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

/** 75.5 -> "1:15.5", 3725 -> "1:02:05" */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds)) return "—";
  const sign = seconds < 0 ? "-" : "";
  const s = Math.abs(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const rest = s % 60;
  const sec = Number.isInteger(rest) ? String(rest) : rest.toFixed(1);
  const secPadded = rest < 10 ? `0${sec}` : sec;
  return h ? `${sign}${h}:${String(m).padStart(2, "0")}:${secPadded}` : `${sign}${m}:${secPadded}`;
}

export function formatPercent(ratio: number): string {
  return `${(ratio * 100).toFixed(ratio === 1 || ratio === 0 ? 0 : 1)}%`;
}

export function formatDate(iso: string): string {
  // The API returns UTC; SQLite drops the offset, so treat bare timestamps as UTC.
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function shortHash(hash: string, size = 10): string {
  return hash.length <= size * 2 ? hash : `${hash.slice(0, size)}…${hash.slice(-4)}`;
}

export const VERDICT_INFO: Record<Verdict, { label: string; tone: "ok" | "warn" | "bad" | "muted" }> =
  {
    AUTHENTIC_EXACT: { label: "Authentic · exact copy", tone: "ok" },
    AUTHENTIC_REENCODED: { label: "Authentic · re-encoded", tone: "ok" },
    TAMPERED: { label: "Tampered", tone: "bad" },
    NO_MATCH: { label: "No match", tone: "muted" },
  };
