"""Stream type classes for tap-frontapp."""

from __future__ import annotations

import typing as t
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from singer_sdk import typing as th

from tap_frontapp.client import FrontAppStream

if t.TYPE_CHECKING:
    from singer_sdk.helpers.types import Context


class EventsStream(FrontAppStream):
    """Define custom stream."""

    name = "events"
    path = "/events"
    primary_keys: t.ClassVar[list[str]] = ["id"]
    replication_key = None
    records_jsonpath = "$._results[*]"
    next_page_token_jsonpath = "$._pagination.next"
    """
    Events are sorted according to the time the event is created on (in reverse chronological order),
    but filtered (through the q query parameter) based on the emission time.
    That is, the creation date determines how event information
    is initially returned to you via the API, but if you use the q query string
    to filter on before and after timeframes, then the filter applies
    to the emission date instead of the creation date.
    In most cases these dates are the same, but they can differ in some situations.

    https://dev.frontapp.com/reference/events
    """
    is_sorted = False
    schema = th.PropertiesList(
        th.Property(
            "_links",
            th.ObjectType(
                th.Property("self", th.StringType),
            ),
        ),
        th.Property(
            "id",
            th.StringType,
        ),
        th.Property("type", th.StringType),
        th.Property("emitted_at", th.NumberType),
        th.Property("emitted_timestamp", th.DateTimeType),
        th.Property("conversation", th.ObjectType(additional_properties=True)),
        th.Property("source", th.ObjectType(additional_properties=True)),
        th.Property("target", th.ObjectType(additional_properties=True)),
    ).to_dict()

    def get_url_params(
        self,
        context: Context | None,
        next_page_token: t.Any | None,  # noqa: ANN401
    ) -> dict[str, t.Any]:
        """Return a dictionary of values to be used in URL parameterization.

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary of URL query parameters.
        """
        params: dict = {}
        if next_page_token:
            parsed_url = urlparse(next_page_token)
            params = parse_qs(parsed_url.query)
        else:
            params["sort_order"] = self.config.get("sort_order")
            params["limit"] = self.config.get("limit")
            if self.config.get("q_types") is not None:
                params["q[types]"] = self.config.get("q_types")
            if self.config.get("q_after") is not None:
                params["q[after]"] = self.config.get("q_after")
            if self.config.get("q_before") is not None:
                params["q[before]"] = self.config.get("q_before")
        return params

    def post_process(
        self,
        row: dict,
        context: dict | None = None,  # noqa: ARG002
    ) -> dict | None:
        emitted_at = float(row.get("emitted_at"))  # type: ignore[arg-type]
        emitted_timestamp = datetime.fromtimestamp(
            emitted_at, tz=timezone.utc
        ).isoformat()
        return {"emitted_timestamp": emitted_timestamp, **row}
