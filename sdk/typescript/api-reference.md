# Reference

> Source: [CheapestYesApiClient](src/client.ts)

## Decisions

> Source: [Decisions](src/resources/decisions.ts)

<details>
<summary><code>decide(request: Decisions.DecideRequestParams, options?: RequestOptions): ApiPromise&lt;DecideResponse, Decisions.DecideError&gt;</code></summary>

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

### Direct Usage

<dl>
<dd>

```ts
try {
  const response = await client.decisions.decide({
    body: {
      cart: [{ id: "sku-123", title: "Wireless headphones", price: 240.0, qty: 1 }],
      session: {
        timeOnPageS: 75,
        productViews: 6,
        cartReturns: 2,
        compareEvents: 0,
        hesitationAfterShippingS: 4,
        hesitationAfterTotalS: 38,
        accessoryViews: 0,
        isMobile: 1,
        isReturning: 0,
        priorOrders: 0,
      },
      shopperId: "shopper-42",
    },
  });
  // TODO: Handle 'response' of type DecideResponse
} catch (err) {
  // TODO: Handle 'err' of type Decisions.DecideError, discriminated with 'err.payload.kind'
}
```

</dd>
</dl>

### Usage as ApiResult

<dl>
<dd>

```ts
const result = await client.decisions
  .decide({
    body: {
      cart: [{ id: "sku-123", title: "Wireless headphones", price: 240.0, qty: 1 }],
      session: {
        timeOnPageS: 75,
        productViews: 6,
        cartReturns: 2,
        compareEvents: 0,
        hesitationAfterShippingS: 4,
        hesitationAfterTotalS: 38,
        accessoryViews: 0,
        isMobile: 1,
        isReturning: 0,
        priorOrders: 0,
      },
      shopperId: "shopper-42",
    },
  })
  .asApiResult();
// TODO: Use 'result.status' and 'result.headers' to read the raw response status and headers
if (result.ok) {
  // TODO: Use 'result.value' of type DecideResponse
} else {
  // TODO: Handle 'result', discriminated with 'result.payload.kind'
}
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[DecideRequest](src/models/decide-request.ts)</code> | The cart (list prices) and session-behaviour signals. |

</dd>
</dl>

### Response

<dl>
<dd>

**Direct**: `await client.decisions.decide(request)`

- **OnSuccess**: <code>[DecideResponse](src/models/decide-response.ts)</code>
- **OnError**: throws <code>[Decisions.DecideError](src/resources/decisions.ts)</code>, with `err.payload` discriminated on `kind`

**As ApiResult**: `await client.decisions.decide(request).asApiResult()`

- **OnSuccess**: <code>[ApiResult](src/core/api-promise.ts)&lt;DecideResponse, Decisions.DecideError&gt;</code>, with `result.value` of type <code>[DecideResponse](src/models/decide-response.ts)</code>
- **OnError**: `result.payload` discriminated on `kind`, with `result.message`

**Thrown**: <code>[CheapestYesApiError](src/core/errors.ts)</code> on any operational failure — a caller abort and a programmer error stay outside the family and reach you raw

</dd>
</dl>

</dd>
</dl>

</details>

## Ops

> Source: [Ops](src/resources/ops.ts)

<details>
<summary><code>getHealth(options?: RequestOptions): ApiPromise&lt;Record&lt;string, unknown&gt;, ApiError&gt;</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Liveness check; reports the PayPal environment (always sandbox) and model metadata.

</dd>
</dl>

### Direct Usage

<dl>
<dd>

```ts
try {
  const response = await client.ops.getHealth();
  // TODO: Handle 'response' of type Record<string, unknown>
} catch (err) {
  // TODO: Handle 'err' of type ApiError, where 'err.payload' is always the Undeclared arm
}
```

</dd>
</dl>

### Usage as ApiResult

<dl>
<dd>

```ts
const result = await client.ops.getHealth().asApiResult();
// TODO: Use 'result.status' and 'result.headers' to read the raw response status and headers
if (result.ok) {
  // TODO: Use 'result.value' of type Record<string, unknown>
} else {
  // TODO: Handle 'result', where 'result.payload' is always the Undeclared arm
}
```

</dd>
</dl>

### Response

<dl>
<dd>

**Direct**: `await client.ops.getHealth()`

- **OnSuccess**: <code>Record&lt;string, unknown&gt;</code>
- **OnError**: throws <code>[ApiError](src/core/api-error.ts)</code>, with `err.payload` always the <code>[Undeclared](src/core/api-error.ts)</code> arm

**As ApiResult**: `await client.ops.getHealth().asApiResult()`

- **OnSuccess**: <code>[ApiResult](src/core/api-promise.ts)&lt;Record&lt;string, unknown&gt;, ApiError&gt;</code>, with `result.value` of type <code>Record&lt;string, unknown&gt;</code>
- **OnError**: `result.payload` always the <code>[Undeclared](src/core/api-error.ts)</code> arm, with `result.message`

**Thrown**: <code>[CheapestYesApiError](src/core/errors.ts)</code> on any operational failure — a caller abort and a programmer error stay outside the family and reach you raw

</dd>
</dl>

</dd>
</dl>

</details>

