from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Option, Poll, Vote
from .templatetags.poll_extras import relative_time, time_left

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

    def test_feed_shows_everyones_polls_newest_first_without_emails(self):
        old = make_poll(self.ali, question="Eski anket sorusu")
        Poll.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
        make_poll(self.ayse, question="Yeni anket sorusu")
        closed = make_poll(self.ali, question="Kapalı anket sorusu", is_active=False)
        Poll.objects.filter(pk=closed.pk).update(created_at=timezone.now() - timedelta(days=2))

        response = self.client.get("/")
        questions = [p.question for p in response.context["page"]]
        # Kapanmış anketler de akışta kalır (sonuçlarıyla, "Kapandı" etiketiyle).
        self.assertEqual(questions, ["Yeni anket sorusu", "Eski anket sorusu", "Kapalı anket sorusu"])
        self.assertContains(response, "Kapandı")
        self.assertContains(response, "@ali")
        self.assertContains(response, "@ayse")
        self.assertNotContains(response, "@example.com")

    def test_feed_query_count_does_not_grow_with_polls(self):
        for i in range(5):
            make_poll(self.ali, question=f"Anket numarası {i}")
        with self.assertNumQueries(4):  # sayım + anketler + seçenekler + kullanıcının oyları
            self.client.get("/")
        for i in range(5):
            make_poll(self.ayse, question=f"Başka anket {i}")
            Vote.objects.create(poll=Poll.objects.first(), option=Option.objects.first(), voter_token=f"t{i}")
        with self.assertNumQueries(4):
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
        self.assertContains(response, '<span class="total-count">1</span> oy', html=False)
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


class VoteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        self.member = User.objects.create_user("ayse@example.com", "ayse", PASSWORD)
        self.poll = make_poll(self.owner, options=("Sinema", "Restoran", "Evde kal"))
        self.sinema, self.restoran, self.evde = self.poll.options.all()
        self.url = reverse("polls:vote", args=[self.poll.pk])
        self.client.get("/")  # tarayıcı çerezini (voter token) oluştur

    def vote_json(self, option, client=None):
        client = client or self.client
        return client.post(
            self.url, {"option_id": option.pk}, HTTP_ACCEPT="application/json"
        )

    def test_voter_cookie_is_set(self):
        cookie = self.client.cookies["voting_projects_voter"]
        self.assertRegex(cookie.value, r"^[0-9a-f]{32}$")
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    def test_guest_votes_once_and_second_vote_moves_it(self):
        response = self.vote_json(self.sinema)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["changed"])
        vote = Vote.objects.get()
        self.assertIsNone(vote.user)
        self.assertEqual(vote.voter_token, self.client.cookies["voting_projects_voter"].value)

        response = self.vote_json(self.restoran)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["changed"])
        self.assertEqual(response.json()["message"], "Oyun güncellendi 🔄")
        self.assertEqual(Vote.objects.get().option, self.restoran)

    def test_same_option_again_changes_nothing(self):
        self.vote_json(self.sinema)
        response = self.vote_json(self.sinema)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["changed"])
        self.assertEqual(Vote.objects.get().option, self.sinema)

    def test_guest_without_cookie_rejected(self):
        fresh = self.client_class()
        response = self.vote_json(self.sinema, client=fresh)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Vote.objects.exists())

    def test_member_can_vote_once_across_browsers(self):
        self.client.force_login(self.member)
        self.assertEqual(self.vote_json(self.sinema).status_code, 200)
        self.assertEqual(Vote.objects.get().user, self.member)

        other_browser = self.client_class()
        other_browser.get("/")
        other_browser.force_login(self.member)
        # İkinci tarayıcıdan yeni oy oluşmaz, mevcut oy taşınır.
        self.assertEqual(self.vote_json(self.restoran, client=other_browser).status_code, 200)
        self.assertEqual(Vote.objects.get().option, self.restoran)

    def test_guest_then_login_same_browser_cannot_vote_twice(self):
        self.assertEqual(self.vote_json(self.sinema).status_code, 200)
        self.client.force_login(self.member)
        self.assertEqual(self.vote_json(self.restoran).status_code, 200)
        self.assertEqual(Vote.objects.get().option, self.restoran)

    def test_member_then_logout_same_browser_cannot_vote_twice(self):
        self.client.force_login(self.member)
        self.assertEqual(self.vote_json(self.sinema).status_code, 200)
        self.client.post(reverse("logout"))
        self.assertEqual(self.vote_json(self.restoran).status_code, 200)
        self.assertEqual(Vote.objects.get().option, self.restoran)

    def test_option_from_other_poll_rejected(self):
        other = make_poll(self.owner, question="Başka bir anket")
        response = self.vote_json(other.options.first())
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        response = self.client.post(self.url, {"option_id": "abc"}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Vote.objects.exists())

    def test_inactive_poll_rejected(self):
        Poll.objects.filter(pk=self.poll.pk).update(is_active=False)
        self.assertEqual(self.vote_json(self.sinema).status_code, 403)

    def test_vote_requires_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_json_response_format_and_percentages(self):
        for i, option in enumerate([self.restoran, self.restoran]):
            Vote.objects.create(poll=self.poll, option=option, voter_token=f"other{i}")
        data = self.vote_json(self.sinema).json()
        self.assertEqual(
            data,
            {
                "ok": True,
                "message": "Oyun kaydedildi 🎉",
                "voted_option_id": self.sinema.pk,
                "changed": False,
                "show_results": True,
                "total_votes": 3,
                "options": [
                    {"id": self.sinema.pk, "text": "Sinema", "votes": 1, "percent": 33.3},
                    {"id": self.restoran.pk, "text": "Restoran", "votes": 2, "percent": 66.7},
                    {"id": self.evde.pk, "text": "Evde kal", "votes": 0, "percent": 0.0},
                ],
            },
        )

    def test_form_post_redirects_to_detail_with_message(self):
        response = self.client.post(self.url, {"option_id": self.sinema.pk}, follow=True)
        self.assertRedirects(response, self.poll.get_absolute_url())
        self.assertContains(response, "Oyun kaydedildi")
        self.assertContains(response, "Senin seçimin")

    def test_results_hidden_before_vote_and_shown_after(self):
        Vote.objects.create(poll=self.poll, option=self.restoran, voter_token="other")
        detail = self.poll.get_absolute_url()
        response = self.client.get(detail)
        self.assertContains(response, 'class="vote-form"')
        self.assertNotContains(response, "option-stats")

        self.vote_json(self.sinema)
        response = self.client.get(detail)
        # Anket açık olduğu için seçenekler oyu taşımak üzere tıklanabilir kalır.
        self.assertContains(response, 'class="vote-form"', count=3)
        self.assertContains(response, "%50,0 · 1 oy", count=2)
        self.assertContains(response, "Oyumu geri al")

    def test_owner_always_sees_results_and_can_vote(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.poll.get_absolute_url())
        self.assertContains(response, "option-stats")
        self.assertContains(response, 'class="vote-form"')
        self.assertEqual(self.vote_json(self.sinema).status_code, 200)

    def test_feed_marks_voted_polls(self):
        other = make_poll(self.owner, question="Oy verilmemiş anket")
        self.vote_json(self.sinema)
        polls = {p.pk: p for p in self.client.get("/").context["page"]}
        self.assertEqual(polls[self.poll.pk].voted_option_id, self.sinema.pk)
        self.assertTrue(polls[self.poll.pk].show_results)
        self.assertTrue(polls[other.pk].can_vote)
        self.assertFalse(polls[other.pk].show_results)


class VoteWithdrawTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        self.poll = make_poll(self.owner)
        self.sinema, self.restoran = self.poll.options.all()
        self.client.get("/")
        self.vote_url = reverse("polls:vote", args=[self.poll.pk])
        self.url = reverse("polls:vote_withdraw", args=[self.poll.pk])

    def vote(self, option):
        return self.client.post(self.vote_url, {"option_id": option.pk}, HTTP_ACCEPT="application/json")

    def withdraw(self):
        return self.client.post(self.url, HTTP_ACCEPT="application/json")

    def test_guest_can_withdraw_and_vote_again(self):
        Vote.objects.create(poll=self.poll, option=self.restoran, voter_token="other")
        self.vote(self.sinema)
        response = self.withdraw()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["voted_option_id"])
        self.assertFalse(data["show_results"])
        self.assertEqual(data["total_votes"], 1)
        # Oy geri alınınca sonuçlar yine gizli: seçeneklerde sayı/yüzde yok.
        self.assertEqual(
            data["options"],
            [{"id": self.sinema.pk, "text": "Sinema"}, {"id": self.restoran.pk, "text": "Restoran"}],
        )
        self.assertEqual(Vote.objects.count(), 1)
        response = self.client.get(self.poll.get_absolute_url())
        self.assertNotContains(response, "option-stats")
        self.assertNotContains(response, "Oyumu geri al")

        self.vote(self.restoran)
        self.assertEqual(Vote.objects.filter(option=self.restoran).count(), 2)

    def test_owner_withdraw_keeps_results(self):
        self.client.force_login(self.owner)
        self.vote(self.sinema)
        data = self.withdraw().json()
        self.assertTrue(data["show_results"])
        self.assertIn("percent", data["options"][0])

    def test_withdraw_without_vote(self):
        self.assertEqual(self.withdraw().status_code, 400)

    def test_withdraw_form_post_redirects(self):
        self.client.post(self.vote_url, {"option_id": self.sinema.pk})
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, self.poll.get_absolute_url())
        self.assertContains(response, "Oyun geri alındı.")
        self.assertFalse(Vote.objects.exists())

    def test_cannot_change_or_withdraw_on_closed_poll(self):
        self.vote(self.sinema)
        Poll.objects.filter(pk=self.poll.pk).update(is_active=False)
        self.assertEqual(self.withdraw().status_code, 403)
        self.assertEqual(self.vote(self.restoran).status_code, 403)
        self.assertEqual(Vote.objects.get().option, self.sinema)

    def test_withdraw_requires_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class PollDurationTests(TestCase):
    def setUp(self):
        self.ali = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        self.client.force_login(self.ali)

    def create(self, duration):
        return self.client.post(
            reverse("polls:create"),
            {"question": "Hangi film izlensin?", "options": ["A filmi", "B filmi"], "duration": duration},
        )

    def test_create_with_duration_sets_ends_at(self):
        before = timezone.now()
        self.create("24")
        poll = Poll.objects.get()
        self.assertAlmostEqual((poll.ends_at - before).total_seconds(), 24 * 3600, delta=60)
        self.assertTrue(poll.is_open)

    def test_default_is_unlimited(self):
        self.create("0")
        self.assertIsNone(Poll.objects.get().ends_at)

    def test_invalid_duration_rejected(self):
        response = self.create("5")
        self.assertContains(response, "Geçerli bir süre seç.")
        self.assertFalse(Poll.objects.exists())

    def test_expired_poll_is_closed_and_shows_results(self):
        poll = make_poll(self.ali, ends_at=timezone.now() - timedelta(minutes=1))
        self.assertFalse(poll.is_open)
        self.assertNotIn(poll, Poll.objects.open())
        guest = self.client_class()
        guest.get("/")
        response = guest.post(
            reverse("polls:vote", args=[poll.pk]),
            {"option_id": poll.options.first().pk},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 403)
        response = guest.get(poll.get_absolute_url())
        self.assertContains(response, "Süresi doldu")
        self.assertContains(response, "option-stats")
        self.assertNotContains(response, 'class="vote-form"')

    def test_open_poll_shows_time_left(self):
        make_poll(self.ali, ends_at=timezone.now() + timedelta(days=2, minutes=5))
        self.assertContains(self.client.get("/"), "2\xa0gün kaldı")  # timeuntil bölünmez boşluk kullanır
        self.assertEqual(time_left(timezone.now() + timedelta(seconds=30)), "1 dakikadan az kaldı")


