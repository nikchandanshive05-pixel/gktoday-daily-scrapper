-- 001_initial_schema.sql
-- Run in Supabase SQL editor or psql

create extension if not exists "pgcrypto";

-- Profiles table
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique not null,
  display_name text not null,
  avatar_url text,
  bio text default '',
  follower_count integer not null default 0 check (follower_count >= 0),
  following_count integer not null default 0 check (following_count >= 0),
  total_likes_received integer not null default 0 check (total_likes_received >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint username_format check (username ~ '^[a-zA-Z0-9_]{3,30}$')
);

-- Sounds table
create table if not exists public.sounds (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  artist_name text not null default 'Original Sound',
  audio_url text not null,
  cover_url text,
  duration_seconds integer not null check (duration_seconds > 0 and duration_seconds <= 300),
  usage_count integer not null default 0 check (usage_count >= 0),
  created_at timestamptz not null default now()
);

-- Videos table
create table if not exists public.videos (
  id uuid primary key default gen_random_uuid(),
  creator_id uuid not null references public.profiles(id) on delete cascade,
  sound_id uuid references public.sounds(id) on delete set null,
  video_url text not null,
  thumbnail_url text not null,
  caption text not null default '',
  duration_seconds numeric(5,2) not null check (duration_seconds > 0),
  view_count bigint not null default 0 check (view_count >= 0),
  like_count integer not null default 0 check (like_count >= 0),
  comment_count integer not null default 0 check (comment_count >= 0),
  share_count integer not null default 0 check (share_count >= 0),
  visibility text not null default 'public' check (visibility in ('public', 'unlisted', 'private')),
  processing_status text not null default 'processing' check (processing_status in ('processing', 'ready', 'failed')),
  search_vector tsvector,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Comments table
create table if not exists public.comments (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references public.videos(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  parent_id uuid references public.comments(id) on delete cascade,
  content text not null check (char_length(content) between 1 and 500),
  like_count integer not null default 0 check (like_count >= 0),
  created_at timestamptz not null default now()
);

-- Likes table
create table if not exists public.video_likes (
  user_id uuid not null references public.profiles(id) on delete cascade,
  video_id uuid not null references public.videos(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, video_id)
);

-- Follows table
create table if not exists public.follows (
  follower_id uuid not null references public.profiles(id) on delete cascade,
  following_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (follower_id, following_id),
  constraint no_self_follow check (follower_id <> following_id)
);

-- Indexes
create index if not exists idx_videos_feed on public.videos(created_at desc) where visibility = 'public' and processing_status = 'ready';
create index if not exists idx_videos_creator on public.videos(creator_id, created_at desc);
create index if not exists idx_comments_video on public.comments(video_id, created_at asc);

-- Row Level Security
alter table public.profiles enable row level security;
alter table public.videos enable row level security;
alter table public.comments enable row level security;
alter table public.video_likes enable row level security;
alter table public.follows enable row level security;

-- Policies
create policy "Public profiles select" on public.profiles for select using (true);
create policy "Ready public videos select" on public.videos for select using (visibility = 'public' and processing_status = 'ready');
create policy "Comments select" on public.comments for select using (true);
create policy "Likes select" on public.video_likes for select using (true);

create policy "Profiles self update" on public.profiles for update using (auth.uid() = id);
create policy "Videos creator insert" on public.videos for insert with check (auth.uid() = creator_id);
create policy "Comments user insert" on public.comments for insert with check (auth.uid() = user_id);
create policy "Likes toggle" on public.video_likes for all using (auth.uid() = user_id);
create policy "Follows toggle" on public.follows for all using (auth.uid() = follower_id);
