<!-- Generated file — do not edit; regenerated with the SDK. -->

# Ops — operations

Accessor: `client.ops` · Source: `src/resources/ops.ts` · 1 operation · Request types: namespace `Ops`

**Type sources**: every type an operation names, with the file that declares it and the schema value exported beside it. Import every name from `cheapest-yes-api`; the `Source` path is where to **read** the shape, never what to import. `ApiError`, the runtime error family and the file vocabulary are excluded — see sdk-map.md.

### getHealth

- **Signature**: `getHealth(options?: RequestOptions): ApiPromise<Record<string, unknown>, ApiError>`
- **Wire**: `GET /health`
- **Auth**: none — public; no credential is sent
- **Request body**: none — no `Content-Type` header is sent
- **Returns**: `Record<string, unknown>` — a bare `application/json` map; the success type *is* the map
- **Error**: `CheapestYesApiError` with `kind: "api"` — untyped, `payload.kind` always `"undeclared"`

