import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";
import { amounts1Schema, type Amounts1 } from "./amounts1.js";
import { optionSchema, type Option } from "./option.js";
import { reasonSchema, type Reason } from "./reason.js";

/** DecideResponse */
export type DecideResponse = {
  /** decision id */
  decisionId: string;
  /** one of: none, paylater, free_shipping, addon, discount_5, discount_10 */
  incentive: string;
  /** label */
  label: string;
  /** amounts */
  amounts: Amounts1;
  /** expected profit vs no incentive, USD */
  expectedGain: number;
  /** explanation */
  explanation: string;
  /** reasons */
  reasons: Reason[];
  /** options */
  options: Option[];
  /** guardrails */
  guardrails: string[];
  /** Properties the service sent or accepts beyond those declared. */
  additionalProperties?: Record<string, JsonValue>;
};

export const decideResponseSchema: Schema<DecideResponse> = s.object<DecideResponse>(
  {
    decisionId: s.string(),
    incentive: s.string(),
    label: s.string(),
    amounts: amounts1Schema,
    expectedGain: s.float64(),
    explanation: s.string(),
    reasons: s.array(s.lazy(() => reasonSchema)),
    options: s.array(s.lazy(() => optionSchema)),
    guardrails: s.array(s.string()),
    _keysMap: {
      decisionId: "decision_id",
      expectedGain: "expected_gain",
    },
  },
  { additionalProperties: s.json() },
);
