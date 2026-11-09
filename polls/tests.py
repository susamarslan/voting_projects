from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Option, Poll, Vote
from .templatetags.poll_extras import relative_time

User = get_user_model()

PASSWORD = "Kararsiz-Parola-42"


def make_poll(author, question="Sinema mı restoran mı?", options=("Sinema", "Restoran"), **kwargs):
    poll = Poll.objects.create(author=author, question=question, **kwargs)
    for index, text in enumerate(options):
        Option.objects.create(poll=poll, text=text, order=index)
    return poll


class PollCreateTests(TestCase):
    url = reverse("polls:create")

    def setUp(self):
        self.user = User.objects.create_user("ali@example.com", "ali", PASSWORD)

    def post(self, options, question="Bugün ne yapsam?", description=""):
        self.client.force_login(self.user)
        return self.client.post(
            self.url, {"question": question, "description": description, "options": options}
        )

    def test_guest_redirected_to_login_with_next(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_create_poll_success(self):
        response = self.post(["  Sinema ", "Restoran", "", "Evde kal"])
        poll = Poll.objects.get()
        self.assertRedirects(response, poll.get_absolute_url())
        self.assertEqual(poll.author, self.user)
        self.assertEqual(
            list(poll.options.values_list("text", "order")),
            [("Sinema", 0), ("Restoran", 1), ("Evde kal", 2)],
        )

    def test_one_option_rejected(self):
        response = self.post(["Sinema", "", ""])
        self.assertEqual(response.status_code, 200)
        self.assertIn("En az 2 seçenek girmelisin.", response.context["form"].option_errors)
        self.assertFalse(Poll.objects.exists())

    def test_six_options_rejected(self):
        response = self.post(["A1", "B2", "C3", "D4", "E5", "F6"])
        self.assertEqual(response.status_code, 200)
        self.assertIn("En fazla 5 seçenek girebilirsin.", response.context["form"].option_errors)
        self.assertFalse(Poll.objects.exists())

    def test_duplicate_option_rejected_case_and_space_insensitive(self):
        response = self.post(["Sinema", "  sİNEMA".replace("İ", "I") + " "])
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Aynı seçeneği birden fazla kez yazamazsın.", response.context["form"].option_errors
        )
        self.assertFalse(Poll.objects.exists())

    def test_short_question_rejected_and_values_kept(self):
        response = self.post(["Sinema", "Restoran"], question="Ne?")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors.get("question"))
        self.assertContains(response, 'value="Sinema"')
        self.assertContains(response, 'value="Restoran"')
        self.assertFalse(Poll.objects.exists())


class FeedAndDetailTests(TestCase):
    def setUp(self):
        self.ali = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        self.ayse = User.objects.create_user("ayse@example.com", "ayse", PASSWORD)

    def test_empty_feed_message(self):
        response = self.client.get("/")
        self.assertContains(response, "Burası çok sessiz")

    def test_feed_shows_everyones_active_polls_newest_first_without_emails(self):
        old = make_poll(self.ali, question="Eski anket sorusu")
        Poll.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        make_poll(self.ayse, question="Yeni anket sorusu")
        make_poll(self.ali, question="Kapalı anket sorusu", is_active=False)

        response = self.client.get("/")
        questions = [p.question for p in response.context["page"]]
        self.assertEqual(questions, ["Yeni anket sorusu", "Eski anket sorusu"])
        self.assertContains(response, "@ali")
        self.assertContains(response, "@ayse")
        self.assertNotContains(response, "@example.com")

    def test_feed_query_count_does_not_grow_with_polls(self):
        for i in range(5):
            make_poll(self.ali, question=f"Anket numarası {i}")
        with self.assertNumQueries(3):  # sayım + anketler + seçenekler
            self.client.get("/")
        for i in range(5):
            make_poll(self.ayse, question=f"Başka anket {i}")
        with self.assertNumQueries(3):
            self.client.get("/")

    def test_feed_paginates_by_20(self):
        for i in range(21):
            make_poll(self.ali, question=f"Anket numarası {i}")
        self.assertEqual(len(self.client.get("/").context["page"]), 20)
        self.assertEqual(len(self.client.get("/?sayfa=2").context["page"]), 1)

    def test_detail_page(self):
        poll = make_poll(self.ali, description="Akşam için karar veremedim.")
        Vote.objects.create(poll=poll, option=poll.options.first(), voter_token="abc")
        response = self.client.get(poll.get_absolute_url())
        self.assertContains(response, poll.question)
        self.assertContains(response, "Akşam için karar veremedim.")
        self.assertContains(response, "1 oy")
        self.assertNotContains(response, "ali@example.com")

    def test_detail_404(self):
        self.assertEqual(self.client.get(reverse("polls:detail", args=[999])).status_code, 404)


class MyPollsAndDeleteTests(TestCase):
    def setUp(self):
        self.ali = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        self.ayse = User.objects.create_user("ayse@example.com", "ayse", PASSWORD)
        self.poll = make_poll(self.ali)

    def test_my_polls_lists_only_own_polls(self):
        make_poll(self.ayse, question="Ayşe'nin anketi")
        self.client.force_login(self.ali)
        response = self.client.get(reverse("polls:my_polls"))
        self.assertEqual(list(response.context["page"]), [self.poll])

    def test_my_polls_requires_login(self):
        response = self.client.get(reverse("polls:my_polls"))
        self.assertEqual(response.status_code, 302)

    def test_owner_can_delete(self):
        self.client.force_login(self.ali)
        response = self.client.post(reverse("polls:delete", args=[self.poll.pk]))
        self.assertRedirects(response, reverse("polls:my_polls"))
        self.assertFalse(Poll.objects.exists())

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.ayse)
        response = self.client.post(reverse("polls:delete", args=[self.poll.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Poll.objects.filter(pk=self.poll.pk).exists())

    def test_delete_requires_post(self):
        self.client.force_login(self.ali)
        response = self.client.get(reverse("polls:delete", args=[self.poll.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Poll.objects.exists())


class VoteConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        self.poll = make_poll(self.user)
        self.option = self.poll.options.first()

    def test_vote_needs_user_or_token(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vote.objects.create(poll=self.poll, option=self.option)

    def test_same_token_cannot_vote_twice(self):
        Vote.objects.create(poll=self.poll, option=self.option, voter_token="t1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vote.objects.create(poll=self.poll, option=self.option, voter_token="t1")

    def test_same_user_cannot_vote_twice(self):
        Vote.objects.create(poll=self.poll, option=self.option, user=self.user, voter_token="t1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vote.objects.create(poll=self.poll, option=self.option, user=self.user, voter_token="t2")


class RelativeTimeTests(TestCase):
    def test_relative_time(self):
        now = timezone.now()
        self.assertEqual(relative_time(now), "az önce")
        # timesince sayı ile birim arasında bölünmez boşluk (\xa0) kullanır.
        self.assertEqual(relative_time(now - timedelta(hours=3, minutes=20)), "3\xa0saat önce")
        self.assertEqual(relative_time(now - timedelta(days=2, hours=5)), "2\xa0gün önce")
