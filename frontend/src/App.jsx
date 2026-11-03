import { useEffect, useState } from "react";
import {
  Activity, ArrowLeft, Check, ChevronRight, CircleAlert, ClipboardList, Download,
  ExternalLink, FileText, FolderOpen, LayoutDashboard, LoaderCircle, LogOut, Search,
  Settings, ShieldCheck, UserRound, Users, X,
} from "lucide-react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import api, { setCsrfToken } from "./api.js";

const navigation = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/forms/connect", label: "Connect a form", icon: ClipboardList },
  { to: "/candidates", label: "Candidates", icon: Users },
  { to: "/settings", label: "Settings", icon: Settings },
];

const mappingFields = [
  ["candidate_name", "Candidate name", true],
  ["mobile_number", "Mobile number"],
  ["date_of_birth", "Date of birth"],
  ["birth_time", "Birth time"],
  ["birth_place", "Birth place"],
  ["height", "Height"],
  ["blood_group", "Blood group"],
  ["education", "Education"],
  ["address", "Address"],
  ["photograph", "Candidate photograph", true],
  ["receipt", "Payment receipt"],
];

function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const location = useLocation();

  useEffect(() => {
    api.get("/auth/me")
      .then(({ data }) => {
        setCsrfToken(data.csrf_token);
        setUser(data);
      })
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, [location.pathname]);

  if (checking) return <CenteredState text="Checking your session…" />;
  if (!user) return <Routes><Route path="*" element={<LoginPage />} /></Routes>;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <div className="flex h-20 items-center gap-3 border-b border-slate-100 px-6">
          <div className="rounded-xl bg-indigo-600 p-2 text-white"><FileText size={20} /></div>
          <div><p className="font-bold leading-5">Candidate</p><p className="text-xs text-slate-500">Marathi automation</p></div>
        </div>
        <nav className="space-y-1 px-3 py-6">
          {navigation.map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${location.pathname === to || (to !== "/" && location.pathname.startsWith(to)) ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"}`}>
              <Icon size={18} />{label}
            </Link>
          ))}
        </nav>
        <div className="absolute inset-x-4 bottom-4 rounded-xl bg-slate-50 p-4">
          <div className="flex items-center gap-3">
            {user.profile_image ? <img src={user.profile_image} alt="" className="h-9 w-9 rounded-full" /> : <div className="rounded-full bg-white p-2"><UserRound size={18} /></div>}
            <div className="min-w-0"><p className="truncate text-sm font-medium">{user.name}</p><p className="truncate text-xs text-slate-500">{user.email}</p></div>
          </div>
        </div>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur sm:px-8">
          <div className="flex items-center gap-2 text-sm text-slate-500"><ShieldCheck size={17} className="text-emerald-600" /> Private workspace</div>
          <button onClick={async () => { await api.post("/auth/logout"); setCsrfToken(""); setUser(null); }} className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100">
            <LogOut size={16} /> Sign out
          </button>
        </header>
        <main className="mx-auto max-w-7xl p-5 sm:p-8">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/forms/connect" element={<ConnectFormPage />} />
            <Route path="/forms/:formId/mapping" element={<MappingPage />} />
            <Route path="/candidates" element={<CandidatesPage />} />
            <Route path="/candidates/:candidateId" element={<CandidateDetailPage />} />
            <Route path="/settings" element={<SettingsPage user={user} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-slate-200 bg-white py-2 lg:hidden">
        {navigation.map(({ to, label, icon: Icon }) => <Link key={to} to={to} className="flex flex-col items-center gap-1 text-[11px] text-slate-600"><Icon size={18} />{label.split(" ")[0]}</Link>)}
      </nav>
    </div>
  );
}

