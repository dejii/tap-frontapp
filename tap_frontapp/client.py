"""REST client handling, including FrontAppStream base class."""

from __future__ import annotations

import decimal
import logging
import time
import typing as t
from http import HTTPStatus

from singer_sdk.authenticators import BearerTokenAuthenticator
from singer_sdk.exceptions import FatalAPIError, RetriableAPIError
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream

if t.TYPE_CHECKING:
    import requests


class FrontAppStream(RESTStream):
    """FrontApp stream class."""

    records_jsonpath = "$[*]"

    next_page_token_jsonpath = "$.next_page"  # noqa: S105

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return self.config.get("api_url")

    @property
    def authenticator(self) -> BearerTokenAuthenticator:
        """Return a new authenticator object.

        Returns:
            An authenticator instance.
        """
        return BearerTokenAuthenticator.create_for_stream(
            self,
            token=self.config.get("api_key", ""),
        )

    def parse_response(self, response: requests.Response) -> t.Iterable[dict]:
        """Parse the response and return an iterator of result records.

        Args:
            response: The HTTP ``requests.Response`` object.

        Yields:
            Each record from the source.
        """
        yield from extract_jsonpath(
            self.records_jsonpath,
            input=response.json(parse_float=decimal.Decimal),
        )

    def validate_response(self, response: requests.Response) -> None:
        """Validate HTTP response.

        Checks for error status codes and whether they are fatal or retriable.

        Args:
            response: A :class:`requests.Response` object.

        Raises:
            FatalAPIError: If the request is not retriable.
            RetriableAPIError: If the request is retriable.
        """
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            msg = self.response_error_message(response)
            raise RetriableAPIError(msg, response)

        if (
            HTTPStatus.BAD_REQUEST
            <= response.status_code
            < HTTPStatus.INTERNAL_SERVER_ERROR
        ) and response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
            msg = self.response_error_message(response)
            raise FatalAPIError(msg)

        # By default, Front's API rate limit starts at 50 requests per minute and varies depending on your plan.
        # Rate limits are enforced on a per-company basis rather than a per-token basis.
        # https://dev.frontapp.com/docs/rate-limiting

        rate_limit_remaining = int(response.headers.get("x-ratelimit-remaining"))  # type: ignore[arg-type]
        rate_limit_reset = float(response.headers.get("x-ratelimit-reset"))  # type: ignore[arg-type]
        rate_limit_limit = int(response.headers.get("x-ratelimit-limit"))  # type: ignore[arg-type]
        rate_limit_used = rate_limit_limit - rate_limit_remaining
        rate_limit_used_pct = (rate_limit_used / rate_limit_limit) * 100
        current_time_seconds = int(time.time())
        rate_limit_quota_pct = self.config.get("rate_limit_quota_pct")

        if (
            response.status_code == HTTPStatus.OK
            and rate_limit_used_pct > rate_limit_quota_pct
        ):
            seconds_to_wait = rate_limit_reset - current_time_seconds
            seconds_to_wait = abs(seconds_to_wait) + 10
            logging.warning(
                f"Approximately {round(rate_limit_used_pct, 2)}% of the rate limit has been used. Sleeping for {seconds_to_wait} seconds to reset the rate limit. Rate limit quota: {rate_limit_quota_pct}%, Rate limit used: {rate_limit_used} requests, Rate limit limit: {rate_limit_limit} requests"
            )
            time.sleep(seconds_to_wait)

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            msg = self.response_error_message(response)
            retry_after = float(response.headers.get("retry-after"))  # type: ignore[arg-type]
            logging.warning(f"Rate limit exceeded. Sleeping for {retry_after} seconds")
            time.sleep(retry_after)
            raise RetriableAPIError(msg, response)
