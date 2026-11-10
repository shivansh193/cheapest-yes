from __future__ import annotations

from typing import Any

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    RawClient,
    RawError,
    RequestOptionsOrDict,
    async_json_decoder,
    json_decoder,
    raw_error_response,
    unwrap,
)
from ..server.server import Server


class Ops:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = OpsWithRawResponse(client, server)

    def get_health(self, *, request_options: RequestOptionsOrDict | None = None) -> Any:
        """Liveness check; reports the PayPal environment (always sandbox) and model metadata.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(self._with_raw_response.get_health(request_options=request_options))

    @property
    def with_raw_response(self) -> OpsWithRawResponse:
        return self._with_raw_response


class AsyncOps:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncOpsWithRawResponse(client, server)

    async def get_health(self, *, request_options: RequestOptionsOrDict | None = None) -> Any:
        """Liveness check; reports the PayPal environment (always sandbox) and model metadata.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(await self._with_raw_response.get_health(request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncOpsWithRawResponse:
        return self._with_raw_response


class OpsWithRawResponse(BaseRawResponse[RawClient, Server]):
    def get_health(self, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[Any, RawError]:
        """Liveness check; reports the PayPal environment (always sandbox) and model metadata.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/health"),
            decoder=json_decoder[Any],
            error_mapper=raw_error_response,
            request_options=request_options,
        )


class AsyncOpsWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def get_health(self, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[Any, RawError]:
        """Liveness check; reports the PayPal environment (always sandbox) and model metadata.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/health"),
            decoder=async_json_decoder[Any],
            error_mapper=raw_error_response,
            request_options=request_options,
        )
