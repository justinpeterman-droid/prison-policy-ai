import { z } from "zod";


export type AssignmentState = "unassigned" | "assigned" | "no_officer_available";
export type EquipmentState = "yes" | "no" | "not_checked";

export interface StaffSelection {
  staff_id: string;
  display_name_snapshot: string;
}

export interface RosterPostDefinition {
  code: string;
  label: string;
  priority: "P1" | "P2";
}

export interface RosterZoneDefinition {
  code: string;
  label: string;
  area: string;
  supervisor_label: string;
  posts: RosterPostDefinition[];
}

export interface RosterDefinition {
  facility_label: string;
  zones: RosterZoneDefinition[];
  assignment_states: AssignmentState[];
  assignment_columns: string[];
  operational_fields: string[];
  security_equipment: string[];
  sign_off_fields: string[];
  priority_one_warning: string;
  notes: string[];
  distribution: string[];
}

const post = (code: string, label: string, priority: "P1" | "P2"): RosterPostDefinition => ({ code, label, priority });

export const ROSTER_DEFINITION: RosterDefinition = {
  facility_label: "North Central Unit",
  zones: [
    {
      code: "zone_1", label: "Zone 1", area: "Bks 8-14 Hallway and Service Area", supervisor_label: "South Hall Sergeant",
      posts: [
        post("bks_8_control", "Bks 8 Control Booth", "P1"),
        post("bks_9_10_control", "Bks 9-10 Control Booth", "P1"),
        post("bks_9_10_desk", "Bks 9-10 Desk", "P2"),
        post("bks_11_12_control", "Bks 11-12 Control Booth", "P1"),
        post("bks_13_14_control", "Bks 13-14 Control Booth", "P1"),
        post("south_tower", "South Tower Officer", "P1"),
        post("east_tower", "East Tower Officer", "P1"),
        post("south_hall_rover", "South Hall Rover", "P2"),
      ],
    },
    {
      code: "zone_2", label: "Zone 2", area: "Bks 1-7 Hallway and Service Area", supervisor_label: "North Hall Sergeant",
      posts: [
        post("bks_1_control", "Bks 1 Control Booth", "P1"),
        post("bks_2_3_control", "Bks 2-3 Control Booth", "P1"),
        post("bks_4_5_control", "Bks 4-5 Control Booth", "P1"),
        post("bks_4_5_desk", "Bks 4-5 Desk", "P2"),
        post("bks_6_7_control", "Bks 6-7 Control Booth", "P1"),
        post("north_tower", "North Tower Officer", "P1"),
        post("west_tower", "West Tower Officer", "P1"),
        post("school_security", "School Security Officer", "P1"),
        post("north_hall_rover", "North Hall Rover", "P2"),
      ],
    },
    {
      code: "zone_3", label: "Zone 3", area: "Isolation and Service Area", supervisor_label: "Isolation Sergeant",
      posts: [
        post("isolation_1", "Isolation Officer #1", "P1"),
        post("isolation_2", "Isolation Officer #2", "P1"),
        post("isolation_rover", "Rover", "P2"),
      ],
    },
    {
      code: "zone_4", label: "Zone 4", area: "Front Entrance and Service Area", supervisor_label: "Front Entrance Sergeant",
      posts: [
        post("master_control_1", "Master Control #1", "P1"),
        post("master_control_2", "Master Control #2", "P2"),
        post("infirmary_officer", "Infirmary Officer", "P1"),
        post("outside_rover", "Outside Rover", "P1"),
        post("biometrics_lobby", "Biometrics Officer Lobby", "P2"),
        post("front_rover", "Rover", "P2"),
      ],
    },
    {
      code: "zone_5", label: "Zone 5", area: "Sally Port and Service Area", supervisor_label: "Sergeant",
      posts: [post("boiler_room", "Boiler Room", "P1")],
    },
  ],
  assignment_states: ["unassigned", "assigned", "no_officer_available"],
  assignment_columns: ["Initial Officer", "Rotation Officer"],
  operational_fields: ["Leave Time (Type of Leave)", "Extra Assignments", "Alternate Shift Supervisor", "Shift Briefing Minutes", "Roll Call", "Uniform Inspection", "Assigned to post and dismissed", "Security Equipment Accounted For", "Guests at Shift Briefing"],
  security_equipment: ["Digital Camera", "Video Camera (Go PRO)", "9 Metal Detector Wands"],
  sign_off_fields: ["Captain", "Lieutenant", "Duty Warden", "Lieutenant Signature", "Date"],
  priority_one_warning: "P1 posts must be staffed in accordance with unit policy or post orders unless otherwise directed by the Warden or Duty Warden; deviations require notification of the Duty Warden.",
  notes: ["NOA = No Officer Available", "CGPS = Cross Gender Pat Searches"],
  distribution: ["Assistant Warden", "Major", "Building Captain", "Control Center", "Human Resources", "Training Officer", "Shift Supervisor", "File"],
};

