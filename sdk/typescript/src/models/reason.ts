import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";

/** Reason */
export type Reason = {
  /** feature */
  feature: string;
  /** value */
  value: number;
  /** contribution */
  contribution: number;
  /** text */
  text: string;
  /** Properties the service sent or accepts beyond those declared. */
  additionalProperties?: Record<string, JsonValue>;
};

export const reasonSchema: Schema<Reason> = s.object<Reason>(
  {
    feature: s.string(),
    value: s.float64(),
    contribution: s.float64(),
    text: s.string(),
  },
  { additionalProperties: s.json() },
);
