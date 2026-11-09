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
  aliases: string[]; // other spoken or written forms, as written; matchers normalize them
  say: string | null; // pronunciation hint, e.g. "ar-ar-EFF"; null when it is obvious
  category: string;
  level: TermLevel;
  simple_def: string; // 20 words or fewer, plain English
  long_def?: string;
  example?: string;
  prereqs: string[]; // term ids this one builds on
  translations?: Partial<Record<Lang, string>>; // one line per language
  ambiguous?: boolean; // common word: needs nearby tech context (README section 6)
  context?: string[]; // optional explicit context words for an ambiguous term
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

// ---------- Sessions ----------
// There is no login, but identity is not client-claimed: the server issues the user id.
//
// POST /api/session  body: SessionRequest -> SessionResponse   (no Authorization needed)
export interface SessionRequest { name: string } // display name, 80 characters or fewer
export interface SessionResponse {
  user_id: string; // UUID chosen by the server
  session: string; // opaque signed string; treat it like a password
  expires_at: number; // epoch ms in server time; a session lasts 12 hours
}
//
// Every other /api route except GET /api/glossary needs the header
//   Authorization: Bearer <session>
// 401: the session is missing, invalid or expired (get a new one from POST /api/session).
// 403: a user_id in the path, query or body that is not the session's own, or a room the
//      session's user has never joined.
// 429: too many requests; the Retry-After header says how many seconds to wait.

// POST /api/token   (the body's user_id must be the session's own)
export interface TokenRequest { user_id: string }
export interface TokenResponse {
  provider: "deepgram";
  token: string; // short-lived; the real key never reaches the browser
  expires_in_s: number;
  // Full streaming URL including model, encoding and keyterms. Browsers cannot set an
  // Authorization header on a WebSocket, so pass the token as a subprotocol:
  //   new WebSocket(ws_url, ["bearer", token])
  // ("token" in place of "bearer" is for raw API keys and gets a 401 with this token.)
  // The token only has to be valid when the socket opens: fetch a new one per connection.
  ws_url: string;
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

// GET /api/rooms/{room}/recap?user_id=   (members of the room only; always the caller's own recap)
export interface Recap {
  room: string;
  new_term_count: number;
  heard: { term_id: string; count: number }[]; // most heard first
  learn_next: string[]; // term ids, ranked by heard count x on-frontier
}

// GET /api/search?q=&room=&user_id=&limit=   (room is required; members of the room only)
export interface SearchHit {
  utterance_id: string;
  speaker: Speaker;
  spoken_at: number;
  text: string;
  highlight: string; // text with <mark> around matches
  term_ids: string[];
}
export interface SearchResponse { hits: SearchHit[] }

// POST /api/ask (room members only). SSE sends moments first, then the answer when ready.
export interface AskRequest { room: string; question: string }
export type AskEvent =
  | { type: "moments"; hits: SearchHit[] }
  | { type: "answer"; answer: string | null };

// ---------- Room WebSocket: /ws/rooms/{room}?session=&name=&role= ----------
// The user id comes from the session; there is no user_id parameter. The handshake is
// refused (HTTP 403) when the Origin header is neither the API's own host nor allow-listed.

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
// Sent to the whole room on every join and leave. The server also resends it to each socket
// every 20 seconds as its heartbeat; there is no separate ping event.
export interface RoomState { type: "room.state"; members: (Speaker & { role: Role })[] }

// unauthorized: the session is missing, invalid or expired; the socket then closes (1008).
// bad_request: bad join parameters; the socket then closes with code 1008.
// bad_event: a frame that is not a valid ClientEvent. forbidden: e.g. a viewer sent a transcript.
// store_unavailable: a knowledge.set could not be saved. internal: the event failed on the server.
// After every code except unauthorized and bad_request the socket stays open.
export type ErrorCode =
  | "unauthorized" | "bad_request" | "bad_event" | "forbidden" | "store_unavailable" | "internal";
export interface ErrorEvent { type: "error"; code: ErrorCode; message: string }

export type ClientEvent = TranscriptEvent | CardShownEvent | KnowledgeSetEvent | TimePing;
export type ServerEvent =
  | TranscriptEvent | ServerCardEvent | CardShownEvent | TimePong | RoomState | ErrorEvent;
