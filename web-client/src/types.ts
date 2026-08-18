export type UserRole = "officer" | "admin";
export type AccountStatus = "active" | "locked" | "disabled";
export type ReportStatus = "in_progress" | "completed" | "archived";
export type Relationship = "owned" | "prepared";

export interface Profile {
  accountId: string;
  staffId: string;
  employeeNumber: string;
  displayName: string;
  rank: string | null;
  shift: string | null;
  role: UserRole;
  status: AccountStatus;
  mustChangePin: boolean;
}

export interface BrowserSessionState {
  authenticated: boolean;
  profile: Profile | null;
  currentSessionId?: string;
  persistent?: boolean;
  accessExpiresAt?: string;
}

export interface AccountSession {
  sessionId: string;
  deviceLabel: string;
  persistent: boolean;
  createdAt: string;
  lastUsedAt: string;
  renewalExpiresAt: string;
  current: boolean;
}

export interface ReportSummary {
  reportId: string;
  incidentId: string;
  reportType: string;
  relationship: Relationship;
  reportingOfficerDisplayName: string;
  preparerDisplayName: string;
  category: string | null;
  incidentDate: string | null;
  status: ReportStatus;
  updatedAt: string;
  currentRevisionNumber: number;
}

export interface ReportContent {
  schemaVersion: 1;
  narrative: string;
  editableFields: Record<string, string | number | boolean | null>;
  validation: Record<string, unknown>;
  warnings: string[];
}

export interface ReportDetail extends ReportSummary {
  content: ReportContent;
  lastEditorDisplayName: string;
  createdAt: string;
}

export interface JobSummary {
  id: string;
  incidentId: string;
  jobType: "classify" | "extract" | "generate" | "disciplinary";
  state: "queued" | "running" | "succeeded" | "failed";
  stage: string;
  createdAt: string;
  completedAt: string | null;
  errorCode: string | null;
}

export interface PolicyCitation {
  n: number;
  source: string;
  text: string;
}

export interface PolicyAnswer {
  answer: string;
  citations: PolicyCitation[];
  sources: string[];
  retrievedSources: string[];
}

export interface PolicyTurn {
  id: string;
  question: string;
  answer: string;
  citations: PolicyCitation[];
  createdAt: string;
}

export interface PolicyDocument {
  id: string;
  title: string;
  code: string;
  section: string;
  updatedLabel: string;
  summary: string;
  body: string[];
  tags: string[];
}

export interface AuditEvent {
  id: string;
  action: string;
  actor: string;
  target: string;
  result: "success" | "error";
  createdAt: string;
}
