"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  BookOpen, CheckCircle2, ChevronLeft, ChevronRight, CircleAlert,
  Home, LoaderCircle, LogOut, MessageCircle, Moon, Send, Settings,
  Sparkles, Sun, Upload, X,
} from "./icons";
import { useAuth } from "@/lib/auth";
import { apiError } from "@/lib/api";
import {
  CatalogCurriculum, Chapter, Concept, CurriculumLesson, LessonDetail, nuviraApi,
  Material, Preferences, Subject, SubjectStructure,
} from "@/lib/nuvira-api";
import { Avatar } from "./Avatar";

type Tab = "garden" | "catalog" | "chapters" | "materials" | "settings";
type Language = Preferences["ui_language"];
type Message = { id: string; from: "user" | "companion"; text: string; grounded?: boolean };

const COPY = {
  de: { garden: "Garten", catalog: "Kurskatalog", chapters: "Lektionen", materials: "Materialien", settings: "Einstellungen", chat: "Mit Nuvira lernen", welcome: "Willkommen zurück", progress: "Dein Lernweg", due: "Heute zur Wiederholung", empty: "Du hast noch kein Fach ausgewählt.", browse: "Kurse entdecken", choose: "Fach wählen", enroll: "Testzugang aktivieren", enrolled: "Ausgewählt", openLesson: "Lektion öffnen", sourceFile: "Originalquelle ansehen", complete: "Als gelernt markieren", upload: "PDF oder PPT hochladen", noChapters: "Noch keine Lektionen verfügbar.", noMaterials: "Noch keine Materialien hochgeladen.", loading: "Wird geladen…", retry: "Erneut versuchen", account: "Konto", appearance: "Erscheinungsbild", language: "Sprache der Oberfläche", send: "Senden", prompt: "Frag Nuvira zu deinem Kurs…", source: "Mit deinem Kursmaterial verknüpft", understood: "Das sitzt", review: "Noch einmal ansehen" },
  en: { garden: "Garden", catalog: "Curriculum catalog", chapters: "Lessons", materials: "Materials", settings: "Settings", chat: "Talk to Nuvira", welcome: "Welcome back", progress: "Your learning path", due: "Due for review", empty: "You have not selected a subject yet.", browse: "Browse curricula", choose: "Choose subject", enroll: "Activate test access", enrolled: "Enrolled", openLesson: "Open lesson", sourceFile: "View original source", complete: "Mark as learned", upload: "Upload PDF or PPT", noChapters: "No lessons are available yet.", noMaterials: "No materials uploaded yet.", loading: "Loading…", retry: "Try again", account: "Account", appearance: "Appearance", language: "Interface language", send: "Send", prompt: "Ask Nuvira about your course…", source: "Linked to your course material", understood: "I understand it", review: "Review again" },
  ar: { garden: "حديقتي", catalog: "مكتبة المناهج", chapters: "الدروس", materials: "المواد", settings: "الإعدادات", chat: "تعلّم مع نوفيرا", welcome: "مرحبًا بعودتك", progress: "مسار تعلمك", due: "للمراجعة اليوم", empty: "لم تختر مادة دراسية بعد.", browse: "تصفّح المناهج", choose: "اختر المادة", enroll: "تفعيل وصول تجريبي", enrolled: "مسجّل", openLesson: "فتح الدرس", sourceFile: "عرض المصدر الأصلي", complete: "وضع علامة تم التعلم", upload: "ارفع PDF أو PPT", noChapters: "لا توجد دروس متاحة بعد.", noMaterials: "لم تُرفع مواد بعد.", loading: "جارٍ التحميل…", retry: "أعد المحاولة", account: "الحساب", appearance: "المظهر", language: "لغة الواجهة", send: "إرسال", prompt: "اسأل نوفيرا عن مادتك…", source: "مرتبط بمواد مقررك", understood: "فهمت الفكرة", review: "أراجعها مرة أخرى" },
} as const;

