from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PollForm
from .models import Poll

POLLS_PER_PAGE = 20


def poll_queryset():
    """Kartlar için gereken her şeyi sabit sayıda sorguyla getirir (N+1 yok).

    order_by açıkça verilir: Django, GROUP BY içeren (annotate+Count) sorgularda
    Meta.ordering'i uygulamaz.
    """
    return (
        Poll.objects.select_related("author")
        .prefetch_related("options")
        .annotate(total_votes=Count("votes"))
        .order_by("-created_at", "-pk")
    )


def feed(request):
    polls = poll_queryset().filter(is_active=True)
    page = Paginator(polls, POLLS_PER_PAGE).get_page(request.GET.get("sayfa"))
    return render(request, "polls/feed.html", {"page": page})


def poll_detail(request, pk):
    poll = get_object_or_404(poll_queryset(), pk=pk)
    return render(request, "polls/detail.html", {"poll": poll})


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
    polls = poll_queryset().filter(author=request.user)
    page = Paginator(polls, POLLS_PER_PAGE).get_page(request.GET.get("sayfa"))
    return render(request, "polls/my_polls.html", {"page": page})


@login_required
@require_POST
def poll_delete(request, pk):
    # Başkasının anketi için 404 döner; anketin varlığı bile sızdırılmaz.
    poll = get_object_or_404(Poll, pk=pk, author=request.user)
    poll.delete()
    messages.info(request, "Anket silindi.")
    return redirect("polls:my_polls")
