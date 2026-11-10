<!-- Generated file — do not edit; regenerated with the SDK. -->

# Decisions — operations

Accessor: `client.decisions` · Source: `cheapest_yes_api/apis/decisions.py` · 1 operation

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.decisions.decide

- **Route**: `POST /decide`
- **Signature**: `def decide(body: DecideRequest | DecideRequestDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` — JSON body
- **Returns (parsed)**: `DecideResponse`
- **Returns (raw)**: `ApiResult[DecideResponse, DecideErrorBody]`
- **Error**: `DecideErrorBody` — **Case A (typed)**
- **Error arms**: `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `DecideRequest` | `cheapest_yes_api/models/decide_request.py` |
| `DecideRequestDict` | `cheapest_yes_api/models/decide_request.py` |
| `DecideResponse` | `cheapest_yes_api/models/decide_response.py` |
| `DecideErrorBody` | `cheapest_yes_api/errors/decide_error.py` |
| `HttpValidationError` | `cheapest_yes_api/models/http_validation_error.py` |

