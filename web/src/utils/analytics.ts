import posthog from 'posthog-js'
import type { SessionUser, UserInfo } from '@/models/LoginModels'

type AnalyticsUser = Pick<SessionUser, 'user_id' | 'user_no' | 'name' | 'status' | 'email' | 'phone'>

type AttributionSnapshot = {
  first_touch_source?: string
  first_touch_medium?: string
  first_touch_campaign?: string
  first_touch_referrer?: string
  landing_path?: string
}

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY?.trim()
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST?.trim() || 'https://us.i.posthog.com'
const ATTRIBUTION_STORAGE_KEY = 'api35:first-touch-attribution'

let initialized = false

function isBrowser() {
  return typeof window !== 'undefined'
}

function isObjectEmpty(value: Record<string, unknown>) {
  return Object.values(value).every((item) => item === undefined || item === null || item === '')
}

function readAttributionSnapshot(): AttributionSnapshot | null {
  if (!isBrowser()) {
    return null
  }
  const raw = window.localStorage.getItem(ATTRIBUTION_STORAGE_KEY)
  if (!raw) {
    return null
  }
  try {
    const parsed = JSON.parse(raw) as AttributionSnapshot
    return parsed
  } catch {
    window.localStorage.removeItem(ATTRIBUTION_STORAGE_KEY)
    return null
  }
}

export function getAnalyticsGrowthContext(): AttributionSnapshot | null {
  const snapshot = ensureAttributionSnapshot()
  return isObjectEmpty(snapshot) ? null : snapshot
}

function buildAttributionSnapshot(): AttributionSnapshot {
  if (!isBrowser()) {
    return {}
  }
  const params = new URLSearchParams(window.location.search)
  return {
    first_touch_source: params.get('utm_source') || undefined,
    first_touch_medium: params.get('utm_medium') || undefined,
    first_touch_campaign: params.get('utm_campaign') || undefined,
    first_touch_referrer: document.referrer || undefined,
    landing_path: `${window.location.pathname}${window.location.search}`,
  }
}

function ensureAttributionSnapshot() {
  const existing = readAttributionSnapshot()
  if (existing) {
    return existing
  }
  const snapshot = buildAttributionSnapshot()
  if (!isObjectEmpty(snapshot)) {
    window.localStorage.setItem(ATTRIBUTION_STORAGE_KEY, JSON.stringify(snapshot))
  }
  return snapshot
}

function getEventDefaults() {
  const attribution = ensureAttributionSnapshot()
  return {
    ...attribution,
    page_path: isBrowser() ? window.location.pathname : undefined,
  }
}

export function isAnalyticsEnabled() {
  return Boolean(POSTHOG_KEY)
}

export function initializeAnalytics() {
  if (initialized || !POSTHOG_KEY || !isBrowser()) {
    return
  }
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    defaults: '2026-01-30',
    person_profiles: 'identified_only',
    autocapture: false,
  })
  initialized = true
  ensureAttributionSnapshot()
}

export function identifyAnalyticsUser(user: AnalyticsUser | UserInfo) {
  if (!isAnalyticsEnabled()) {
    return
  }
  initializeAnalytics()
  const distinctId = user.user_no || `user:${user.user_id}`
  posthog.identify(distinctId, {
    user_id: user.user_id,
    user_no: user.user_no,
    name: user.name,
    email: user.email || undefined,
    phone: user.phone || undefined,
    status: user.status,
  })
}

export function resetAnalyticsUser() {
  if (!isAnalyticsEnabled()) {
    return
  }
  initializeAnalytics()
  posthog.reset()
}

export function captureAnalyticsEvent(event: string, properties: Record<string, unknown> = {}) {
  if (!isAnalyticsEnabled()) {
    return
  }
  initializeAnalytics()
  posthog.capture(event, {
    ...getEventDefaults(),
    ...properties,
  })
}
