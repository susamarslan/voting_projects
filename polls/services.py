"""Oy kuralları ve sonuç hesapları (bkz. plan 4.4 ve 5. bölüm)."""

from django.db.models import Count, Q

from .models import Option, Vote


def voter_filter(request):
    """Bu isteği yapan kişinin oylarını bulan Q nesnesi.

    Üye: user VEYA bu tarayıcının token'ı (giriş/çıkışla ikinci oy engellenir).
    Misafir: yalnızca token.
    """
    condition = Q(voter_token=request.voter_token)
    if request.user.is_authenticated:
        condition |= Q(user=request.user)
    return condition


def get_user_vote(request, poll):
    return Vote.objects.filter(voter_filter(request), poll=poll).first()


def voted_option_ids(request, polls):
    """{poll_id: option_id} — verilen anketlerde kullanıcının oyları, tek sorguyla."""
    poll_ids = [poll.pk for poll in polls]
    if not poll_ids:
        return {}
    rows = Vote.objects.filter(voter_filter(request), poll_id__in=poll_ids).values_list(
        "poll_id", "option_id"
    )
    return dict(rows)


def percent(votes, total):
    return round(votes * 100 / total, 1) if total else 0.0


def poll_results(poll):
    """Her seçenek için oy sayısı ve yüzde (1 ondalık) + toplam oy."""
    options = list(poll.options.annotate(vote_count=Count("votes")).order_by("order", "pk"))
    total = sum(option.vote_count for option in options)
    return {
        "total_votes": total,
        "options": [
            {
                "id": option.pk,
                "text": option.text,
                "votes": option.vote_count,
                "percent": percent(option.vote_count, total),
            }
            for option in options
        ],
    }


def options_with_counts():
    """Prefetch için: her seçeneğe vote_count ekleyen queryset."""
    return Option.objects.annotate(vote_count=Count("votes")).order_by("order", "pk")


def decorate_polls(request, polls):
    """Şablonun ihtiyaç duyduğu durumları anket nesnelerine ekler.

    poll.voted_option_id, poll.can_vote, poll.show_results ve her seçenekte
    option.percent / option.is_choice. Sonuçlar yalnızca show_results ise
    şablona basılır; böylece oy vermeden önce sayfa kaynağında görünmez.
    """
    polls = list(polls)
    voted = voted_option_ids(request, polls)
    user = request.user
    for poll in polls:
        poll.voted_option_id = voted.get(poll.pk)
        is_owner = user.is_authenticated and poll.author_id == user.pk
        poll.can_vote = poll.is_active and poll.voted_option_id is None
        poll.show_results = poll.voted_option_id is not None or is_owner or not poll.is_active
        for option in poll.options.all():
            option.percent = percent(option.vote_count, poll.total_votes)
            option.is_choice = option.pk == poll.voted_option_id
    return polls
