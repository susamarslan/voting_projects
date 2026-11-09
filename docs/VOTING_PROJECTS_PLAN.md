# voting_projects — Proje Planı ve Claude Code Promptları

> Bu dosya `docs/VOTING_PROJECTS_PLAN.md` konumundadır. Claude Code'a her fazda şunu söyle:
> **"docs/VOTING_PROJECTS_PLAN.md dosyasını oku ve Faz X'i uygula."**
> Fazları sırayla ilerlet. Bir faz bitip test edilmeden diğerine geçme.
>
> **Çalışma kararları (2026-11-09):** Python 3.12 (.venv 3.12 ile yeniden kurulur). Her faz sonunda durulur, kullanıcı elle test edip onay verince sonraki faza geçilir. Git commit/push işlemlerini kullanıcı yapar; Claude commit atmaz.

---

## 1. Proje Özeti

**voting_projects**, kullanıcıların kararsız kaldıkları konularda diğer kullanıcılara anket açarak danıştığı bir web uygulamasıdır.

- Örnek: *"Bugün sinemaya mı gitsem, restorana mı?"*
- Her ankette **en az 2, en fazla 5** seçenek bulunur.
- **Takip sistemi yoktur.** Herkes platformdaki tüm anketleri tek bir akışta görür.
- **Üye olmayanlar** anketleri görüntüleyebilir ve oy kullanabilir.
- **Anket oluşturmak için üyelik zorunludur.**
- Kayıt: **e-posta + kullanıcı adı + parola.**
- Anketlerde **kullanıcı adı görünür**, e-posta **hiçbir yerde görünmez.**

**Hedef:** Önce çalışan, sade bir prototip. Gereksiz karmaşıklık yok. Özellikler sonra adım adım eklenecek.

---

## 2. Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Dil | Python 3.12 |
| Framework | Django 5.2 (LTS) |
| Veritabanı | Supabase (yalnızca PostgreSQL olarak kullanılır) |
| Frontend | Django şablonları + saf HTML, CSS, JavaScript (framework yok, aynı repo) |
| Statik dosyalar | WhiteNoise |
| Deployment | Vercel (Python runtime) |

**Python paketleri (`requirements.txt`):**
```
Django>=5.2,<5.3
dj-database-url
psycopg[binary]
python-dotenv
whitenoise
```

**Önemli kararlar:**
- Supabase **yalnızca Postgres veritabanı** olarak kullanılır. Supabase Auth, Supabase JS istemcisi veya Realtime **kullanılmaz**. Kimlik doğrulamayı Django'nun kendi auth sistemi yapar.
- Yerel geliştirmede `DATABASE_URL` tanımlı değilse SQLite kullanılır; tanımlıysa Supabase'e bağlanılır.
- Frontend için React/Vue/Tailwind/npm build süreci **yok**. Tek bir CSS dosyası ve küçük JS dosyaları yeterli.

---

## 3. Klasör Yapısı

```
voting_projects/
├── VOTING_PROJECTS_PLAN.md
├── CLAUDE.md                  # Faz 0'da oluşturulacak kısa kurallar dosyası
├── manage.py
├── requirements.txt
├── vercel.json
├── build_files.sh             # Vercel build adımı (collectstatic)
├── .env.example
├── .gitignore
├── config/                    # Django proje ayarları
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                  # Kullanıcı, kayıt, giriş
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── polls/                     # Anket, seçenek, oy
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── middleware.py          # Anonim oy çerezi
├── templates/
│   ├── base.html
│   ├── accounts/  (register.html, login.html)
│   └── polls/     (feed.html, detail.html, create.html, my_polls.html, _poll_card.html)
└── static/
    ├── css/style.css
    └── js/
        ├── create_poll.js     # Seçenek ekle/sil
        └── vote.js            # Oy gönderme ve sonuç animasyonu
```

---

## 4. Veri Modeli

### 4.1 `accounts.User` (özel kullanıcı modeli — projenin en başında oluşturulmalı)
`AbstractUser`'dan türetilir.

| Alan | Tip | Kural |
|---|---|---|
| `email` | EmailField | Benzersiz, zorunlu, küçük harfe çevrilerek kaydedilir. **Giriş alanıdır.** |
| `username` | CharField(20) | Benzersiz (büyük/küçük harf duyarsız), 3–20 karakter, yalnızca harf, rakam ve `_` |
| `password` | — | Django'nun varsayılan hash'lemesi |

