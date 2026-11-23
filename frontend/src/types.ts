export type Verdict = "AUTHENTIC_EXACT" | "AUTHENTIC_REENCODED" | "TAMPERED" | "NO_MATCH";

export interface FingerprintSummary {
  id: string;
  claim_reference: string;
  policy_number: string | null;
  vehicle_plate: string | null;
  original_filename: string;
  file_size_bytes: number;
  sha256: string;
  perceptual_digest: string;
  duration_s: number;
  fps: number;
  width: number;
  height: number;
  frame_count: number;
  sample_interval_s: number;
  signature: string;
  created_at: string;
}

export interface FingerprintDetail extends FingerprintSummary {
  notes: string | null;
  frame_hashes: string[];
  signature_valid: boolean;
}

export interface FingerprintPage {
  items: FingerprintSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface Segment {
  start_s: number;
  end_s: number;
  kind: "altered" | "missing" | "extra";
}

export interface Comparison {
  verdict: Verdict;
  similarity: number;
  exact_match: boolean;
  offset_s: number;
  matched_samples: number;
  reference_samples: number;
  candidate_samples: number;
  mean_distance: number | null;
  duration_delta_s: number;
  segments: Segment[];
  timeline: (number | null)[];
}

export interface VerificationResult {
  id: string;
  verdict: Verdict;
  similarity: number;
  uploaded_filename: string;
  uploaded_sha256: string;
  matched_fingerprint: FingerprintSummary | null;
  record_signature_valid: boolean | null;
  comparison: Comparison | null;
  message: string;
  created_at: string;
}

export interface VerificationLogItem {
  id: string;
  fingerprint_id: string | null;
  uploaded_filename: string;
  verdict: Verdict;
  similarity: number;
  record_signature_valid: boolean | null;
  created_at: string;
}

export interface Stats {
  fingerprints: number;
  verifications: number;
  verdicts: Record<Verdict, number>;
  total_video_seconds: number;
}
