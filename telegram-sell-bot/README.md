# 🤖 Telegram Sell Bot (MLBB ID Top-Up)

GitHub + Supabase (Postgres) + Render + UptimeRobot သုံးပြီး run ရန် ပြင်ဆင်ထားသော
Telegram sale bot အပြည့်အစုံ။

## 📁 Project Structure
```
telegram-sell-bot/
├── bot/
│   ├── main.py              # entrypoint (registers all handlers, run_polling)
│   ├── config.py            # env vars
│   ├── database.py          # Supabase async wrapper
│   ├── keep_alive.py        # Flask ping server (UptimeRobot target)
│   ├── handlers/
│   │   ├── start.py         # /start /help /mystatus
│   │   ├── group_control.py # /open /close + sell-price pin flow
│   │   ├── admin.py         # /addadmin /removeadmin /admins
│   │   ├── order.py         # package select, game id, dup-check
│   │   ├── payment.py       # payment select, screenshot, order create
│   │   ├── confirm.py       # admin confirm/reject buttons
│   │   ├── receipt.py       # auto receipt post
│   │   ├── search.py        # /search
│   │   ├── report.py        # /report /stats + daily job
│   │   ├── settings.py      # /panel /addpackage /setpayment /backup /logs
│   │   └── jobs.py          # pending-order reminder job
│   └── utils/
│       ├── validators.py      # game id / server regex
│       ├── payment_regex.py   # -ph/wave/kpay/aya/ငွေလွှဲ regex extractor
│       └── ratelimit.py       # anti-spam
├── sql/schema.sql           # run once in Supabase SQL editor
├── requirements.txt
├── render.yaml
├── Procfile
└── .env.example
```

## 🚀 Setup လုပ်ရန် (Step by Step)

### 1. Telegram Bot ဖန်တီးရန်
- Telegram ထဲ **@BotFather** ကို ဖွင့်ပြီး `/newbot` → Bot token ကူးထားပါ။
- Bot ကို group ထဲ **admin** အဖြစ် ထည့်ပါ (Pin messages, Delete messages permission ပေးထားပါ)။

### 2. Supabase Database
1. https://supabase.com → New Project ဖန်တီးပါ။
2. **SQL editor** ဖွင့်ပြီး `sql/schema.sql` file ထဲက code အားလုံးကို paste → Run လုပ်ပါ။
3. **Project Settings → API** ထဲက `Project URL` (SUPABASE_URL) နှင့် `service_role` key (SUPABASE_KEY) ကို ကူးထားပါ (service_role key က server-side bot အတွက် အသင့်တော်ဆုံးဖြစ်ပါတယ်, browser ထဲမတင်ပါနဲ့)။

### 3. GitHub
```bash
git init
git add .
git commit -m "init telegram sell bot"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

### 4. Render Deploy
1. https://render.com → **New → Web Service** → GitHub repo ချိတ်ပါ။
2. Build command: `pip install -r requirements.txt`
3. Start command: `python -m bot.main`
4. **Environment** tab ထဲ `.env.example` ကို ကြည့်ပြီး variable တွေအားလုံးထည့်ပါ
   (`BOT_TOKEN`, `OWNER_IDS`, `GROUP_ID`, `ADMIN_GROUP_ID`, `RECEIPT_CHAT_ID`,
   `SUPABASE_URL`, `SUPABASE_KEY` ...)
5. Deploy → logs ထဲ "Bot starting (polling)..." ပေါ်ရင် အောင်မြင်ပါပြီ။

> Render Free plan က idle 15 မိနစ်ကျော်ရင် sleep သွားတတ်လို့ Step 5 လိုအပ်ပါတယ်။

### 5. UptimeRobot (Bot မအိပ်အောင်)
1. https://uptimerobot.com → New Monitor → **HTTP(s)**
2. URL: `https://<your-render-app>.onrender.com/`
3. Monitoring interval: 5 minutes
4. Save — ဒါဆိုရင် Render app ကို ၅ မိနစ်တိုင်း ping ပေးနေမှာဖြစ်လို့ bot အိပ်မသွားတော့ပါ။

## 🔑 Group ID ရှာနည်း
Bot ကို group ထဲထည့်ပြီး `/id` စတဲ့ helper bot တစ်ခု (e.g. @RawDataBot) ကနေ chat id ကူးယူနိုင်ပါတယ်။
Group/Channel id တွေက `-100` နဲ့ စပါတယ်။

## 🧑‍💼 Owner / Admin System
- `.env` ထဲက `OWNER_IDS` ဟာ full access ရှိတဲ့ boss account(s) ဖြစ်ပါတယ် (database မထည့်ရသေးလည်း အလုပ်လုပ်ပါတယ်)။
- Owner က `/addadmin <user_id> [admin|owner]` နဲ့ Admin/Owner အသစ်တွေ database ထဲ ထည့်နိုင်ပါတယ်။

## 🟢 Group Open Flow
1. Owner: `/open`
2. Bot: "sell price message ပို့ပါ" လို့ မေးမယ်
3. Owner ရဲ့ နောက် message (ဥပမာ- "86💎-5200 Ks\nKPay - 09xxxxxxxx\nWave - 09xxxxxxxx") ကို:
   - ဟောင်း pinned sell-price message ရှိရင် **unpin**
   - message အသစ်ကို **pin**
   - regex နဲ့ `KPay / Wave / AYA / Phone / ငွေလွှဲ` keywords + `09xxxxxxxxx` phone number တွေကို ဖတ်ထုတ်ပြီး `payment_methods` table ထဲ auto-save (checkout မှာ ချက်ချင်းပေါ်လာမယ်)

## 🛒 Order Flow (Customer)
`/order` → Package ရွေး → Game ID ပို့ (`123456789 (12345)` format) → duplicate check →
Payment method ရွေး → phone number ပြပြီး Screenshot တောင်း → Screenshot ပို့ →
Order ID ထုတ် → Admin group ကို photo + Confirm/Reject button ပါတဲ့ notification ပို့ →
Admin confirm/reject → customer ကို status အသိပေး + auto receipt post

## 📌 Admin Commands
| Command | Description |
|---|---|
| `/open` `/close` | Group ဖွင့်/ပိတ် |
| `/addadmin` `/removeadmin` `/admins` | Admin management |
| `/addpackage <name>|<price>` | Package အသစ်ထည့် |
| `/removepackage <id>` | Package ပိတ် |
| `/packages` | Package list |
| `/setpayment <method> <phone>` | Payment number update |
| `/search <order_id>` | Order တစ်ခုချင်း ရှာ |
| `/report` | ယနေ့ sales report |
| `/stats` | All-time statistics |
| `/backup` | Orders CSV (owner only) |
| `/logs` | Admin action logs |
| `/panel` | Command list |

## ⚠️ Notes
- Order flow state (`context.user_data`) is in-memory per running process — customer ဟာ
  order တစ်ခု လုပ်နေစဉ် bot restart ဖြစ်ရင် ပြန်စရပါမယ် (order ID confirmed ဖြစ်ပြီးသားများ
  database ထဲ ဘေးကင်းစွာ ရှိပါတယ်)။
- Payment screenshot verification ဟာ admin manual confirm ပေါ်မူတည်ပါတယ် — OCR auto-amount
  detection မပါသေးပါ (ချဲ့ထွင်လိုလျှင် Google Vision / Tesseract ထည့်နိုင်ပါတယ်)။
