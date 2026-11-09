// The knowledge map (known / frontier / beyond) and the adaptive onboarding probe.
// The probe walks the prerequisite graph: "I could explain it" jumps to a harder dependent,
// "New to me" steps down to a prerequisite. In effect it is a binary search for the frontier.

import type { KnowledgeStatus, Term } from '../../../contracts/types';

export type ProbeAnswer = 'explain' | 'heard' | 'new';

/** Keyed by term id. Key order must be the order the questions were answered in. */
export type ProbeAnswers = Record<string, ProbeAnswer>;

export interface KnowledgeMap {
  known: string[];
  frontier: string[];
  beyond: string[];
}

export const DEFAULT_MAX_PROBE_QUESTIONS = 9;

const STATUS_BY_ANSWER: Readonly<Record<ProbeAnswer, KnowledgeStatus>> = {
  explain: 'known',
  heard: 'learning',
  new: 'unknown',
};

/** frontier: not known, every prereq known (or none). beyond: not known, some prereq unknown. */
export function classify(terms: Term[], knowledge: Record<string, KnowledgeStatus>): KnowledgeMap {
  const ids = new Set(terms.map((t) => t.id));
  const isKnown = (id: string): boolean => knowledge[id] === 'known';
  const ready = (t: Term): boolean => t.prereqs.filter((id) => ids.has(id)).every(isKnown);
  const unknown = terms.filter((t) => !isKnown(t.id));
  return {
    known: terms.filter((t) => isKnown(t.id)).map((t) => t.id),
    frontier: unknown.filter(ready).map((t) => t.id),
    beyond: unknown.filter((t) => !ready(t)).map((t) => t.id),
  };
}

type Links = ReadonlyMap<string, readonly string[]>;

function prereqLinks(terms: readonly Term[]): Links {
  const ids = new Set(terms.map((t) => t.id));
  return new Map(terms.map((t) => [t.id, t.prereqs.filter((id) => ids.has(id))] as const));
}

function dependentLinks(terms: readonly Term[], prereqs: Links): Links {
  return new Map(
    terms.map((t) => [t.id, terms.filter((d) => (prereqs.get(d.id) ?? []).includes(t.id)).map((d) => d.id)] as const),
  );
}

/** Every id reachable from `starts` by following `links`, not counting the starts themselves. */
function reachable(starts: readonly string[], links: Links): Set<string> {
  const seen = new Set<string>();
  const visit = (id: string): void => {
    (links.get(id) ?? []).forEach((next) => {
      if (seen.has(next)) return;
      seen.add(next);
      visit(next);
    });
  };
  starts.forEach(visit);
  return seen;
}

const answeredWith = (answers: ProbeAnswers, answer: ProbeAnswer): string[] =>
  Object.keys(answers).filter((id) => answers[id] === answer);

/** Lowest score wins; ties go to the better-connected term, then to glossary order. */
function pick(candidates: readonly Term[], score: (t: Term) => number, linkCount: (t: Term) => number): string | null {
  const ranked = [...candidates].sort((a, b) => score(a) - score(b) || linkCount(b) - linkCount(a));
  return ranked[0]?.id ?? null;
}

/** The next term to ask about, or null when the probe is over. */
export function nextProbeTerm(
  terms: Term[],
  answers: ProbeAnswers,
  maxQuestions: number = DEFAULT_MAX_PROBE_QUESTIONS,
): string | null {
  const answeredIds = Object.keys(answers);
  if (answeredIds.length >= maxQuestions) return null;

  const prereqs = prereqLinks(terms);
  const dependents = dependentLinks(terms, prereqs);
  // Skip what is already implied: prereqs of an explained term, dependents of a new one.
  const settled = new Set([
    ...answeredIds,
    ...reachable(answeredWith(answers, 'explain'), prereqs),
    ...reachable(answeredWith(answers, 'new'), dependents),
  ]);
  const open = terms.filter((t) => !settled.has(t.id));
  const linkCount = (t: Term): number => (prereqs.get(t.id)?.length ?? 0) + (dependents.get(t.id)?.length ?? 0);
  const nearLevel = (level: number) => (t: Term): number => Math.abs(t.level - level);

  const answeredInGlossary = answeredIds.filter((id) => prereqs.has(id));
  const lastId = answeredInGlossary[answeredInGlossary.length - 1];
  const last = terms.find((t) => t.id === lastId);
  if (!last) {
    const levels = terms.map((t) => t.level);
    const middle = Math.floor((Math.min(...levels) + Math.max(...levels)) / 2);
    return pick(open, nearLevel(middle), linkCount);
  }

  const answer = answers[last.id];
  const linked = (links: Links): Term[] => open.filter((t) => (links.get(last.id) ?? []).includes(t.id));
  if (answer === 'explain') {
    const harder = open.filter((t) => t.level > last.level);
    return pick(linked(dependents), nearLevel(last.level), linkCount)
      ?? pick(harder, nearLevel(last.level), linkCount)
      ?? pick(open, nearLevel(last.level), linkCount);
  }
  if (answer === 'new') {
    const easier = open.filter((t) => t.level < last.level);
    return pick(linked(prereqs), nearLevel(last.level), linkCount)
      ?? pick(easier, nearLevel(last.level), linkCount)
      ?? pick(open, nearLevel(last.level), linkCount);
  }
  return pick(open, nearLevel(last.level), linkCount);
}

/**
 * Turns probe answers into knowledge statuses. Pass the glossary terms to also mark every
 * prereq of an explained term as known; an explicit answer always beats an inferred one.
 */
export function answersToKnowledge(answers: ProbeAnswers, terms: Term[] = []): Record<string, KnowledgeStatus> {
  const inferred = [...reachable(answeredWith(answers, 'explain'), prereqLinks(terms))];
  const explicit = Object.entries(answers).map(([id, answer]) => [id, STATUS_BY_ANSWER[answer]] as const);
  return Object.fromEntries([...inferred.map((id) => [id, 'known'] as const), ...explicit]);
}
