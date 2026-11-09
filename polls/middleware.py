import re
import uuid

from django.conf import settings

VOTER_COOKIE_NAME = "voting_projects_voter"
VOTER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 yıl
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")


class VoterTokenMiddleware:
    """Her tarayıcıya kalıcı, rastgele bir oy token'ı verir."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.COOKIES.get(VOTER_COOKIE_NAME, "")
        is_new = not _TOKEN_RE.match(token)
        if is_new:
            token = uuid.uuid4().hex
        request.voter_token = token
        request.voter_token_is_new = is_new

        response = self.get_response(request)

        if is_new:
            response.set_cookie(
                VOTER_COOKIE_NAME,
                token,
                max_age=VOTER_COOKIE_MAX_AGE,
                httponly=True,
                samesite="Lax",
                secure=not settings.DEBUG,
            )
        return response
