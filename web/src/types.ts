export interface TopicSummary {
  id: string;
  name: string;
  description: string;
  subtopicCount: number;
}

export interface Area {
  id: string;
  name: string;
  published?: boolean;
}

export interface Subtopic {
  id: string;
  name: string;
  description: string;
  generate: boolean;
  areas: Area[];
}

export interface Topic {
  id: string;
  name: string;
  description: string;
  subtopics: Subtopic[];
}

export interface PageContent {
  title: string;
  summary: string;
  overview: string;
  diagram: { caption: string; mermaid: string };
  keyConcepts: { term: string; explanation: string }[];
  comparison: { caption: string; columns: string[]; rows: string[][] };
  whenToUse: { option: string; useWhen: string }[];
  pitfalls: string[];
  quiz: { question: string; options: string[]; answerIndex: number; explanation: string }[];
  sources: { title: string; url: string }[];
}

export interface PageDoc {
  id: string;
  pageId: string;
  topicId: string;
  subtopicId: string;
  areaId: string;
  areaName: string;
  status: "draft" | "approved" | "rejected";
  content: PageContent;
  checks: { passed: boolean; problems: string[] };
  generation: {
    generatedAt: string;
    model: string;
    promptVersion: string;
    query: string;
    fetchedSources: { title: string; url: string }[];
  };
  review?: { by: string; at: string; decision: string; comment?: string };
}

export interface DraftSummary {
  id: string;
  pageId: string;
  topicId: string;
  subtopicId: string;
  areaName: string;
  status: "draft" | "rejected";
  title?: string;
  generatedAt?: string;
  checks: { passed: boolean; problems: string[] };
}

export interface Me {
  name: string;
  isReviewer: boolean;
}

export interface RunStatus {
  status: string;
  output?: { total: number; drafted: number; failedChecks: string[]; errors: { pageId: string; error: string }[] };
  customStatus?: { done: number; total: number };
}
