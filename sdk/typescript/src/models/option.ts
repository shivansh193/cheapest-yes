import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";

/** Option */
export type Option = {
  /** incentive */
  incentive: string;
  /** allowed */
  allowed: boolean;
  /** blocked by */
  blockedBy: string | null;
  /** p buy */
  pBuy: number;
  /** p paylater */
  pPaylater: number;
  /** profit if buy */
  profitIfBuy: number;
  /** expected profit */
  expectedProfit: number;
  /** gain vs none */
  gainVsNone: number;
  /** expected spend */
  expectedSpend: number;
  /** Properties the service sent or accepts beyond those declared. */
  additionalProperties?: Record<string, JsonValue>;
};

export const optionSchema: Schema<Option> = s.object<Option>(
  {
    incentive: s.string(),
    allowed: s.boolean(),
    blockedBy: s.nullable(s.string()),
    pBuy: s.float64(),
    pPaylater: s.float64(),
    profitIfBuy: s.float64(),
    expectedProfit: s.float64(),
    gainVsNone: s.float64(),
    expectedSpend: s.float64(),
    _keysMap: {
      blockedBy: "blocked_by",
      pBuy: "p_buy",
      pPaylater: "p_paylater",
      profitIfBuy: "profit_if_buy",
      expectedProfit: "expected_profit",
      gainVsNone: "gain_vs_none",
      expectedSpend: "expected_spend",
    },
  },
  { additionalProperties: s.json() },
);