function LoginPage() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const signIn = async () => {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/auth/google/login");
      window.location.assign(data.authorization_url);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to start Google sign-in. Check backend configuration.");
      setBusy(false);
    }
  };
  return (
    <div className="grid min-h-screen place-items-center bg-slate-50 px-5">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-7 inline-flex rounded-xl bg-indigo-600 p-3 text-white"><FileText /></div>
        <h1 className="text-2xl font-bold">Candidate Automation</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">Connect your Google Form to translate candidate details and create organized Word documents in Drive.</p>
        {error && <Notice kind="error" className="mt-5">{error}</Notice>}
        <button onClick={signIn} disabled={busy} className="mt-7 flex w-full items-center justify-center gap-3 rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60">
          {busy ? <LoaderCircle className="animate-spin" size={18} /> : <GoogleMark />} Sign in with Google
        </button>
        <p className="mt-5 text-xs leading-5 text-slate-500">Your Google tokens stay on the backend. Form and Drive access is limited to the Google account you authorize.</p>
      </div>
    </div>
  );
}

function GoogleMark() {
  return <span aria-hidden="true" className="rounded-full bg-white px-1.5 py-0.5 text-sm font-bold text-indigo-600">G</span>;
}

function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api.get("/dashboard/stats"), api.get("/candidates", { params: { limit: 6 } })])
      .then(([a, b]) => { setStats(a.data); setCandidates(b.data); })
      .catch((err) => setError(err.response?.data?.detail || "Could not load dashboard."));
  }, []);
  const metrics = [
    ["Total candidates", stats?.total_candidates ?? "—", Users],
    ["Completed documents", stats?.completed ?? "—", Check],
    ["Pending", stats?.pending ?? "—", Activity],
    ["Failed", stats?.failed ?? "—", CircleAlert],
  ];
  return <>
    <PageHeading eyebrow="Overview" title="Dashboard" description="Monitor form processing and candidate documents." action={<Link className="primary-button" to="/forms/connect">Connect Google Form <ChevronRight size={16} /></Link>} />
    {error && <Notice kind="error">{error}</Notice>}
    <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map(([label, value, Icon]) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between text-sm text-slate-500"><span>{label}</span><Icon size={18} className="text-indigo-600" /></div><p className="mt-4 text-3xl font-semibold">{value}</p></div>)}
    </div>
    <section className="mt-8 rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 className="font-semibold">Recent candidates</h2><p className="mt-1 text-sm text-slate-500">Latest responses and processing status</p></div><Link to="/candidates" className="text-sm font-medium text-indigo-700">View all</Link></div>
      <CandidateTable candidates={candidates} compact />
    </section>
  </>;
}

function ConnectFormPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const connect = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/forms/connect", { form_url: url });
      navigate(`/forms/${data.id}/mapping`, { state: { form: data } });
    } catch (err) {
      setError(err.response?.data?.detail || "Could not connect this Google Form.");
    } finally { setLoading(false); }
  };
  return <>
    <PageHeading eyebrow="Setup" title="Connect Google Form" description="Use a form your signed-in Google account can edit." />
    <form onSubmit={connect} className="mt-7 max-w-2xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <label className="label" htmlFor="form-url">Google Form URL</label>
      <input id="form-url" required value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://docs.google.com/forms/d/…" className="input mt-2" />
      {error && <Notice kind="error" className="mt-4">{error}</Notice>}
      <div className="mt-5 flex items-center justify-between gap-4">
        <p className="text-xs leading-5 text-slate-500">Google Forms API editor permissions are required. Public responder links are not used to bypass access controls.</p>
        <button className="primary-button shrink-0" disabled={loading}>{loading && <LoaderCircle size={16} className="animate-spin" />} Connect form</button>
      </div>
    </form>
  </>;
}

