from django import forms
from django.db import transaction

from .models import MAX_OPTIONS, MIN_OPTIONS, Option, Poll

OPTION_MAX_LENGTH = Option._meta.get_field("text").max_length


class PollForm(forms.ModelForm):
    """Soru + açıklama ModelForm alanlarıyla; seçenekler `options` adlı çoklu input'tan gelir."""

    question = forms.CharField(
        label="Soru",
        min_length=5,
        max_length=200,
        error_messages={
            "required": "Soru zorunludur.",
            "min_length": "Soru en az 5 karakter olmalı.",
            "max_length": "Soru en fazla 200 karakter olabilir.",
        },
        widget=forms.TextInput(attrs={"placeholder": "Bugün sinemaya mı gitsem, restorana mı?"}),
    )
    description = forms.CharField(
        label="Açıklama (opsiyonel)",
        required=False,
        max_length=500,
        error_messages={"max_length": "Açıklama en fazla 500 karakter olabilir."},
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Biraz detay ver..."}),
    )

    class Meta:
        model = Poll
        fields = ("question", "description")

    def __init__(self, *args, options=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Kullanıcının girdiği ham değerler (hata durumunda formu geri doldurmak için).
        self.raw_options = list(options or [])
        self.option_errors = []
        self.cleaned_options = []

    def clean(self):
        cleaned = super().clean()
        options = [text.strip() for text in self.raw_options if text and text.strip()]

        if len(options) < MIN_OPTIONS:
            self.option_errors.append(f"En az {MIN_OPTIONS} seçenek girmelisin.")
        elif len(options) > MAX_OPTIONS:
            self.option_errors.append(f"En fazla {MAX_OPTIONS} seçenek girebilirsin.")

        if any(len(text) > OPTION_MAX_LENGTH for text in options):
            self.option_errors.append(
                f"Her seçenek en fazla {OPTION_MAX_LENGTH} karakter olabilir."
            )

        keys = [text.casefold() for text in options]
        if len(set(keys)) != len(keys):
            self.option_errors.append("Aynı seçeneği birden fazla kez yazamazsın.")

        if not self.option_errors:
            self.cleaned_options = options
        return cleaned

    def is_valid(self):
        # Seçenek hataları ModelForm alanı olmadığından ayrıca tutulur
        # ve şablonda seçeneklerin altında gösterilir.
        return super().is_valid() and not self.option_errors

    def option_values(self):
        """Şablonda gösterilecek en az MAX_OPTIONS uzunluğunda değer listesi."""
        values = self.raw_options[:MAX_OPTIONS]
        return values + [""] * (MAX_OPTIONS - len(values))

    @transaction.atomic
    def save(self, author):
        poll = super().save(commit=False)
        poll.author = author
        poll.save()
        Option.objects.bulk_create(
            Option(poll=poll, text=text, order=index)
            for index, text in enumerate(self.cleaned_options)
        )
        return poll
