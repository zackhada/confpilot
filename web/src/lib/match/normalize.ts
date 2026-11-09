// Normalizer for the on-device matcher. Rules: contracts/README.md section 6.
// Glossary phrases and spoken words both pass through here, so they always agree.

export interface NormalizedWords {
  tokens: string[];
  /** origin[i] is the [first, last] index in the input words that token i came from. */
  origin: [number, number][];
}

interface Piece {
  readonly text: string;
  readonly first: number;
  readonly last: number;
  readonly spelled?: boolean;
}

const SEPARATORS = /[\s\-‐-―/_]+/u;
const NOT_WORD_CHARS = /[^\p{L}\p{N}]/gu;
const SINGLE_LETTER = /^[a-z]$/;
const LETTERS = /^[a-z]+$/;
const DIGITS = /^\d+$/;
const MAX_JOINABLE_LETTERS = 2;

const UNITS: ReadonlyMap<string, number> = new Map(Object.entries({
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9,
  ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
  seventeen: 17, eighteen: 18, nineteen: 19,
}));
const TENS: ReadonlyMap<string, number> = new Map(Object.entries({
  twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90,
}));

// Short everyday words that must never be glued to a number ("is 25", "a zero trust model").
const COMMON_SHORT_WORDS: ReadonlySet<string> = new Set([
  'a', 'i', 'am', 'an', 'as', 'at', 'be', 'by', 'do', 'go', 'he', 'hi', 'if', 'in', 'is', 'it',
  'me', 'my', 'no', 'of', 'oh', 'ok', 'on', 'or', 'so', 'to', 'up', 'us', 'we',
]);

/** Lowercase, split on hyphens and slashes, and strip all other punctuation. */
function toPieces(words: readonly string[]): Piece[] {
  return words.flatMap((word, index) =>
    word
      .toLowerCase()
      .split(SEPARATORS)
      .map((part) => part.replace(NOT_WORD_CHARS, ''))
      .filter((text) => text.length > 0)
      .map((text) => ({ text, first: index, last: index })),
  );
}

/** "twenty five" becomes "25", "nine" becomes "9". */
function readNumberWords(pieces: readonly Piece[]): Piece[] {
  const out: Piece[] = [];
  let i = 0;
  while (i < pieces.length) {
    const piece = pieces[i] as Piece;
    const next = pieces[i + 1];
    const tens = TENS.get(piece.text);
    const unit = UNITS.get(piece.text);
    const nextUnit = next ? UNITS.get(next.text) : undefined;
    if (tens !== undefined && next && nextUnit !== undefined && nextUnit >= 1 && nextUnit <= 9) {
      out.push({ text: String(tens + nextUnit), first: piece.first, last: next.last });
      i += 2;
    } else {
      const value = tens ?? unit;
      out.push(value === undefined ? piece : { ...piece, text: String(value) });
      i += 1;
    }
  }
  return out;
}

function joinPieces(run: readonly Piece[], spelled: boolean): Piece {
  const head = run[0] as Piece;
  const tail = run[run.length - 1] as Piece;
  return { text: run.map((p) => p.text).join(''), first: head.first, last: tail.last, spelled };
}

/** "r r f" becomes "rrf". A leading "a" is treated as the article ("a k 8 s cluster"). */
function joinSpelledLetters(pieces: readonly Piece[]): Piece[] {
  const out: Piece[] = [];
  let i = 0;
  while (i < pieces.length) {
    let end = i;
    while (end < pieces.length && SINGLE_LETTER.test((pieces[end] as Piece).text)) end += 1;
    if (end === i) {
      out.push(pieces[i] as Piece);
      i += 1;
      continue;
    }
    const run = pieces.slice(i, end);
    const hasArticle = run.length > 1 && (run[0] as Piece).text === 'a';
    let letters = hasArticle ? run.slice(1) : run;
    const lastText = (letters[letters.length - 1] as Piece | undefined)?.text;
    const trailing = letters.length > 2 && (lastText === 'i' || lastText === 'a') ? letters[letters.length - 1] : undefined;
    if (trailing) letters = letters.slice(0, -1);
    if (hasArticle) out.push(run[0] as Piece);
    out.push(letters.length >= 2 ? joinPieces(letters, true) : (letters[0] as Piece));
    if (trailing) out.push(trailing);
    i = end;
  }
  return out;
}

function canStartAlnumRun(piece: Piece): boolean {
  if (!LETTERS.test(piece.text)) return false;
  if (piece.spelled) return true;
  return piece.text.length <= MAX_JOINABLE_LETTERS && !COMMON_SHORT_WORDS.has(piece.text);
}

function canContinueAlnumRun(piece: Piece): boolean {
  if (DIGITS.test(piece.text)) return true;
  return SINGLE_LETTER.test(piece.text) && !COMMON_SHORT_WORDS.has(piece.text);
}

/** "bm 25" becomes "bm25" and "k 8 s" becomes "k8s". Longer words are left alone ("pod 3"). */
function joinLettersAndNumbers(pieces: readonly Piece[]): Piece[] {
  const out: Piece[] = [];
  let i = 0;
  while (i < pieces.length) {
    const piece = pieces[i] as Piece;
    const next = pieces[i + 1];
    if (next && canStartAlnumRun(piece) && DIGITS.test(next.text)) {
      let end = i + 2;
      while (end < pieces.length && canContinueAlnumRun(pieces[end] as Piece)) end += 1;
      out.push(joinPieces(pieces.slice(i, end), false));
      i = end;
    } else {
      out.push(piece);
      i += 1;
    }
  }
  return out;
}

export function normalizeWords(words: string[]): NormalizedWords {
  const pieces = joinLettersAndNumbers(joinSpelledLetters(readNumberWords(toPieces(words))));
  return {
    tokens: pieces.map((p) => p.text),
    origin: pieces.map((p): [number, number] => [p.first, p.last]),
  };
}
