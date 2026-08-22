-- =====================================================================
-- Telegram Sell Bot - Supabase (Postgres) Schema
-- Run this once in Supabase SQL editor before starting the bot.
-- =====================================================================

-- 1. Admins & roles (owner / admin)
create table if not exists admins (
    user_id      bigint primary key,
    username     text,
    role         text not null default 'admin',   -- 'owner' | 'admin'
    added_by     bigint,
    added_at     timestamptz not null default now()
);

-- 2. Packages / products (e.g. 86 Diamonds, 172 Diamonds, Weekly Pass...)
create table if not exists packages (
    id           serial primary key,
    name         text not null,
    price        numeric not null,
    emoji        text default '💎',
    active       boolean not null default true,
    sort_order   int default 0
);

-- 3. Payment methods, auto-filled by regex from owner's sell-price message
create table if not exists payment_methods (
    method       text primary key,      -- 'KPay' | 'Wave' | 'AYA' | 'BankTransfer' | 'Phone'
    phone        text,
    active       boolean not null default true,
    updated_at   timestamptz not null default now()
);

-- 4. Orders
create table if not exists orders (
    order_id           text primary key,        -- e.g. ORD-20260821-4821
    customer_id        bigint not null,
    customer_username  text,
    game_id            text,
    server_id          text,
    package_id         int references packages(id),
    package_name       text,
    price              numeric,
    payment_method     text,
    payment_phone      text,
    screenshot_file_id text,
    verified_nickname  text,     -- from optional live ID-checker verification
    verified_country   text,
    status             text not null default 'pending', -- pending|confirmed|rejected|completed
    reject_reason      text,
    chat_id            bigint,          -- where the order was placed (DM or group)
    admin_msg_id       bigint,          -- message id of the admin notification (for editing)
    receipt_msg_id     bigint,
    created_at         timestamptz not null default now(),
    confirmed_at       timestamptz,
    confirmed_by       bigint
);

create index if not exists idx_orders_customer on orders(customer_id);
create index if not exists idx_orders_status on orders(status);
create index if not exists idx_orders_created on orders(created_at);

-- 5. Bot settings (group open/close, pinned sell-price message, etc.)
create table if not exists settings (
    key    text primary key,
    value  text
);
insert into settings(key, value) values ('group_open', 'false')
    on conflict (key) do nothing;

-- 6. Sell price message tracking (for pin/unpin old->new)
create table if not exists sell_price_messages (
    id          serial primary key,
    chat_id     bigint not null,
    message_id  bigint not null,
    content     text,
    created_at  timestamptz not null default now()
);

-- 7. Admin action logs
create table if not exists action_logs (
    id           serial primary key,
    admin_id     bigint,
    admin_username text,
    action       text not null,
    detail       text,
    created_at   timestamptz not null default now()
);

-- 8. Rate limit tracking (simple sliding counter)
create table if not exists rate_limits (
    user_id      bigint primary key,
    window_start timestamptz not null default now(),
    count        int not null default 0
);

-- Seed a few default packages (edit as you like)
insert into packages (name, price, emoji, sort_order) values
 ('11 Diamonds', 700, '💎', 1),
 ('22 Diamonds', 1400, '💎', 2),
 ('56 Diamonds', 3500, '💎', 3),
 ('86 Diamonds', 5200, '💎', 4),
 ('172 Diamonds', 10400, '💎', 5),
 ('Weekly Pass', 6500, '🎟️', 6),
 ('Twilight Pass', 40000, '🌌', 7)
on conflict do nothing;
