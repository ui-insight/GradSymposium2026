export interface CompetitionSettings {
  Event_ID: string;
  Required_Reviews: number | null;
  Assignment_Only: boolean | null;
  Aggregation: 'average' | 'total' | null;
  Tie_Policy: 'shared' | 'manual' | null;
  Award_Groups: string[] | null;
  Rules_Confirmed: boolean;
  Judging_Open: boolean;
}

export interface CoverageRow {
  Project_ID: string;
  Project_Number: string;
  Presenter_Display_Name: string;
  Project_Title: string;
  Judging_Eligible: boolean | null;
  Award_Groups: string[];
  Assigned_Judges: number;
  Complete_Reviews: number;
  Required_Reviews: number | null;
  Missing_Reviews: number | null;
}

export interface CompetitionStatus {
  Event_ID: string;
  Event_Name: string;
  Is_Rehearsal: boolean;
  settings: CompetitionSettings;
  missing: string[];
  coverage: CoverageRow[];
  Active_Judges: number;
  Eligible_Projects: number;
  Complete_Reviews: number;
  Projects_At_Target: number;
}

export interface JudgeConflict {
  Conflict_ID: number;
  Judge_ID: string;
  Project_ID: string;
  Judge_Name: string;
  Project_Number: string;
  Reason: string;
}

export interface VotingRound {
  Round_ID: string;
  Event_ID: string;
  Round_Name: string;
  Status: 'draft' | 'open' | 'closed';
  Min_Choices: number | null;
  Max_Choices: number | null;
  Ranked: boolean | null;
  Allow_Self_Votes: boolean | null;
  Allow_Edits: boolean | null;
  Opens_At: string | null;
  Closes_At: string | null;
  Rules_Confirmed: boolean;
}

export interface Voter {
  Voter_ID: string;
  Event_ID: string;
  Registration_Reference: string;
  Is_Active: boolean;
  Affiliation_Confirmed: boolean;
  Presenter_Project_IDs: string[];
}

export interface VoteTally {
  Project_Number: string;
  Presenter_Display_Name: string;
  Project_Title: string;
  Votes: number;
  Rank_Counts: Record<string, number>;
}

export interface VotingSummary {
  Round_ID: string;
  Ballots_Submitted: number;
  Voting_Open: boolean;
  Tallies_Available: boolean;
  missing: string[];
  tally: VoteTally[];
  Top_Ten_Report: AttendeeChoiceReport | null;
}

export interface AttendeeChoiceEntry {
  Project_Number: string;
  Presenter_Display_Name: string;
  Project_Title: string;
  Votes: number;
  Vote_Rank: number;
  Tied_Count: number;
}

export interface AttendeeChoiceReport {
  Eligible_Count: number;
  Top_Ten: AttendeeChoiceEntry[];
  Additional_Cutoff_Ties: AttendeeChoiceEntry[];
  Cutoff_Votes: number | null;
  Cutoff_Spans_Ten: boolean;
}

export interface SavedBallot {
  saved: boolean;
  Project_IDs: string[];
  Submitted_At: string | null;
  Updated_At: string | null;
}

export interface VotingPoster {
  Project_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_Display_Name: string;
  Institution: string | null;
  Can_Select: boolean;
}

export interface VoterSession {
  Event_Name: string;
  Is_Rehearsal: boolean;
  Affiliation_Confirmed: boolean;
  Presenter_Project_IDs: string[];
  rounds: VotingRound[];
}
