-- Run this in the Supabase SQL Editor (Project -> SQL Editor -> New query).
-- Safe to run more than once, and safe to run on top of the old demo schema.
--
-- Security model:
--   * The app uses the PUBLISHABLE key. That key is public by design --
--     anyone can see it. It identifies your project; it does not protect data.
--   * What protects data is Row Level Security (RLS). Every row has an owner
--     (user_id), and the policies below only let a signed-in user touch rows
--     they own. Signed-out requests (role "anon") get nothing at all.

create table if not exists public.todos (
    id bigint generated always as identity primary key,
    task text not null,
    is_complete boolean not null default false,
    inserted_at timestamptz not null default now()
);

-- Owner column. default auth.uid() fills it from the signed-in user's JWT,
-- so the app never sends (and can't fake) a user_id.
alter table public.todos
    add column if not exists user_id uuid
    default auth.uid()
    references auth.users (id) on delete cascade;

-- Old demo rows have no owner and would be invisible to everyone; remove them.
delete from public.todos where user_id is null;
alter table public.todos alter column user_id set not null;

alter table public.todos drop constraint if exists todos_task_length;
alter table public.todos
    add constraint todos_task_length check (char_length(task) between 1 and 500);

create index if not exists todos_user_id_idx on public.todos (user_id);

alter table public.todos enable row level security;

-- Remove the old wide-open policy.
drop policy if exists "Allow anon full access (demo only)" on public.todos;

-- One policy per operation, all scoped to the row's owner.
-- (select auth.uid()) is evaluated once per query instead of once per row.
drop policy if exists "Users can view their own todos" on public.todos;
create policy "Users can view their own todos"
    on public.todos for select
    to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users can create their own todos" on public.todos;
create policy "Users can create their own todos"
    on public.todos for insert
    to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own todos" on public.todos;
create policy "Users can update their own todos"
    on public.todos for update
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete their own todos" on public.todos;
create policy "Users can delete their own todos"
    on public.todos for delete
    to authenticated
    using ((select auth.uid()) = user_id);

-- Belt and braces: signed-out users have no table privileges at all.
revoke all on public.todos from anon;
grant select, insert, update, delete on public.todos to authenticated;
