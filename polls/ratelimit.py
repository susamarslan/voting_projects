"""Veritabanı tabanlı basit hız sınırı (bkz. plan 5. bölüm, "Hız sınırları")."""

import hashlib
import hmac
import random
import time
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import RateLimit

# (sınır, pencere saniyesi)
VOTE = (60, 10 * 60)
LOGIN_FAILURE = (10, 15 * 60)
REGISTER = (5, 60 * 60)
CREATE_POLL = (10, 60 * 60)

CLEANUP_PROBABILITY = 0.02

LIMITED_MESSAGE = "Çok hızlı gidiyorsun. Biraz bekleyip tekrar dene."


def client_ip(request):
    """İstemci IP'si. Proxy başlıklarına yalnızca güvenilen ortamda (Vercel) bakılır,
    yoksa herkes başlığı uydurup sınırı aşabilirdi."""
    if settings.TRUST_PROXY_HEADERS:
        ip = request.headers.get("X-Real-IP") or request.headers.get(
            "X-Forwarded-For", ""
        ).split(",")[0]
        if ip.strip():
            return ip.strip()
    return request.META.get("REMOTE_ADDR", "")


def _bucket(scope, ident, window):
    # IP gibi kimlikler tabloya ham yazılmaz.
    digest = hmac.new(
        settings.SECRET_KEY.encode(), str(ident).encode(), hashlib.sha256
    ).hexdigest()[:32]
    index = int(time.time() // window)
    expires_at = datetime.fromtimestamp((index + 1) * window, tz=dt_timezone.utc)
    return f"{scope}:{digest}:{index}", expires_at


def count(scope, ident, window):
    key, _ = _bucket(scope, ident, window)
    return RateLimit.objects.filter(key=key).values_list("count", flat=True).first() or 0


def record(scope, ident, window):
    """Sayacı bir artırır ve yeni değeri döndürür."""
    key, expires_at = _bucket(scope, ident, window)
    bump = lambda: RateLimit.objects.filter(key=key).update(count=F("count") + 1)  # noqa: E731
    if not bump():
        try:
            with transaction.atomic():
                RateLimit.objects.create(key=key, count=1, expires_at=expires_at)
        except IntegrityError:
            # Aynı anda iki istek satırı oluşturmaya çalıştıysa diğeri kazandı.
            bump()
    if random.random() < CLEANUP_PROBABILITY:
        RateLimit.objects.filter(expires_at__lt=timezone.now()).delete()
    return count(scope, ident, window)


def is_limited(scope, ident, rule):
    """Sınıra ulaşılmış mı? (sayacı artırmaz)"""
    limit, window = rule
    return count(scope, ident, window) >= limit


def hit(scope, ident, rule):
    """Sayacı artırır; bu istekle sınır aşıldıysa True döner."""
    limit, window = rule
    return record(scope, ident, window) > limit
