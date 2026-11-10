import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";
import { cartItemInternalSchema, cartItemSchema, type CartItem } from "./cart-item.js";
import { session2InternalSchema, session2Schema, type Session2 } from "./session2.js";

/** DecideRequest */
export type DecideRequest = {
  /** cart */
  cart: CartItem[];
  /** session */
  session?: Session2;
  /** Opaque id for per-shopper caps; stored only as a hash */
  shopperId?: string | null;
  /** Properties the service sent or accepts beyond those declared. */
  additionalProperties?: Record<string, JsonValue>;
};

const decideRequestProperties: s.Shape<DecideRequest> = {
  cart: s.array(s.lazy(() => cartItemInternalSchema)),
  session: s.optional(s.lazy(() => session2InternalSchema)),
  shopperId: s.optionalNullable(s.string()),
  _keysMap: {
    shopperId: "shopper_id",
  },
};

export const decideRequestInternalSchema: Schema<DecideRequest> = s.object<DecideRequest>(
  decideRequestProperties,
  { additionalProperties: s.json() },
);

export const decideRequestSchema: Schema<DecideRequest> = s.lazySchema(() =>
  s.object<DecideRequest>(
    {
      ...decideRequestProperties,
      cart: s.array(s.lazy(() => cartItemSchema)).check(s.minLength(1)),
      session: s.optional(s.lazy(() => session2Schema)),
    },
    { additionalProperties: s.json() },
  ),
);
