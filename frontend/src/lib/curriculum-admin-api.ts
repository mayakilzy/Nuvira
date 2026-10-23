import { api } from "./api";

export type AdminResource = {
  id: number; title: string; processing_status: string; publication_status: string;
  rights_status: string; processing_job_id: string; error_note?: string | null;
  reviewed_at?: string | null;
  lessons: { id: number; title: string; page_start?: number | null; content_text?: string | null }[];
};

export const curriculumAdminApi = {
  async library() { return (await api.get("/curricula/admin/library")).data; },
  async createSystem(payload: Record<string, unknown>) { return (await api.post("/curricula/admin/systems", payload)).data; },
  async createCurriculum(payload: Record<string, unknown>) { return (await api.post("/curricula/admin/curricula", payload)).data; },
  async createVersion(payload: Record<string, unknown>) { return (await api.post("/curricula/admin/versions", payload)).data; },
  async createSubject(payload: Record<string, unknown>) { return (await api.post("/curricula/admin/subjects", payload)).data; },
  async upload(subjectId: number, title: string, language: string, rights: string, provenance: string, file: File) {
    const data = new FormData();
    data.append("subject_package_id", String(subjectId)); data.append("title", title);
    data.append("content_language", language); data.append("rights_status", rights);
    data.append("provenance", provenance); data.append("file", file);
    return (await api.post<AdminResource>("/curricula/admin/resources/upload", data)).data;
  },
  async resource(id: number) { return (await api.get<AdminResource>(`/curricula/admin/resources/${id}`)).data; },
  async importUrl(payload: Record<string, unknown>) { return (await api.post<AdminResource>("/curricula/admin/resources/import-url", payload)).data; },
  async updateLesson(id: number, payload: Record<string, unknown>) { return (await api.patch(`/curricula/admin/lessons/${id}`, payload)).data; },
  async approveReview(id: number) { return (await api.post(`/curricula/admin/resources/${id}/approve-review`)).data; },
  async publish(versionId: number) { return (await api.post(`/curricula/admin/versions/${versionId}/publish`)).data; },
};
