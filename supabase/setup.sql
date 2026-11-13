-- Belote Coinchée — historique des parties et identités des joueurs.
--
-- À exécuter une seule fois dans Supabase : SQL Editor → New query →
-- coller ce fichier → Run (voir SUPABASE.md).
--
-- Deux tables :
--   * players : identité d'un joueur, avec un username unique (choisi à
--     l'inscription) lié optionnellement à un compte auth.users. Un joueur
--     anonyme n'a pas de ligne ici ; il est identifié par un id anonyme
--     généré côté navigateur.
--   * game_history : une ligne par partie terminée. `user_id` est renseigné
--     uniquement pour les comptes connectés. `player_id` est toujours
--     renseigné (username si connecté, id anonyme sinon). Les colonnes
--     `players` (les 4 joueurs de la partie) et `dones` (détail de chaque
--     donne) sont stockées en JSONB.
-- Les politiques RLS garantissent que chacun ne lit et n'écrit que ses
-- propres lignes : la clé anon utilisée par le navigateur ne suffit jamais
-- à voir les autres parties.

-- ------------------------------------------------------------------
-- Identités des joueurs (username unique, comptes connectés uniquement)
-- ------------------------------------------------------------------
create table if not exists public.players (
  id uuid primary key default gen_random_uuid(),
  username text unique not null,
  auth_user_id uuid references auth.users on delete cascade,
  created_at timestamptz not null default now()
);

create index if not exists players_auth_user_idx
  on public.players (auth_user_id);

alter table public.players enable row level security;

drop policy if exists "players_select_own" on public.players;
create policy "players_select_own" on public.players
  for select using (auth.uid() = auth_user_id);

-- L'inscription a besoin de vérifier qu'un username n'est pas déjà pris :
-- la lecture du username est donc ouverte à tous (les prénoms de salon sont
-- déjà publics), mais l'écriture est réservée aux comptes connectés.
drop policy if exists "players_insert_own" on public.players;
create policy "players_insert_own" on public.players
  for insert with check (auth.uid() = auth_user_id);

grant select on table public.players to authenticated;
grant select on table public.players to anon;
grant insert on table public.players to authenticated;
revoke all on table public.players from anon;

-- ------------------------------------------------------------------
-- Historique des parties (connectés et invités anonymes)
-- ------------------------------------------------------------------
create table if not exists public.game_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users on delete cascade,   -- null si invité anonyme
  player_id text not null,                                -- username ou id anonyme
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
  players jsonb,      -- les 4 joueurs : { seat, name, kind, identity }
  dones jsonb,        -- détail de chaque donne : contrat, scores, plis, ...
  unique (player_id, game_id)
);

-- Historique trié par date pour chaque identité.
create index if not exists game_history_player_played_idx
  on public.game_history (player_id, played_at desc);
create index if not exists game_history_user_played_idx
  on public.game_history (user_id, played_at desc);

alter table public.game_history enable row level security;

drop policy if exists "game_history_select_own" on public.game_history;
create policy "game_history_select_own" on public.game_history
  for select using (auth.uid() = user_id);

-- Insertion : un compte connecté écrit ses propres lignes (user_id = auth.uid()).
-- Un invité anonyme écrit aussi (user_id null, player_id = son id anonyme) :
-- la clé anon peut insérer mais ne peut pas lire les lignes des autres.
drop policy if exists "game_history_insert_own" on public.game_history;
create policy "game_history_insert_own" on public.game_history
  for insert with check (
    (auth.uid() is not null and auth.uid() = user_id)
    or (auth.uid() is null and player_id is not null)
  );

-- Lecture et écriture pour les comptes connectés ; insertion seule pour les
-- visiteurs anonymes (ils ne peuvent pas consulter l'historique des autres).
grant select, insert on table public.game_history to authenticated;
grant insert on table public.game_history to anon;
revoke all on table public.game_history from anon;
