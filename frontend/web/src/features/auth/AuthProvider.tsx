import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { WebApiError } from "../../api/client";
import {
  getBrowserSession,
  loginBrowserSession,
  logoutBrowserSession,
  type SessionProfile,
} from "./api";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

interface AuthContextValue {
  status: AuthStatus;
  profile: SessionProfile | null;
  message: string | null;
  signIn(input: { employeeNumber: string; pin: string; persistent: boolean }): Promise<void>;
  signOut(): Promise<void>;
  refresh(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function userMessage(error: unknown): string {
  if (error instanceof WebApiError) return error.message;
  return "The sign-in service returned an unreadable response.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [profile, setProfile] = useState<SessionProfile | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const apply = useCallback((authenticated: boolean, nextProfile: SessionProfile | null) => {
    setProfile(nextProfile);
    setStatus(authenticated && nextProfile ? "authenticated" : "unauthenticated");
    setMessage(null);
  }, []);

  const refresh = useCallback(async () => {
    // Keep an authenticated workspace mounted while refreshing rotated session
    // cookies (for example after a PIN change). Initial and signed-out checks
    // still show the dedicated loading screen.
    setStatus((current) => current === "authenticated" ? current : "loading");
    try {
      const state = await getBrowserSession();
      apply(state.authenticated, state.profile);
    } catch (error) {
      setProfile(null);
      setStatus("error");
      setMessage(userMessage(error));
    }
  }, [apply]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(async (input: {
    employeeNumber: string;
    pin: string;
    persistent: boolean;
  }) => {
    setMessage(null);
    try {
      const state = await loginBrowserSession(input);
      apply(state.authenticated, state.profile);
    } catch (error) {
      setProfile(null);
      setStatus("unauthenticated");
      setMessage(userMessage(error));
      throw error;
    }
  }, [apply]);

  const signOut = useCallback(async () => {
    try {
      await logoutBrowserSession();
    } finally {
      apply(false, null);
    }
  }, [apply]);

  const value = useMemo<AuthContextValue>(() => ({
    status,
    profile,
    message,
    signIn,
    signOut,
    refresh,
  }), [status, profile, message, signIn, signOut, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
