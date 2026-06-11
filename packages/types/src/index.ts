/**
 * Shared domain types, hand-mirrored from the backend Pydantic schemas
 * (apps/api/src/obelisk_api/domain). Phase 1 keeps these in sync by hand; a
 * future task generates them from the OpenAPI spec (see packages/api-client).
 */

export type Equipment = 'bodyweight' | 'minimal' | 'home_gym' | 'full_gym';
export type ProgramModel = 'hybrid_531' | 'linear_novice' | 'marathon_block';
export type BlockPhase = 'active' | 'completed' | 'archived';
export type PrimaryModality =
  | 'strength'
  | 'hybrid'
  | 'endurance'
  | 'climbing'
  | 'tactical';

export interface AthleteProfile {
  id: string;
  user_id: string;
  name: string;
  age: number;
  sex?: string | null;
  bodyweight_lb?: number | null;
  height_in?: number | null;
  resting_hr_bpm?: number | null;
  estimated_1rm: Record<string, number>;
  rep_max_known?: Record<string, unknown> | null;
  maf_data?: Record<string, unknown> | null;
  primary_goals: string[];
  equipment: Equipment;
  days_per_week: number;
  injuries: Array<Record<string, unknown>>;
  primary_modality: PrimaryModality;
  created_at: string;
  updated_at: string;
}

export type AthleteProfileInput = Omit<
  AthleteProfile,
  'id' | 'user_id' | 'created_at' | 'updated_at'
>;

/** The canonical plan (CyclePlan) — the subset the UI renders. */
export interface TrainingBlockItem {
  label: string;
  kind: 'main' | 'accessory' | 'note';
  lift_key?: string | null;
  note?: string | null;
}

export interface TrainingDay {
  day: string;
  session: string;
  blocks: TrainingBlockItem[];
}

export interface TrainingMaxRow {
  lift_key: string;
  display_name: string;
  est_1rm: number;
  tm_wave1: number;
  tm_wave2: number;
  tm_wave3: number;
  increment: number;
  notes: string;
}

export interface Wave {
  wave_num: number;
  week_range: string;
  phase?: string | null;
  training_maxes: Record<string, number>;
}

export interface NutritionProfile {
  calories_low: number;
  calories_high: number;
  protein_g: number;
  carbs_by_day: Record<string, number>;
  fat_floor_g: number;
  notes: string[];
}

export interface CyclePlan {
  title: string;
  subtitle: string;
  goals: string[];
  program_model: ProgramModel;
  maf_cap_bpm: number;
  training_maxes: TrainingMaxRow[];
  nutrition: NutritionProfile;
  day_template: TrainingDay[];
  waves: Wave[];
  week_overrides: Record<string, TrainingDay[]>;
}

export interface Block {
  id: string;
  athlete_id: string;
  name: string;
  goal: string;
  program_model: ProgramModel;
  phase: BlockPhase;
  start_date?: string | null;
  end_date?: string | null;
  plan_json?: CyclePlan | null;
  created_at: string;
  updated_at: string;
}

export type BlockSummary = Pick<
  Block,
  'id' | 'name' | 'goal' | 'program_model' | 'phase' | 'start_date' | 'end_date' | 'created_at'
>;

export interface PlanResponse {
  plan: CyclePlan | null;
  summary: string;
}

/** Analytics: per-lift e1RM time series (GET /v1/athlete/analytics/lifts). */
export interface LiftPoint {
  date: string;
  e1rm: number;
}

export interface AnalyticsLifts {
  series: Record<string, LiftPoint[]>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: unknown;
  tokens_in?: number | null;
  tokens_out?: number | null;
  cost_usd?: number | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface CreateBlockInput {
  name: string;
  goal: string;
  program_model?: string | null;
}

/** SSE event protocol (ADR-006). */
export interface SseDone {
  message_id: string | null;
  cost_usd: number;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
}

export interface SsePlanEdit {
  edit_id: string;
  diff: string;
}

export type ChatStreamEvent =
  | { type: 'open'; block_id: string }
  | { type: 'tool_use'; name: string }
  | { type: 'token'; text: string }
  | { type: 'plan_edit'; edit: SsePlanEdit }
  | { type: 'done'; done: SseDone }
  | { type: 'error'; message: string };
