/**
 * What to do after a conversation: sessions to attend and books to read, tagged with the
 * glossary terms they cover. The sessions are SAMPLES written for the demo (every title starts
 * with "Sample:"); swap in the real event schedule when there is one. The books are real titles.
 */

export type SessionKind = 'Talk' | 'Workshop'

export interface CatalogSession {
  id: string
  kind: SessionKind
  title: string
  when: string
  room: string
  termIds: readonly string[]
}

export interface CatalogBook {
  id: string
  title: string
  author: string
  category: string
  termIds: readonly string[]
}

export const SESSIONS: readonly CatalogSession[] = [
  {
    id: 'rag-zero',
    kind: 'Workshop',
    title: 'Sample: RAG from zero: chunking, embeddings and retrieval',
    when: '3:00 PM',
    room: 'Room B',
    termIds: ['rag', 'chunking', 'embedding', 'vector', 'retrieval', 'llm', 'context-window', 'knowledge-base'],
  },
  {
    id: 'agents-mcp',
    kind: 'Talk',
    title: 'Sample: Building AI agents with MCP',
    when: '3:45 PM',
    room: 'Room A',
    termIds: ['ai-agent', 'mcp', 'guardrails', 'evals', 'llm', 'prompt', 'hallucination', 'inference'],
  },
  {
    id: 'hybrid-search',
    kind: 'Talk',
    title: 'Sample: Hybrid search in practice: BM25, vectors and RRF',
    when: '4:15 PM',
    room: 'Room C',
    termIds: ['hybrid-search', 'bm25', 'rrf', 'vector-database', 'semantic-search', 'keyword-search', 'reranker', 'elasticsearch'],
  },
  {
    id: 'k8s-101',
    kind: 'Workshop',
    title: 'Sample: Kubernetes 101: pods, deployments and services',
    when: '2:30 PM',
    room: 'Room D',
    termIds: ['kubernetes', 'pod', 'cluster', 'node', 'k8s-deployment', 'k8s-service', 'kubectl', 'container', 'docker'],
  },
  {
    id: 'helm-operators',
    kind: 'Talk',
    title: 'Sample: Helm, operators and CRDs without the fear',
    when: '4:45 PM',
    room: 'Room A',
    termIds: ['helm', 'k8s-operator', 'crd', 'manifest', 'namespace', 'control-plane', 'sidecar', 'service-mesh'],
  },
  {
    id: 'otel-e2e',
    kind: 'Workshop',
    title: 'Sample: OpenTelemetry end to end',
    when: '3:30 PM',
    room: 'Room E',
    termIds: ['opentelemetry', 'trace', 'span', 'metrics', 'logs', 'observability', 'telemetry', 'rum', 'apm'],
  },
  {
    id: 'slo-budgets',
    kind: 'Talk',
    title: 'Sample: SLOs and error budgets for humans',
    when: '5:00 PM',
    room: 'Room B',
    termIds: ['sli', 'slo', 'error-budget', 'sre', 'percentile-latency', 'alert', 'incident', 'on-call', 'mttr'],
  },
  {
    id: 'demo-to-startup',
    kind: 'Talk',
    title: 'Sample: From hackathon demo to funded startup',
    when: '5:15 PM',
    room: 'Room C',
    termIds: ['mvp', 'poc', 'product-market-fit', 'series-funding', 'venture-capital', 'runway', 'go-to-market', 'ipo'],
  },
]

export const BOOKS: readonly CatalogBook[] = [
  { id: 'ai-engineering', title: 'AI Engineering', author: 'Chip Huyen', category: 'ai', termIds: ['rag', 'llm', 'evals', 'fine-tuning'] },
  {
    id: 'k8s-up-running',
    title: 'Kubernetes: Up and Running',
    author: 'Brendan Burns, Joe Beda, Kelsey Hightower and Lachlan Evenson',
    category: 'cloud',
    termIds: ['kubernetes', 'pod', 'helm'],
  },
  {
    id: 'observability-engineering',
    title: 'Observability Engineering',
    author: 'Charity Majors, Liz Fong-Jones and George Miranda',
    category: 'ops',
    termIds: ['observability', 'slo', 'trace'],
  },
  { id: 'relevant-search', title: 'Relevant Search', author: 'Doug Turnbull and John Berryman', category: 'data', termIds: ['bm25', 'relevance'] },
  {
    id: 'pragmatic-programmer',
    title: 'The Pragmatic Programmer',
    author: 'David Thomas and Andrew Hunt',
    category: 'tech',
    termIds: ['refactor', 'git'],
  },
  { id: 'lean-startup', title: 'The Lean Startup', author: 'Eric Ries', category: 'business', termIds: ['mvp', 'pivot'] },
]

/** A search link for a book, so we never guess a store or publisher URL. */
export function bookLink(book: Pick<CatalogBook, 'title' | 'author'>): string {
  return `https://openlibrary.org/search?q=${encodeURIComponent(`${book.title} ${book.author}`)}`
}
