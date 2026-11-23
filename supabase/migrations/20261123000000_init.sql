-- Dashcam video-fingerprint schema for Supabase (PostgreSQL).
-- Apply with:  supabase db push   or paste into Supabase -> SQL Editor.
--
-- The FastAPI backend connects with the database connection string (server-side only), so
-- Row Level Security is enabled with NO policies: the public anon/authenticated API keys
-- cannot read or write these tables through PostgREST.

create table if not exists public.fingerprints (
    id                 varchar(36)      primary key,
    claim_reference    varchar(64)      not null,
    policy_number      varchar(64),
    vehicle_plate      varchar(32),
    notes              text,
    original_filename  varchar(255)     not null,
    file_size_bytes    bigint           not null check (file_size_bytes > 0),
    sha256             varchar(64)      not null,
    perceptual_digest  varchar(64)      not null,
    duration_s         double precision not null,
    fps                double precision not null,
    width              integer          not null,
    height             integer          not null,
    frame_count        integer          not null,
    sample_interval_s  double precision not null,
    frame_hashes       jsonb            not null,
    signature          varchar(64)      not null,
    created_at         timestamptz      not null default now()
);

create index if not exists ix_fingerprints_claim_reference   on public.fingerprints (claim_reference);
create index if not exists ix_fingerprints_sha256            on public.fingerprints (sha256);
create index if not exists ix_fingerprints_perceptual_digest on public.fingerprints (perceptual_digest);
create index if not exists ix_fingerprints_created_at        on public.fingerprints (created_at desc);

create table if not exists public.verifications (
    id                     varchar(36)      primary key,
    fingerprint_id         varchar(36)      references public.fingerprints (id) on delete set null,
    uploaded_filename      varchar(255)     not null,
    uploaded_sha256        varchar(64)      not null,
    verdict                varchar(32)      not null
        check (verdict in ('AUTHENTIC_EXACT', 'AUTHENTIC_REENCODED', 'TAMPERED', 'NO_MATCH')),
    similarity             double precision not null check (similarity between 0 and 1),
    record_signature_valid boolean,
    details                jsonb            not null default '{}'::jsonb,
    created_at             timestamptz      not null default now()
);

create index if not exists ix_verifications_fingerprint_id on public.verifications (fingerprint_id);
create index if not exists ix_verifications_verdict        on public.verifications (verdict);
create index if not exists ix_verifications_created_at     on public.verifications (created_at desc);

alter table public.fingerprints  enable row level security;
alter table public.verifications enable row level security;

-- Handy view for dashboards / Supabase Studio.
create or replace view public.verification_summary
with (security_invoker = true) as
select
    date_trunc('day', created_at) as day,
    verdict,
    count(*)                      as total
from public.verifications
group by 1, 2;
