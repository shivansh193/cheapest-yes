import type { CoreClientOptions } from "./core/client-options.js";

export type ClientOptions = SdkClientOptions & CoreClientOptions;

type SdkClientOptions = ServerOptions;

type ServerOptions = {
  /** Hosted demo (PayPal sandbox) */
  readonly serverOptions?: {
    baseUrl?: string;
  };
};
