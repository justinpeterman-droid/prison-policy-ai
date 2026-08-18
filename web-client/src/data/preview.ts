import type {
  AccountSession,
  AuditEvent,
  JobSummary,
  PolicyDocument,
  Profile,
  ReportDetail,
  ReportSummary,
} from "../types";

export const previewOfficer: Profile = {
  accountId: "00000000-0000-4000-8000-000000000101",
  staffId: "00000000-0000-4000-8000-000000000201",
  employeeNumber: "F-1042",
  displayName: "Officer Jordan Lee",
  rank: "Officer",
  shift: "B Shift",
  role: "officer",
  status: "active",
  mustChangePin: false,
};

export const previewAdmin: Profile = {
  accountId: "00000000-0000-4000-8000-000000000102",
  staffId: "00000000-0000-4000-8000-000000000202",
  employeeNumber: "F-1007",
  displayName: "Lt. Avery Morgan",
  rank: "Lieutenant",
  shift: "A Shift",
  role: "admin",
  status: "active",
  mustChangePin: false,
};

export const previewReports: ReportSummary[] = [
  {
    reportId: "00000000-0000-4000-8000-000000001001",
    incidentId: "00000000-0000-4000-8000-000000002001",
    reportType: "Incident Report",
    relationship: "owned",
    reportingOfficerDisplayName: "Officer Jordan Lee",
    preparerDisplayName: "Officer Jordan Lee",
    category: "Contraband",
    incidentDate: "2026-08-17",
    status: "in_progress",
    updatedAt: "2026-08-18T15:42:00Z",
    currentRevisionNumber: 4,
  },
  {
    reportId: "00000000-0000-4000-8000-000000001002",
    incidentId: "00000000-0000-4000-8000-000000002002",
    reportType: "Use of Force Report",
    relationship: "owned",
    reportingOfficerDisplayName: "Officer Jordan Lee",
    preparerDisplayName: "Officer Jordan Lee",
    category: "Use of Force",
    incidentDate: "2026-08-14",
    status: "completed",
    updatedAt: "2026-08-15T02:18:00Z",
    currentRevisionNumber: 7,
  },
  {
    reportId: "00000000-0000-4000-8000-000000001003",
    incidentId: "00000000-0000-4000-8000-000000002003",
    reportType: "Incident Report",
    relationship: "prepared",
    reportingOfficerDisplayName: "Officer Casey Rivers",
    preparerDisplayName: "Officer Jordan Lee",
    category: "Medical Response",
    incidentDate: "2026-08-11",
    status: "completed",
    updatedAt: "2026-08-12T07:05:00Z",
    currentRevisionNumber: 5,
  },
  {
    reportId: "00000000-0000-4000-8000-000000001004",
    incidentId: "00000000-0000-4000-8000-000000002004",
    reportType: "Disciplinary Report",
    relationship: "owned",
    reportingOfficerDisplayName: "Officer Jordan Lee",
    preparerDisplayName: "Officer Jordan Lee",
    category: "Rule Violation",
    incidentDate: "2026-08-06",
    status: "archived",
    updatedAt: "2026-08-08T19:30:00Z",
    currentRevisionNumber: 3,
  },
];

export const previewReportDetail: ReportDetail = {
  ...previewReports[0],
  lastEditorDisplayName: "Officer Jordan Lee",
  createdAt: "2026-08-17T23:26:00Z",
  content: {
    schemaVersion: 1,
    narrative:
      "On August 17, 2026, at approximately 1840 hours, I conducted a routine inspection of Barracks 2. During the inspection, I observed an unauthorized item concealed beneath the lower bunk assigned to the involved resident. I secured the area, notified the shift supervisor, and maintained chain of custody until the item was transferred for processing.",
    editableFields: {
      facility: "North Unit",
      location: "Barracks 2, lower bunk area",
      incident_time: "18:40",
    },
    validation: {
      chronology: "complete",
      identities: "review_required",
      policy_alignment: "complete",
    },
    warnings: ["Confirm the property receipt number before finalizing."],
  },
};

export const previewJobs: JobSummary[] = [
  {
    id: "00000000-0000-4000-8000-000000003001",
    incidentId: previewReports[0].incidentId,
    jobType: "generate",
    state: "running",
    stage: "Drafting narrative",
    createdAt: "2026-08-18T15:40:00Z",
    completedAt: null,
    errorCode: null,
  },
  {
    id: "00000000-0000-4000-8000-000000003002",
    incidentId: previewReports[1].incidentId,
    jobType: "extract",
    state: "succeeded",
    stage: "Facts extracted",
    createdAt: "2026-08-14T23:44:00Z",
    completedAt: "2026-08-14T23:45:16Z",
    errorCode: null,
  },
];