class PollCloseTests(TestCase):
    def setUp(self):
        self.ali = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        self.ayse = User.objects.create_user("ayse@example.com", "ayse", PASSWORD)
        self.poll = make_poll(self.ali)
        self.close_url = reverse("polls:close", args=[self.poll.pk])
        self.reopen_url = reverse("polls:reopen", args=[self.poll.pk])

    def test_owner_can_close_and_reopen(self):
        self.client.force_login(self.ali)
        self.assertContains(self.client.get(self.poll.get_absolute_url()), "Anketi kapat")
        response = self.client.post(self.close_url, follow=True)
        self.assertRedirects(response, self.poll.get_absolute_url())
        self.assertContains(response, "Anket kapatıldı.")
        self.assertContains(response, "Yeniden aç")
        self.poll.refresh_from_db()
        self.assertFalse(self.poll.is_active)

        self.client.post(self.reopen_url)
        self.poll.refresh_from_db()
        self.assertTrue(self.poll.is_active)

    def test_close_returns_to_safe_next(self):
        self.client.force_login(self.ali)
        response = self.client.post(self.close_url, {"next": reverse("polls:my_polls")})
        self.assertRedirects(response, reverse("polls:my_polls"))
        response = self.client.post(self.reopen_url, {"next": "https://kotu.example.com/"})
        self.assertRedirects(response, self.poll.get_absolute_url())

    def test_expired_poll_cannot_be_reopened(self):
        Poll.objects.filter(pk=self.poll.pk).update(
            is_active=False, ends_at=timezone.now() - timedelta(hours=1)
        )
        self.client.force_login(self.ali)
        response = self.client.post(self.reopen_url, follow=True)
        self.assertContains(response, "Süresi dolan anket yeniden açılamaz.")
        self.poll.refresh_from_db()
        self.assertFalse(self.poll.is_active)

    def test_other_user_and_guest_cannot_close(self):
        self.client.force_login(self.ayse)
        self.assertNotContains(self.client.get(self.poll.get_absolute_url()), "Anketi kapat")
        self.assertEqual(self.client.post(self.close_url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.post(self.close_url).status_code, 302)  # girişe yönlendirir
        self.poll.refresh_from_db()
        self.assertTrue(self.poll.is_active)

    def test_close_requires_post(self):
        self.client.force_login(self.ali)
        self.assertEqual(self.client.get(self.close_url).status_code, 405)


class FeedSortTests(TestCase):
    def setUp(self):
        self.ali = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        now = timezone.now()

        def poll_at(question, days_ago, **kwargs):
            poll = make_poll(self.ali, question=question, **kwargs)
            Poll.objects.filter(pk=poll.pk).update(created_at=now - timedelta(days=days_ago))
            return poll

        self.old_popular = poll_at("Eski ama popüler", 2)
        self.mid = poll_at("Ortadaki anket", 1)
        self.new = poll_at("En yeni anket", 0)
        poll_at("Kapanmış anket", 3, is_active=False)
        for i in range(3):
            Vote.objects.create(
                poll=self.old_popular, option=self.old_popular.options.first(), voter_token=f"p{i}"
            )
        Vote.objects.create(poll=self.mid, option=self.mid.options.first(), voter_token="m")
        self.client.get("/")

    def questions(self, query=""):
        return [p.question for p in self.client.get("/" + query).context["page"]]

    def test_newest(self):
        self.assertEqual(
            self.questions(),
            ["En yeni anket", "Ortadaki anket", "Eski ama popüler", "Kapanmış anket"],
        )

    def test_popular(self):
        self.assertEqual(
            self.questions("?sirala=populer"),
            ["Eski ama popüler", "Ortadaki anket", "En yeni anket", "Kapanmış anket"],
        )

    def test_not_voted_excludes_voted_and_closed(self):
        self.client.post(
            reverse("polls:vote", args=[self.new.pk]),
            {"option_id": self.new.options.first().pk},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(
            self.questions("?sirala=oy-vermediklerim"), ["Ortadaki anket", "Eski ama popüler"]
        )

    def test_unknown_sort_falls_back_to_newest(self):
        self.assertEqual(self.client.get("/?sirala=xyz").context["sort"], "")

    def test_pagination_keeps_sort(self):
        for i in range(20):
            make_poll(self.ali, question=f"Ek anket {i}")
        response = self.client.get("/?sirala=populer")
        self.assertContains(response, "?sirala=populer&amp;sayfa=2")

    def test_sorted_feed_query_count(self):
        with self.assertNumQueries(4):
            self.client.get("/?sirala=oy-vermediklerim")
        with self.assertNumQueries(4):
            self.client.get("/?sirala=populer")


class OpenGraphTests(TestCase):
    def test_detail_has_share_preview_without_results(self):
        ali = User.objects.create_user("ali@example.com", "ali", PASSWORD)
        poll = make_poll(ali)
        Vote.objects.create(poll=poll, option=poll.options.first(), voter_token="x")
        response = self.client.get(poll.get_absolute_url())
        self.assertContains(
            response, '<meta property="og:title" content="Sinema mı restoran mı?">', html=False
        )
        self.assertContains(response, "Sinema · Restoran — Sen olsan hangisini seçerdin?")
        self.assertContains(response, f'content="http://testserver{poll.get_absolute_url()}"')
        self.assertContains(response, 'name="twitter:card" content="summary"')
        self.assertNotContains(response, "option-stats")
        self.assertNotContains(response, "ali@example.com")

    def test_feed_has_default_preview(self):
        response = self.client.get("/")
        self.assertContains(
            response, '<meta property="og:site_name" content="Kararsızım">', html=False
        )


class ErrorPageTests(TestCase):
    def test_404_page(self):
        # Test koşucusu DEBUG=False çalıştığından özel 404.html kullanılır.
        response = self.client.get("/olmayan-sayfa/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Bu sayfa da kararsız kalmış", status_code=404)

    def test_500_page_renders_without_context(self):
        from django.template.loader import render_to_string

        html = render_to_string("500.html")
        self.assertIn("sunucumuz da kararsız kaldı", html)
