from django.http import JsonResponse
from django.http import HttpRequest as Request


def root(_: Request) -> JsonResponse:
    """Echoes an ok status for the root page.

    Args:
        _ (Request): The request object.

    Returns:
        JsonResponse: Return a JSON indicating an ok status
    """
    return JsonResponse({'status': 'ok'})
