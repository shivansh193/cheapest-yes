import type { ClientOptions } from "./client-options.js";
import { buildCoreClientOptions } from "./core/client-options.js";
import { RawClient } from "./core/raw-client.js";
import * as host from "./core/runtime-environment.js";
import * as s from "./core/validation/index.js";
import { Decisions } from "./resources/decisions.js";
import { Ops } from "./resources/ops.js";
import { buildServers, type Servers } from "./servers.js";

/**
 * Picks the cheapest incentive that turns a hesitant shopper into a buyer: PayPal Pay Later
 * messaging, free shipping, a free add-on or a small discount, chosen to maximise the merchant's
 * expected profit. List price is the ceiling: no response from this API ever raises a price.
 */
export class CheapestYesApiClient {
  readonly #rawClient: RawClient;
  readonly #servers: Servers;
  #decisions?: Decisions;
  #ops?: Ops;

  constructor(options: ClientOptions = {}) {
    this.#rawClient = new RawClient({
      ...buildCoreClientOptions(options, "CHEAPEST_YES_API_CLIENT_LOG"),
      defaultHeaders: [
        { name: "User-Agent", value: "CheapestYesApiClient/1.0.0 TypeScript", schema: s.string() },
        { name: "X-APIMatic-Lang", value: "TypeScript", schema: s.string() },
        { name: "X-APIMatic-Package-Version", value: "1.0.0", schema: s.string() },
        { name: "X-APIMatic-Gen-Version", value: "4.0.0", schema: s.string() },
        { name: "X-APIMatic-OS", value: host.operatingSystem(), schema: s.optional(s.string()) },
        { name: "X-APIMatic-Runtime", value: host.runtimeDescription(), schema: s.optional(s.string()) },
      ],
      defaultQuery: [],
      defaultPathParams: [],
    });

    this.#servers = buildServers(options);
  }

  get decisions(): Decisions {
    return (this.#decisions ??= new Decisions(this.#rawClient, this.#servers));
  }

  get ops(): Ops {
    return (this.#ops ??= new Ops(this.#rawClient, this.#servers));
  }
}
