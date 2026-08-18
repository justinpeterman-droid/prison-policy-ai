import {
  createContext,
  type FormEvent,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiRequest, designPreviewEnabled } from "../api/client";
import { previewAdmin, previewOfficer } from "../data/preview";
import type { BrowserSessionState, Profile } from "../types";

export type AuthStatus = "loading" | "signed-out" | "signed-in";

interface LoginInput {
  employeeNumber: string;
  pin: string;
  persistent: boolean;
}

interface ChangePinInput {
  currentPin: string;
  newPin: string;
}

interface RawProfile {
  account_id?: string;
  accountId?: string;
  staff_id?: string;
  staffId?: string;
  employee_number?: string;
  employeeNumber?: string;
  display_name?: string;
  displayName?: string;
  rank?: string | null;
  shift?: string | null;
  role: "officer" | "admin";
  status: "active" | "locked" | "disabled";
  must_change_pin?: boolean;
  mustChangePin?: boolean;
}

interface RawBrowserSession {
  authenticated?: boolean;
  profile?: RawProfile | null;
  session_id?: string;
  current_session_id?: string;
  persistent?: boolean;
  access_expires_at?: string;
  requires_pin_change?: boolean;
}

interface AuthContextValue {
  status: AuthStatus;
  profile: Profile | null;
  session: BrowserSessionState | null;
  isDesignPreview: boolean;
  login(input: LoginInput): Promise<void>;
  logout(): Promise<void>;
  changePin(input: ChangePinInput): Promise<void>;
  refresh(): Promise<void>;
  previewAs(role: "officer" | "admin"): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function browserDeviceId(): string {
  // A browser identifier is intentionally ephemeral here. The server-side browser
  // adapter owns durable device/session semantics and credentials.
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return `browser-${Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function browserLabel(): string {
  const browserNavigator = navigator as Navigator & {
    userAgentData?: { platform?: string };
  };
  const platform =
    browserNavigator.userAgentData?.platform || browserNavigator.platform || "Unknown device";
  return `Web browser on ${platform}`.slice(0, 120);
}

function mapProfile(raw: RawProfile): Profile {
  return {
    accountId: raw.account_id ?? raw.accountId ?? "",
    staffId: raw.staff_id ?? raw.staffId ?? "",
    employeeNumber: raw.employee_number ?? raw.employeeNumber ?? "",
    displayName: raw.display_name ?? raw.displayName ?? "Staff member",
    rank: raw.rank ?? null,
    shift: raw.shift ?? null,
    role: raw.role,
    status: raw.status,
    mustChangePin: raw.must_change_pin ?? raw.mustChangePin ?? false,
  };
}

function mapSession(raw: RawBrowserSession): BrowserSessionState {
  const profile = raw.profile ? mapProfile(raw.profile) : null;
  if (profile && raw.requires_pin_change !== undefined) {
    profile.mustChangePin = raw.requires_pin_change;
  }
  return {
    authenticated: raw.authenticated ?? Boolean(profile),
    profile,
    currentSessionId: raw.current_session_id ?? raw.session_id,
    persistent: raw.persistent,
    accessExpiresAt: raw.access_expires_at,
  };
}

function previewProfileFromUrl(): Profile {
  const role = new URLSearchParams(window.location.search).get("role");
  return role === "admin" ? previewAdmin : previewOfficer;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [session, setSession] = useState<BrowserSessionState | null>(null);
  const [deviceId] = useState(browserDeviceId);

  const applySession = useCallback((next: BrowserSessionState | null) => {
    setSession(next);
    setStatus(next?.authenticated && next.profile ? "signed-in" : "signed-out");
  }, []);

  const refresh = useCallback(async () => {
    if (designPreviewEnabled) {
      const signedOut = new URLSearchParams(window.location.search).get("signedout") === "1";
      applySession(
        signedOut
          ? null
          : {
              authenticated: true,
              profile: previewProfileFromUrl(),
              currentSessionId: "preview-session",
              persistent: true,
            },
      );
      return;
    }

    try {
      const raw = await apiRequest<RawBrowserSession>("/web-auth/session");
      applySession(mapSession(raw));
    } catch (error) {
      if (error instanceof Error && "status" in error && (error as { status: number }).status === 401) {
        applySession(null);
        return;
      }
      setStatus("signed-out");
      setSession(null);
    }
  }, [applySession]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(
    async ({ employeeNumber, pin, persistent }: LoginInput) => {
      if (designPreviewEnabled) {
        const profile = employeeNumber.toLowerCase().includes("admin") ? previewAdmin : previewOfficer;
        applySession({
          authenticated: true,
          profile,
          currentSessionId: "preview-session",
          persistent,
        });
        return;
      }
      const raw = await apiRequest<RawBrowserSession>("/web-auth/login", {
        method: "POST",
        body: JSON.stringify({
          employee_number: employeeNumber,
          pin,
          device_id: deviceId,
          device_label: browserLabel(),
          persistent,
        }),
      });
      applySession(mapSession(raw));
    },
    [applySession, deviceId],
  );

  const logout = useCallback(async () => {
    if (!designPreviewEnabled) {
      await apiRequest<void>("/web-auth/logout", { method: "POST", body: JSON.stringify({}) });
    }
    applySession(null);
  }, [applySession]);

  const changePin = useCallback(
    async ({ currentPin, newPin }: ChangePinInput) => {
      if (!designPreviewEnabled) {
        const raw = await apiRequest<RawBrowserSession>("/web-auth/change-pin", {
          method: "POST",
          body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }),
        });
        applySession(mapSession(raw));
        return;
      }
      if (!session?.profile) return;
      applySession({
        ...session,
        profile: { ...session.profile, mustChangePin: false },
      });
    },
    [applySession, session],
  );

  const previewAs = useCallback(
    (role: "officer" | "admin") => {
      if (!designPreviewEnabled) return;
      applySession({
        authenticated: true,
        profile: role === "admin" ? previewAdmin : previewOfficer,
        currentSessionId: "preview-session",
        persistent: true,
      });
    },
    [applySession],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      profile: session?.profile ?? null,
      session,
      isDesignPreview: designPreviewEnabled,
      login,
      logout,
      changePin,
      refresh,
      previewAs,
    }),
    [status, session, login, logout, changePin, refresh, previewAs],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export function preventDefault<T extends HTMLElement>(
  handler: () => void | Promise<void>,
): (event: FormEvent<T>) => void {
  return (event) => {
    event.preventDefault();
    void handler();
  };
}
