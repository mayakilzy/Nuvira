import { api } from "./api";

export type Subject = {
  id: number;
  name: string;
  university?: string | null;
  language: string;
  review_status: string;
};

export type Chapter = { id: number; number: number; title: string };

export type Concept = {
  id: number;
  name: string;
  everyday_analogy?: string | null;
  mechanism?: unknown;
  difficulty: number;
  official_source_note?: string | null;
};

export type Material = {
  id: number;
  filename: string;
  chapter_id?: number | null;
  status: "processing" | "ready" | "failed";
  chunk_count: number;
  error_note?: string | null;
};

export type Preferences = {
  ui_language: "de" | "en" | "ar";
  theme: "light" | "dark" | "system";
  avatar_corner_enabled: boolean;
};

export const fahemApi = {
  async subjects() {
    return (await api.get<{ subjects: Subject[] }>("/agent/subjects")).data.subjects;
  },
  async chapters(subjectId: number) {
    return (await api.get<{ chapters: Chapter[] }>("/agent/chapters", {
      params: { subject_package_id: subjectId },
    })).data.chapters;
  },
  async concepts(subjectId: number, chapterId?: number) {
    return (await api.get<{ concepts: Concept[]; chapter_filter_applied: boolean }>("/agent/concepts", {
      params: { subject_package_id: subjectId, chapter_id: chapterId },
    })).data;
  },
  async materials(subjectId: number) {
    return (await api.get<{ documents: Material[] }>("/agent/materials", {
      params: { subject_package_id: subjectId },
    })).data.documents;
  },
  async upload(subjectId: number, chapterId: number | undefined, file: File) {
    const data = new FormData();
    data.append("subject_package_id", String(subjectId));
    if (chapterId) data.append("chapter_id", String(chapterId));
    data.append("file", file);
    return (await api.post("/agent/materials/upload", data)).data as {
      document_id: number;
      status: "processing";
    };
  },
  async chat(message: string, subjectId: number, chapterId?: number) {
    return (await api.post("/agent/chat", {
      message,
      subject_package_id: subjectId,
      chapter_id: chapterId,
    })).data as { reply: string; used_material_context: boolean };
  },
  async reviewQueue(subjectId: number) {
    return (await api.get("/agent/review-queue", {
      params: { subject_package_id: subjectId },
    })).data.due_concepts as { id: number; name: string }[];
  },
  async history(subjectId: number) {
    return (await api.get("/agent/history", {
      params: { subject_package_id: subjectId },
    })).data.items as { id: number; concept_id: number; concept_name: string; is_correct: boolean }[];
  },
  async recordAttempt(conceptId: number, isCorrect: boolean, attemptNumber = 1) {
    return (await api.post("/agent/attempt", {
      concept_id: conceptId,
      is_correct: isCorrect,
      attempt_number: attemptNumber,
    })).data as { companion_message?: string | null };
  },
  async preferences() {
    return (await api.get<Preferences>("/agent/preferences")).data;
  },
  async savePreferences(prefs: Partial<Preferences>) {
    return (await api.put<Preferences>("/agent/preferences", prefs)).data;
  },
  async startSession(sessionKey: string) {
    return (await api.post("/agent/session/start", null, { params: { session_key: sessionKey } })).data.avatar as {
      shape: "leaf" | "molecule" | "droplet" | "sprout";
      color: "blue" | "purple" | "green" | "coral";
    };
  },
};
