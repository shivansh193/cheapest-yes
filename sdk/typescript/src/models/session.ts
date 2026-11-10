import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";

/** Session */
export type Session = {
  /** time on the checkout page (s) @default 0 */
  timeOnPageS?: number;
  /** product pages viewed this session @default 0 */
  productViews?: number;
  /** times the shopper came back to the cart @default 0 */
  cartReturns?: number;
  /** price-comparison signals (copied a product name, switched tabs) @default 0 */
  compareEvents?: number;
  /** idle time right after the shipping cost was shown (s) @default 0 */
  hesitationAfterShippingS?: number;
  /** idle time right after the order total was shown (s) @default 0 */
  hesitationAfterTotalS?: number;
  /** accessory / add-on products viewed @default 0 */
  accessoryViews?: number;
  /** device class is mobile @default 0 */
  isMobile?: number;
  /** returning visitor @default 0 */
  isReturning?: number;
  /** past orders with this merchant (logged-in only) @default 0 */
  priorOrders?: number;
  /** seconds spent on product pages (feeds the intent model) */
  browseSeconds?: number | null;
  /** optional precomputed purchase-intent score */
  intentScore?: number | null;
  /** Properties the service sent or accepts beyond those declared. */
  additionalProperties?: Record<string, JsonValue>;
};

const sessionProperties: s.Shape<Session> = {
  timeOnPageS: s.defaulted(s.float64(), 0),
  productViews: s.defaulted(s.int(), 0),
  cartReturns: s.defaulted(s.int(), 0),
  compareEvents: s.defaulted(s.int(), 0),
  hesitationAfterShippingS: s.defaulted(s.float64(), 0),
  hesitationAfterTotalS: s.defaulted(s.float64(), 0),
  accessoryViews: s.defaulted(s.int(), 0),
  isMobile: s.defaulted(s.int(), 0),
  isReturning: s.defaulted(s.int(), 0),
  priorOrders: s.defaulted(s.int(), 0),
  browseSeconds: s.optionalNullable(s.float64()),
  intentScore: s.optionalNullable(s.float64()),
  _keysMap: {
    timeOnPageS: "time_on_page_s",
    productViews: "product_views",
    cartReturns: "cart_returns",
    compareEvents: "compare_events",
    hesitationAfterShippingS: "hesitation_after_shipping_s",
    hesitationAfterTotalS: "hesitation_after_total_s",
    accessoryViews: "accessory_views",
    isMobile: "is_mobile",
    isReturning: "is_returning",
    priorOrders: "prior_orders",
    browseSeconds: "browse_seconds",
    intentScore: "intent_score",
  },
};

export const sessionInternalSchema: Schema<Session> = s.object<Session>(sessionProperties, {
  additionalProperties: s.json(),
});

export const sessionSchema: Schema<Session> = s.lazySchema(() =>
  s.object<Session>(
    {
      ...sessionProperties,
      timeOnPageS: s.defaulted(s.float64().check(s.gte(0)), 0),
      productViews: s.defaulted(s.int().check(s.gte(0)), 0),
      cartReturns: s.defaulted(s.int().check(s.gte(0)), 0),
      compareEvents: s.defaulted(s.int().check(s.gte(0)), 0),
      hesitationAfterShippingS: s.defaulted(s.float64().check(s.gte(0)), 0),
      hesitationAfterTotalS: s.defaulted(s.float64().check(s.gte(0)), 0),
      accessoryViews: s.defaulted(s.int().check(s.gte(0)), 0),
      isMobile: s.defaulted(s.int().check(s.gte(0), s.lte(1)), 0),
      isReturning: s.defaulted(s.int().check(s.gte(0), s.lte(1)), 0),
      priorOrders: s.defaulted(s.int().check(s.gte(0)), 0),
      browseSeconds: s.optionalNullable(s.float64().check(s.gte(0))),
      intentScore: s.optionalNullable(s.float64().check(s.gte(0), s.lte(1))),
    },
    { additionalProperties: s.json() },
  ),
);
