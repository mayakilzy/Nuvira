"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { apiError } from "@/lib/api";
import { AdminResource, curriculumAdminApi } from "@/lib/curriculum-admin-api";

type Setup = { systemId?: number; curriculumId?: number; versionId?: number; subjectId?: number };

export default function CurriculumAdminPage() {
  const [library, setLibrary] = useState<any>({ curricula: [] });
  const [setup, setSetup] = useState<Setup>({});
  const [resource, setResource] = useState<AdminResource>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = () => curriculumAdminApi.library().then(setLibrary).catch((reason) => setError(apiError(reason)));
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!resource || !["queued", "processing"].includes(resource.processing_status)) return;
    const timer = window.setInterval(() => curriculumAdminApi.resource(resource.id).then(setResource).catch(() => undefined), 2500);
    return () => window.clearInterval(timer);
  }, [resource]);

  async function createHierarchy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    const data = new FormData(event.currentTarget);
    try {
      const system = await curriculumAdminApi.createSystem({ title: data.get("system"), country_code: data.get("country") || null, system_type: data.get("system_type") || null });
      const curriculum = await curriculumAdminApi.createCurriculum({ educational_system_id: system.id, title: data.get("curriculum"), description: data.get("description") || null, academic_level: data.get("level") || null, grade_track: data.get("track") || null, primary_language: data.get("language"), supported_languages: [data.get("language")], provenance: data.get("provenance") || null });
      const version = await curriculumAdminApi.createVersion({ curriculum_id: curriculum.id, academic_year: data.get("year"), edition: data.get("edition"), rights_status: data.get("rights") });
      const subject = await curriculumAdminApi.createSubject({ curriculum_version_id: version.id, name: data.get("subject"), language: data.get("language"), order_index: 1 });
      setSetup({ systemId: system.id, curriculumId: curriculum.id, versionId: version.id, subjectId: subject.id });
      setMessage("Draft hierarchy created. Upload a source document next."); await refresh();
    } catch (reason) { setError(apiError(reason)); } finally { setBusy(false); }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!setup.subjectId || !fileRef.current?.files?.[0]) return;
    const data = new FormData(event.currentTarget); setBusy(true); setError(""); setMessage("");
    try {
      const result = await curriculumAdminApi.upload(setup.subjectId, String(data.get("title")), String(data.get("language")), String(data.get("rights")), String(data.get("provenance")), fileRef.current.files[0]);
      setResource(result); setMessage("Source stored privately and queued for extraction.");
    } catch (reason) { setError(apiError(reason)); } finally { setBusy(false); }
  }

  async function importUrl(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!setup.subjectId) return;
    const data = new FormData(event.currentTarget); setBusy(true); setError(""); setMessage("");
    try {
      const result = await curriculumAdminApi.importUrl({
        subject_package_id: setup.subjectId, title: data.get("title"), url: data.get("url"),
        content_language: data.get("language"), rights_status: data.get("rights"),
        provenance: data.get("provenance"), resource_type: "textbook",
      });
      setResource(result); setMessage("HTTPS source stored privately and queued for extraction.");
    } catch (reason) { setError(apiError(reason)); } finally { setBusy(false); }
  }

  async function updateLesson(id: number, title: string) {
    try { await curriculumAdminApi.updateLesson(id, { title }); setResource(await curriculumAdminApi.resource(resource!.id)); }
    catch (reason) { setError(apiError(reason)); }
  }

  async function publish() {
    if (!setup.versionId) return;
    try { setBusy(true); await curriculumAdminApi.publish(setup.versionId); setMessage("Curriculum version published to the student catalog."); await refresh(); }
    catch (reason) { setError(apiError(reason)); } finally { setBusy(false); }
  }

  async function approveReview() {
    if (!resource) return;
    try {
      setBusy(true); setError("");
      await curriculumAdminApi.approveReview(resource.id);
      setResource(await curriculumAdminApi.resource(resource.id));
      setMessage("Editorial review approved. The verified version can now be published.");
    } catch (reason) { setError(apiError(reason)); } finally { setBusy(false); }
  }

  async function resumeResource(versionId: number, subjectId: number, resourceId: number) {
    try { setSetup((current) => ({ ...current, versionId, subjectId })); setResource(await curriculumAdminApi.resource(resourceId)); window.scrollTo({ top: 0, behavior: "smooth" }); }
    catch (reason) { setError(apiError(reason)); }
  }

  return <div className="curriculum-admin">
    <header><h1 className="page-title">Curriculum library</h1><p className="muted">Create, review and explicitly publish structured learning content.</p></header>
    {error && <p className="alert alert-error" role="alert">{error}</p>}
    {message && <p className="alert alert-ok" role="status">{message}</p>}

    <section className="card card-pad admin-section">
      <div className="step-label">1 · Draft hierarchy</div>
      <form className="admin-form-grid" onSubmit={createHierarchy}>
        <label className="field"><span className="label">Educational system</span><input className="input" name="system" required defaultValue="Syrian secondary education - demo" /></label>
        <label className="field"><span className="label">Country code</span><input className="input" name="country" maxLength={2} defaultValue="SY" /></label>
        <label className="field"><span className="label">System type</span><input className="input" name="system_type" defaultValue="National secondary" /></label>
        <label className="field"><span className="label">Curriculum title</span><input className="input" name="curriculum" required defaultValue="Scientific Baccalaureate - development demo" /></label>
        <label className="field"><span className="label">Academic level</span><input className="input" name="level" defaultValue="Upper secondary" /></label>
        <label className="field"><span className="label">Grade / track</span><input className="input" name="track" defaultValue="Scientific track" /></label>
        <label className="field"><span className="label">Academic year</span><input className="input" name="year" required defaultValue="2026-demo" /></label>
        <label className="field"><span className="label">Edition</span><input className="input" name="edition" required defaultValue="1.0" /></label>
        <label className="field"><span className="label">Subject</span><input className="input" name="subject" required defaultValue="Mathematics" /></label>
        <label className="field"><span className="label">Content language</span><input className="input" name="language" required defaultValue="ar" /></label>
        <label className="field"><span className="label">Rights status</span><select className="input" name="rights" defaultValue="verified"><option value="pending">Pending</option><option value="verified">Verified</option><option value="restricted">Restricted</option><option value="rejected">Rejected</option></select></label>
        <label className="field wide"><span className="label">Description</span><input className="input" name="description" defaultValue="Original development fixture; not an official government curriculum." /></label>
        <label className="field wide"><span className="label">Provenance</span><input className="input" name="provenance" defaultValue="Nuvira-owned development fixture" /></label>
        <button className="btn btn-primary wide" disabled={busy}>Create draft</button>
      </form>
    </section>

    <section className="card card-pad admin-section" aria-disabled={!setup.subjectId}>
      <div className="step-label">2 · Private source import</div>
      <form className="admin-form-grid" onSubmit={upload}>
        <label className="field"><span className="label">Resource title</span><input className="input" name="title" required defaultValue="Demo mathematics - two lessons" /></label>
        <label className="field"><span className="label">Content language</span><input className="input" name="language" required defaultValue="ar" /></label>
        <label className="field"><span className="label">Rights status</span><select className="input" name="rights" defaultValue="verified"><option value="pending">Pending</option><option value="verified">Verified</option><option value="restricted">Restricted</option></select></label>
        <label className="field"><span className="label">PDF source</span><input className="input" ref={fileRef} type="file" accept="application/pdf,.pdf" required /></label>
        <label className="field wide"><span className="label">Provenance</span><input className="input" name="provenance" defaultValue="Original Nuvira development fixture" /></label>
        <button className="btn btn-primary wide" disabled={busy || !setup.subjectId}>Upload and process</button>
      </form>
      <details className="remote-import"><summary>Or import from an approved HTTPS URL</summary><form className="admin-form-grid" onSubmit={importUrl}>
        <label className="field"><span className="label">Resource title</span><input className="input" name="title" required /></label>
        <label className="field"><span className="label">HTTPS URL</span><input className="input" name="url" type="url" required pattern="https://.*" /></label>
        <label className="field"><span className="label">Content language</span><input className="input" name="language" required defaultValue="ar" /></label>
        <label className="field"><span className="label">Rights status</span><select className="input" name="rights" defaultValue="pending"><option value="pending">Pending</option><option value="verified">Verified</option><option value="restricted">Restricted</option></select></label>
        <label className="field wide"><span className="label">Provenance</span><input className="input" name="provenance" required /></label>
        <button className="btn btn-primary wide" disabled={busy || !setup.subjectId}>Import and process</button>
      </form></details>
      {resource && <div className="processing-card"><div><strong>{resource.title}</strong><span className={`badge ${resource.processing_status === "review" ? "badge-ok" : "badge-warn"}`}>{resource.processing_status}</span></div><small>Job {resource.processing_job_id}</small>{resource.error_note && <p className="alert alert-error">{resource.error_note}</p>}</div>}
    </section>

    {resource?.processing_status === "review" && <section className="card card-pad admin-section">
      <div className="step-label">3 · Review extracted lessons</div>
      {resource.lessons.map((lesson, index) => <LessonEditor key={lesson.id} lesson={lesson} number={index + 1} onSave={updateLesson} />)}
      <div className="review-actions">
        <button className="btn btn-ghost" disabled={busy || !resource.lessons.length || Boolean(resource.reviewed_at)} onClick={() => void approveReview()}>{resource.reviewed_at ? "Review approved" : "Approve editorial review"}</button>
        <button className="btn btn-primary" disabled={busy || !resource.lessons.length || !resource.reviewed_at} onClick={() => void publish()}>Publish approved version</button>
      </div>
    </section>}

    <section className="card card-pad admin-section"><div className="step-label">Library status</div>{library.curricula.length ? library.curricula.map((item: any) => <article className="library-item" key={item.id}><div className="library-row"><strong>{item.title}</strong><span className="badge">{item.publication_status}</span></div>{item.versions.map((version: any) => <div className="library-version" key={version.id}><small>{version.academic_year} · {version.edition}</small>{version.subjects.map((subject: any) => <div className="library-subject" key={subject.id}><button className="btn btn-ghost" onClick={() => setSetup((current) => ({ ...current, versionId: version.id, subjectId: subject.id }))}>Use {subject.name}</button>{subject.resources.map((source: any) => <button className="resource-link" key={source.id} onClick={() => void resumeResource(version.id, subject.id, source.id)}>{source.title} · {source.processing_status}</button>)}</div>)}</div>)}</article>) : <p className="muted">No curricula created yet.</p>}</section>
  </div>;
}

function LessonEditor({ lesson, number, onSave }: { lesson: AdminResource["lessons"][number]; number: number; onSave: (id: number, title: string) => Promise<void> }) {
  const [title, setTitle] = useState(lesson.title);
  useEffect(() => setTitle(lesson.title), [lesson.title]);
  return <article className="lesson-editor"><div><small>Lesson {number} · page {lesson.page_start || "-"}</small><label className="field"><span className="label">Reviewed title</span><input className="input" value={title} onChange={(event) => setTitle(event.target.value)} /></label><p dir="auto">{lesson.content_text?.slice(0, 500)}</p></div><button className="btn btn-ghost" onClick={() => void onSave(lesson.id, title)}>Save correction</button></article>;
}
