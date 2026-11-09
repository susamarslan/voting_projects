# Kararsızım (voting_projects)

Kararsız kaldığın konularda anket açıp başkalarına danıştığın bir web uygulaması. Her ankette 2–5 seçenek olur. Misafirler oy verebilir, anket açmak için üyelik gerekir.

**Yığın:** Django 5.2 · Python 3.12 · Supabase (yalnızca PostgreSQL) · Django şablonları + saf HTML/CSS/JS · WhiteNoise · Vercel

Ayrıntılı plan ve kurallar: [`docs/VOTING_PROJECTS_PLAN.md`](docs/VOTING_PROJECTS_PLAN.md)

---

## Yerel kurulum

```bash
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env          # sonra SECRET_KEY'i değiştir
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py createsuperuser
.venv/Scripts/python.exe manage.py runserver
```

(macOS/Linux'ta `.venv/Scripts/python.exe` yerine `.venv/bin/python` kullan.)

Testler:

```bash
.venv/Scripts/python.exe manage.py test
```

### `.env` ayarları

| Değişken | Yerelde | Açıklama |
|---|---|---|
| `SECRET_KEY` | herhangi bir değer | `DEBUG=False` iken **zorunlu**, yoksa uygulama açılmaz |
| `DEBUG` | `True` | Tanımlı değilse `False` sayılır |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Virgülle ayrılmış |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | Şema dahil (`https://...`) |
| `DATABASE_URL` | boş | Boşsa SQLite (`db.sqlite3`), doluysa PostgreSQL |

`.env` ve `.env.local` asla commit edilmez.

### Yeni bir SECRET_KEY üretmek

```bash
.venv/Scripts/python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Supabase (veritabanı)

Supabase **yalnızca PostgreSQL** olarak kullanılır; Supabase Auth / JS istemcisi / Realtime kullanılmaz.

1. [supabase.com](https://supabase.com)'da proje aç ve veritabanı parolasını kaydet.
2. **Connect** düğmesinden (veya Project Settings → Database) iki bağlantı adresi al:
   - **Transaction pooler** (port `6543`): Vercel'deki `DATABASE_URL` için.
   - **Session pooler** (port `5432`): yerelden migration çalıştırmak için. Direct connection da olur ama yalnızca IPv6 destekler.
3. Parolada `@ : / ? # %` gibi özel karakterler varsa adreste URL-encode edilmeli (ör. `@` → `%40`), yoksa bağlantı hatası alınır.

### Mevcut kurulum

- Proje: **kararsizim** (ref `exdmzqdfupxmifwqwuny`, bölge `eu-central-1` Frankfurt).
- Django ana `postgres` kullanıcısıyla değil, yalnızca bu uygulama için açılmış **`django_app`** veritabanı kullanıcısıyla bağlanır. Tabloların sahibi bu kullanıcıdır, bu yüzden RLS onu etkilemez. Pooler'da kullanıcı adı `django_app.exdmzqdfupxmifwqwuny` biçimindedir.
- Bağlantı adresleri (parola dahil) git'e girmeyen **`.env.supabase`** dosyasındadır:
  - `SUPABASE_SESSION_URL` (5432): yerelden migrate/createsuperuser için.
  - `SUPABASE_TRANSACTION_URL` (6543): Vercel'deki `DATABASE_URL` için.

Yerelden Supabase'e komut çalıştırmak için (Git Bash):

```bash
DATABASE_URL=$(grep '^SUPABASE_SESSION_URL=' .env.supabase | cut -d= -f2-) .venv/Scripts/python.exe manage.py migrate
```

### Migration'ları Supabase'e uygulamak (yerelden)

Migration'lar Vercel build'inde **çalıştırılmaz**; yeni bir migration eklendiğinde yerelden bir kez çalıştırılır:

1. `.env` içinde `DATABASE_URL` değerini geçici olarak **5432 portlu** adrese ayarla.
2. Şunları çalıştır:
   ```bash
   .venv/Scripts/python.exe manage.py migrate
   .venv/Scripts/python.exe manage.py createsuperuser
   ```
3. İşin bitince `DATABASE_URL`'i yeniden boşalt (yerelde tekrar SQLite'a dönmek için).

### Row Level Security (RLS)

Supabase, `public` şemasındaki tabloları kendi REST API'si üzerinden dışarı açar. `polls/migrations/0002_enable_rls.py` migration'ı tüm Django tablolarında RLS'i açar. Hiç politika eklenmediği için bu API'den (anon/authenticated anahtarlarla) hiçbir satır okunamaz. Django tablo sahibi olan `postgres` rolüyle bağlandığı için etkilenmez. Migration SQLite'ta hiçbir şey yapmaz.

Kapsanan tablolar: `accounts_user`, `accounts_user_groups`, `accounts_user_user_permissions`, `auth_group`, `auth_group_permissions`, `auth_permission`, `django_admin_log`, `django_content_type`, `django_session`, `django_migrations`, `polls_poll`, `polls_option`, `polls_vote`.

**Yeni bir model eklenirse** onun tablosu için de RLS açan bir migration yazılmalı. Kontrol için Supabase → Table Editor'da her tabloda "RLS enabled" görünmeli.

---

## Vercel (yayınlama)

Vercel Django projelerini `manage.py` üzerinden kendisi tanır ve `WSGI_APPLICATION` ayarından giriş noktasını (`config/wsgi.py`) bulur. `STATIC_ROOT` tanımlı olduğu için build sırasında `collectstatic`'i kendisi çalıştırır ve statik dosyaları CDN'den sunar. Bu yüzden `vercel.json` veya ayrı bir build betiği gerekmez. Python sürümü `.python-version` dosyasından gelir (3.12).

### Ortam değişkenleri (Vercel → Project → Settings → Environment Variables)

| Değişken | Değer |
|---|---|
| `SECRET_KEY` | Yukarıdaki komutla üretilen yeni, uzun bir anahtar |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | Özel alan adın varsa (ör. `kararsizim.com`); yoksa boş bırakılabilir |
| `CSRF_TRUSTED_ORIGINS` | Özel alan adın varsa `https://kararsizim.com`; yoksa boş bırakılabilir |
| `DATABASE_URL` | Supabase **Transaction pooler** adresi (port `6543`) |

Vercel'in verdiği `*.vercel.app` adresleri (production ve önizleme) `VERCEL_URL`, `VERCEL_BRANCH_URL`, `VERCEL_PROJECT_PRODUCTION_URL` sistem değişkenlerinden okunur ve `ALLOWED_HOSTS` ile `CSRF_TRUSTED_ORIGINS`'e otomatik eklenir.

### Deploy adımları

1. Kodu GitHub'a gönder.
2. [vercel.com](https://vercel.com) → **Add New → Project** → GitHub reposunu içe aktar. Framework olarak Django algılanmalı.
3. Yukarıdaki ortam değişkenlerini ekle.
4. Daha hızlı yanıt için Settings → Functions → **Function Region**'ı Supabase projesinin bölgesine en yakın bölge yap (ör. Supabase `eu-central-1` Frankfurt → Vercel `fra1`).
5. **Deploy**. Sonraki her push otomatik deploy edilir.
6. Supabase'e migration'ları henüz uygulamadıysan yerelden uygula (bkz. yukarı).
7. Kontrol et: site açılıyor ve stiller yükleniyor; kayıt, giriş, anket oluşturma ve oy verme çalışıyor; `/admin/` açılıyor.
