-- Leituras enviadas pelos dispositivos (ESP32) via API REST.
create table if not exists public.readings (
  id         bigint generated always as identity primary key,
  device_id  text not null check (char_length(device_id) between 1 and 64), -- qual dispositivo
  metric     text not null check (char_length(metric) between 1 and 32),     -- qual grandeza
  value      double precision not null,
  unit       text not null check (char_length(unit) between 1 and 16),
  state      text check (state in ('open', 'closed')),
  alert      boolean not null default false,
  created_at timestamptz not null default now() -- horário do servidor (o ESP32 não tem relógio confiável)
);

-- Consultas sempre filtram por dispositivo e ordenam pela leitura mais recente.
create index if not exists readings_device_time_idx
  on public.readings (device_id, created_at desc);

-- RLS ligado e SEM policies: ninguém acessa a tabela direto pela chave pública.
-- Só a Edge Function (service role) lê e grava.
alter table public.readings enable row level security;

-- Permissão explícita só para a API (funciona mesmo com o "grant automático" desligado no projeto).
grant select, insert on public.readings to service_role;
