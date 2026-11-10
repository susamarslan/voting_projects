from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import services
from .forms import PollForm
from .models import Option, Poll, Vote

POLLS_PER_PAGE = 20

# Akış sıralamaları: ?sirala= değeri → sekme adı. Boş değer "En yeni"dir.
FEED_SORTS = [
    ("", "En yeni"),
    ("populer", "En çok oy alan"),
    ("oy-vermediklerim", "Oy vermediklerim"),
]


def poll_queryset():
    """Kartlar için gereken her şeyi sabit sayıda sorguyla getirir (N+1 yok).

    order_by açıkça verilir: Django, GROUP BY içeren (annotate+Count) sorgularda
    Meta.ordering'i uygulamaz.
    """
    return (
        Poll.objects.select_related("author")
        .prefetch_related(Prefetch("options", queryset=services.options_with_counts()))
        .annotate(total_votes=Count("votes"))
        .order_by("-created_at", "-pk")
    )


def paginate(request, queryset):
    page = Paginator(queryset, POLLS_PER_PAGE).get_page(request.GET.get("sayfa"))
    page.object_list = services.decorate_polls(request, page.object_list)
    return page


def feed(request):
    sort = request.GET.get("sirala", "")
    if sort not in dict(FEED_SORTS):
        sort = ""
    queryset = poll_queryset()
    if sort == "populer":
        queryset = queryset.order_by("-total_votes", "-created_at", "-pk")
    elif sort == "oy-vermediklerim":
        voted = Vote.objects.filter(services.voter_filter(request)).values("poll_id")
        queryset = queryset.filter(pk__in=Poll.objects.open().values("pk")).exclude(pk__in=voted)
    page = paginate(request, queryset)
    return render(
        request, "polls/feed.html", {"page": page, "sort": sort, "sorts": FEED_SORTS}
    )


def poll_detail(request, pk):
    poll = get_object_or_404(poll_queryset(), pk=pk)
    services.decorate_polls(request, [poll])
    return render(request, "polls/detail.html", {"poll": poll})


def wants_json(request):
    return (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def json_or_redirect(request, poll, message, level=messages.SUCCESS, **data):
    if wants_json(request):
        return JsonResponse({"ok": True, "message": message, **data})
    messages.add_message(request, level, message)
    return redirect(poll)


def fail_response(request, poll, message, status):
    if wants_json(request):
        return JsonResponse({"ok": False, "error": message}, status=status)
    messages.error(request, message)
    return redirect(poll)


@require_POST
def vote(request, pk):
    """Oy verir; kişinin oyu zaten varsa seçilen seçeneğe taşır (plan 5. bölüm, Faz 6)."""
    poll = get_object_or_404(Poll, pk=pk)

    if not poll.is_open:
        return fail_response(request, poll, "Bu anket oylamaya kapalı.", 403)

    try:
        option = Option.objects.get(pk=int(request.POST.get("option_id", "")), poll=poll)
    except (ValueError, Option.DoesNotExist):
        return fail_response(request, poll, "Geçersiz seçenek.", 400)

    user = request.user if request.user.is_authenticated else None
    if user is None and request.voter_token_is_new:
        # Çerez yoksa her istekte yeni token oluşur; sınırsız oy olmasın diye reddedilir.
        return fail_response(
            request, poll, "Oy verebilmek için tarayıcında çerezlerin açık olmalı.", 400
        )

    existing = Vote.objects.filter(services.voter_filter(request), poll=poll)
    changed = False
    level = messages.SUCCESS
    if existing.exists():
        changed = existing.exclude(option=option).update(option=option) > 0
        message = "Oyun güncellendi 🔄" if changed else "Oyun zaten bu seçenekte."
        if not changed:
            level = messages.INFO
    else:
        try:
            with transaction.atomic():
                Vote.objects.create(
                    poll=poll, option=option, user=user, voter_token=request.voter_token
                )
        except IntegrityError:
            # Aynı anda gelen iki istekte veritabanı kısıtları ikinci oyu yakalar.
            return fail_response(request, poll, "Bu ankete zaten oy verdin.", 409)
        message = "Oyun kaydedildi 🎉"

    return json_or_redirect(
        request,
        poll,
        message,
        level=level,
        voted_option_id=option.pk,
        changed=changed,
        show_results=True,
        **services.poll_results(poll),
    )


@require_POST
def vote_withdraw(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    if not poll.is_open:
        return fail_response(request, poll, "Kapanmış ankette oy geri alınamaz.", 403)

    deleted, _ = Vote.objects.filter(services.voter_filter(request), poll=poll).delete()
    if not deleted:
        return fail_response(request, poll, "Bu ankete henüz oy vermedin.", 400)

    show_results = services.is_owner(request, poll)
    return json_or_redirect(
        request,
        poll,
        "Oyun geri alındı.",
        level=messages.INFO,
        voted_option_id=None,
        show_results=show_results,
        **services.poll_results(poll, show_results=show_results),
    )


@login_required
def poll_create(request):
    if request.method == "POST":
        form = PollForm(request.POST, options=request.POST.getlist("options"))
        if form.is_valid():
            poll = form.save(author=request.user)
            messages.success(request, "Anketin yayında! 🚀")
            return redirect(poll)
    else:
        form = PollForm()
    return render(request, "polls/create.html", {"form": form})


@login_required
def my_polls(request):
    page = paginate(request, poll_queryset().filter(author=request.user))
    return render(request, "polls/my_polls.html", {"page": page})


@login_required
@require_POST
def poll_delete(request, pk):
    # Başkasının anketi için 404 döner; anketin varlığı bile sızdırılmaz.
    poll = get_object_or_404(Poll, pk=pk, author=request.user)
    poll.delete()
    messages.info(request, "Anket silindi.")
    return redirect("polls:my_polls")


def redirect_back(request, fallback):
    """Formdaki güvenli `next` adresine, yoksa fallback'e döner."""
    target = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(fallback)


@login_required
@require_POST
def poll_close(request, pk):
    poll = get_object_or_404(Poll, pk=pk, author=request.user)
    if poll.is_active:
        poll.is_active = False
        poll.save(update_fields=["is_active"])
    messages.info(request, "Anket kapatıldı. Artık oy verilemez, sonuçları herkes görüyor.")
    return redirect_back(request, poll)


@login_required
@require_POST
def poll_reopen(request, pk):
    poll = get_object_or_404(Poll, pk=pk, author=request.user)
    if poll.is_expired:
        messages.error(request, "Süresi dolan anket yeniden açılamaz.")
    else:
        poll.is_active = True
        poll.save(update_fields=["is_active"])
        messages.success(request, "Anket yeniden oylamaya açıldı.")
    return redirect_back(request, poll)
