import type { KnowledgeStatus, Lang } from '@contracts'
import { readStored, readStoredJson, removeStored, writeStored } from '@/shared/storage'
import { isLang, isPersonaId, type PersonaId } from './personas'

const USER_ID_KEY = 'confpilot.user_id'
const PROFILE_KEY = 'confpilot.profile'
const KNOWLEDGE_KEY = 'confpilot.knowledge'
const SAVED_KEY = 'confpilot.saved'
const ROOM_CODE = /^[a-z0-9-]{1,32}$/

export interface Profile {
  name: string
  persona: PersonaId
  lang: Lang | null
}

function newUuid(): string {
  // randomUUID needs a secure context; phones on a LAN dev URL fall back to getRandomValues.
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6]! & 0x0f) | 0x40
  b[8] = (b[8]! & 0x3f) | 0x80
  const hex = [...b].map((x) => x.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

/** There is no login: the phone keeps a UUID, and switching persona makes a new one. */
export function getUserId(): string {
  const existing = readStored(USER_ID_KEY)
  if (existing) return existing
  const created = newUuid()
  writeStored(USER_ID_KEY, created)
  return created
}

function isProfile(value: unknown): value is Profile {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.name === 'string' &&
    v.name.trim().length > 0 &&
    isPersonaId(v.persona) &&
    (v.lang === null || isLang(v.lang))
  )
}

export function loadProfile(): Profile | null {
  return readStoredJson(PROFILE_KEY, isProfile)
}

export function saveProfile(profile: Profile): void {
  writeStored(PROFILE_KEY, JSON.stringify(profile))
}

/** Forget this persona entirely, so the next join starts as a new person. */
export function clearIdentity(): void {
  for (const key of [PROFILE_KEY, USER_ID_KEY, KNOWLEDGE_KEY, SAVED_KEY]) removeStored(key)
}

function isStatusMap(value: unknown): value is Record<string, KnowledgeStatus> {
  if (typeof value !== 'object' || value === null) return false
  return Object.values(value).every((s) => s === 'known' || s === 'learning' || s === 'unknown')
}

export function loadKnowledge(): Record<string, KnowledgeStatus> {
  return readStoredJson(KNOWLEDGE_KEY, isStatusMap) ?? {}
}

export function storeKnowledge(knowledge: Record<string, KnowledgeStatus>): void {
  writeStored(KNOWLEDGE_KEY, JSON.stringify(knowledge))
}

function isIdList(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === 'string')
}

export function loadSaved(): string[] {
  return readStoredJson(SAVED_KEY, isIdList) ?? []
}

export function storeSaved(termIds: string[]): void {
  writeStored(SAVED_KEY, JSON.stringify(termIds))
}

/** Room codes are short lowercase slugs, e.g. "slc1". Returns null when the input is not one. */
export function parseRoomCode(raw: string | null): string | null {
  const code = (raw ?? '').trim().toLowerCase()
  return ROOM_CODE.test(code) ? code : null
}
