# Raw Reference

**Raw** endpoints, reached through `with_raw_response`, return `ApiResult[T, E]` and never raise for an API error. For the parsed endpoints, see [API Reference](api-reference.md).

> Source: [CheapestYesApiClient](cheapest_yes_api/client.py)

## Decisions

> Source: [Decisions](cheapest_yes_api/apis/decisions.py)

<details>
<summary><code>def decide(body: DecideRequest | DecideRequestDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[DecideResponse, DecideErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Takes a cart and session-behaviour signals, returns the incentive with the highest expected
profit (or none), the order amounts, and the reasons. Deterministic given the inputs and
today's guardrail state. Amounts never exceed list price plus standard shipping.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.decisions.with_raw_response.decide(
    DecideRequest(
        cart=[CartItem(id="sku-123", title="Wireless headphones", price=240, qty=1)],
        session=Session2(
            time_on_page_s=75,
            product_views=6,
            cart_returns=2,
            compare_events=0,
            hesitation_after_shipping_s=4,
            hesitation_after_total_s=38,
            accessory_views=0,
            is_mobile=1,
            is_returning=0,
            prior_orders=0,
        ),
        shopper_id="shopper-42",
    ),
)
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type DecideResponse
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type DecideErrorBody
```

**Async**

```python
result = await async_client.decisions.with_raw_response.decide(
    DecideRequest(
        cart=[CartItem(id="sku-123", title="Wireless headphones", price=240, qty=1)],
        session=Session2(
            time_on_page_s=75,
            product_views=6,
            cart_returns=2,
            compare_events=0,
            hesitation_after_shipping_s=4,
            hesitation_after_total_s=38,
            accessory_views=0,
            is_mobile=1,
            is_returning=0,
            prior_orders=0,
        ),
        shopper_id="shopper-42",
    ),
)
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type DecideResponse
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type DecideErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[DecideRequest](cheapest_yes_api/models/decide_request.py) \| [DecideRequestDict](cheapest_yes_api/models/decide_request.py)</code> | The cart (list prices) and session-behaviour signals. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](cheapest_yes_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](cheapest_yes_api/core/results.py)&#91;[DecideResponse](cheapest_yes_api/models/decide_response.py), [DecideErrorBody](cheapest_yes_api/errors/decide_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[DecideResponse](cheapest_yes_api/models/decide_response.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[DecideErrorBody](cheapest_yes_api/errors/decide_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 422 | <code>[HttpValidationError](cheapest_yes_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](cheapest_yes_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## Ops

> Source: [Ops](cheapest_yes_api/apis/ops.py)

<details>
<summary><code>def get_health(*, request_options: RequestOptionsOrDict | None = None) -> ApiResult[Any, RawError]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Liveness check; reports the PayPal environment (always sandbox) and model metadata.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.ops.with_raw_response.get_health()
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type Any
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type RawError
```

**Async**

```python
result = await async_client.ops.with_raw_response.get_health()
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type Any
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type RawError
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>request_options</code> | <code>[RequestOptionsOrDict](cheapest_yes_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](cheapest_yes_api/core/results.py)&#91;Any, [RawError](cheapest_yes_api/core/results.py)&#93;</code>

**On `Success`**: `payload` is <code>Any</code> -- Successful Response

**On `Failure`**: `error` is <code>[RawError](cheapest_yes_api/core/results.py)</code>

</dd>
</dl>

</dd>
</dl>

</details>

