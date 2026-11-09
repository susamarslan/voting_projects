from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import PollForm
from .models import Option, Poll, Vote

POLLS_PER_PAGE = 20


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
    page = paginate(request, poll_queryset().filter(is_active=True))
    return render(request, "polls/feed.html", {"page": page})


def poll_detail(request, pk):
    poll = get_object_or_404(poll_queryset(), pk=pk)
    services.decorate_polls(request, [poll])
    return render(request, "polls/detail.html", {"poll": poll})


def wants_json(request):
    return (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


@require_POST
def vote(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    as_json = wants_json(request)

    def fail(message, status):
        if as_json:
            return JsonResponse({"ok": False, "error": message}, status=status)
        messages.error(request, message)
        return redirect(poll)

    if not poll.is_active:
        return fail("Bu anket oylamaya kapalı.", 403)

    try:
        option = Option.objects.get(pk=int(request.POST.get("option_id", "")), poll=poll)
    except (ValueError, Option.DoesNotExist):
        return fail("Geçersiz seçenek.", 400)

    user = request.user if request.user.is_authenticated else None
    if user is None and request.voter_token_is_new:
        # Çerez yoksa her istekte yeni token oluşur; sınırsız oy olmasın diye reddedilir.
        return fail("Oy verebilmek için tarayıcında çerezlerin açık olmalı.", 400)

    if Vote.objects.filter(services.voter_filter(request), poll=poll).exists():
        return fail("Bu ankete zaten oy verdin.", 409)

    try:
        with transaction.atomic():
            Vote.objects.create(
                poll=poll, option=option, user=user, voter_token=request.voter_token
            )
    except IntegrityError:
        # Aynı anda gelen iki istekte veritabanı kısıtları ikinci oyu yakalar.
        return fail("Bu ankete zaten oy verdin.", 409)

    if as_json:
        return JsonResponse({"ok": True, "voted_option_id": option.pk, **services.poll_results(poll)})
    messages.success(request, "Oyun kaydedildi 🎉")
    return redirect(poll)


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
