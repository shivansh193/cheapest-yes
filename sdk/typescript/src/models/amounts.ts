import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";

/** Amounts */
export type Amounts = {
  /** item total */
  itemTotal: number;
  /** shipping */
  shipping: number;
  /** discount */
  discount: number;
  /** total */
  total: number;
  /** Properties the service sent or accepts beyond those declared. */
  additionalProperties?: Record<string, JsonValue>;
};

export const amountsSchema: Schema<Amounts> = s.object<Amounts>(
  {
    itemTotal: s.float64(),
    shipping: s.float64(),
    discount: s.float64(),
    total: s.float64(),
    _keysMap: {
      itemTotal: "item_total",
    },
  },
  { additionalProperties: s.json() },
);
