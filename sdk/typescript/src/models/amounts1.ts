import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";

/** amounts */
export type Amounts1 = {
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

export const amounts1Schema: Schema<Amounts1> = s.object<Amounts1>(
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
