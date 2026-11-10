from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render

from polls import ratelimit

from .forms import LoginForm, RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        ip = ratelimit.client_ip(request)
        # Sayılan şey oluşturulan hesaplar; formu yanlış dolduran kullanıcı cezalandırılmaz.
        if ratelimit.is_limited("register", ip, ratelimit.REGISTER):
            form.add_error(None, "Bu ağdan kısa sürede çok fazla hesap açıldı. Biraz sonra tekrar dene.")
            return render(request, "accounts/register.html", {"form": form}, status=429)
        if form.is_valid():
            user = form.save()
            ratelimit.record("register", ip, ratelimit.REGISTER[1])
            login(request, user)
            messages.success(request, f"Hoş geldin, @{user.username}! 🎉")
            return redirect("/")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        # Yalnızca başarısız denemeler sayılır; sınırdayken parola hiç denenmez.
        if ratelimit.is_limited("login_fail", ratelimit.client_ip(request), ratelimit.LOGIN_FAILURE):
            # Bağlı form kullanılmaz: form.errors'a erişmek authenticate()'i çalıştırırdı.
            form = self.get_form_class()(
                request, initial={"username": request.POST.get("username", "")}
            )
            context = self.get_context_data(
                form=form,
                limit_error="Çok fazla hatalı giriş denemesi. Lütfen 15 dakika sonra tekrar dene.",
            )
            return self.render_to_response(context, status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        ratelimit.record("login_fail", ratelimit.client_ip(self.request), ratelimit.LOGIN_FAILURE[1])
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Tekrar hoş geldin, @{form.get_user().username}!")
        return response


class LogoutView(auth_views.LogoutView):
    """Django 5'te LogoutView yalnızca POST kabul eder."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "Çıkış yaptın. Görüşmek üzere! 👋")
        return response