function MappingPage() {
  const { formId } = useParams();
  const location = useLocation();
  const [form, setForm] = useState(location.state?.form || null);
  const [questions, setQuestions] = useState(location.state?.form?.questions || []);
  const [mapping, setMapping] = useState(location.state?.form?.field_mappings || {});
  const [customFields, setCustomFields] = useState([]);
  const [folder, setFolder] = useState(location.state?.form?.parent_drive_folder_id || "");
  const [enabled, setEnabled] = useState(location.state?.form?.automatic_processing_enabled || false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setCustomFields(Object.keys(mapping).filter((key) => key.startsWith("custom_")));
  }, [mapping]);
  useEffect(() => {
    if (form && questions.length) return;
    api.get("/forms").then(({ data }) => {
      const found = data.find((item) => item.id === formId);
      if (!found) throw new Error("Connected form not found.");
      setForm(found); setMapping(found.field_mappings || {}); setFolder(found.parent_drive_folder_id || ""); setEnabled(found.automatic_processing_enabled);
      return api.get(`/forms/${formId}/questions`);
    }).then(({ data }) => setQuestions(data.questions))
      .catch((err) => setError(err.response?.data?.detail || err.message || "Unable to load questions."));
  }, [formId]);

  const save = async (event) => {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      await api.post(`/forms/${formId}/mapping`, { field_mappings: mapping, parent_drive_folder_id: folder || null });
      await api.post(`/forms/${formId}/start-processing`, { enabled });
      setMessage(enabled ? "Mappings saved. Automatic processing is enabled." : "Mappings saved.");
    } catch (err) { setError(err.response?.data?.detail || "Could not save your settings."); }
    finally { setSaving(false); }
  };
  const update = (key, value) => setMapping((previous) => ({ ...previous, [key]: value }));
  const addCustomField = () => {
    let number = customFields.length + 1;
    let key = `custom_field_${number}`;
    while (Object.hasOwn(mapping, key)) key = `custom_field_${++number}`;
    setCustomFields((current) => [...current, key]);
    update(key, "");
  };
  return <>
    <button onClick={() => navigate("/forms/connect")} className="mb-5 inline-flex items-center gap-2 text-sm text-slate-500"><ArrowLeft size={16} /> Back</button>
    <PageHeading eyebrow="Form mapping" title={form?.form_name || "Map form questions"} description="Choose which form question supplies each candidate field." />
    {error && <Notice kind="error" className="mt-5">{error}</Notice>}
    {message && <Notice kind="success" className="mt-5">{message}</Notice>}
    <form onSubmit={save} className="mt-6 max-w-3xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      {mappingFields.map(([key, label, required]) => (
        <label key={key} className="mb-5 block">
          <span className="label">{label}{required && <span className="ml-1 text-rose-600">*</span>}</span>
          <select required={required} value={mapping[key] || ""} onChange={(e) => update(key, e.target.value)} className="input mt-2">
            <option value="">Select a question…</option>
            {questions.map((question) => <option key={question.item_id} value={question.item_id}>{question.title}</option>)}
          </select>
        </label>
      ))}
      {customFields.map((key) => (
        <label key={key} className="mb-5 block">
          <span className="label">Custom field <code className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-xs">{`{{${key.toUpperCase()}}}`}</code></span>
          <select value={mapping[key] || ""} onChange={(e) => update(key, e.target.value)} className="input mt-2">
            <option value="">Select a question…</option>
            {questions.map((question) => <option key={question.item_id} value={question.item_id}>{question.title}</option>)}
          </select>
        </label>
      ))}
      <button type="button" onClick={addCustomField} className="secondary-button mb-5">Add custom field</button>
      <label className="mb-5 block"><span className="label">Parent Drive folder ID <span className="font-normal text-slate-400">(optional)</span></span><input value={folder} onChange={(e) => setFolder(e.target.value)} className="input mt-2" placeholder="Drive folder ID" /></label>
      <label className="flex items-start gap-3 rounded-lg bg-indigo-50 p-4">
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="mt-1 accent-indigo-600" />
        <span><span className="block text-sm font-semibold text-indigo-950">Enable automatic processing</span><span className="mt-1 block text-xs text-indigo-800">A cloud worker checks this form every two minutes. It continues when this page is closed.</span></span>
      </label>
      <button disabled={saving || !questions.length} className="primary-button mt-6">{saving && <LoaderCircle size={16} className="animate-spin" />} Save mapping</button>
    </form>
  </>;
}

