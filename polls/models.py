from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

MIN_OPTIONS = 2
MAX_OPTIONS = 5


class PollQuerySet(models.QuerySet):
    def open(self):
        """Oylamaya açık anketler: aktif ve süresi dolmamış."""
        return self.filter(is_active=True).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gt=timezone.now())
        )


class Poll(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="polls",
        verbose_name="sahibi",
    )
    question = models.CharField(
        "soru", max_length=200, validators=[MinLengthValidator(5)]
    )
    description = models.TextField("açıklama", max_length=500, blank=True)
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True)
    is_active = models.BooleanField("aktif", default=True)
    ends_at = models.DateTimeField("bitiş", null=True, blank=True)

    objects = PollQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "anket"
        verbose_name_plural = "anketler"

    def __str__(self):
        return self.question

    def get_absolute_url(self):
        return reverse("polls:detail", args=[self.pk])

    @property
    def is_expired(self):
        return self.ends_at is not None and self.ends_at <= timezone.now()

    @property
    def is_open(self):
        """Oylamaya açık mı? (sahibi kapatmadı ve süresi dolmadı)"""
        return self.is_active and not self.is_expired


class Option(models.Model):
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name="options", verbose_name="anket"
    )
    text = models.CharField("seçenek", max_length=100)
    order = models.PositiveSmallIntegerField("sıra", default=0)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "seçenek"
        verbose_name_plural = "seçenekler"
        constraints = [
            models.UniqueConstraint(fields=["poll", "order"], name="polls_option_unique_order"),
        ]

    def __str__(self):
        return self.text


class Vote(models.Model):
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name="votes", verbose_name="anket"
    )
    option = models.ForeignKey(
        Option, on_delete=models.CASCADE, related_name="votes", verbose_name="seçenek"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="votes",
        verbose_name="üye",
    )
    # Oyun verildiği tarayıcının çerez token'ı; üye oylarında da kaydedilir (bkz. plan 4.4).
    voter_token = models.CharField("tarayıcı token'ı", max_length=64, null=True, blank=True)
    created_at = models.DateTimeField("oy zamanı", auto_now_add=True)

    class Meta:
        verbose_name = "oy"
        verbose_name_plural = "oylar"
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "user"],
                condition=Q(user__isnull=False),
                name="polls_vote_unique_user",
            ),
            models.UniqueConstraint(
                fields=["poll", "voter_token"],
                condition=Q(voter_token__isnull=False),
                name="polls_vote_unique_token",
            ),
            models.CheckConstraint(
                condition=Q(user__isnull=False) | Q(voter_token__isnull=False),
                name="polls_vote_has_voter",
            ),
        ]

    def __str__(self):
        return f"{self.poll_id} → {self.option_id}"
