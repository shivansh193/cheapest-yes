import { ApiError, type Declared, type Undeclared } from "../core/api-error.js";
import type { ApiPromise } from "../core/api-promise.js";
import type { RequestOptions } from "../core/api-request.js";
import { noneAuth } from "../core/auth/schemes.js";
import type { RawClient } from "../core/raw-client.js";
import type { ErrorDecoders } from "../core/response-decoder.js";
import { uuid } from "../core/uuid.js";
import * as s from "../core/validation/index.js";
import { decideRequestInternalSchema, type DecideRequest } from "../models/decide-request.js";
import { decideResponseSchema, type DecideResponse } from "../models/decide-response.js";
import { httpValidationErrorSchema, type HttpValidationError } from "../models/http-validation-error.js";
import type { Servers } from "../servers.js";

export class Decisions {
  readonly #rawClient: RawClient;
  readonly #servers: Servers;

  constructor(rawClient: RawClient, servers: Servers) {
    this.#rawClient = rawClient;
    this.#servers = servers;
  }

  /**
   * Choose the cheapest incentive for a cart
   *
   * @remarks
   * Takes a cart and session-behaviour signals, returns the incentive with the highest expected
   * profit (or none), the order amounts, and the reasons. Deterministic given the inputs and
   * today's guardrail state. Amounts never exceed list price plus standard shipping.
   *
   * @returns Successful Response
   *
   * @throws {@link Decisions.DecideError} when the API answers with an error status — narrow on
   * `err.payload.kind`
   *
   * @throws {@link CheapestYesApiError} when no usable response was produced: a connection failure,
   * a timeout, a body that would not decode, a value that would not encode, or a credential that
   * could not be obtained
   */
  decide(
    request: Decisions.DecideRequestParams,
    options?: RequestOptions,
  ): ApiPromise<DecideResponse, Decisions.DecideError> {
    return this.#rawClient.execute(
      {
        method: "POST",
        urlTemplate: this.#servers.default("/decide"),
        auth: noneAuth,
        pathParams: [],
        query: [],
        headers: [{ name: "Idempotency-Key", value: uuid(), schema: s.string() }],
        body: { kind: "json", value: request.body, schema: decideRequestInternalSchema },
      },
      {
        success: { kind: "json", schema: decideResponseSchema },
        errorFactory: Decisions.DecideError,
      },
      options,
    );
  }
}

export namespace Decisions {
  export type DecideRequestParams = {
    /** The cart (list prices) and session-behaviour signals. */
    body: DecideRequest;
  };

  export class DecideError extends ApiError {
    declare readonly payload: Declared<"httpValidationError", HttpValidationError> | Undeclared;

    static readonly errors: ErrorDecoders<DecideError> = [
      { on: 422, kind: "httpValidationError", decode: { kind: "json", schema: httpValidationErrorSchema } },
    ];
  }
}
