from __future__ import annotations

from uuid import UUID, uuid4

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    RawClient,
    RequestOptionsOrDict,
    async_json_decoder,
    json_body,
    json_decoder,
    param,
    unwrap,
)
from ..errors.decide_error import DecideErrorBody, decide_error_mapper
from ..models.decide_request import DecideRequest, DecideRequestDict
from ..models.decide_response import DecideResponse
from ..server.server import Server


class Decisions:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = DecisionsWithRawResponse(client, server)

    def decide(
        self, body: DecideRequest | DecideRequestDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> DecideResponse:
        """Takes a cart and session-behaviour signals, returns the incentive with the highest expected profit (or none),
        the order amounts, and the reasons. Deterministic given the inputs and today's guardrail state. Amounts never
        exceed list price plus standard shipping.

        Args:
            body: The cart (list prices) and session-behaviour signals.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.decide(body, request_options=request_options))

    @property
    def with_raw_response(self) -> DecisionsWithRawResponse:
        return self._with_raw_response


class AsyncDecisions:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncDecisionsWithRawResponse(client, server)

    async def decide(
        self, body: DecideRequest | DecideRequestDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> DecideResponse:
        """Takes a cart and session-behaviour signals, returns the incentive with the highest expected profit (or none),
        the order amounts, and the reasons. Deterministic given the inputs and today's guardrail state. Amounts never
        exceed list price plus standard shipping.

        Args:
            body: The cart (list prices) and session-behaviour signals.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Validation Error ``error`` is ``HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.decide(body, request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncDecisionsWithRawResponse:
        return self._with_raw_response


class DecisionsWithRawResponse(BaseRawResponse[RawClient, Server]):
    def decide(
        self, body: DecideRequest | DecideRequestDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[DecideResponse, DecideErrorBody]:
        """Takes a cart and session-behaviour signals, returns the incentive with the highest expected profit (or none),
        the order amounts, and the reasons. Deterministic given the inputs and today's guardrail state. Amounts never
        exceed list price plus standard shipping.

        Args:
            body: The cart (list prices) and session-behaviour signals.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/decide"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[DecideRequest | DecideRequestDict](body),
            decoder=json_decoder[DecideResponse],
            error_mapper=decide_error_mapper,
            request_options=request_options,
        )


class AsyncDecisionsWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def decide(
        self, body: DecideRequest | DecideRequestDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[DecideResponse, DecideErrorBody]:
        """Takes a cart and session-behaviour signals, returns the incentive with the highest expected profit (or none),
        the order amounts, and the reasons. Deterministic given the inputs and today's guardrail state. Amounts never
        exceed list price plus standard shipping.

        Args:
            body: The cart (list prices) and session-behaviour signals.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/decide"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[DecideRequest | DecideRequestDict](body),
            decoder=async_json_decoder[DecideResponse],
            error_mapper=decide_error_mapper,
            request_options=request_options,
        )
