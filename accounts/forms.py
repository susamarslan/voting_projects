import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm

from .models import User

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


class RegisterForm(BaseUserCreationForm):
    """E-posta + kullanıcı adı + parola ile kayıt formu."""

    email = forms.EmailField(
        label="E-posta",
        max_length=254,
        error_messages={
            "required": "E-posta adresi zorunludur.",
            "invalid": "Geçerli bir e-posta adresi gir.",
        },
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    username = forms.CharField(
        label="Kullanıcı adı",
        max_length=20,
        help_text="3–20 karakter; yalnızca harf, rakam ve _.",
        error_messages={
            "required": "Kullanıcı adı zorunludur.",
            "max_length": "Kullanıcı adı en fazla 20 karakter olabilir.",
        },
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )

    class Meta:
        model = User
        fields = ("email", "username")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Parola"
        self.fields["password2"].label = "Parola (tekrar)"
        self.fields["password2"].help_text = ""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu e-posta adresiyle zaten bir hesap var.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if len(username) < 3:
            raise forms.ValidationError("Kullanıcı adı en az 3 karakter olmalı.")
        if not USERNAME_RE.match(username):
            raise forms.ValidationError(
                "Kullanıcı adı yalnızca harf, rakam ve _ içerebilir."
            )
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Bu kullanıcı adı zaten alınmış.")
        return username


class LoginForm(AuthenticationForm):
    """E-posta + parola ile giriş formu."""

    username = forms.EmailField(
        label="E-posta",
        error_messages={
            "required": "E-posta adresi zorunludur.",
            "invalid": "Geçerli bir e-posta adresi gir.",
        },
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    error_messages = {
        "invalid_login": "E-posta veya parola hatalı.",
        "inactive": "Bu hesap aktif değil.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].label = "Parola"