export const previewSessions: AccountSession[] = [
  {
    sessionId: "00000000-0000-4000-8000-000000004001",
    deviceLabel: "Chrome on Windows",
    persistent: true,
    createdAt: "2026-08-10T14:15:00Z",
    lastUsedAt: "2026-08-18T17:08:00Z",
    renewalExpiresAt: "2026-09-17T17:08:00Z",
    current: true,
  },
  {
    sessionId: "00000000-0000-4000-8000-000000004002",
    deviceLabel: "Safari on iPhone",
    persistent: false,
    createdAt: "2026-08-16T21:05:00Z",
    lastUsedAt: "2026-08-16T21:48:00Z",
    renewalExpiresAt: "2026-08-17T09:05:00Z",
    current: false,
  },
];

export const previewPolicyDocuments: PolicyDocument[] = [
  {
    id: "policy-001",
    title: "Incident Reporting and Documentation",
    code: "OP-5.14",
    section: "Operations",
    updatedLabel: "Reviewed July 2026",
    summary: "Required content, review standards, timelines, and supervisory routing for incident reports.",
    tags: ["reports", "documentation", "supervision"],
    body: [
      "Staff must document material incidents in a clear chronological account using observed facts and attributable statements.",
      "Reports must identify the date, approximate time, location, involved persons, actions taken, notifications made, and disposition of evidence when applicable.",
      "Uncertain details must be labeled as estimates or attributed to the person who supplied them. Staff must not present assumptions as observed fact.",
    ],
  },
  {
    id: "policy-002",
    title: "Contraband Control and Evidence Handling",
    code: "SEC-3.07",
    section: "Security",
    updatedLabel: "Reviewed May 2026",
    summary: "Search, seizure, documentation, packaging, and chain-of-custody requirements.",
    tags: ["contraband", "evidence", "search"],
    body: [
      "Staff discovering suspected contraband must control the immediate area and avoid unnecessary handling.",
      "The discovering employee records where the item was found, who was present, and each transfer of custody.",
      "Evidence is packaged and labeled according to facility procedure before transfer to the designated custodian.",
    ],
  },
  {
    id: "policy-003",
    title: "Use of Force Review",
    code: "SEC-4.02",
    section: "Security",
    updatedLabel: "Reviewed August 2026",
    summary: "Authorization, reporting, medical review, video preservation, and supervisory assessment.",
    tags: ["force", "medical", "video"],
    body: [
      "Force is limited to the level objectively reasonable to accomplish a lawful correctional objective.",
      "Staff involved in or witnessing a reportable use of force complete separate accounts before the end of shift unless medically unable.",
      "Supervisors ensure medical assessment and preservation of relevant video and records.",
    ],
  },
  {
    id: "policy-004",
    title: "Emergency Medical Response",
    code: "MED-2.11",
    section: "Health Services",
    updatedLabel: "Reviewed June 2026",
    summary: "Initial response, communication, scene safety, documentation, and post-event review.",
    tags: ["medical", "emergency", "response"],
    body: [
      "Staff immediately summon medical assistance and provide care within training while maintaining scene safety.",
      "The report records observed condition, notifications, interventions, transfer of care, and any delay with its known reason.",
      "Protected medical details are included only when necessary for the operational record.",
    ],
  },
];

export const previewAuditEvents: AuditEvent[] = [
  {
    id: "audit-001",
    action: "report.updated",
    actor: "Lt. Avery Morgan",
    target: "Incident Report · …1001",
    result: "success",
    createdAt: "2026-08-18T16:52:00Z",
  },
  {
    id: "audit-002",
    action: "account.session_revoked",
    actor: "Lt. Avery Morgan",
    target: "F-1098",
    result: "success",
    createdAt: "2026-08-18T15:21:00Z",
  },
  {
    id: "audit-003",
    action: "policy.question",
    actor: "Officer Jordan Lee",
    target: "Policy Expert request",
    result: "success",
    createdAt: "2026-08-18T14:47:00Z",
  },
  {
    id: "audit-004",
    action: "ai.generate",
    actor: "Officer Casey Rivers",
    target: "Incident …2028",
    result: "error",
    createdAt: "2026-08-18T13:03:00Z",
  },
];
