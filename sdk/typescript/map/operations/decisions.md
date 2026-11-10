<!-- Generated file — do not edit; regenerated with the SDK. -->

# Decisions — operations

Accessor: `client.decisions` · Source: `src/resources/decisions.ts` · 1 operation · Request and error types: namespace `Decisions`

**Type sources**: every type an operation names, with the file that declares it and the schema value exported beside it. Import every name from `cheapest-yes-api`; the `Source` path is where to **read** the shape, never what to import. `ApiError`, the runtime error family and the file vocabulary are excluded — see sdk-map.md.

### decide

- **Signature**: `decide(request: Decisions.DecideRequestParams, options?: RequestOptions): ApiPromise<DecideResponse, Decisions.DecideError>`
- **Wire**: `POST /decide`
- **Auth**: none — public; no credential is sent
- **Request body**: `application/json` — the `body` field
- **SDK-sent**: `header Idempotency-Key` (minted per call)
- **Returns**: `DecideResponse`
- **Error**: `CheapestYesApiError` with `kind: "api"`, an instance of `Decisions.DecideError` — **typed arms**, narrowed on `err.payload.kind`
- **Error arms**: `"httpValidationError"` [422] `HttpValidationError` · `"undeclared"` [any other] `rawBody: ArrayBuffer`

**Fields** — `Decisions.DecideRequestParams` (1):

| Field | Channel | Type | Req |
| --- | --- | --- | --- |
| `body` | `body` | `DecideRequest` | yes |

| Type | Schema value | Source |
| --- | --- | --- |
| `DecideRequest` | `decideRequestSchema` | `src/models/decide-request.ts` |
| `DecideResponse` | `decideResponseSchema` | `src/models/decide-response.ts` |
| `HttpValidationError` | `httpValidationErrorSchema` | `src/models/http-validation-error.ts` |

