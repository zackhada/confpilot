// Demo accounts, opened by link: ?demo=returning or ?demo=new.
//   returning  "Priya", day three of the conference: a known map, terms in progress,
//              saved cards and a flashcard history, so only her real frontier pops cards.
//   new        a clean phone that lands on the join screen, ready for "Tune it to me first".
// Runs before the app loads, so the profile store starts from what is written here.
import type { KnowledgePatch, KnowledgeStatus } from '@contracts'
import { putKnowledge } from './api'
import { ensureSession } from './auth'
import { clearIdentity, saveProfile, storeKnowledge, storeSaved } from './identity'

const DAY_MS = 86_400_000

const KNOWN = [
  // Everyday tech, business and conference talk.
  'api', 'sdk', 'cloud', 'server', 'database', 'latency', 'throughput', 'frontend', 'backend',
  'open-source', 'repository', 'git', 'pull-request', 'commit', 'branch', 'merge', 'code-review',
  'ci-cd', 'deploy', 'production', 'staging', 'bug', 'hotfix', 'rollback', 'refactor',
  'technical-debt', 'legacy', 'monolith', 'microservices', 'scalability', 'load-balancer', 'cache',
  'cdn', 'dns', 'webhook', 'authentication', 'authorization', 'encryption', 'uptime', 'outage',
  'keynote', 'breakout-session', 'hallway-track', 'lightning-talk', 'booth', 'swag',
  'saas', 'b2b', 'roi', 'kpi', 'okr', 'stakeholder', 'roadmap', 'mvp', 'pivot', 'churn',
  'enterprise', 'sla', 'use-case', 'circle-back', 'ping', 'bandwidth', 'deep-dive',
  // Learned during the first two days.
  'container', 'docker', 'container-image', 'kubernetes', 'cluster', 'node', 'pod',
  'k8s-deployment', 'k8s-service', 'namespace', 'kubectl', 'helm', 'devops', 'cncf', 'cloud-native',
  'monitoring', 'logs', 'metrics', 'dashboard', 'alert', 'incident', 'on-call',
  'llm', 'prompt', 'token', 'machine-learning', 'gpu', 'gen-ai', 'query',
]

const LEARNING = ['observability', 'trace', 'span', 'slo', 'sli', 'error-budget', 'ai-agent', 'embedding', 'ingress', 'gitops']

const SAVED = ['slo', 'error-budget', 'ebpf', 'rag', 'hybrid-search', 'embedding']

/** Flashcard history the API keeps for her: some reviewed, a few already learned. */
const REVIEWS: Record<string, KnowledgePatch> = {
  kubernetes: { status: 'known', source: 'srs', reps: 4, ease: 2.7, interval_days: 9, learned: true },
  pod: { status: 'known', source: 'srs', reps: 4, ease: 2.6, interval_days: 8, learned: true },
  container: { status: 'known', source: 'srs', reps: 5, ease: 2.8, interval_days: 12, learned: true },
  observability: { status: 'learning', source: 'srs', reps: 2, ease: 2.5, interval_days: 3 },
  trace: { status: 'learning', source: 'srs', reps: 2, ease: 2.4, interval_days: 2 },
  slo: { status: 'learning', source: 'srs', reps: 1, ease: 2.3, interval_days: 1 },
  embedding: { status: 'learning', source: 'srs', reps: 1, ease: 2.5, interval_days: 1 },
}

const RETURNING_NAME = 'Priya'

function seedReturning(): void {
  clearIdentity()
  saveProfile({ name: RETURNING_NAME, persona: 'ana', lang: 'es' })
  const statuses: Record<string, KnowledgeStatus> = {}
  for (const id of KNOWN) statuses[id] = 'known'
  for (const id of LEARNING) statuses[id] = 'learning'
  storeKnowledge(statuses)
  storeSaved(SAVED)
}

/** Put the review history on the server under her new session. Best effort. */
async function pushReviews(): Promise<void> {
  try {
    const session = await ensureSession(RETURNING_NAME)
    const now = Date.now()
    await Promise.all(
      Object.entries(REVIEWS).map(([termId, patch]) => {
        const days = patch.interval_days ?? 0
        // Learned cards come due in the future; the ones in progress are due today.
        const dueAt = patch.learned ? now + days * DAY_MS : now - DAY_MS
        return putKnowledge(RETURNING_NAME, session.user_id, termId, { ...patch, due_at: dueAt })
      }),
    )
  } catch {
    // The local layer still carries her map and saved cards.
  }
}

/** Apply ?demo= if present, then drop it from the URL so a reload keeps the account. */
export async function applyDemoLink(): Promise<void> {
  const url = new URL(window.location.href)
  const demo = url.searchParams.get('demo')
  if (demo !== 'returning' && demo !== 'new') return
  url.searchParams.delete('demo')
  window.history.replaceState(null, '', url.toString())
  if (demo === 'new') {
    clearIdentity()
    return
  }
  seedReturning()
  void pushReviews()
}