const NAV: { key: Tab; icon: typeof Home }[] = [
  { key: "garden", icon: Home },
  { key: "catalog", icon: BookOpen },
  { key: "chapters", icon: BookOpen },
  { key: "materials", icon: Upload },
  { key: "settings", icon: Settings },
];

function Garden({ completed, total }: { completed: number; total: number }) {
  const count = Math.max(total, 8);
  return (
    <div className="garden-scene" aria-label={`${completed} of ${total} concepts practiced`}>
      <div className="garden-sun" />
      <div className="garden-cloud cloud-one" /><div className="garden-cloud cloud-two" />
      <div className="garden-ground" />
      <div className="plant-row">
        {Array.from({ length: count }).map((_, index) => (
          <span key={index} className={`plant plant-${index % 4} ${index < completed ? "grown" : "waiting"}`}>
            <i /><b />
          </span>
        ))}
      </div>
      <span className="garden-count">{completed} / {total || "—"} ✓</span>
    </div>
  );
}

function Status({ material }: { material: Material }) {
  if (material.status === "processing") return <span className="status processing"><LoaderCircle size={12}/>{material.status}</span>;
  if (material.status === "failed") return <span className="status failed"><CircleAlert size={12}/>failed</span>;
  return <span className="status ready"><CheckCircle2 size={12}/>ready</span>;
}

function mechanismSteps(mechanism: unknown): string[] {
  if (!mechanism) return [];
  if (Array.isArray(mechanism)) return mechanism.map((item) => typeof item === "string" ? item : JSON.stringify(item));
  if (typeof mechanism === "object") {
    const value = mechanism as Record<string, unknown>;
    if (Array.isArray(value.steps)) return value.steps.map((item) => typeof item === "string" ? item : JSON.stringify(item));
  }
  return [typeof mechanism === "string" ? mechanism : JSON.stringify(mechanism)];
}

