// Shared TypeScript type definitions for the PreMock AI frontend

export interface InterviewSession {
  sessionId: string;
  role: string;
  difficulty: "Easy" | "Medium" | "Hard";
  resumeText: string;
  startedAt: Date;
}

export interface InterviewQuestion {
  text: string;
  index: number;
}

export interface InterviewAnswer {
  sessionId: string;
  answer: string;
}

export interface InterviewSetupResponse {
  session_id: string;
  first_question: string;
}

export interface InterviewAnswerResponse {
  next_question: string;
}

export interface InterviewEvaluation {
  overall_score: number;
  technical_depth: number;
  communication: number;
  problem_solving: number;
  feedback: string;
}

export interface UserProfile {
  id: string;
  email: string;
  fullName?: string;
  avatarUrl?: string;
  createdAt: Date;
}
