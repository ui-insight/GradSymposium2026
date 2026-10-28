import type { PublicPosterDirectory } from './index';

export interface RosterSource {
  source_file: string; source_sha256: string; source_sheet: string;
  source_row: number; submitted_at: string; requested_formats: string;
  current_position: string; flags: string[]; duplicate_rows: number[];
}
export interface RosterDecision {
  Decision_ID: number; Decision: 'accepted' | 'withdrawn' | 'pending'; Reason: string;
  Recorded_By: string; Recorded_At: string; Superseded_By: string | null;
  Snapshot: { Project_Number: string; Project_Title: string; Presenter_Name: string };
}
export interface RosterRow {
  Project_ID: string; Project_Number: string; Project_Title: string;
  Presenter_Name: string; Institution: string | null; Advisor_Name: string | null;
  Table_Number: string | null; Source: RosterSource | null; Is_Active: boolean;
  Judging_Eligible: boolean | null; Voting_Eligible: boolean | null;
  Acceptance: 'accepted' | 'withdrawn' | 'pending'; Changed: boolean;
  Is_Published: boolean; Assigned_Count: number; Score_Count: number;
  Context: string; Decision: RosterDecision | null; History: RosterDecision[];
}
export interface DuplicateGroup {
  Source_Rows: number[]; Project_IDs: string[]; Later_ID: string | null; Complete_Source: boolean;
}
export interface RosterWorkspace {
  Event_ID: string; Event_Name: string;
  Final_Review_Required: boolean;
  Counts: { Total: number; Source: number; Additions: number; Accepted: number; Withdrawn: number; Pending: number; Changed: number };
  Sources: { SHA256: string; Sheet: string; Rows: number[]; Accepted: number; Withdrawn: number; Pending: number }[];
  Rows: RosterRow[]; Duplicate_Groups: DuplicateGroup[]; Blockers: string[]; Context: string;
  Signoff: { Signed_By: string; Signed_At: string; Reference: string; Accepted_Count: number; Current: boolean } | null;
  Preview: Pick<PublicPosterDirectory, 'event' | 'posters'>;
}
export interface RosterChangePreview {
  Rows: { Row: number; Action: string; Reason: string; Project_ID: string; Project_Number: string | null;
    Presenter_Name: string; Title?: string; Payload: Record<string, unknown>; Assignments_Removed?: number }[];
  Errors: string[]; Context: string; Applied: boolean;
}
