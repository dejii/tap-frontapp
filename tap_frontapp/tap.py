"""FrontApp tap class."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_frontapp import streams


class TapFrontApp(Tap):
    """FrontApp tap class."""

    name = "tap-frontapp"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType(nullable=False),
            required=True,
            secret=True,  # Flag config as protected.
            title="API Key",
            description="The API key to authenticate against the API service",
        ),
        th.Property(
            "q_types",
            th.ArrayType(th.StringType(), nullable=True),
            required=False,
            title="Types",
            description="Types to filter events. See https://dev.frontapp.com/reference/list-events",
        ),
        th.Property(
            "limit",
            th.IntegerType(minimum=1, maximum=15, nullable=True),
            default=15,
            title="Limit",
            description="Max number of results per page (max 15)",
        ),
        th.Property(
            "rate_limit_quota_pct",
            th.IntegerType(minimum=0, maximum=100, nullable=False),
            default=100,
            title="Rate Limit Quota Percentage",
            description="Percentage of the rate limit to use",
        ),
        th.Property(
            "sort_order",
            th.StringType(allowed_values=["asc", "desc"]),
            default="asc",
            title="Sort Order",
            description="Sort order for the results",
        ),
        th.Property(
            "q_after",
            th.StringType(nullable=True),
            title="After",
            description="Timestamp in seconds with up to 3 decimal places. See https://dev.frontapp.com/reference/list-events",
        ),
        th.Property(
            "q_before",
            th.StringType(nullable=True),
            title="Before",
            description="Timestamp in seconds with up to 3 decimal places. See https://dev.frontapp.com/reference/list-events",
        ),
        th.Property(
            "api_url",
            th.StringType(nullable=False),
            title="API URL",
            default="https://api2.frontapp.com",
            description="The url for the API service",
        ),
    ).to_dict()

    def discover_streams(self) -> list[streams.FrontAppStream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [
            streams.EventsStream(self),
        ]


if __name__ == "__main__":
    TapFrontApp.cli()
