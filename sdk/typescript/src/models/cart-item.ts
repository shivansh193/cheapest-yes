import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";

/** CartItem */
export type CartItem = {
  /** Product id (catalog id for the demo store) */
  id: string;
  /** Product name */
  title?: string;
  /** List price in USD */
  price: number;
  /** qty @default 1 */
  qty?: number;
  /** brand */
  brand?: string | null;
  /** image */
  image?: string | null;
  /** Properties the service sent or accepts beyond those declared. */
  additionalProperties?: Record<string, JsonValue>;
};

const cartItemProperties: s.Shape<CartItem> = {
  id: s.string(),
  title: s.optional(s.string()),
  price: s.float64(),
  qty: s.defaulted(s.int(), 1),
  brand: s.optionalNullable(s.string()),
  image: s.optionalNullable(s.string()),
};

export const cartItemInternalSchema: Schema<CartItem> = s.object<CartItem>(cartItemProperties, {
  additionalProperties: s.json(),
});

export const cartItemSchema: Schema<CartItem> = s.lazySchema(() =>
  s.object<CartItem>(
    {
      ...cartItemProperties,
      price: s.float64().check(s.gte(0)),
      qty: s.defaulted(s.int().check(s.gte(1), s.lte(20)), 1),
    },
    { additionalProperties: s.json() },
  ),
);
