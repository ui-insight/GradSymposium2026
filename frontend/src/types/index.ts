export interface Event {
  Event_ID: string;
  Event_Name: string;
  Event_Date: string;
  Event_End_Date: string | null;
  Public_Poster_Lookup_Enabled: boolean;
  Location: string | null;
  Description: string | null;
  Is_Active: boolean;
  Created_At: string;
}

export interface Project {
  Project_ID: string;
  Event_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_First_Name: string;
  Presenter_Last_Name: string;
  Presenter_Email: string | null;
  Presenter_Display_Name: string | null;
  Institution: string | null;
  Judging_Eligible: boolean | null;
  Voting_Eligible: boolean | null;
  Award_Groups: string[] | null;
  Is_Published: boolean;
  Roster_Review_Required: boolean;
  Roster_Review: {
    source_file: string;
    source_sheet: string;
    source_row: number;
    source_sha256: string;
    requested_formats: string;
    current_position: string;
    submitted_at: string;
    flags: string[];
    duplicate_rows: number[];
  } | null;
  Department: string | null;
  College: string | null;
  Advisor_Name: string | null;
  Category: 'Poster' | 'Art';
  Table_Number: string | null;
  Is_Active: boolean;
  score_count: number;
}

export interface Judge {
  Name_Confirmed_At: string | null;
  Previous_Name: string | null;
  Conflict_Review_Required: boolean;
  Judge_ID: string;
  Event_ID: string;
  First_Name: string;
  Last_Name: string;
  Email: string | null;
  Department: string | null;
  Access_Code: string;
  Is_Active: boolean;
  assignment_count: number;
  score_count: number;
}

export interface JudgeProfile {
  Judge_ID: string;
  Event_ID: string;
  First_Name: string;
  Last_Name: string;
  Name_Confirmed_At: string | null;
  Conflict_Review_Required: boolean;
}

export interface Criterion {
  Criterion_ID: number;
  Rubric_ID: string;
  Criterion_Name: string;
  Criterion_Group: string | null;
  Description: string | null;
  Min_Score: number;
  Max_Score: number;
  Sort_Order: number;
}

export interface Rubric {
  Score_Labels: Record<string, string> | null;
  Is_Locked: boolean;
  Rubric_ID: string;
  Event_ID: string;
  Rubric_Name: string;
  Category: string;
  Max_Score: number;
  Description: string | null;
  criteria: Criterion[];
}

export interface ProjectResult {
  Required_Reviews: number | null;
  Meets_Review_Target: boolean | null;
  Award_Groups: string[];
  Tied: boolean;
  Provisional: boolean;
  Project_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_First_Name: string;
  Presenter_Last_Name: string;
  Presenter_Display_Name: string | null;
  Department: string | null;
  Category: string;
  Judge_Count: number;
  Total_Score: number;
  Average_Score: number;
  Rank: number;
}

export interface ScoreOverride {
  Override_ID: number;
  Old_Score_Value: number;
  New_Score_Value: number;
  Admin_Username: string;
  Overridden_At: string;
}

export interface ProjectScoreReviewCriterion {
  Score_ID: number;
  Criterion_ID: number;
  Criterion_Name: string;
  Criterion_Group: string | null;
  Min_Score: number;
  Max_Score: number;
  Score_Value: number;
  Original_Score_Value: number;
  Override_Count: number;
  Latest_Override: ScoreOverride | null;
}

export interface JudgeScoreReview {
  Judge_ID: string;
  Judge_Name: string;
  Judge_Department: string | null;
  Submitted_At: string | null;
  Total_Score: number;
  Feedback_Text: string | null;
  criteria: ProjectScoreReviewCriterion[];
}

export interface ProjectScoreReview {
  Project_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_First_Name: string;
  Presenter_Last_Name: string;
  Presenter_Display_Name: string | null;
  Department: string | null;
  Category: string;
  submissions: JudgeScoreReview[];
}

export interface EventSummary {
  Eligible_Projects: number;
  Required_Reviews: number | null;
  Projects_At_Target: number;
  Judging_Open: boolean;
  Total_Projects: number;
  Total_Judges: number;
  Total_Scores_Submitted: number;
  Projects_With_Scores: number;
  Scoring_Coverage_Percent: number;
  Poster_Count: number;
  Art_Count: number;
}

export interface JudgeProject {
  can_score: boolean;
  Project_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_First_Name: string;
  Presenter_Last_Name: string;
  Presenter_Display_Name: string | null;
  Department: string | null;
  Category: 'Poster' | 'Art';
  Table_Number: string | null;
  is_assigned: boolean;
  is_scored: boolean;
}

export interface JudgeProjectDetail {
  can_score: boolean;
  Judging_Message: string | null;
  Event_Name: string;
  Event_Date: string;
  Project_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_First_Name: string;
  Presenter_Last_Name: string;
  Presenter_Display_Name: string | null;
  Department: string | null;
  Category: string;
  Table_Number: string | null;
  rubric: Rubric | null;
  existing_scores: Record<number, number>;
  existing_feedback: string | null;
}

export interface JudgeMe {
  Judge_ID: string;
  First_Name: string;
  Last_Name: string;
  Event_ID: string;
}

export interface AccessCodeCard {
  First_Name: string;
  Last_Name: string;
  Access_Code: string;
}

export interface Assignment {
  Assignment_ID: number;
  Judge_ID: string;
  Project_ID: string;
  Project_Number: string | null;
  Project_Title: string | null;
}

export interface CSVImportResult {
  imported: number;
  skipped: number;
  errors: string[];
  preview: Project[];
}

export interface PublicEvent {
  Event_Name: string;
  Event_Date: string;
  Event_End_Date: string | null;
  Location: string | null;
}

export interface PublicPoster {
  Project_Number: string;
  Project_Title: string;
  Presenter_Display_Name: string;
  Institution: string | null;
  Table_Number: string | null;
}

export interface PublicPosterDirectory {
  is_draft_preview: boolean;
  event: PublicEvent | null;
  posters: PublicPoster[];
}
