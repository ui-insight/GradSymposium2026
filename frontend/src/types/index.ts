export interface Event {
  Event_ID: string;
  Event_Name: string;
  Event_Date: string;
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
  Department: string | null;
  College: string | null;
  Advisor_Name: string | null;
  Category: 'Poster' | 'Art';
  Table_Number: string | null;
  Is_Active: boolean;
  score_count: number;
}

export interface Judge {
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
  Rubric_ID: string;
  Event_ID: string;
  Rubric_Name: string;
  Category: string;
  Max_Score: number;
  Description: string | null;
  criteria: Criterion[];
}

export interface ProjectResult {
  Project_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_First_Name: string;
  Presenter_Last_Name: string;
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
  Department: string | null;
  Category: string;
  submissions: JudgeScoreReview[];
}

export interface EventSummary {
  Total_Projects: number;
  Total_Judges: number;
  Total_Scores_Submitted: number;
  Projects_With_Scores: number;
  Scoring_Coverage_Percent: number;
  Poster_Count: number;
  Art_Count: number;
}

export interface JudgeProject {
  Project_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_First_Name: string;
  Presenter_Last_Name: string;
  Department: string | null;
  Category: 'Poster' | 'Art';
  Table_Number: string | null;
  is_assigned: boolean;
  is_scored: boolean;
}

export interface JudgeProjectDetail {
  Project_ID: string;
  Project_Number: string;
  Project_Title: string;
  Presenter_First_Name: string;
  Presenter_Last_Name: string;
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
}