export default function NuviraApp() {
  const { user, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("garden");
  const [language, setLanguage] = useState<Language>("de");
  const [theme, setTheme] = useState<Preferences["theme"]>("system");
  const [avatar, setAvatar] = useState<{ shape: "leaf"|"molecule"|"droplet"|"sprout"; color: "blue"|"purple"|"green"|"coral" }>({ shape: "molecule", color: "blue" });
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [catalog, setCatalog] = useState<CatalogCurriculum[]>([]);
  const [developmentEnrollment, setDevelopmentEnrollment] = useState(false);
  const [subjectId, setSubjectId] = useState<number>();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [history, setHistory] = useState<{ concept_id: number; is_correct: boolean }[]>([]);
  const [due, setDue] = useState<{ id: number; name: string }[]>([]);
  const [chapterId, setChapterId] = useState<number>();
  const [concept, setConcept] = useState<Concept>();
  const [structure, setStructure] = useState<SubjectStructure>();
  const [lesson, setLesson] = useState<LessonDetail>();
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatText, setChatText] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const t = COPY[language];
  const rtl = language === "ar";

  const loadSubject = useCallback(async (id: number) => {
    try {
      setError("");
      const [chapterData, conceptData, materialData, historyData, reviewData, structureData] = await Promise.all([
        nuviraApi.chapters(id), nuviraApi.concepts(id), nuviraApi.materials(id), nuviraApi.history(id), nuviraApi.reviewQueue(id), nuviraApi.subjectStructure(id),
      ]);
      setChapters(chapterData); setConcepts(conceptData.concepts); setMaterials(materialData); setHistory(historyData); setDue(reviewData); setStructure(structureData);
    } catch (reason) { setError(apiError(reason)); }
  }, []);

  useEffect(() => {
    Promise.all([nuviraApi.subjects(), nuviraApi.preferences(), nuviraApi.startSession(crypto.randomUUID()), nuviraApi.catalog()])
      .then(([subjectData, prefs, avatarData, catalogData]) => {
        setSubjects(subjectData); setLanguage(prefs.ui_language); setTheme(prefs.theme); setAvatar(avatarData);
        setCatalog(catalogData.curricula); setDevelopmentEnrollment(catalogData.development_enrollment_enabled);
        if (subjectData[0]) { setSubjectId(subjectData[0].id); void loadSubject(subjectData[0].id); }
      })
      .catch((reason) => setError(apiError(reason)))
      .finally(() => setBusy(false));
  }, [loadSubject]);

  useEffect(() => {
    const hasProcessing = materials.some((item) => item.status === "processing");
    if (!hasProcessing || !subjectId) return;
    const timer = window.setInterval(() => {
      nuviraApi.materials(subjectId).then(setMaterials).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [materials, subjectId]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.lang = language;
    document.documentElement.dir = rtl ? "rtl" : "ltr";
  }, [language, rtl, theme]);

  const completed = useMemo(() => new Set(history.filter((item) => item.is_correct).map((item) => item.concept_id)).size, [history]);
  const curriculumLessons = useMemo(
    () => structure?.resources.flatMap((resource) => resource.lessons.map((item) => ({ ...item, resourceId: resource.id }))) || [],
    [structure],
  );

  async function changeSubject(id: number) {
    setSubjectId(id); setChapterId(undefined); setConcept(undefined); setLesson(undefined); setBusy(true);
    await loadSubject(id); setBusy(false);
  }

  async function updatePreferences(patch: Partial<Preferences>) {
    try {
      const saved = await nuviraApi.savePreferences(patch);
      setLanguage(saved.ui_language); setTheme(saved.theme);
    } catch (reason) { setError(apiError(reason)); }
  }

  async function uploadFile(file?: File) {
    if (!file || !subjectId) return;
    try {
      setError(""); await nuviraApi.upload(subjectId, chapterId, file);
      setMaterials(await nuviraApi.materials(subjectId));
    } catch (reason) { setError(apiError(reason)); }
    if (fileRef.current) fileRef.current.value = "";
  }

  async function sendChat() {
    const text = chatText.trim();
    if (!text || !subjectId || chatBusy) return;
    const userMessage: Message = { id: crypto.randomUUID(), from: "user", text };
    setMessages((current) => [...current, userMessage]); setChatText(""); setChatBusy(true);
    try {
      const response = await nuviraApi.chat(text, subjectId, chapterId);
      setMessages((current) => [...current, { id: crypto.randomUUID(), from: "companion", text: response.reply, grounded: response.used_material_context }]);
    } catch (reason) {
      setMessages((current) => [...current, { id: crypto.randomUUID(), from: "companion", text: apiError(reason) }]);
    } finally { setChatBusy(false); }
  }

  async function record(conceptId: number, understood: boolean) {
    try {
      const response = await nuviraApi.recordAttempt(conceptId, understood);
      if (subjectId) await loadSubject(subjectId);
      if (response.companion_message) setMessages((current) => [...current, { id: crypto.randomUUID(), from: "companion", text: response.companion_message! }]);
    } catch (reason) { setError(apiError(reason)); }
  }

  async function enroll(subject: { id: number }) {
    try {
      setError(""); await nuviraApi.enroll(subject.id);
      const [subjectData, catalogData] = await Promise.all([nuviraApi.subjects(), nuviraApi.catalog()]);
      setSubjects(subjectData); setCatalog(catalogData.curricula); setSubjectId(subject.id);
      await loadSubject(subject.id); setTab("chapters");
    } catch (reason) { setError(apiError(reason)); }
  }

  async function openLesson(item: CurriculumLesson) {
    try { setError(""); setLesson(await nuviraApi.lesson(item.id)); }
    catch (reason) { setError(apiError(reason)); }
  }

  async function completeLesson() {
    if (!lesson || !subjectId) return;
    try { await nuviraApi.saveLessonProgress(lesson.id, true); await loadSubject(subjectId); }
    catch (reason) { setError(apiError(reason)); }
  }

  async function openSource(resourceId: number) {
    const preview = window.open("about:blank", "_blank");
    if (preview) preview.opener = null;
    try {
      const blob = await nuviraApi.source(resourceId); const url = URL.createObjectURL(blob);
      if (preview) preview.location.href = url;
      else { const link = document.createElement("a"); link.href = url; link.download = "curriculum-source.pdf"; link.click(); }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (reason) { preview?.close(); setError(apiError(reason)); }
  }

  if (busy) return <div className="nuvira-loading"><Avatar expression="thinking" size={72}/><span>{t.loading}</span></div>;

  return (
    <div className="nuvira-app" dir={rtl ? "rtl" : "ltr"}>
      <aside className="nuvira-sidebar">
        <div className="nuvira-brand"><Avatar color={avatar.color} shape={avatar.shape} size={42}/><div><strong>Nuvira</strong><small>Lernbegleiterin</small></div></div>
        <nav>{NAV.map(({ key, icon: Icon }) => <button key={key} className={tab === key ? "active" : ""} onClick={() => { setTab(key); setChatOpen(false); }}><Icon size={19}/><span>{t[key]}</span></button>)}</nav>
        <button className="talk-button" onClick={() => setChatOpen(true)}><Avatar color={avatar.color} shape={avatar.shape} size={31}/><span>{t.chat}</span><MessageCircle size={15}/></button>
        <small className="version">Nuvira v1.0</small>
      </aside>

      <main className="nuvira-main">
        {error && <div className="nuvira-error"><CircleAlert size={16}/><span>{error}</span><button onClick={() => setError("")}><X size={15}/></button></div>}
        {!subjects.length && tab !== "catalog" && tab !== "settings" ? <section className="empty-state"><Avatar expression="thinking" size={92}/><h1>{t.empty}</h1><p>{language === "ar" ? "يمكنك اختيار مادة منشورة بنفسك دون تدخل إداري." : language === "de" ? "Wähle selbst ein veröffentlichtes Fach aus dem Katalog." : "Choose a published subject directly from the catalog."}</p><button className="primary-action" onClick={() => setTab("catalog")}>{t.browse}</button></section> : chatOpen && subjects.length ? (
          <section className="chat-panel">
            <header><Avatar color={avatar.color} shape={avatar.shape} size={44}/><div><strong>Nuvira</strong><small>{t.chat}</small></div><button onClick={() => setChatOpen(false)}><X size={18}/></button></header>
            <div className="messages">
              {!messages.length && <div className="chat-welcome"><Avatar color={avatar.color} shape={avatar.shape} expression="smiling" size={76}/><p>{t.prompt}</p></div>}
              {messages.map((message) => <div key={message.id} className={`message ${message.from}`}><p>{message.text}</p>{message.grounded && <small><BookOpen size={11}/>{t.source}</small>}</div>)}
              {chatBusy && <div className="typing"><i/><i/><i/></div>}
            </div>
            <form className="chat-input" onSubmit={(event) => { event.preventDefault(); void sendChat(); }}><input value={chatText} onChange={(event) => setChatText(event.target.value)} placeholder={t.prompt}/><button disabled={!chatText.trim() || chatBusy} aria-label={t.send}><Send size={18}/></button></form>
          </section>
        ) : (
          <>
            <header className="page-header"><div><h1>{tab === "garden" ? `${t.welcome}${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}` : t[tab]}</h1><p>{tab === "catalog" ? (language === "ar" ? "اختر منهجًا أو عدة مواد واحتفظ بتقدمك بينها." : language === "de" ? "Wähle Lehrplan und Fächer; dein Fortschritt bleibt erhalten." : "Choose curricula and subjects; your progress remains separate.") : subjects.find((item) => item.id === subjectId)?.name}</p></div>{subjects.length > 1 && tab !== "catalog" && <label><span>{t.choose}</span><select value={subjectId} onChange={(event) => void changeSubject(Number(event.target.value))}>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>}</header>

            {tab === "catalog" && <section className="catalog-grid" aria-live="polite">{catalog.length ? catalog.map((curriculum) => <article className="catalog-card" key={curriculum.id}><div className="catalog-heading"><span>{curriculum.academic_level || curriculum.primary_language}</span><h2>{curriculum.title}</h2><p>{curriculum.description}</p></div>{curriculum.versions.map((version) => <div className="catalog-version" key={version.id}><small>{version.academic_year} · {version.edition}</small>{version.subjects.map((subject) => <div className="catalog-subject" key={subject.id}><div><strong>{subject.name}</strong><small>{subject.language}</small></div>{subject.enrolled ? <span className="enrolled-badge"><CheckCircle2 size={14}/>{t.enrolled}</span> : <button disabled={!developmentEnrollment} onClick={() => void enroll(subject)}>{t.enroll}</button>}</div>)}</div>)}</article>) : <div className="empty-inline"><BookOpen size={36}/><p>{language === "ar" ? "لا توجد مناهج منشورة حاليًا." : language === "de" ? "Noch keine veröffentlichten Lehrpläne." : "No published curricula are available yet."}</p></div>}</section>}

            {tab === "garden" && <section className="content-grid"><div className="garden-card"><div className="section-title"><div><small>{t.progress}</small><h2>{subjects.find((item) => item.id === subjectId)?.name}</h2></div><Sparkles size={21}/></div><Garden completed={completed} total={concepts.length}/><p className="gentle-note">Jeder Schritt zählt. Dein Garten wächst mit jedem Lernmoment.</p></div><div className="side-stack"><article className="summary-card"><span className="summary-icon"><BookOpen size={20}/></span><div><small>{t.chapters}</small><strong>{chapters.length}</strong></div></article><article className="summary-card"><span className="summary-icon green"><CheckCircle2 size={20}/></span><div><small>{t.progress}</small><strong>{completed} / {concepts.length}</strong></div></article><article className="review-card"><small>{t.due}</small>{due.length ? due.map((item) => <button key={item.id} onClick={() => { setTab("chapters"); setConcept(concepts.find((c) => c.id === item.id)); }}>{item.name}<ChevronRight size={15}/></button>) : <p>Heute wartet keine Wiederholung auf dich.</p>}</article></div></section>}

            {tab === "chapters" && <section className="learning-layout"><div className="chapter-list"><h2>{t.chapters}</h2>{curriculumLessons.length ? curriculumLessons.map((item) => <button key={item.id} className={lesson?.id === item.id ? "selected" : ""} onClick={() => void openLesson(item)}><span>{item.order_index}</span><strong>{item.title}</strong>{item.completed ? <CheckCircle2 size={16}/> : <ChevronRight size={16}/>}</button>) : <p className="muted-copy">{t.noChapters}</p>}</div><div className="concept-area">{lesson ? <article className="lesson-detail" dir={lesson.content_language.startsWith("ar") ? "rtl" : "ltr"}><button className="back-link" onClick={() => setLesson(undefined)}><ChevronLeft size={15}/> {t.chapters}</button><small>{lesson.page_start ? `${language === "ar" ? "الصفحة" : "Page"} ${lesson.page_start}` : ""}</small><h2>{lesson.title}</h2><div className="lesson-text">{lesson.content_text}</div>{lesson.examples.length > 0 && <section><h3>{language === "ar" ? "أمثلة" : "Examples"}</h3>{lesson.examples.map((item, index) => <p key={index}>{item}</p>)}</section>}{lesson.exercises.length > 0 && <section><h3>{language === "ar" ? "تمارين" : "Exercises"}</h3>{lesson.exercises.map((item, index) => <p key={index}>{item}</p>)}</section>}<div className="attempt-actions"><button onClick={() => void openSource(lesson.resource_id)}><BookOpen size={16}/>{t.sourceFile}</button><button className="primary" onClick={() => void completeLesson()}><CheckCircle2 size={16}/>{t.complete}</button></div></article> : concept ? <article className="concept-detail"><button className="back-link" onClick={() => setConcept(undefined)}><ChevronLeft size={15}/> {t.chapters}</button><div className="concept-heading"><span>0{concept.difficulty}</span><div><small>Concept</small><h2>{concept.name}</h2></div></div>{concept.everyday_analogy && <div className="analogy"><Sparkles size={18}/><p>{concept.everyday_analogy}</p></div>}<div className="mechanism">{mechanismSteps(concept.mechanism).map((step, index) => <div className="mechanism-step" key={index}><span>{index + 1}</span><p>{step}</p></div>)}</div><div className="attempt-actions"><button onClick={() => void record(concept.id, false)}>{t.review}</button><button className="primary" onClick={() => void record(concept.id, true)}><CheckCircle2 size={16}/>{t.understood}</button></div></article> : <><div className="concept-intro"><Avatar color={avatar.color} shape={avatar.shape} expression="calm" size={64}/><div><h2>{t.chapters}</h2><p>{language === "ar" ? "اختر درسًا لقراءة النص المستخرج ومراجعة المصدر الأصلي." : language === "de" ? "Öffne eine Lektion mit Text und Originalquelle." : "Open a lesson to read the extracted text and review its original source."}</p></div></div>{!curriculumLessons.length && <p className="muted-copy">{t.noChapters}</p>}</>}</div></section>}

            {tab === "materials" && <section className="materials-layout"><div><input ref={fileRef} hidden type="file" accept=".pdf,.ppt,.pptx" onChange={(event) => void uploadFile(event.target.files?.[0])}/><button className="drop-zone" onClick={() => fileRef.current?.click()}><span><Upload size={28}/></span><strong>{t.upload}</strong><small>PDF, PPT, PPTX · max. 50 MB</small></button><div className="material-list">{materials.length ? materials.map((item) => <article key={item.id}><span className="file-icon">{item.filename.toLowerCase().endsWith("pdf") ? "PDF" : "PPT"}</span><div><strong>{item.filename}</strong><small>{item.chunk_count} chunks{item.error_note ? ` · ${item.error_note}` : ""}</small></div><Status material={item}/></article>) : <p className="muted-copy">{t.noMaterials}</p>}</div></div><aside className="upload-settings"><h3>Kapitel zuweisen</h3><select value={chapterId || ""} onChange={(event) => setChapterId(event.target.value ? Number(event.target.value) : undefined)}><option value="">Allgemeines Material</option>{chapters.map((item) => <option key={item.id} value={item.id}>{item.number}. {item.title}</option>)}</select><p>Der echte Verarbeitungsstatus wird automatisch vom Worker aktualisiert.</p></aside></section>}

            {tab === "settings" && <section className="settings-grid"><article><h2>{t.language}</h2><p>Beeinflusst nur die App-Sprache — unabhängig von der Unterrichtssprache.</p><div className="choice-row">{(["de", "en", "ar"] as Language[]).map((item) => <button className={language === item ? "selected" : ""} key={item} onClick={() => void updatePreferences({ ui_language: item })}>{item === "de" ? "Deutsch" : item === "en" ? "English" : "العربية"}</button>)}</div></article><article><h2>{t.appearance}</h2><div className="choice-row">{(["light", "dark", "system"] as Preferences["theme"][]).map((item) => <button className={theme === item ? "selected" : ""} key={item} onClick={() => void updatePreferences({ theme: item })}>{item === "light" ? <Sun size={17}/> : item === "dark" ? <Moon size={17}/> : <Settings size={17}/>} {item}</button>)}</div></article><article><h2>{t.account}</h2><div className="account-row"><div className="user-dot">{(user?.full_name || user?.email || "U")[0].toUpperCase()}</div><div><strong>{user?.full_name || "Student"}</strong><small>{user?.email}</small></div></div><div className="account-links"><Link href="/billing">Billing</Link><Link href="/settings">Profile</Link>{user?.role === "admin" && <Link href="/admin/users">Admin</Link>}<button onClick={logout}><LogOut size={16}/>Sign out</button></div></article></section>}
          </>
        )}
        {!chatOpen && subjects.length > 0 && <button className="chat-fab" onClick={() => setChatOpen(true)} aria-label={t.chat}><Avatar color={avatar.color} shape={avatar.shape} size={48}/><span/></button>}
      </main>

      <nav className="mobile-nav">{NAV.map(({ key, icon: Icon }) => <button key={key} className={tab === key ? "active" : ""} onClick={() => { setTab(key); setChatOpen(false); }}><Icon size={19}/><small>{t[key]}</small></button>)}</nav>
    </div>
  );
}