function CandidatesPage() {
  const [candidates, setCandidates] = useState([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => api.get("/candidates", { params: { search: search || undefined, status: status || undefined } })
      .then(({ data }) => { setCandidates(data); setError(""); })
      .catch((err) => setError(err.response?.data?.detail || "Could not load candidates.")), 180);
    return () => clearTimeout(timer);
  }, [search, status]);
  return <>
    <PageHeading eyebrow="Registrations" title="Candidates" description="Search and review submitted candidate records." />
    <div className="mt-6 flex flex-col gap-3 sm:flex-row">
      <div className="relative flex-1"><Search className="absolute left-3 top-3 text-slate-400" size={17} /><input value={search} onChange={(e) => setSearch(e.target.value)} className="input pl-10" placeholder="Search name or mobile number" /></div>
      <select value={status} onChange={(e) => setStatus(e.target.value)} className="input sm:w-52"><option value="">All statuses</option><option value="completed">Completed</option><option value="pending">Pending</option><option value="processing">Processing</option><option value="failed">Failed</option></select>
    </div>
    {error && <Notice kind="error" className="mt-4">{error}</Notice>}
    <section className="mt-5 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><CandidateTable candidates={candidates} /></section>
  </>;
}

function CandidateDetailPage() {
  const { candidateId } = useParams();
  const [candidate, setCandidate] = useState(null);
  const [error, setError] = useState("");
  const [translations, setTranslations] = useState({});
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState("");
  const navigate = useNavigate();
  useEffect(() => { api.get(`/candidates/${candidateId}`).then(({ data }) => { setCandidate(data); setTranslations(data.translated_data || {}); }).catch((err) => setError(err.response?.data?.detail || "Candidate not found.")); }, [candidateId]);
  useEffect(() => {
    if (!candidate || !["pending", "processing"].includes(candidate.processing_status)) return undefined;
    const timer = setInterval(() => api.get(`/candidates/${candidateId}`).then(({ data }) => {
      setCandidate(data);
      setTranslations(data.translated_data || {});
    }).catch(() => {}), 5000);
    return () => clearInterval(timer);
  }, [candidate?.processing_status, candidateId]);
  if (error) return <Notice kind="error">{error}</Notice>;
  if (!candidate) return <CenteredState text="Loading candidate…" />;
  const saveTranslations = async () => {
    setBusy(true); setNotice("");
    try { const { data } = await api.patch(`/candidates/${candidateId}/translation`, { translated_data: translations }); setCandidate(data); setNotice("Translations saved."); }
    catch (err) { setNotice(err.response?.data?.detail || "Could not save translations."); }
    finally { setBusy(false); }
  };
  const run = async (path) => {
    setBusy(true); setNotice("");
    try { const { data } = await api.post(`/candidates/${candidateId}/${path}`); setCandidate((current) => ({ ...current, processing_status: data.processing_status })); setNotice(path === "retry" ? "Retry queued for the background worker." : "Document regeneration queued for the background worker."); }
    catch (err) { setNotice(err.response?.data?.detail || "Processing failed."); }
    finally { setBusy(false); }
  };
  const openFolder = async () => {
    try { const { data } = await api.get(`/candidates/${candidateId}/drive-folder`); window.open(data.url, "_blank", "noopener,noreferrer"); }
    catch (err) { setNotice(err.response?.data?.detail || "Drive folder unavailable."); }
  };
  return <>
    <button onClick={() => navigate("/candidates")} className="mb-5 inline-flex items-center gap-2 text-sm text-slate-500"><ArrowLeft size={16} /> Candidates</button>
    <PageHeading eyebrow={candidate.registration_id} title={candidate.candidate_name} description={candidate.mobile_number || "No mobile number"} action={<div className="flex flex-wrap gap-2">{candidate.document_drive_id && <a className="secondary-button" href={`${api.defaults.baseURL}/candidates/${candidate.id}/document`} onClick={(e) => { e.preventDefault(); api.get(`/candidates/${candidate.id}/document`, { responseType: "blob" }).then(({ data }) => { const url = URL.createObjectURL(data); const a = document.createElement("a"); a.href = url; a.download = `${candidate.candidate_name}_${candidate.registration_id}.docx`; a.click(); URL.revokeObjectURL(url); }); }}><Download size={16} /> Download DOCX</a>}<button onClick={openFolder} className="secondary-button"><FolderOpen size={16} /> Drive folder</button></div>} />
    {notice && <Notice kind="success" className="mt-5">{notice}</Notice>}
    {candidate.error_message && <Notice kind="error" className="mt-5">{candidate.error_message}</Notice>}
    <div className="mt-6 grid gap-5 xl:grid-cols-2">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold">Submitted information</h2>
        <dl className="mt-4 divide-y divide-slate-100">{Object.entries(candidate.original_data || {}).filter(([key]) => !key.startsWith("_")).map(([key, value]) => <div key={key} className="grid grid-cols-2 gap-3 py-3 text-sm"><dt className="text-slate-500">{key}</dt><dd className="break-words font-medium">{Array.isArray(value) ? value.join(", ") : String(value)}</dd></div>)}</dl>
        <div className="mt-5 flex flex-wrap gap-2"><button onClick={() => setPreview("photograph")} className="secondary-button">Preview photo</button><button onClick={() => setPreview("receipt")} className="secondary-button">Preview receipt</button></div>
      </section>
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between"><h2 className="font-semibold">Translation review</h2><button onClick={saveTranslations} disabled={busy} className="text-sm font-semibold text-indigo-700">Save edits</button></div>
        <div className="mt-4 space-y-4">{Object.entries(translations).map(([key, value]) => <label key={key} className="block"><span className="label">{key.replaceAll("_", " ")}</span><textarea rows={2} value={value} onChange={(e) => setTranslations((old) => ({ ...old, [key]: e.target.value }))} className="input mt-1" /></label>)}</div>
        <div className="mt-5 flex flex-wrap gap-2"><button onClick={() => run("regenerate")} disabled={busy} className="primary-button">{busy && <LoaderCircle size={16} className="animate-spin" />} Regenerate DOCX</button>{candidate.processing_status === "failed" && <button onClick={() => run("retry")} disabled={busy} className="secondary-button">Retry processing</button>}</div>
      </section>
    </div>
    {preview && <PreviewModal candidateId={candidate.id} kind={preview} close={() => setPreview("")} />}
  </>;
}

