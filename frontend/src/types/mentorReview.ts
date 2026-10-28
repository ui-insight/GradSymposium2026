export type MentorDecision = 'clear' | 'conflict' | 'needs_input';
export type MentorStatus = MentorDecision | 'unreviewed' | 'stale';
export interface MentorJudge {
  Judge_ID: string; Name: string; Department: string | null;
  Is_Active: boolean; Conflict_Review_Required: boolean; Previous_Name: string | null;
}
export interface MentorProject {
  Project_ID: string; Project_Number: string; Project_Title: string;
  Presenter_Name: string; Advisor_Name: string | null; Institution: string | null;
  Is_Active: boolean; Judging_Eligible: boolean | null; Roster_Review_Required: boolean;
  Required: boolean; Assigned: boolean; Has_Scores: boolean;
  Status: MentorStatus; Note: string; Reviewed_By: string | null; Reviewed_At: string | null;
  Conflict_ID: number | null; Conflict_Reason: string | null; Context: string;
}
export interface MentorWorkspace {
  Event_ID: string; Event_Name: string; Judges: MentorJudge[]; Judge_ID: string | null;
  Projects: MentorProject[]; Remaining: number; Completion_Blockers: string[];
  Context: string; Required_Reviews: number | null;
  Assignment_Shortages: { Project_Number: string; Assigned: number; Target: number }[];
}
export interface MentorImportPreview {
  Rows: { Row: number; Action?: string; Judge_ID: string | null; Judge_Name?: string;
    First_Name?: string; Last_Name?: string; Email?: string | null; Department?: string | null; Current_Name?: string | null;
    Project_Number?: string; Decision?: MentorDecision; Note?: string;
    Assignment_Removed?: boolean; Historical_Scores_Excluded?: boolean }[];
  Errors: string[]; Context: string; Applied: boolean;
}
