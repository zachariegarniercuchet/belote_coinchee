-- Belote Coinchée — historique des parties pour les comptes connectés.
--
-- À exécuter une seule fois dans Supabase : SQL Editor → New query →
-- coller ce fichier → Run (voir SUPABASE.md).
--
-- Une ligne par partie terminée et par compte connecté. Les politiques RLS
-- garantissent que chacun ne lit et n'écrit que ses propres lignes : la clé
-- anon utilisée par le navigateur ne suffit jamais à voir les autres.

create table if not exists public.game_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users on delete cascade,
  game_id text not null,
  room_code text,
  played_at timestamptz not null default now(),
  target_score integer not null default 0,
  donne_count integer not null default 0,
  score_a integer not null default 0,
  score_b integer not null default 0,
  winner_team smallint not null,
  my_seat smallint,
  my_team smallint,
  players jsonb,
  unique (user_id, game_id)
);

-- Historique trié par date pour chaque compte.
create index if not exists game_history_user_played_idx
  on public.game_history (user_id, played_at desc);

alter table public.game_history enable row level security;

drop policy if exists "game_history_select_own" on public.game_history;
create policy "game_history_select_own" on public.game_history
  for select using (auth.uid() = user_id);

drop policy if exists "game_history_insert_own" on public.game_history;
create policy "game_history_insert_own" on public.game_history
  for insert with check (auth.uid() = user_id);

-- Lecture et écriture pour les comptes connectés uniquement (la règle RLS
-- ci-dessus reste le vrai filtre) ; rien pour les visiteurs anonymes.
grant select, insert on table public.game_history to authenticated;
revoke all on table public.game_history from anon;
