/** 절대 세션 유효 시간 (8시간) */
const SESSION_DURATION_MS = 8 * 60 * 60 * 1000

/** 내부 래핑 형식 식별용 키 */
const EXPIRE_MARKER = "__expire__"

/** 특정 역할(admin 등) 만료 면제 플래그 키 */
const ADMIN_FLAG_KEY = "__session_is_admin__"

interface WrappedItem {
  value: string
  [key: string]: unknown
}

function isWrappedItem(obj: unknown): obj is WrappedItem {
  return (
    typeof obj === "object" &&
    obj !== null &&
    "value" in obj &&
    EXPIRE_MARKER in (obj as Record<string, unknown>)
  )
}

export const ExpireStorage = {
  setAdmin(isAdmin: boolean): void {
    if (isAdmin) {
      localStorage.setItem(ADMIN_FLAG_KEY, "1")
    } else {
      localStorage.removeItem(ADMIN_FLAG_KEY)
    }
  },

  isAdmin(): boolean {
    return localStorage.getItem(ADMIN_FLAG_KEY) === "1"
  },

  getItem(key: string): string | null {
    const raw = localStorage.getItem(key)
    if (raw === null) return null

    try {
      const parsed: unknown = JSON.parse(raw)

      if (isWrappedItem(parsed)) {
        if (this.isAdmin()) return parsed.value

        if (Date.now() > (parsed as Record<string, number>)[EXPIRE_MARKER]) {
          localStorage.removeItem(key)
          return null
        }

        return parsed.value
      }
    } catch {
      // JSON 파싱 실패 → 일반 문자열
    }

    return raw
  },

  setItem(key: string, value: string): void {
    const item = {
      value,
      [EXPIRE_MARKER]: Date.now() + SESSION_DURATION_MS,
    }
    localStorage.setItem(key, JSON.stringify(item))
  },

  removeItem(key: string): void {
    localStorage.removeItem(key)
  },
}
