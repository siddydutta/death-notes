import logging

from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.views import View

from auth_app.clients.microsoft import REDIRECT_URI, SCOPES, get_user_info, msal_app


logger = logging.getLogger(__name__)


class MSLoginView(View):
    def get(self, request, *args, **kwargs):
        return redirect(
            msal_app.get_authorization_request_url(
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,
            )
        )


class MSLoginCallbackView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code')
        if code is None:
            logger.warning('[MICROSOFT CALLBACK] No code in request')
            return HttpResponseBadRequest()
        result = msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        access_token = result.get('access_token')
        if access_token is None:
            logger.warning(f'[MICROSOFT CALLBACK] No access token in result: {result}')
            return HttpResponseBadRequest()
        user_info = get_user_info(access_token)
        return JsonResponse(user_info)