- `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = ["username"]`
- `settings.AUTH_USER_MODEL = "accounts.User"`
- E-posta **hiçbir şablonda, API yanıtında veya sayfa kaynağında** gösterilmez (admin paneli hariç).

### 4.2 `polls.Poll`
| Alan | Tip | Kural |
|---|---|---|
| `author` | FK → User | `on_delete=CASCADE` |
| `question` | CharField(200) | Zorunlu, en az 5 karakter |
| `description` | TextField(500) | Opsiyonel, kısa açıklama |
| `created_at` | DateTimeField | `auto_now_add` |
| `is_active` | BooleanField | Varsayılan `True` (ileride anket kapatma için) |

Sıralama: `-created_at`.

### 4.3 `polls.Option`
| Alan | Tip | Kural |
|---|---|---|
| `poll` | FK → Poll | `related_name="options"`, CASCADE |
| `text` | CharField(100) | Zorunlu |
| `order` | PositiveSmallIntegerField | Görüntüleme sırası (0–4) |

Kural: Bir anketin **2–5** seçeneği olur; aynı ankette tekrar eden seçenek metni olamaz (büyük/küçük harf ve baş/son boşluk göz ardı edilerek).

### 4.4 `polls.Vote`
| Alan | Tip | Kural |
|---|---|---|
| `poll` | FK → Poll | CASCADE |
| `option` | FK → Option | CASCADE |
| `user` | FK → User, null=True | Üye oyu ise dolu |
| `voter_token` | CharField(64), null=True | Oyun verildiği tarayıcının çerez token'ı (üye oylarında da kaydedilir) |
| `created_at` | DateTimeField | `auto_now_add` |

**Kısıtlar (veritabanı seviyesinde):**
- `UniqueConstraint(fields=["poll", "user"], condition=Q(user__isnull=False))`
- `UniqueConstraint(fields=["poll", "voter_token"], condition=Q(voter_token__isnull=False))`
- `CheckConstraint`: `user` veya `voter_token`'dan **en az biri** dolu olmalı.
- `option.poll == poll` olduğu view'da doğrulanır.

> **Karar (2026-11-09):** Üye oy verirken o tarayıcının çerez token'ı da kaydedilir. Böylece aynı tarayıcıdan misafirken oy verip sonra giriş yaparak (veya tersi) ikinci oy verilemez. "Oy verdi mi?" kontrolü: üye ise `user` **veya** `voter_token` eşleşmesi; misafir ise `voter_token` eşleşmesi.

---

## 5. İş Kuralları

