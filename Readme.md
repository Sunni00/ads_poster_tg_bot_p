# 📢 Telegram Ad Bot

Aiogram 3 + PostgreSQL da reklamaberuvchilar uchun bot.

## 🚀 Tezkor start

### 1. Loyihani yuklab oling / arxivdan chiqaring

```
tgbot/
├── main.py
├── config.py
├── requirements.txt
├── .env
├── db/
│   ├── models.py
│   └── queries.py
├── handlers/
│   ├── start.py
│   ├── ads.py
│   └── admin.py
├── keyboards/
│   └── keys.py
└── states/
    └── forms.py
```

### 2. Kutubxonalarni o'rnating

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. `.env` ni sozlang

`.env.example` ni → `.env` ga nusxalang va to'ldiring:

```env
BOT_TOKEN=your_bot_token_here
SUPERADMIN_ID=123456789        # sizning Telegram ID ingiz
GROUP_ID=-100123456789         # nashr qilish uchun guruh ID si
DATABASE_URL=postgresql://user:password@localhost:5432/adbot
```

### 4. Ma'lumotlar bazasini yarating

```bash
psql -U postgres -c "CREATE DATABASE adbot;"
```

Jadvallar bot ishga tushganda avtomatik ravishable yaratiladi.

### 5. Botni ishga tushiring

```bash
python main.py
```

---

## 📋 Buyruqlar

### Foydalanuvchi
| Buyruq / tugma | Tavsif |
|---|---|
| `/start` | Ro'yxatdan o'tish / asosiy menyu |
| `📤 Reklama berish` | Reklama berish (rasm + matn) |

### Admin / Superadmin
| Buyruq | Tavsif |
|---|---|
| `/subscriptions` | Mijozlar ro'yxati va ularning obunasi |
| `/extend` | Foydalanuvchi obunasini uzaytirish |
| `/blackout` | Taqiq davrlarini boshqarish |
| `/setrole <id> <role>` | Rolni o'zgartirish (faqat superadmin) |

---

## ⚙️ Logika

- **Obuna**: `/extend` orqali qo'lda o'rnatiladi. Obunasiz reklama nashr etilmaydi.
- **Cooldown**: bitta reklamaberuvchining nashrlari orasidagi vaqt — **4 soat**.
- **Blackout**: agar taqiq davri faol bo'lsa — bot darhol arizani rad etadi.
- **Nashr qilish**: tasdiqlangandan so'ng darhol guruhga (`GROUP_ID`) avtomatik nashr etish.
- **Mediaguruh**: bir nechta rasm qo'llab-quvvatlanadi.
- **Matn (caption)**: ixtiyoriy.

---

## 🔐 Rollar

| Rol | Imkoniyatlar |
|---|---|
| `client` | Reklama berish |
| `admin` | `/subscriptions`, `/extend`, `/blackout` |
| `superadmin` | Yuqoridagilarning barchasi + `/setrole` |

Birinchi superadmin `.env` dagi `SUPERADMIN_ID` orqali o'rnatiladi.