const staffSchema = z.object({
  staff_id: z.string().uuid(),
  display_name_snapshot: z.string().trim().min(1).max(160),
}).strict();
const stateSchema = z.enum(["unassigned", "assigned", "no_officer_available"]);
const postSchema = z.object({
  post_code: z.string(),
  initial_staff: staffSchema.nullable(),
  rotation_staff: staffSchema.nullable(),
  initial_state: stateSchema.default("unassigned"),
  rotation_state: stateSchema.default("unassigned"),
}).strict();
const zoneSchema = z.object({
  zone_code: z.string(),
  supervisor: staffSchema.nullable(),
  posts: z.array(postSchema),
}).strict();
const leaveSchema = z.object({ staff: staffSchema, leave_time: z.string().max(160), leave_type: z.string().max(160) }).strict();
const extraSchema = z.object({ label: z.string().trim().min(1).max(160), staff: staffSchema.nullable() }).strict();

export const rosterPayloadSchema = z.object({
  schema_version: z.literal(1),
  work_date: z.iso.date(),
  shift: z.string().min(1).max(32),
  captain: staffSchema.nullable(),
  lieutenant: staffSchema.nullable(),
  duty_warden: z.string().max(160).nullable(),
  alternate_shift_supervisor: staffSchema.nullable(),
  leave_entries: z.array(leaveSchema).max(40),
  extra_assignments: z.array(extraSchema).max(40),
  zones: z.array(zoneSchema).length(5),
  briefing_minutes: z.string().max(10_000),
  roll_call_completed: z.boolean(),
  uniform_inspection_completed: z.boolean(),
  equipment: z.object({
    digital_camera: z.enum(["yes", "no", "not_checked"]),
    video_camera_go_pro: z.enum(["yes", "no", "not_checked"]),
    metal_detector_wands: z.enum(["yes", "no", "not_checked"]),
  }).strict(),
  briefing_guests: z.array(z.string().trim().min(1).max(160)).max(20),
  assigned_and_dismissed: z.boolean(),
  lieutenant_signature_name: z.string().max(160).nullable(),
}).strict();

export type RosterPayload = z.infer<typeof rosterPayloadSchema>;
export type RosterPost = RosterPayload["zones"][number]["posts"][number];

export function createEmptyRosterPayload(workDate: string, shift: string): RosterPayload {
  return {
    schema_version: 1,
    work_date: workDate,
    shift,
    captain: null,
    lieutenant: null,
    duty_warden: null,
    alternate_shift_supervisor: null,
    leave_entries: [],
    extra_assignments: [],
    zones: ROSTER_DEFINITION.zones.map((zone) => ({
      zone_code: zone.code,
      supervisor: null,
      posts: zone.posts.map((item) => ({
        post_code: item.code,
        initial_staff: null,
        rotation_staff: null,
        initial_state: "unassigned",
        rotation_state: "unassigned",
      })),
    })),
    briefing_minutes: "",
    roll_call_completed: false,
    uniform_inspection_completed: false,
    equipment: {
      digital_camera: "not_checked",
      video_camera_go_pro: "not_checked",
      metal_detector_wands: "not_checked",
    },
    briefing_guests: [],
    assigned_and_dismissed: false,
    lieutenant_signature_name: null,
  };
}

export function parseRosterPayload(value: unknown): RosterPayload {
  const parsed = rosterPayloadSchema.parse(value);
  for (const [zoneIndex, zone] of parsed.zones.entries()) {
    const definition = ROSTER_DEFINITION.zones[zoneIndex];
    if (zone.zone_code !== definition.code) throw new Error("Roster zones do not match the approved definition.");
    const approved = new Set(definition.posts.map((item) => item.code));
    if (zone.posts.length !== approved.size || zone.posts.some((item) => !approved.has(item.post_code))) {
      throw new Error("Roster posts do not match the approved definition.");
    }
  }
  return parsed;
}

export function displayStaff(staff: StaffSelection | null, state: AssignmentState): string {
  if (state === "no_officer_available") return "NOA";
  return staff?.display_name_snapshot ?? "—";
}
