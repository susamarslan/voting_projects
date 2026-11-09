from django.contrib import admin
from django.db.models import Count

from .models import Option, Poll, Vote


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0
    max_num = 5


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ("question", "author", "created_at", "is_active", "vote_count")
    list_filter = ("is_active", "created_at")
    search_fields = ("question", "author__username")
    raw_id_fields = ("author",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("author").annotate(
            _vote_count=Count("votes")
        )

    @admin.display(description="oy", ordering="_vote_count")
    def vote_count(self, obj):
        return obj._vote_count


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("poll", "option", "user", "voter_token", "created_at")
    list_select_related = ("poll", "option", "user")
    readonly_fields = ("poll", "option", "user", "voter_token", "created_at")
