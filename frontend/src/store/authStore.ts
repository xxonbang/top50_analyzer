import { create } from 'zustand';
import { supabase } from '@/lib/supabase';
import { ExpireStorage } from '@/lib/expire-storage';
import type { User, Session, AuthError } from '@supabase/supabase-js';

/** 비활성 자동 로그아웃 시간 (1시간) */
const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000;

/** 활동 감지 쓰로틀 간격 (30초) */
const ACTIVITY_THROTTLE_MS = 30 * 1000;

// 모듈 스코프 타이머 변수 (Zustand store 외부)
let inactivityTimer: ReturnType<typeof setTimeout> | null = null;
let lastActivity = Date.now();
let activityListenersAttached = false;
let initialized = false;

function checkAdmin(user: User | null): boolean {
  return user?.app_metadata?.role === 'admin';
}

function clearInactivityTimer() {
  if (inactivityTimer) {
    clearTimeout(inactivityTimer);
    inactivityTimer = null;
  }
}

function startInactivityTimer() {
  clearInactivityTimer();
  inactivityTimer = setTimeout(() => {
    supabase.auth.signOut();
  }, INACTIVITY_TIMEOUT_MS);
}

function handleActivity() {
  const now = Date.now();
  if (now - lastActivity > ACTIVITY_THROTTLE_MS) {
    lastActivity = now;
    startInactivityTimer();
  }
}

const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'scroll', 'touchstart'] as const;

function attachActivityListeners() {
  if (activityListenersAttached) return;
  ACTIVITY_EVENTS.forEach((event) =>
    window.addEventListener(event, handleActivity, { passive: true })
  );
  activityListenersAttached = true;
}

function detachActivityListeners() {
  if (!activityListenersAttached) return;
  ACTIVITY_EVENTS.forEach((event) =>
    window.removeEventListener(event, handleActivity)
  );
  activityListenersAttached = false;
}

interface AuthStore {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  isAdmin: boolean;
  initialize: () => Promise<void>;
  signUp: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  session: null,
  isLoading: true,
  isAdmin: false,

  initialize: async () => {
    const { data: { session } } = await supabase.auth.getSession();
    const user = session?.user ?? null;
    const isAdmin = checkAdmin(user);

    // admin 상태를 ExpireStorage에 동기화
    ExpireStorage.setAdmin(isAdmin);

    set({
      session,
      user,
      isLoading: false,
      isAdmin,
    });

    // admin이 아니고 로그인 상태이면 비활성 타이머 시작
    if (user && !isAdmin) {
      lastActivity = Date.now();
      startInactivityTimer();
      attachActivityListeners();
    }

    // 중복 등록 방지 (React strict mode 등으로 initialize가 여러 번 호출될 수 있음)
    if (initialized) return;
    initialized = true;

    // 탭 복귀 시 세션 재확인 (visibilitychange)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState !== 'visible') return;
      const { user: currentUser, isAdmin: currentIsAdmin } = get();
      if (!currentUser || currentIsAdmin) return;

      supabase.auth.getSession().then(({ data: { session } }) => {
        if (!session) {
          // ExpireStorage에서 만료 감지됨 → 상태 초기화
          set({ session: null, user: null, isAdmin: false });
          clearInactivityTimer();
          detachActivityListeners();
        }
      });
    });

    // auth 상태 변경 감지
    supabase.auth.onAuthStateChange((_event, session) => {
      const user = session?.user ?? null;
      const isAdmin = checkAdmin(user);

      ExpireStorage.setAdmin(isAdmin);

      set({
        session,
        user,
        isAdmin,
      });

      if (_event === 'SIGNED_OUT') {
        ExpireStorage.setAdmin(false);
        clearInactivityTimer();
        detachActivityListeners();
      } else if (user && !isAdmin) {
        lastActivity = Date.now();
        startInactivityTimer();
        attachActivityListeners();
      } else {
        // admin이거나 user가 없으면 타이머 불필요
        clearInactivityTimer();
        detachActivityListeners();
      }
    });
  },

  signUp: async (email, password) => {
    const { error } = await supabase.auth.signUp({ email, password });
    return { error };
  },

  signIn: async (email, password) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return { error };
  },

  signOut: async () => {
    clearInactivityTimer();
    detachActivityListeners();
    await supabase.auth.signOut();
  },
}));
