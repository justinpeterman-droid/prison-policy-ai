export const ACCOUNT_ROUTES = {
  changePin: {
    method: "POST",
    path: "/change-pin",
    bodyFields: ["current_pin", "new_pin"],
  },
  logoutAll: {
    method: "POST",
    path: "/logout-all",
    bodyFields: [],
  },
  sessions: {
    method: "GET",
    path: "/sessions",
    bodyFields: [],
  },
  revokeSession: {
    method: "DELETE",
    path: "/sessions/<uuid:session_id>",
    bodyFields: [],
  },
} as const;

export const ACCOUNT_PIN_FIELDS = {
  current: "current_pin",
  newPin: "new_pin",
  confirm: null,
} as const;