### Oy kullanma
- **Herkes** (üye olsun olmasın) her ankete **bir kez** oy verebilir.
- **Üye kullanıcı:** oy `user` ile kaydedilir.
- **Anonim kullanıcı:** bir middleware, ilk ziyarette `voting_projects_voter` adında rastgele bir token (UUID4 hex) içeren çerez oluşturur (HttpOnly, SameSite=Lax, 1 yıl, prod'da Secure). Oy bu token ile kaydedilir.
- Prototipte oy **değiştirilemez ve geri alınamaz.**
- Anket sahibi kendi anketine oy verebilir.
- Bilinen sınırlama (prototip için kabul edilir): anonim kullanıcı çerezleri silerse tekrar oy verebilir. Bu, ileride IP/hız sınırlaması ile iyileştirilecek.

### Sonuçların görünürlüğü
- Kullanıcı oy vermeden önce yalnızca seçenekleri görür (sonuçlar etkilemesin diye).
- Oy verdikten sonra her seçeneğin **yüzdesi, oy sayısı ve toplam oy** görünür; kullanıcının seçtiği seçenek işaretlenir.
- Anket sahibi sonuçları her zaman görür.

### Anket oluşturma
- Yalnızca giriş yapmış kullanıcılar. Giriş yapmamış biri "Anket oluştur"a tıklarsa giriş sayfasına yönlendirilir (`?next=` ile geri döner); giriş sayfasında kayıt ol bağlantısı belirgin olur.
- Form: soru + opsiyonel açıklama + 2–5 seçenek. Doğrulama **hem JS'de hem sunucuda** yapılır.
- Prototipte anket düzenleme yok. Sahibi kendi anketini **silebilir** (onay ile).

### Görünürlük ve gizlilik
- Takip/arkadaşlık sistemi yok. Tüm anketler tek ana akışta, en yeniden en eskiye.
- Kartta: `@kullaniciadi`, "3 saat önce" gibi göreli zaman, soru, seçenekler, toplam oy sayısı.

---

## 6. Sayfalar ve URL'ler

| URL | View | Erişim | Açıklama |
|---|---|---|---|
| `/` | `feed` | Herkes | Tüm anketler, sayfa başına 20 (Django Paginator) |
| `/anket/<id>/` | `poll_detail` | Herkes | Tek anket, oy verme, sonuçlar, paylaşım linki kopyalama |
| `/anket/<id>/oy/` | `vote` | Herkes, **POST** | Oy kaydeder. `fetch` isteğine JSON, normal form isteğine redirect döner |
| `/anket/yeni/` | `poll_create` | Üye | Anket oluşturma formu |
| `/anket/<id>/sil/` | `poll_delete` | Sadece sahibi, POST | Anketi siler |
| `/anketlerim/` | `my_polls` | Üye | Kullanıcının kendi anketleri |
| `/kayit/` | `register` | Misafir | Kayıt; başarıda otomatik giriş + ana sayfaya yönlendirme |
| `/giris/` | `login` | Misafir | E-posta + parola |
| `/cikis/` | `logout` | Üye, POST | Çıkış |
| `/admin/` | Django admin | Superuser | Yönetim |

**Oy endpoint'i JSON yanıtı:**
```json
{
  "ok": true,
  "voted_option_id": 12,
  "total_votes": 37,
  "options": [
    {"id": 11, "text": "Sinema", "votes": 15, "percent": 40.5},
    {"id": 12, "text": "Restoran", "votes": 22, "percent": 59.5}
  ]
}
```
Hatalar: zaten oy verilmişse `409`, geçersiz seçenekse `400`, anket pasifse `403`. JSON'da `{"ok": false, "error": "..."}`.

**Performans:** Akışta oy sayıları `annotate(Count(...))` ve `prefetch_related("options")` ile çekilir; N+1 sorgu olmaz. Kullanıcının oy verdiği anketler tek sorguyla bulunur.

---

## 7. Arayüz Tasarımı

**Hedef his:** Genç, eğlenceli, enerjik ama temiz. Açık arka plan, canlı renkler, yumuşak tonlamalar. Mobil öncelikli.

### Renk paleti (CSS değişkenleri)
```css
:root {
  --bg: #FAFAFF;            /* çok açık, hafif mor tonlu arka plan */
  --surface: #FFFFFF;       /* kartlar */
  --text: #1E1B2E;          /* ana metin */
  --text-muted: #6B6880;
  --border: #ECEAF5;

  --primary: #7C3AED;       /* canlı mor — ana buton, logo */
  --primary-soft: #F1EAFE;

  /* Seçenek renkleri — her seçenek sırasına göre bir renk alır */
  --opt-1: #7C3AED;  --opt-1-soft: #F1EAFE;  /* mor */
  --opt-2: #EC4899;  --opt-2-soft: #FDE8F3;  /* pembe */
  --opt-3: #F97316;  --opt-3-soft: #FEEEDF;  /* turuncu */
  --opt-4: #14B8A6;  --opt-4-soft: #DDF6F2;  /* turkuaz */
  --opt-5: #EAB308;  --opt-5-soft: #FDF6D8;  /* sarı */

  --radius: 18px;
  --shadow: 0 4px 20px rgba(124, 58, 237, 0.08);
}
```

### Tipografi
- Google Fonts: **"Plus Jakarta Sans"** (400, 600, 800). Türkçe karakterleri destekler.
- Soru başlıkları kalın (700–800), seçenekler 600.

### Bileşenler
- **Üst bar:** Solda "voting_projects" logosu (mor→pembe gradyan metin + küçük 🤔 emoji). Sağda: giriş yapılmamışsa "Giriş" + "Kayıt ol"; yapılmışsa `@kullaniciadi`, "Anketlerim", "Çıkış". Her durumda belirgin bir **"+ Anket oluştur"** butonu.
- **Anket kartı:** Beyaz, `--radius` köşeler, hafif mor gölge. Üstte `@kullaniciadi · 2 saat önce`, altında soru, altında seçenekler, en altta "37 oy".
- **Seçenek butonları (oy öncesi):** Tam genişlik, seçeneğin soft rengi arka plan, solunda renkli küçük daire. Hover'da hafif büyüme ve renk koyulaşması.
- **Sonuç çubukları (oy sonrası):** Aynı satır, arka planda seçenek renginde soldan sağa dolan bir çubuk (CSS transition, ~600 ms), sağda yüzde. Kullanıcının seçtiği satırda ✓ işareti ve kalın kenar.
- **Formlar:** Büyük, yuvarlak input'lar; odakta mor halka. Hata mesajları pembe-kırmızı tonda, alanın altında.
- **Boş durum:** Henüz anket yoksa eğlenceli bir mesaj: "Burası çok sessiz... İlk kararsızlığı sen paylaş!"
- **Toast bildirimleri:** "Oyun kaydedildi 🎉", "Anketin yayında!" gibi kısa mesajlar (Django messages + küçük JS ile otomatik kaybolma).

### Genel kurallar
- Mobil öncelikli; içerik alanı masaüstünde en fazla ~640px genişlik, ortalanmış.
- Erişilebilirlik: yeterli kontrast, `button` elementleri, `aria-label`'lar, klavyeyle kullanılabilir.
- Tüm arayüz metinleri **Türkçe.** `LANGUAGE_CODE = "tr"`, `TIME_ZONE = "Europe/Istanbul"`.
- Animasyonlar hafif tutulur; `prefers-reduced-motion` desteklenir.

---

## 8. Ortam Değişkenleri

`.env.example`:
```
SECRET_KEY=degistir-bunu
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
# Boş bırakılırsa yerelde SQLite kullanılır
DATABASE_URL=
```

`.env` dosyası **asla** commit edilmez (`.gitignore`'a eklenir).

---

## 9. Fazlar ve Claude Code Promptları

Her fazın sonunda: uygulamayı çalıştır, elle test et, sonra commit at.

---

### FAZ 0 — Proje Kurulumu

**Amaç:** Çalışan boş Django projesi, doğru ayarlar ve özel kullanıcı modeli.

**Claude Code'a yapıştır:**
```
VOTING_PROJECTS_PLAN.md dosyasını baştan sona oku. Şimdi yalnızca FAZ 0'ı uygula:

1. Planın 3. bölümündeki klasör yapısına uygun bir Django 5.2 projesi oluştur. Proje paketi adı "config" olsun. "accounts" ve "polls" uygulamalarını oluştur ve INSTALLED_APPS'e ekle.
2. requirements.txt'yi plandaki paketlerle oluştur. Python sanal ortamı (.venv) kullan.
3. settings.py:
   - python-dotenv ile .env oku; SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS ortam değişkenlerinden gelsin.
   - DATABASE_URL varsa dj-database-url ile kullan (conn_max_age=0); yoksa SQLite'a düş.
   - LANGUAGE_CODE="tr", TIME_ZONE="Europe/Istanbul", USE_TZ=True.
   - TEMPLATES DIRS = BASE_DIR / "templates"; STATICFILES_DIRS = [BASE_DIR / "static"]; STATIC_ROOT = BASE_DIR / "staticfiles".
   - WhiteNoise middleware'ini ekle.
   - AUTH_USER_MODEL = "accounts.User".
4. accounts uygulamasında plandaki 4.1 bölümüne uygun özel User modelini oluştur (USERNAME_FIELD="email"). Bir UserManager yaz (create_user, create_superuser). Admin'e kaydet. Bu modeli İLK migration'dan önce oluştur.
5. .env.example, .gitignore (Python, .venv, .env, staticfiles, db.sqlite3, __pycache__) oluştur.
6. Kök dizine kısa bir CLAUDE.md yaz: proje özeti (3-4 satır), "her zaman VOTING_PROJECTS_PLAN.md'ye uy", "frontend framework ekleme", "arayüz metinleri Türkçe", "e-posta asla arayüzde gösterilmez", "yeni paket eklemeden önce sor".
7. templates/base.html'i boş bir iskelet olarak oluştur (henüz stil yok).
8. Migration'ları oluştur ve uygula, createsuperuser'ın çalıştığını doğrula, runserver ile sayfanın açıldığını kontrol et.

Başka faza geçme. Bittiğinde neyi yaptığını ve nasıl test edeceğimi kısaca özetle.
```

**Kontrol listesi:**
- [ ] `python manage.py runserver` hatasız açılıyor
- [ ] `/admin/` açılıyor, superuser e-posta ile giriş yapabiliyor
- [ ] `.env` git'e eklenmiyor

---

### FAZ 1 — Kayıt, Giriş, Çıkış

**Amaç:** Kullanıcılar e-posta + kullanıcı adı + parola ile kayıt olup giriş yapabilsin.

**Claude Code'a yapıştır:**
```
VOTING_PROJECTS_PLAN.md'yi oku ve FAZ 1'i uygula:

1. accounts/forms.py:
   - RegisterForm: email, username, password1, password2. Kurallar planın 4.1 bölümündeki gibi: e-posta küçük harfe çevrilip benzersiz kontrol edilsin, kullanıcı adı 3-20 karakter, sadece harf/rakam/_ ve büyük-küçük harf duyarsız benzersiz olsun. Django'nun parola doğrulayıcılarını kullan. Hata mesajları Türkçe.
   - LoginForm: email + password (Django AuthenticationForm'u e-posta etiketiyle uyarlayabilirsin).
2. Views: register (başarıda otomatik login ve "/"e yönlendirme), login (?next= desteği), logout (sadece POST). Giriş yapmış kullanıcı kayıt/giriş sayfasına girerse ana sayfaya yönlendir.
3. URL'ler: /kayit/, /giris/, /cikis/. settings'te LOGIN_URL="/giris/", LOGIN_REDIRECT_URL="/", LOGOUT_REDIRECT_URL="/".
4. templates/accounts/register.html ve login.html: şimdilik base.html'i extend eden sade formlar. Giriş sayfasında "Hesabın yok mu? Kayıt ol" bağlantısı olsun.
5. base.html'e üst bar ekle: giriş yapılmamışsa "Giriş" ve "Kayıt ol", yapılmışsa "@kullaniciadi" ve Çıkış butonu (POST formu). E-posta hiçbir yerde gösterilmesin.
6. Django messages framework'ünü base.html'de göster.
7. accounts için temel testler yaz: başarılı kayıt, tekrar eden e-posta/kullanıcı adı reddi, geçersiz kullanıcı adı reddi, e-posta ile giriş. Testleri çalıştır.

Stil işine girme, o Faz 4'te. Bittiğinde özetle.
```

**Kontrol listesi:**
- [ ] Kayıt → otomatik giriş → üst barda `@kullaniciadi`
- [ ] Aynı e-posta / kullanıcı adı ile ikinci kayıt reddediliyor (`Ali` ve `ali` aynı sayılıyor)
- [ ] Çıkış ve tekrar giriş çalışıyor
- [ ] `python manage.py test` geçiyor

---

### FAZ 2 — Anket Oluşturma ve Listeleme

**Amaç:** Üyeler anket açabilsin, herkes tüm anketleri görebilsin.

**Claude Code'a yapıştır:**
```
VOTING_PROJECTS_PLAN.md'yi oku ve FAZ 2'yi uygula:

1. polls/models.py: planın 4.2, 4.3 ve 4.4 bölümlerindeki Poll, Option ve Vote modellerini tüm kısıtlarıyla (UniqueConstraint ve CheckConstraint dahil) oluştur. Admin'e kaydet (Poll admin'inde Option inline olsun). Migration'ları oluştur ve uygula.
2. Anket oluşturma formu (/anket/yeni/, login_required):
   - Soru (zorunlu, 5-200 karakter), açıklama (opsiyonel, max 500), seçenekler.
   - Seçenekleri "options" adıyla birden çok input olarak al (request.POST.getlist). Boş olanları at, kırp, en az 2 en fazla 5 olduğunu ve tekrar etmediğini (büyük/küçük harf duyarsız) sunucuda doğrula. Hata varsa formu girilen değerlerle geri göster.
   - Kayıt işlemini transaction.atomic içinde yap. Başarıda "Anketin yayında!" mesajı ve anket detayına yönlendirme.
3. static/js/create_poll.js: sayfa 2 seçenek input'u ile açılsın. "+ Seçenek ekle" butonu 5'e kadar ekler (5'te gizlenir), her input'un yanında sil butonu olsun ama 2'nin altına inilemesin. Gönderimden önce aynı kuralları JS ile kontrol et. JS kapalıysa sayfa 5 input gösterebilir (progressive enhancement).
4. Ana akış (/): tüm aktif anketler, en yeni üstte, sayfa başına 20 (Paginator). Her kart için _poll_card.html partial'ı: @kullaniciadi, göreli zaman (timesince, Türkçe), soru, seçenekler (şimdilik sadece metin), toplam oy sayısı. annotate + prefetch_related ile N+1 sorgudan kaçın. Kart detay sayfasına bağlansın.
5. Anket detayı (/anket/<id>/): soru, açıklama, sahibi, tarih, seçenekler. Bu fazda oy verme yok.
6. Anketlerim (/anketlerim/, login_required): kullanıcının kendi anketleri. Her birinde "Sil" butonu (POST /anket/<id>/sil/, sadece sahibi; JS confirm ile onay).
7. Üst bara "+ Anket oluştur" butonu ekle. Giriş yapmamış kullanıcı tıklarsa /giris/?next=/anket/yeni/ adresine gitsin.
8. Boş akış için Türkçe boş durum mesajı göster.
9. Testler: misafir /anket/yeni/'ye girince yönlendiriliyor; 1 seçenek ve 6 seçenek reddediliyor; tekrar eden seçenek reddediliyor; başkasının anketi silinemiyor. Testleri çalıştır.

Bittiğinde özetle.
```

**Kontrol listesi:**
- [ ] Misafir "Anket oluştur"a basınca girişe yönleniyor, girişten sonra forma dönüyor
- [ ] 2–5 seçenek sınırı hem tarayıcıda hem sunucuda çalışıyor
- [ ] Ana sayfada tüm kullanıcıların anketleri görünüyor, e-posta hiçbir yerde yok
- [ ] Kendi anketini silebiliyor, başkasınınkini silemiyor

---

### FAZ 3 — Oy Verme ve Sonuçlar

**Amaç:** Üyeler ve misafirler her ankete bir kez oy verebilsin, sonuçları görsün.

**Claude Code'a yapıştır:**
```
VOTING_PROJECTS_PLAN.md'yi oku (özellikle 4.4, 5 ve 6. bölümler) ve FAZ 3'ü uygula:

1. polls/middleware.py: anonim kullanıcılar için "voting_projects_voter" çerezi. Yoksa uuid4().hex üret; request.voter_token'a ata ve yanıtta çerezi ayarla (HttpOnly, SameSite=Lax, max_age 1 yıl, DEBUG False ise Secure). Middleware'i settings'e ekle.
2. Yardımcı fonksiyonlar (polls/services.py gibi bir dosyada):
   - get_user_vote(request, poll): üye ise user ile, değilse voter_token ile oyu bulur.
   - poll_results(poll): her seçenek için oy sayısı ve yüzde (1 ondalık), toplam oy.
3. POST /anket/<id>/oy/:
   - option_id al, seçeneğin bu ankete ait olduğunu doğrula, anket aktif mi kontrol et.
   - Üye ise user ile, değilse voter_token ile Vote oluştur. Daha önce oy verilmişse (IntegrityError dahil) reddet.
   - İstek fetch ile geldiyse (Accept: application/json veya X-Requested-With) planın 6. bölümündeki JSON formatında yanıt ver ve doğru HTTP kodlarını kullan (409, 400, 403). Normal form gönderimiyse mesaj ekleyip detay sayfasına redirect et.
   - CSRF korumasını kapatma; JS çerezden csrftoken'ı okuyup header'a eklesin.
4. Detay sayfası ve akış kartları:
   - Kullanıcı oy vermediyse seçenekler tıklanabilir butonlardır (her biri JS yokken de çalışan küçük bir POST formu).
   - Oy verdiyse veya anketin sahibiyse sonuçlar gösterilir: her seçenek için yüzde çubuğu, oy sayısı, yüzde, kullanıcının seçtiği seçenekte ✓.
   - Akışta hangi anketlere oy verildiğini tek sorguyla bul (N+1 olmasın).
5. static/js/vote.js: seçenek butonuna tıklanınca fetch ile oy gönder, butonları kilitle, dönen JSON ile kartı sonuç görünümüne çevir ve çubukları 0'dan hedef yüzdeye animasyonla doldur. Toplam oy sayısını güncelle. Hata olursa Türkçe kısa bir uyarı göster. Hem akışta hem detay sayfasında çalışsın.
6. Testler: misafir oy verebiliyor; aynı misafir ikinci kez oy veremiyor; üye oy verebiliyor ve ikinci kez veremiyor; başka ankete ait option_id reddediliyor; JSON yanıt formatı doğru; yüzdeler doğru hesaplanıyor. Testleri çalıştır.

Bittiğinde özetle.
```

**Kontrol listesi:**
- [ ] Gizli pencerede (misafir) oy verilebiliyor, sayfa yenilenince sonuçlar kalıcı
- [ ] Aynı tarayıcıdan ikinci oy verilemiyor
- [ ] Üye oyu, farklı tarayıcıdan girse de tek sayılıyor
- [ ] JS kapalıyken de oy verilebiliyor

---

### FAZ 4 — Arayüz ve Görsel Tasarım

**Amaç:** Planın 7. bölümündeki genç, canlı ve temiz tasarımı uygulamak.

**Claude Code'a yapıştır:**
```
VOTING_PROJECTS_PLAN.md'yi oku (özellikle 7. bölüm) ve FAZ 4'ü uygula. İşlevselliği değiştirme, sadece görünümü ve küçük UX iyileştirmelerini yap:

1. static/css/style.css: 7. bölümdeki CSS değişkenlerini aynen kullan. Plus Jakarta Sans'ı Google Fonts'tan yükle. Framework (Tailwind, Bootstrap vb.) kullanma.
2. Üst bar: mor→pembe gradyan logo metni + 🤔, sağda planda tarif edilen bağlantılar, belirgin "+ Anket oluştur" butonu. Mobilde sade kalsın.
3. Anket kartları ve detay sayfası: 7. bölümdeki kart, seçenek butonu ve sonuç çubuğu tarifini uygula. Her seçenek sırasına göre --opt-1...--opt-5 renklerini alsın (data-index veya sınıf ile). Sonuç çubukları seçenek renginde, arka plan soft tonda.
4. Formlar (kayıt, giriş, anket oluştur): büyük yuvarlak input'lar, odakta mor halka, alan altında Türkçe hata mesajları. Anket oluşturma formunda her seçenek input'unun solunda kendi renginde küçük bir daire olsun.
5. Django messages için sağ alt / üst ortada otomatik kaybolan toast bildirimleri (küçük JS).
6. Detay sayfasına "Linki kopyala" butonu ekle (navigator.clipboard, başarıda "Kopyalandı!" toast'ı).
7. Boş durum, 404 ve 500 sayfaları için eğlenceli Türkçe metinli, temaya uygun şablonlar.
8. Mobil öncelikli: 360px genişlikte kusursuz görünsün; içerik masaüstünde max ~640px ortalanmış. prefers-reduced-motion'da animasyonları kapat. Kontrast ve klavye erişilebilirliğini kontrol et.

Bittiğinde hangi sayfaları değiştirdiğini özetle.
```

**Kontrol listesi:**
- [ ] Telefonda (DevTools 360px) düzgün görünüyor
- [ ] Seçenek renkleri ve sonuç animasyonu çalışıyor
- [ ] Toast'lar ve link kopyalama çalışıyor

---

### FAZ 5 — Supabase ve Vercel'e Yayınlama

**Ön hazırlık (senin yapacakların):**
1. [supabase.com](https://supabase.com)'da yeni proje aç, veritabanı parolasını kaydet.
2. Project Settings → Database → Connection string bölümünden iki adres al:
   - **Transaction pooler** (port `6543`) → Vercel'deki `DATABASE_URL` için
   - **Session pooler veya direct connection** (port `5432`) → yerelden migration çalıştırmak için
3. Kodu bir GitHub reposuna gönder.
4. [vercel.com](https://vercel.com)'da GitHub reposunu içe aktar.

**Claude Code'a yapıştır:**
```
VOTING_PROJECTS_PLAN.md'yi oku ve FAZ 5'i uygula. Önce Vercel'in güncel Python/Django deployment dokümantasyonunu kontrol et; aşağıdaki yapılandırma güncel önerilerle çelişirse güncel olanı uygula ve bana söyle.

1. config/wsgi.py'de Vercel için "app = application" satırını ekle.
2. vercel.json oluştur: config/wsgi.py'yi @vercel/python ile çalıştır; statik dosyaları build sırasında collectstatic ile topla (build_files.sh) ve /static/ isteklerini doğru yere yönlendir; diğer tüm istekleri Django'ya yönlendir. Python 3.12 kullan.
3. settings.py prod ayarları (DEBUG=False iken):
   - ALLOWED_HOSTS ve CSRF_TRUSTED_ORIGINS ortam değişkenlerinden (".vercel.app" alan adı dahil).
   - SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE = True; SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https").
   - Supabase transaction pooler (pgbouncer) ile uyum için: conn_max_age=0, DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True, sslmode=require.
   - WhiteNoise için CompressedManifestStaticFilesStorage.
4. Güvenlik: Django tabloları Supabase'in public şemasında oluşacağı için Supabase REST API'sinden erişilememeleri adına tüm tablolarda Row Level Security'yi açan bir migration yaz (polls uygulamasında RunSQL ile; sadece PostgreSQL'de çalışsın, SQLite'ta atlansın). Politika ekleme — Django postgres rolüyle bağlandığı için etkilenmez. Hangi tabloların kapsandığını listele (auth, session, admin, contenttypes tabloları dahil).
5. README.md yaz: yerel kurulum, .env ayarları, Supabase'e migration çalıştırma (5432 portlu bağlantıyla `python manage.py migrate` ve `createsuperuser`), Vercel'de girilmesi gereken ortam değişkenleri (SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, DATABASE_URL=6543 portlu adres) ve deploy adımları.
6. Yeni güçlü bir SECRET_KEY üretmenin komutunu README'ye ekle.

Migration'ları Vercel build'inde çalıştırma; README'de yerelden çalıştırılacağını açıkla. Bittiğinde benim elle yapmam gereken adımları numaralı liste olarak ver.
```

**Kontrol listesi:**
- [ ] Vercel adresi açılıyor, CSS yükleniyor
- [ ] Kayıt, giriş, anket oluşturma, oy verme canlıda çalışıyor
- [ ] Supabase Table Editor'da tablolar görünüyor ve RLS açık
- [ ] `/admin/` canlıda çalışıyor

---

## 10. Sonraki Adımlar (Prototip Sonrası Fikirler)

Prototip yayına girdikten sonra öncelik sırasına göre değerlendirilebilir:

1. **Kötüye kullanım önleme:** oy ve anket oluşturma için hız sınırı, IP hash'i ile ek anonim oy kontrolü, basit küfür filtresi.
2. **Anket süresi:** "24 saat sonra kapanır" seçeneği; süresi dolan anket sonuç modunda kalır.
3. **Kategoriler / etiketler:** Yemek, Eğlence, Alışveriş, Moda... ve akışta filtre.
4. **Sıralama:** "En yeni" / "Popüler (son 24 saatte en çok oy alan)" sekmeleri.
5. **Yorumlar:** seçeneklere kısa gerekçeli yorumlar.
6. **Anketi raporlama** ve admin moderasyon ekranı.
7. **Parola sıfırlama** (e-posta gönderimi için Resend/SendGrid gibi bir servis).
8. **Paylaşım görselleri:** Open Graph meta etiketleri, sosyal medyada güzel önizleme.
9. **Profil sayfası:** `/u/<kullaniciadi>/` — kullanıcının açtığı anketler (takip sistemi olmadan).
10. **Karanlık mod.**

---

## 11. Claude Code ile Çalışma İpuçları

- Her fazdan önce `/clear` ile bağlamı temizleyip planı tekrar okutmak daha tutarlı sonuç verir.
- Faz bitince Claude Code'dan **testleri çalıştırmasını** ve **değişiklikleri özetlemesini** iste.
- Her fazın sonunda git commit at: `git commit -m "Faz 2: anket oluşturma ve listeleme"`.
- Bir şey beklediğin gibi değilse tüm fazı baştan yaptırma; somut hatayı söyle: *"Akışta oy verdikten sonra toplam oy sayısı güncellenmiyor, düzelt."*
- Plan değişirse önce bu dosyayı güncelle, sonra Claude Code'a uygulat. Böylece dosya her zaman tek doğru kaynak olur.
