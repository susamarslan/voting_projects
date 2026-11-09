from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

PASSWORD = "Kararsiz-Parola-42"


def register_data(**overrides):
    data = {
        "email": "ali@example.com",
        "username": "ali",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


class RegisterTests(TestCase):
    url = reverse("register")

    def test_successful_register_logs_in_and_redirects_home(self):
        response = self.client.post(self.url, register_data(email="Ali@Example.COM"))
        self.assertRedirects(response, "/")
        user = User.objects.get(username="ali")
        self.assertEqual(user.email, "ali@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_rejected_case_insensitive(self):
        User.objects.create_user("ali@example.com", "ali", PASSWORD)
        response = self.client.post(
            self.url, register_data(email="ALI@example.com", username="baska")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "email", "Bu e-posta adresiyle zaten bir hesap var."
        )
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_username_rejected_case_insensitive(self):
        User.objects.create_user("ali@example.com", "Ali", PASSWORD)
        response = self.client.post(
            self.url, register_data(email="baska@example.com", username="ali")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "username", "Bu kullanıcı adı zaten alınmış."
        )
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_usernames_rejected(self):
        for username in ["ab", "a" * 21, "ali veli", "ali-veli", "çiğdem"]:
            with self.subTest(username=username):
                response = self.client.post(self.url, register_data(username=username))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors.get("username"))
        self.assertFalse(User.objects.exists())

    def test_weak_password_rejected(self):
        response = self.client.post(
            self.url, register_data(password1="12345678", password2="12345678")
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors.get("password2"))
        self.assertFalse(User.objects.exists())

    def test_authenticated_user_redirected_away(self):
        user = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(self.url), "/")
        self.assertRedirects(self.client.get(reverse("login")), "/")


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ali@example.com", "ali", PASSWORD)

    def test_login_with_email(self):
        response = self.client.post(
            reverse("login"), {"username": "ALI@example.com", "password": PASSWORD}
        )
        self.assertRedirects(response, "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_wrong_password(self):
        response = self.client.post(
            reverse("login"), {"username": "ali@example.com", "password": "yanlis"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "E-posta veya parola hatalı.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_respects_next(self):
        response = self.client.post(
            reverse("login") + "?next=/admin/",
            {"username": "ali@example.com", "password": PASSWORD, "next": "/admin/"},
        )
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, "/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_topbar_shows_username_but_never_email(self):
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertContains(response, "@ali")
        self.assertNotContains(response, "ali@example.com")
