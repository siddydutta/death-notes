from urllib.parse import parse_qs, urlencode, urlparse

from rest_framework.pagination import LimitOffsetPagination


class CustomLimitOffsetPagination(LimitOffsetPagination):
    def _format_link(self, url):
        if not url:
            return None
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        return '?' + urlencode(query_params, doseq=True)

    def get_next_link(self):
        return self._format_link(super().get_next_link())

    def get_previous_link(self):
        return self._format_link(super().get_previous_link())
