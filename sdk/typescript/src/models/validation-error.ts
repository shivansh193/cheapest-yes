import * as s from "../core/validation/index.js";
import type { JsonValue, Schema } from "../core/validation/schema.js";
import { locSchema, type Loc } from "./unions/loc.js";

/** One validation problem. */
export type ValidationError = {
  /** loc */
  loc: Loc[];
  /** msg */
  msg: string;
  /** type */
  type: string;
  /** input */
  input?: Record<string, unknown>;
  /** ctx */
  ctx?: Record<string, unknown>;
  /** Properties the service sent or accepts beyond those declared. */
  additionalProperties?: Record<string, JsonValue>;
};

export const validationErrorSchema: Schema<ValidationError> = s.object<ValidationError>(
  {
    loc: s.array(s.lazy(() => locSchema)),
    msg: s.string(),
    type: s.string(),
    input: s.optional(s.record(s.string(), s.unknown())),
    ctx: s.optional(s.record(s.string(), s.unknown())),
  },
  { additionalProperties: s.json() },
);
