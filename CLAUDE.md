# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proje

voting_projects: kullanıcıların kararsız kaldıkları konularda anket açıp başkalarına danıştığı bir web uygulaması. Her ankette 2–5 seçenek olur. Takip sistemi yok, tüm anketler tek akışta görünür. Misafirler oy verebilir, anket açmak için üyelik gerekir.

Yığın: Django 5.2 + Python 3.12, Supabase (yalnızca Postgres olarak), Django şablonları + saf HTML/CSS/JS, WhiteNoise, Vercel.

**Tek doğru kaynak `docs/VOTING_PROJECTS_PLAN.md`.** Veri modeli, iş kuralları, URL'ler (Türkçe yollar: `/anket/<id>/`, `/kayit/`, `/giris/`...), oy endpoint'inin JSON formatı, tasarım paleti ve faz faz yapılacaklar orada. Bir işe başlamadan önce ilgili bölümü oku. Plan değişecekse önce dosyayı güncelle, sonra kodu değiştir.

## Çalışma kuralları

- Fazlar sırayla uygulanır. Her faz sonunda dur, testleri çalıştır, özetle ve kullanıcının onayını bekle. Şu ana kadar Faz 0 tamamlandı.
- Git commit/push işlerini kullanıcı yapar; commit atma.
- Frontend framework veya build adımı ekleme (React, Vue, Tailwind, Bootstrap, npm yok).
- Yeni paket eklemeden önce sor.
- Arayüz metinleri ve hata mesajları Türkçe.
- E-posta hiçbir şablonda, JSON yanıtında veya sayfa kaynağında görünmez; yalnızca admin panelinde görünür. Kullanıcı arayüzde `@kullaniciadi` olarak gösterilir.
- Supabase Auth, Supabase JS istemcisi veya Realtime kullanılmaz. Kimlik doğrulamayı Django yapar.

## Komutlar

Windows ortamı; sanal ortam `.venv` (Python 3.12).

```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py runserver
.venv/Scripts/python.exe manage.py makemigrations && .venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py test                                  # tüm testler
.venv/Scripts/python.exe manage.py test accounts                         # tek uygulama
.venv/Scripts/python.exe manage.py test accounts.tests.SomeTest.test_x   # tek test
```

Linter/formatter yapılandırılmadı.

## Mimari notlar

- **Ayarlar (`config/settings.py`):** Her şey `.env` dosyasından okunur (`.env.example`'a bak). `DEBUG` tanımlı değilse **False** olur; yerelde `.env` içinde `DEBUG=True` gerekir. `DATABASE_URL` boşsa SQLite, doluysa `dj-database-url` ile Postgres kullanılır (`conn_max_age=0`: Supabase transaction pooler ve Vercel serverless için).
- **Kullanıcı modeli (`accounts.User`):** `AbstractUser`'dan türetilir ve giriş alanı e-postadır (`USERNAME_FIELD = "email"`). Bu yüzden `authenticate(username=...)` çağrısına e-posta verilir.
  - E-posta `save()` sırasında küçük harfe çevrilir. `UserManager.get_by_natural_key` `iexact` ile eşleştirdiği için giriş büyük/küçük harf duyarsızdır.
  - Kullanıcı adının büyük/küçük harf duyarsız benzersizliği veritabanında `Lower("username")` UniqueConstraint ile sağlanır. Bu kısıt formlarda ayrıca `iexact` kontrolüyle Türkçe hata mesajına çevrilmelidir.
- **Oy kuralı (planın 4.4 bölümündeki karar):** Her `Vote` kaydı tarayıcının `voting_projects_voter` çerez token'ını taşır; üye oylarında `user` da doldurulur. "Oy verdi mi?" kontrolü: üye için `user` **veya** `voter_token` eşleşmesi, misafir için yalnızca `voter_token`. CheckConstraint "en az biri dolu" şeklindedir.
- **Geçici ana sayfa:** `config/urls.py` içindeki `""` rotası şimdilik `base.html`'i gösteren bir `TemplateView`. Faz 2'de `polls` akışıyla değiştirilecek.
- Şablonlar kökteki `templates/` altında, statik dosyalar `static/` altında (app içinde değil). `polls` uygulaması henüz boş; modelleri Faz 2'de gelecek.
