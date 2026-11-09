# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proje

voting_projects (arayüzdeki adı **Kararsızım**; `voting_projects` kullanıcıya hiçbir yerde gösterilmez): kullanıcıların kararsız kaldıkları konularda anket açıp başkalarına danıştığı bir web uygulaması. Her ankette 2–5 seçenek olur. Takip sistemi yok, tüm anketler tek akışta görünür. Misafirler oy verebilir, anket açmak için üyelik gerekir.

Yığın: Django 5.2 + Python 3.12, Supabase (yalnızca Postgres olarak), Django şablonları + saf HTML/CSS/JS, WhiteNoise, Vercel.

**Tek doğru kaynak `docs/VOTING_PROJECTS_PLAN.md`.** Veri modeli, iş kuralları, URL'ler (Türkçe yollar: `/anket/<id>/`, `/kayit/`, `/giris/`...), oy endpoint'inin JSON formatı, tasarım paleti ve faz faz yapılacaklar orada. Bir işe başlamadan önce ilgili bölümü oku. Plan değişecekse önce dosyayı güncelle, sonra kodu değiştir.

## Çalışma kuralları

- Fazlar sırayla uygulanır. Her faz sonunda dur, testleri çalıştır, özetle ve kullanıcının onayını bekle. Faz 0–5'in kodu tamamlandı; deploy adımları README.md'de.
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

- **Ayarlar (`config/settings.py`):** Her şey `.env` dosyasından okunur (`.env.example`'a bak). `DEBUG` tanımlı değilse **False** olur; yerelde `.env` içinde `DEBUG=True` gerekir. `DEBUG=False` iken `SECRET_KEY` yoksa uygulama başlamaz. `DATABASE_URL` boşsa SQLite, doluysa `dj-database-url` ile Postgres kullanılır (`conn_max_age=0`, `ssl_require`, `DISABLE_SERVER_SIDE_CURSORS`: Supabase transaction pooler ve Vercel serverless için). `DEBUG=False`'ta statik dosyalar WhiteNoise `CompressedManifestStaticFilesStorage` ile hash'lenir (önce `collectstatic` gerekir).
- **Deploy (Vercel):** `vercel.json` yok; Vercel Django'yu `manage.py` + `WSGI_APPLICATION` üzerinden kendisi tanır ve `collectstatic`'i kendisi çalıştırır. Python sürümü `.python-version`'da. `VERCEL_URL` vb. sistem değişkenleri `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`'e otomatik eklenir. Migration'lar build'de değil, yerelden 5432 portlu Supabase adresiyle çalıştırılır.
- **Supabase:** Proje `kararsizim` (ref `exdmzqdfupxmifwqwuny`, eu-central-1). Django `django_app` rolüyle bağlanır (tabloların sahibi); adresler git'e girmeyen `.env.supabase`'de (`SUPABASE_SESSION_URL` 5432, `SUPABASE_TRANSACTION_URL` 6543). Yerel `.env`'deki `DATABASE_URL` boş kalır; Supabase'e komut çalıştırırken `DATABASE_URL` ortam değişkeni olarak verilir (README'de örnek var). Bu adresleri/parolayı sohbete veya çıktıya yazdırma.
- **RLS:** `polls/migrations/0002_enable_rls.py` Supabase'de tüm Django tablolarında Row Level Security'yi açar (yalnızca PostgreSQL'de). Yeni bir model eklenirse onun tablosu için de RLS açan yeni bir migration yazılmalı.
- **Kullanıcı modeli (`accounts.User`):** `AbstractUser`'dan türetilir ve giriş alanı e-postadır (`USERNAME_FIELD = "email"`). Bu yüzden `authenticate(username=...)` çağrısına e-posta verilir.
  - E-posta `save()` sırasında küçük harfe çevrilir. `UserManager.get_by_natural_key` `iexact` ile eşleştirdiği için giriş büyük/küçük harf duyarsızdır.
  - Kullanıcı adının büyük/küçük harf duyarsız benzersizliği veritabanında `Lower("username")` UniqueConstraint ile sağlanır. Bu kısıt formlarda ayrıca `iexact` kontrolüyle Türkçe hata mesajına çevrilmelidir.
- **Oy kuralı (planın 4.4 bölümündeki karar):** Her `Vote` kaydı tarayıcının `voting_projects_voter` çerez token'ını taşır; üye oylarında `user` da doldurulur. "Oy verdi mi?" kontrolü: üye için `user` **veya** `voter_token` eşleşmesi, misafir için yalnızca `voter_token`. CheckConstraint "en az biri dolu" şeklindedir.
  - Token'ı `polls/middleware.py` verir (`request.voter_token`, `request.voter_token_is_new`). Çerezi olmayan misafirin oyu reddedilir (yoksa her istekte yeni token = sınırsız oy).
  - Oy kuralları ve sonuç hesapları `polls/services.py`'de. `decorate_polls()` her ankete `can_vote`, `show_results`, `voted_option_id` ve seçeneklere `percent`/`is_choice` ekler; listeleyen her view bunu çağırmalı.
  - Sonuç sayıları yalnızca `show_results` iken HTML'e basılır (oy öncesi sayfa kaynağında görünmemeli). Anket sahibi sonuçları her zaman görür ve oy da verebilir.
  - Seçenek/sonuç markup'ı `templates/polls/_poll_options.html` ile `static/js/vote.js`'teki `renderResults` arasında ikizdir; biri değişirse diğeri de güncellenmeli.
- **Anket sorguları:** Kart gösteren her liste `polls/views.py`'deki `poll_queryset()`'i kullanır (`select_related` + `prefetch_related("options")` + `total_votes` annotate). Burada `order_by` açıkça verilir, çünkü Django GROUP BY içeren sorgularda `Meta.ordering`'i uygulamaz. Akışın sabit sorgu sayısı `assertNumQueries` testiyle korunur.
- **Anket formu:** Seçenekler ModelForm alanı değil; view `request.POST.getlist("options")` ile `PollForm(options=...)`'a verir. Seçenek hataları `form.option_errors` içinde tutulur, `is_valid()` bunları da hesaba katar. Şablon JS yokken 5 input çizer; `static/js/create_poll.js` boşları gizleyip ekle/sil ve aynı doğrulamayı yapar (sunucu kuralları değişirse JS'i de güncelle).
- **Arayüz:** Tek stil dosyası `static/css/style.css`; renkler plandaki CSS değişkenleri. Seçenek rengi `data-index="1..5"` özniteliğinden `--c`/`--c-soft` olarak gelir (kartlar, sonuç çubukları ve oluşturma formu aynı mekanizmayı kullanır). `static/js/app.js` her sayfada yüklenir: Django messages'ı toast'a çevirir, `window.showToast(mesaj, "success"|"error"|"info")` sağlar, `data-confirm` ve `data-copy-url` davranışlarını yönetir. `500.html` bağlamsız render edildiği için `base.html`'i extend etmez.
- Geliştirmede WhiteNoise statik dosyaları 60 sn önbelleğe aldırır; JS/CSS değişikliği tarayıcıda görünmüyorsa önbelleği atlayarak yenile.
- URL isimleri: hesap rotaları namespace'siz (`login`, `register`, `logout`), anket rotaları `polls:` namespace'inde. Sayfalama parametresi `?sayfa=`.
- Şablonlar kökteki `templates/` altında (ortak parçalar `templates/partials/`), statik dosyalar `static/` altında (app içinde değil). Child şablonlarda `{% static %}` için `{% load static %}` ayrıca yazılmalı.
