import * as s from "../../core/validation/index.js";
import type { Schema } from "../../core/validation/schema.js";

export type Loc = string | number;

export const locSchema: Schema<Loc> = s.of<Loc>(s.union([s.string(), s.int()]));
