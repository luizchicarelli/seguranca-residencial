-- Versão 2: vários sensores (porta, janelas, presença) e alarme armável pelo painel.

-- 1) Estados do sensor de presença (PIR): 'motion' (movimento) e 'clear' (sem movimento).
alter table public.readings drop constraint if exists readings_state_check;
alter table public.readings
  add constraint readings_state_check check (state in ('open', 'closed', 'motion', 'clear'));

-- 2) Alarme: uma única linha dizendo se o sistema está armado.
create table if not exists public.alarm (
  id         int primary key default 1 check (id = 1),
  armed      boolean not null default false,
  updated_at timestamptz not null default now()
);
insert into public.alarm (id) values (1) on conflict (id) do nothing;
alter table public.alarm enable row level security; -- sem policies: só a API acessa
grant select, update on public.alarm to service_role;

-- 3) Última leitura de cada sensor (usada pela planta da casa no painel).
--    O índice (device_id, created_at desc) da 001 deixa essa consulta rápida.
create or replace view public.latest_readings
  with (security_invoker = true) as
  select distinct on (device_id) *
  from public.readings
  order by device_id, created_at desc;
grant select on public.latest_readings to service_role;