function PreviewModal({ candidateId, kind, close }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let objectUrl;
    api.get(`/candidates/${candidateId}/${kind}`, { responseType: "blob" })
      .then(({ data }) => { objectUrl = URL.createObjectURL(data); setUrl(objectUrl); })
      .catch((err) => setError(err.response?.data?.detail || "Preview not available."));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [candidateId, kind]);
  return <div onClick={close} className="fixed inset-0 z-50 grid place-items-center bg-slate-950/60 p-4"><div onClick={(e) => e.stopPropagation()} className="relative max-h-[90vh] max-w-3xl rounded-xl bg-white p-4"><button onClick={close} className="absolute -right-3 -top-3 rounded-full bg-white p-2 shadow"><X size={18} /></button>{error ? <p className="p-8 text-sm text-rose-700">{error}</p> : url ? <img src={url} alt={kind === "photograph" ? "Candidate photograph" : "Payment receipt"} className="max-h-[80vh] max-w-full object-contain" /> : <CenteredState text="Loading preview…" />}</div></div>;
}

function SettingsPage({ user }) {
  const [forms, setForms] = useState([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { api.get("/forms").then(({ data }) => setForms(data)).catch((err) => setError(err.response?.data?.detail || "Unable to load forms.")); }, []);
  const disconnect = async () => {
    try { await api.post("/auth/disconnect-google"); setNotice("Google account disconnected; automatic form processing is paused."); }
    catch (err) { setError(err.response?.data?.detail || "Could not disconnect Google."); }
  };
  return <>
    <PageHeading eyebrow="Account" title="Settings" description="Manage your connected Google account and forms." />
    {notice && <Notice kind="success" className="mt-5">{notice}</Notice>}{error && <Notice kind="error" className="mt-5">{error}</Notice>}
    <section className="mt-6 max-w-3xl rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-semibold">Google account</h2><p className="mt-2 text-sm text-slate-600">{user.email} · {user.google_connected ? "Connected" : "Disconnected"}</p><button onClick={disconnect} className="secondary-button mt-4">Disconnect Google</button></section>
    <section className="mt-5 max-w-3xl rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-semibold">Connected forms</h2>{forms.length ? <ul className="mt-3 divide-y divide-slate-100">{forms.map((form) => <li key={form.id} className="flex items-center justify-between gap-4 py-3 text-sm"><span>{form.form_name}</span><Link className="font-medium text-indigo-700" to={`/forms/${form.id}/mapping`}>Configure</Link></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">No forms connected yet.</p>}<Link className="primary-button mt-4" to="/forms/connect">Connect form</Link></section>
  </>;
}

function CandidateTable({ candidates, compact = false }) {
  if (!candidates?.length) return <div className="px-5 py-12 text-center"><Users className="mx-auto text-slate-300" size={28} /><p className="mt-3 text-sm font-medium">No candidates yet</p><p className="mt-1 text-sm text-slate-500">Connect a form and enable automatic processing to get started.</p></div>;
  return <div className="overflow-x-auto"><table className="w-full min-w-[690px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Candidate</th><th className="px-5 py-3">Mobile</th><th className="px-5 py-3">Submitted</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Document</th></tr></thead><tbody className="divide-y divide-slate-100">{candidates.map((candidate) => <tr key={candidate.id} className="hover:bg-slate-50"><td className="px-5 py-3.5"><Link to={`/candidates/${candidate.id}`} className="font-semibold text-slate-800 hover:text-indigo-700">{candidate.candidate_name}</Link><p className="mt-0.5 text-xs text-slate-500">{candidate.registration_id}</p></td><td className="px-5 py-3.5 text-slate-600">{candidate.mobile_number || "—"}</td><td className="px-5 py-3.5 text-slate-600">{new Date(candidate.submission_timestamp).toLocaleDateString()}</td><td className="px-5 py-3.5"><StatusBadge status={candidate.processing_status} /></td><td className="px-5 py-3.5">{candidate.document_drive_id ? <Link className="inline-flex items-center gap-1 font-medium text-indigo-700" to={`/candidates/${candidate.id}`}>Open <ExternalLink size={14} /></Link> : <span className="text-slate-400">—</span>}</td></tr>)}</tbody></table></div>;
}

function StatusBadge({ status }) {
  const style = status === "completed" ? "bg-emerald-50 text-emerald-700" : status === "failed" ? "bg-rose-50 text-rose-700" : status === "processing" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${style}`}>{status}</span>;
}

function PageHeading({ eyebrow, title, description, action }) {
  return <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-600">{eyebrow}</p><h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">{title}</h1><p className="mt-2 text-sm text-slate-500">{description}</p></div>{action}</div>;
}

function Notice({ children, kind, className = "" }) {
  return <div className={`${kind === "error" ? "border-rose-200 bg-rose-50 text-rose-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"} rounded-lg border px-4 py-3 text-sm ${className}`}>{children}</div>;
}

function CenteredState({ text }) {
  return <div className="grid min-h-[45vh] place-items-center text-sm text-slate-500"><span className="flex items-center gap-2"><LoaderCircle className="animate-spin" size={17} />{text}</span></div>;
}

export default App;
