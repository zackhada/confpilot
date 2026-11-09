// ConfPilot contracts: the single source of truth for every shape that crosses a boundary.
// The web app imports these types directly. The API mirrors them as Pydantic models.
// Change this file only by PR, and update every consumer in the same PR.
//
// Conventions: JSON keys are snake_case. Every timestamp is epoch milliseconds in SERVER
// time (see "Clock sync" in README.md). Ids are lowercase slugs or UUIDs.

// ---------- Glossary ----------

export type Lang = "es" | "zh" | "hi" | "pt";
export type TermLevel = 1 | 2 | 3 | 4; // 1 business, 2 general tech, 3 practitioner, 4 specialist

export interface Term {
  id: string; // slug, e.g. "rrf"
  term: string; // display form, e.g. "RRF"
  aliases: string[]; // other spoken or written forms, already normalized
  say: string; // pronunciation hint, e.g. "ar-ar-EFF"
  category: string;
  level: TermLevel;
  simple_def: string; // 15 words or fewer, plain English
  long_def?: string;
  example?: string;
  prereqs: string[]; // term ids this one builds on
  translations?: Partial<Record<Lang, string>>; // one line per language
  ambiguous?: boolean; // common word: only match near a word in `context`
  context?: string[];
  source: "seed" | "llm";
}

export interface Glossary {
  version: string; // changes whenever terms change; the phone caches by version
  terms: Term[];
}

// ---------- User knowledge (SM-2) ----------

export type KnowledgeStatus = "unknown" | "learning" | "known";

export interface Knowledge {
  user_id: string;
  term_id: string;
  status: KnowledgeStatus;
  source: "probe" | "tap" | "srs" | "seed";
  encounters: number;
  ease: number; // SM-2 ease factor, starts at 2.5
  interval_days: number;
  reps: number;
  due_at: number | null;
  learned: boolean; // true once interval_days >= 7
}

// ---------- HTTP ----------

export interface Health { status: "ok"; version: string }

// POST /api/token
export interface TokenRequest { user_id: string }
export interface TokenResponse {
  provider: "deepgram";
  token: string; // short-lived; the real key never reaches the browser
  expires_in_s: number;
  ws_url: string; // full streaming URL including model, encoding and keyterms
}

// GET /api/glossary -> Glossary
// GET /api/users/{user_id}/knowledge -> { items: Knowledge[] }
// PUT /api/users/{user_id}/knowledge/{term_id}  body: KnowledgePatch -> Knowledge
export type KnowledgePatch = Partial<Omit<Knowledge, "user_id" | "term_id">>;

// POST /api/probe  (the only place an LLM call is awaited by the client)
export interface ProbeRequest { user_id: string; transcript: string }
export interface ProbeResponse {
  role: string;
  domain: string;
  known_term_ids: string[];
  english_level: "A2" | "B1" | "B2" | "C1" | "C2";
  goals: string[];
}

// GET /api/rooms/{room}/recap?user_id=
export interface Recap {
  room: string;
  new_term_count: number;
  heard: { term_id: string; count: number }[]; // most heard first
  learn_next: string[]; // term ids, ranked by heard count x on-frontier
}

// GET /api/search?q=&room=&user_id=
export interface SearchHit {
  utterance_id: string;
  speaker: Speaker;
  spoken_at: number;
  text: string;
  highlight: string; // text with <mark> around matches
  term_ids: string[];
}
export interface SearchResponse { hits: SearchHit[] }

// ---------- Room WebSocket: /ws/rooms/{room}?user_id=&name=&role= ----------

export type Role = "speaker" | "viewer"; // the stage view joins as a viewer
export interface Speaker { user_id: string; name: string }
export interface Word { w: string; start_ms: number; end_ms: number } // offsets in the utterance

export type CardTier = 1 | 2 | 3; // 1 on-device, 2 percolator, 3 LLM-found new term

// Sent by a speaker's phone for every interim and final STT result.
// The server relays it to everyone else in the room right away, then stores finals.
export interface TranscriptEvent {
  type: "transcript";
  utterance_id: string; // stable across the interims and the final of one utterance
  seq: number; // increases with every update of this utterance
  is_final: boolean;
  text: string;
  words: Word[];
  started_at: number; // server-time ms when the utterance's audio began
  speaker?: Speaker; // set by the server on relay
}

// Server -> phones: a term the phone's own matcher could not have found.
export interface ServerCardEvent {
  type: "card";
  tier: 2 | 3;
  term: Term; // full term, because tier 3 terms are new to the phone
  utterance_id: string;
  spoken_at: number; // server-time ms when the matched word ended
}

// Phone -> server -> viewers: a card was put on this user's screen.
// This is both the stage view's feed and the source of the latency SLI.
export interface CardShownEvent {
  type: "card.shown";
  card_id: string;
  term_id: string;
  tier: CardTier;
  utterance_id: string;
  spoken_at: number;
  rendered_at: number;
  word_to_card_ms: number; // rendered_at - spoken_at
  user?: Speaker; // set by the server on relay
}

export interface KnowledgeSetEvent { type: "knowledge.set"; term_id: string; status: KnowledgeStatus }
export interface TimePing { type: "time.ping"; t0: number } // t0 is the client clock
export interface TimePong { type: "time.pong"; t0: number; server_ts: number }
export interface RoomState { type: "room.state"; members: (Speaker & { role: Role })[] }
export interface ErrorEvent { type: "error"; code: string; message: string }

export type ClientEvent = TranscriptEvent | CardShownEvent | KnowledgeSetEvent | TimePing;
export type ServerEvent =
  | TranscriptEvent | ServerCardEvent | CardShownEvent | TimePong | RoomState | ErrorEvent;
