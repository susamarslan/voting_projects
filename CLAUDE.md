# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proje

voting_projects: kullanıcıların kararsız kaldıkları konularda anket açıp başkalarına danıştığı bir web uygulaması. Her ankette 2–5 seçenek olur. Takip sistemi yok, tüm anketler tek akışta görünür. Misafirler oy verebilir, anket açmak için üyelik gerekir.

Yığın: Django 5.2 + Python 3.12, Supabase (yalnızca Postgres olarak), Django şablonları + saf HTML/CSS/JS, WhiteNoise, Vercel.

**Tek doğru kaynak `docs/VOTING_PROJECTS_PLAN.md`.** Veri modeli, iş kuralları, URL'ler (Türkçe yollar: `/anket/<id>/`, `/kayit/`, `/giris/`...), oy endpoint'inin JSON formatı, tasarım paleti ve faz faz yapılacaklar orada. Bir işe başlamadan önce ilgili bölümü oku. Plan değişecekse önce dosyayı güncelle, sonra kodu değiştir.

## Çalışma kuralları

- Fazlar sırayla uygulanır. Her faz sonunda dur, testleri çalıştır, özetle ve kullanıcının onayını bekle. Şu ana kadar Faz 0–2 tamamlandı.
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
- **Anket sorguları:** Kart gösteren her liste `polls/views.py`'deki `poll_queryset()`'i kullanır (`select_related` + `prefetch_related("options")` + `total_votes` annotate). Burada `order_by` açıkça verilir, çünkü Django GROUP BY içeren sorgularda `Meta.ordering`'i uygulamaz. Akışın sabit sorgu sayısı `assertNumQueries` testiyle korunur.
- **Anket formu:** Seçenekler ModelForm alanı değil; view `request.POST.getlist("options")` ile `PollForm(options=...)`'a verir. Seçenek hataları `form.option_errors` içinde tutulur, `is_valid()` bunları da hesaba katar. Şablon JS yokken 5 input çizer; `static/js/create_poll.js` boşları gizleyip ekle/sil ve aynı doğrulamayı yapar (sunucu kuralları değişirse JS'i de güncelle).
- URL isimleri: hesap rotaları namespace'siz (`login`, `register`, `logout`), anket rotaları `polls:` namespace'inde. Sayfalama parametresi `?sayfa=`.
- Şablonlar kökteki `templates/` altında (ortak parçalar `templates/partials/`), statik dosyalar `static/` altında (app içinde değil). Child şablonlarda `{% static %}` için `{% load static %}` ayrıca yazılmalı.
