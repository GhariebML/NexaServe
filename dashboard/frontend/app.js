/**
 * NexaServe Production Admin Dashboard - Core Frontend Controller
 * Real-time API communication, State management, Bilingual Arabic/English i18n, Chart.js rendering
 */

const STATE = {
  token: localStorage.getItem('nexaserve_jwt_token') || null,
  user: JSON.parse(localStorage.getItem('nexaserve_user') || 'null'),
  currentView: 'executive',
  currentLang: localStorage.getItem('nexaserve_lang') || 'en',
  period: 'all',
  program: 'DEPI',
  charts: {},
  customerSearchTimeout: null,
  ticketSearchTimeout: null,
  selectedTicketId: null,
  customerPage: 1,
  convPage: 1,
  ticketPage: 1,
  isExporting: false
};

// Bilingual dictionary
const I18N = {
  en: {
    ops_center: "Operations Command",
    login_sub: "MCIT Enterprise Support Platform",
    lbl_username: "Username",
    lbl_password: "Password",
    btn_login: "Authenticate Session",
    btn_logout: "Logout",
    btn_change_password: "Password",
    pw_title: "Change Password",
    pw_forced_note: "Your account requires a new password before you can continue.",
    pw_current: "Current password",
    pw_new: "New password (at least 12 characters)",
    pw_confirm: "Confirm new password",
    pw_submit: "Update Password",
    pw_cancel: "Cancel",
    pw_mismatch: "The new passwords do not match.",
    pw_too_short: "The new password must be at least 12 characters.",
    nav_executive: "Executive KPIs",
    nav_customers: "Customers & Students",
    nav_conversations: "Conversations",
    nav_tickets: "Tickets & HITL",
    nav_n8n: "n8n Automation",
    nav_simulator: "Live AI Simulator",
    nav_rag: "RAG & AI Quality",
    nav_kb: "Knowledge Base",
    nav_health: "System Health",
    nav_activity: "Recent Activity",
    title_n8n_workflows: "n8n Automation Engine & Workflows",
    sub_n8n_workflows: "Direct bidirectional link with local n8n instance and workflow execution engine",
    btn_open_n8n: "Open n8n Canvas",
    title_deployed_wfs: "Registered System Workflows",
    title_n8n_live_execs: "Live n8n REST Executions",
    title_simulator: "Live Customer Service AI Simulator",
    sub_simulator: "Interact directly with live n8n Master Gateway, Ollama LLM, pgvector RAG, and HITL escalation",
    btn_send: "Send Inquiry 🚀",
    title_live_telemetry: "Correlated n8n Trace & Telemetry",
    title_recent_executions: "Recent customer requests",
    status_not_measured: "Not measured",
    open_trace: "Open n8n trace",
    inspect: "Inspect",
    no_executions: "No correlated requests recorded yet.",
    filter_period: "Period:",
    filter_program: "Program:",
    opt_all_time: "All Time",
    opt_today: "Today",
    opt_yesterday: "Yesterday",
    opt_7d: "Last 7 Days",
    opt_30d: "Last 30 Days",
    opt_month: "This Month",
    opt_all_programs: "All Programs",
    title_customers: "Customer & Student Registry",
    title_conversations: "Conversations Log",
    title_tickets: "Human-in-the-Loop Tickets",
    title_kb_breakdown: "Knowledge Base Documents by Program & Source",
    title_sys_health: "Enterprise Stack Health Status",
    title_recent_activity: "System Observability & Audit Trail",
    title_program_isolation: "Program Isolation Guardrail Verification",
    isolation_desc: "Enforced by multi-tier query normalization, explicit program scoping, and conservative Arabic normalizer.",
    chart_conv_time: "Conversations Over Time",
    chart_depi_digilians: "DEPI vs Digilians Breakdown",
    chart_confidence: "AI Confidence Distribution",
    kb_by_prog: "By Initiative",
    kb_by_source: "By Attribution Source",
    col_name: "Name",
    col_phone: "Phone (Masked)",
    col_program: "Program",
    col_created: "Created",
    col_last_act: "Last Interaction",
    col_conv_count: "Convs",
    col_open_tickets: "Open Tickets",
    col_status: "Status",
    col_customer: "Customer",
    col_channel: "Channel",
    col_intent: "Intent",
    col_confidence: "Confidence",
    col_actions: "Actions",
    col_priority: "Priority",
    col_agent: "Assigned Agent",
    col_sla_deadline: "SLA Deadline",
    col_sla_status: "SLA Status",
    col_event: "Event",
    col_workflow: "Workflow",
    col_summary: "Summary",
    col_latency: "Latency",
    col_timestamp: "Timestamp",
    btn_view_details: "View Details",
    kpi_total_customers: "Total Customers",
    kpi_sub_total_customers: "Registered across channels",
    kpi_active_convs: "Active Conversations",
    kpi_sub_active_convs: "Currently in session",
    kpi_total_convs: "Total Conversations",
    kpi_sub_total_convs: "All-time volume",
    kpi_open_tickets: "Open Tickets",
    kpi_sub_open_tickets: "Awaiting resolution",
    kpi_pending_tickets: "Pending Tickets",
    kpi_sub_pending_tickets: "In progress by agent",
    kpi_resolved_tickets: "Resolved Tickets",
    kpi_sub_resolved_tickets: "Successfully closed",
    kpi_sla_breaches: "SLA Breaches",
    kpi_sub_sla_breaches: "Action required immediately",
    kpi_escalated_convs: "Escalated Convs",
    kpi_sub_escalated_convs: "Routed to human tier",
    kpi_avg_response_time: "Avg Response Time",
    kpi_sub_avg_response_time: "End-to-end audit latency",
    kpi_rag_success_rate: "Successful Turn Rate",
    kpi_sub_rag_success_rate: "Operational successful turns; not answer accuracy",
    unit_ms: " ms",
    export_report: "Export to Excel",
    export_loading: "Preparing workbook…",
    export_success: "Excel report downloaded.",
    export_error: "The report could not be generated.",
    rag_eval_title: "RAG Evaluation",
    rag_eval_definition: "Acceptance test pass rate among completed cases. This is not answer accuracy.",
    rag_eval_loading: "Loading verified evaluation summary…",
    rag_eval_unavailable: "No verified evaluation summary is available.",
    rag_eval_runtime: "Runtime",
    rag_eval_corpus: "Corpus",
    rag_eval_cases: "Cases",
    rag_eval_details: "View evaluation details",
    rag_eval_refresh: "Reload evaluation summary"
  },
  ar: {
    ops_center: "مركز العمليات والتحكم",
    login_sub: "منصة الدعم الفني الموحدة لوزارة الاتصالات",
    lbl_username: "اسم المستخدم",
    lbl_password: "كلمة المرور",
    btn_login: "تسجيل الدخول للنظام",
    btn_logout: "خروج",
    btn_change_password: "كلمة المرور",
    pw_title: "تغيير كلمة المرور",
    pw_forced_note: "يتطلب حسابك تعيين كلمة مرور جديدة قبل المتابعة.",
    pw_current: "كلمة المرور الحالية",
    pw_new: "كلمة المرور الجديدة (12 حرفاً على الأقل)",
    pw_confirm: "تأكيد كلمة المرور الجديدة",
    pw_submit: "تحديث كلمة المرور",
    pw_cancel: "إلغاء",
    pw_mismatch: "كلمتا المرور الجديدتان غير متطابقتين.",
    pw_too_short: "يجب ألا تقل كلمة المرور الجديدة عن 12 حرفاً.",
    nav_executive: "المؤشرات التنفيذية",
    nav_customers: "العملاء والطلاب",
    nav_conversations: "المحادثات المباشرة",
    nav_tickets: "التذاكر والدعم البشري",
    nav_n8n: "أتمتة وسير عمل n8n",
    nav_simulator: "محاكي الذكاء الاصطناعي الحي",
    nav_rag: "جودة الذكاء الاصطناعي و RAG",
    nav_kb: "قاعدة المعرفة والوثائق",
    nav_health: "سلامة وخوادم النظام",
    nav_activity: "سجل العمليات الأخير",
    title_n8n_workflows: "محرك الأتمتة وسير العمل n8n",
    sub_n8n_workflows: "ربط تكاملي مباشر ثنائي الاتجاه مع منصة n8n المحلية ومحرك تنفيذ التدفقات",
    btn_open_n8n: "فتح لوحة سير عمل n8n",
    title_deployed_wfs: "تدفقات العمل المسجة في النظام",
    title_n8n_live_execs: "تنفيذات n8n الحية (REST API)",
    title_simulator: "محاكي خدمة العملاء المباشر",
    sub_simulator: "تفاعل مباشر مع بوابة n8n الرئيسية، نموذج Ollama، تقنية pgvector RAG، والتصعيد البشري",
    btn_send: "إرسال الاستفسار 🚀",
    title_live_telemetry: "التتبع الحي والقياسات من n8n",
    title_recent_executions: "طلبات العملاء الأخيرة",
    status_not_measured: "لم يُقَس بعد",
    open_trace: "فتح التنفيذ في n8n",
    inspect: "تفاصيل",
    no_executions: "لا توجد طلبات مترابطة مسجلة حتى الآن.",
    filter_period: "الفترة الزمنية:",
    filter_program: "المبادرة:",
    opt_all_time: "كل الفترات",
    opt_today: "اليوم",
    opt_yesterday: "أمس",
    opt_7d: "آخر 7 أيام",
    opt_30d: "آخر 30 يوماً",
    opt_month: "الشهر الحالي",
    opt_all_programs: "كافة المبادرات",
    title_customers: "سجل الطلاب والمستفيدين",
    title_conversations: "سجل المحادثات والجلسات",
    title_tickets: "تذاكر الدعم والتدخل البشري",
    title_kb_breakdown: "توزيع مستندات المعرفة حسب المبادرة والمصدر",
    title_sys_health: "حالة وجاهزية مكونات الخادم",
    title_recent_activity: "سجل المراقبة والتدقيق الفوري",
    title_program_isolation: "التحقق من عزل المبادرات وحماية البيانات",
    isolation_desc: "يتم تطبيقه عبر المعايرة اللغوية المحافظة، نطاقات الاستعلام الصارمة، وحواجز الحماية التلقائية.",
    chart_conv_time: "المحادثات عبر الزمن",
    chart_depi_digilians: "توزيع DEPI مقابل Digilians",
    chart_confidence: "توزيع درجات ثقة النموذج",
    kb_by_prog: "حسب المبادرة",
    kb_by_source: "حسب جهة الاعتماد",
    col_name: "الاسم",
    col_phone: "الهاتف (مشفر)",
    col_program: "المبادرة",
    col_created: "تاريخ الإنشاء",
    col_last_act: "آخر تفاعل",
    col_conv_count: "المحادثات",
    col_open_tickets: "التذاكر المفتوحة",
    col_status: "الحالة",
    col_customer: "المستفيد",
    col_channel: "القناة",
    col_intent: "النية المصنفة",
    col_confidence: "الثقة",
    col_actions: "إجراءات",
    col_priority: "الأولوية",
    col_agent: "المسؤول المكلف",
    col_sla_deadline: "موعد اتفاقية SLA",
    col_sla_status: "حالة SLA",
    col_event: "الحدث",
    col_workflow: "مسار العمل",
    col_summary: "الملخص",
    col_latency: "زمن الاستجابة",
    col_timestamp: "الوقت",
    btn_view_details: "عرض التفاصيل",
    kpi_total_customers: "إجمالي المستفيدين والطلاب",
    kpi_sub_total_customers: "المسجلين عبر جميع القنوات",
    kpi_active_convs: "المحادثات الجارية حالياً",
    kpi_sub_active_convs: "جلسات نشطة في الوقت الفعلي",
    kpi_total_convs: "إجمالي المحادثات",
    kpi_sub_total_convs: "الحجم الكلي لجميع الجلسات",
    kpi_open_tickets: "التذاكر المفتوحة",
    kpi_sub_open_tickets: "في انتظار المراجعة والمعالجة",
    kpi_pending_tickets: "التذاكر قيد المعالجة",
    kpi_sub_pending_tickets: "جارٍ العمل عليها من قبل موظف الدعم",
    kpi_resolved_tickets: "التذاكر المكتملة والمغلقة",
    kpi_sub_resolved_tickets: "تم حلها وإغلاقها بنجاح",
    kpi_sla_breaches: "تجاوزات اتفاقية مستوى الخدمة SLA",
    kpi_sub_sla_breaches: "تتطلب إجراءً فورياً وعاجلاً",
    kpi_escalated_convs: "المحادثات المصعدة بشرياً",
    kpi_sub_escalated_convs: "تم تحويلها لفرق الدعم البشري",
    kpi_avg_response_time: "متوسط زمن الاستجابة",
    kpi_sub_avg_response_time: "الزمن الكلي لمعالجة وتدقيق الرد",
    kpi_rag_success_rate: "نسبة نجاح المعالجة",
    kpi_sub_rag_success_rate: "نجاح المعالجة التشغيلية؛ لا يمثل دقة الإجابة",
    unit_ms: " مللي ثانية",
    export_report: "تصدير إلى Excel",
    export_loading: "جارٍ إعداد الملف…",
    export_success: "تم تنزيل تقرير Excel.",
    export_error: "تعذر إنشاء التقرير.",
    rag_eval_title: "تقييم RAG",
    rag_eval_definition: "نسبة اختبارات القبول الناجحة من الحالات المكتملة. لا تمثل دقة الإجابة.",
    rag_eval_loading: "جارٍ تحميل ملخص التقييم الموثق…",
    rag_eval_unavailable: "لا يتوفر ملخص تقييم موثق.",
    rag_eval_runtime: "بيئة التشغيل",
    rag_eval_corpus: "مجموعة المعرفة",
    rag_eval_cases: "الحالات",
    rag_eval_details: "عرض تفاصيل التقييم",
    rag_eval_refresh: "إعادة تحميل ملخص التقييم"
  }
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

// Encodes a value as a JS string literal that is safe inside a double-quoted inline handler attribute.
function jsArg(value) {
  return escapeHtml(JSON.stringify(String(value ?? '')));
}

function formatMetric(value, suffix = '') {
  return value === null || value === undefined ? 'N/A' : `${Number(value).toLocaleString()}${suffix}`;
}

const PASSWORD_CHANGE_REQUIRED = 'password_change_required';

// API Fetch Helper with Bearer Token
async function apiRequest(endpoint, options = {}) {
  const headers = options.headers || {};
  if (STATE.token) {
    headers['Authorization'] = `Bearer ${STATE.token}`;
  }
  options.headers = headers;

  const res = await fetch(endpoint, options);
  if (res.status === 401) {
    clearSession();
    throw new Error('Session expired or unauthorized');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const detail = errorData.detail;
    if (res.status === 403 && detail === PASSWORD_CHANGE_REQUIRED) {
      showPasswordModal(true);
      throw new Error(I18N[STATE.currentLang].pw_forced_note);
    }
    let errMsg;
    if (Array.isArray(detail)) {
      // Pydantic validation error format
      errMsg = detail.map(d => d.msg || JSON.stringify(d)).join('; ');
    } else if (detail && typeof detail === 'object') {
      errMsg = JSON.stringify(detail);
    } else {
      errMsg = detail || `Request failed with status ${res.status}`;
    }
    throw new Error(errMsg);
  }
  return await res.json();
}

// Initial Boot
document.addEventListener('DOMContentLoaded', () => {
  applyLanguage(STATE.currentLang);
  setupAuthForm();
  setupPasswordForm();

  if (STATE.token && STATE.user) {
    enterSession();
  } else {
    showLoginModal();
  }
});

function storeSession(data) {
  STATE.token = data.access_token;
  STATE.user = data.user;
  localStorage.setItem('nexaserve_jwt_token', data.access_token);
  localStorage.setItem('nexaserve_user', JSON.stringify(data.user));
}

// Accounts flagged for a forced password change see only the password screen.
function enterSession() {
  if (STATE.user && STATE.user.must_change_password) {
    showPasswordModal(true);
  } else {
    showAppShell();
  }
}

function showPasswordModal(forced) {
  const modal = document.getElementById('password-modal');
  document.getElementById('password-form').reset();
  document.getElementById('password-error').style.display = 'none';
  document.getElementById('password-forced-note').style.display = forced ? 'block' : 'none';
  document.getElementById('password-cancel').style.display = forced ? 'none' : 'block';
  document.getElementById('password-signout').style.display = forced ? 'block' : 'none';
  modal.dataset.forced = forced ? 'true' : 'false';
  document.getElementById('login-modal').style.display = 'none';
  if (forced) document.getElementById('app-shell').style.display = 'none';
  modal.style.display = 'flex';
  document.getElementById('pw-current').focus();
}

function hidePasswordModal() {
  document.getElementById('password-modal').style.display = 'none';
}

function setupPasswordForm() {
  const form = document.getElementById('password-form');
  document.getElementById('password-cancel').addEventListener('click', hidePasswordModal);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const t = I18N[STATE.currentLang];
    const errBox = document.getElementById('password-error');
    errBox.style.display = 'none';
    const oldPassword = document.getElementById('pw-current').value;
    const newPassword = document.getElementById('pw-new').value;
    const confirmPassword = document.getElementById('pw-confirm').value;
    const showError = (message) => { errBox.textContent = message; errBox.style.display = 'block'; };
    if (newPassword.length < 12) return showError(t.pw_too_short);
    if (newPassword !== confirmPassword) return showError(t.pw_mismatch);

    try {
      const res = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${STATE.token}` },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 401) {
        clearSession();
        return;
      }
      if (!res.ok) throw new Error(data.detail || `Request failed with status ${res.status}`);
      // The server revoked the previous token; continue with the one it issued.
      const wasForced = document.getElementById('password-modal').dataset.forced === 'true';
      storeSession(data);
      hidePasswordModal();
      if (wasForced) showAppShell();
    } catch (err) {
      showError(err.message);
    }
  });
}

function applyLanguage(lang) {
  STATE.currentLang = lang;
  localStorage.setItem('nexaserve_lang', lang);
  document.documentElement.lang = lang;
  document.documentElement.dir = (lang === 'ar') ? 'rtl' : 'ltr';

  const langLabel = document.getElementById('lang-label');
  if (langLabel) {
    langLabel.innerText = (lang === 'ar') ? 'EN' : 'عربي';
  }

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (I18N[lang] && I18N[lang][key]) {
      el.innerText = I18N[lang][key];
    }
  });

  if (STATE.token && STATE.user) {
    refreshCurrentView();
  }
}

function toggleLanguage() {
  const next = (STATE.currentLang === 'en') ? 'ar' : 'en';
  applyLanguage(next);
}

function setupAuthForm() {
  const form = document.getElementById('login-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errBox = document.getElementById('login-error');
    errBox.style.display = 'none';

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Login failed');

      storeSession(data);
      enterSession();
    } catch (err) {
      errBox.innerText = err.message;
      errBox.style.display = 'block';
    }
  });
}

function showLoginModal() {
  document.getElementById('login-modal').style.display = 'flex';
  document.getElementById('app-shell').style.display = 'none';
}

function showAppShell() {
  document.getElementById('login-modal').style.display = 'none';
  document.getElementById('app-shell').style.display = 'flex';

  document.getElementById('user-display-name').innerText = STATE.user.full_name || STATE.user.username;
  document.getElementById('user-role-badge').innerText = (STATE.user.role || 'READONLY').toUpperCase();

  switchView('executive');
}

function clearSession() {
  STATE.token = null;
  STATE.user = null;
  localStorage.removeItem('nexaserve_jwt_token');
  localStorage.removeItem('nexaserve_user');
  hidePasswordModal();
  showLoginModal();
}

function logout() {
  // Revoke server-side too, so a copied token stops working; sign out locally even if this fails.
  if (STATE.token) {
    fetch('/api/auth/logout', { method: 'POST', headers: { Authorization: `Bearer ${STATE.token}` } }).catch(() => {});
  }
  clearSession();
}

function switchView(viewName) {
  STATE.currentView = viewName;
  document.querySelectorAll('.nav-item button').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-view') === viewName);
  });

  document.querySelectorAll('.dashboard-section').forEach(sec => {
    sec.style.display = 'none';
  });

  const activeSec = document.getElementById(`view-${viewName}`);
  if (activeSec) activeSec.style.display = 'block';
  updateExportAvailability();

  refreshCurrentView();
}

const EXPORT_REPORTS = {
  executive: 'executive', customers: 'customers', conversations: 'conversations',
  tickets: 'tickets', n8n: 'n8n', rag: 'rag', kb: 'knowledge-base',
  health: 'health', activity: 'activity'
};

function updateExportAvailability() {
  const button = document.getElementById('export-report-btn');
  if (!button) return;
  button.hidden = !EXPORT_REPORTS[STATE.currentView];
  button.disabled = STATE.isExporting;
  const label = (I18N[STATE.currentLang] || I18N.en).export_report;
  button.title = label;
  button.setAttribute('aria-label', label);
}

function showExportToast(message, isError = false) {
  const toast = document.getElementById('export-toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `export-toast ${isError ? 'error' : 'success'}`;
  toast.hidden = false;
  clearTimeout(STATE.exportToastTimeout);
  STATE.exportToastTimeout = setTimeout(() => { toast.hidden = true; }, 4500);
}

async function exportCurrentReport() {
  const reportType = EXPORT_REPORTS[STATE.currentView];
  const button = document.getElementById('export-report-btn');
  const t = I18N[STATE.currentLang] || I18N.en;
  if (!reportType || STATE.isExporting || !button) return;
  const query = new URLSearchParams({ lang: STATE.currentLang });
  if (['executive', 'customers', 'conversations', 'tickets'].includes(reportType)) {
    query.set('program', STATE.program);
  }
  if (['executive', 'conversations'].includes(reportType)) query.set('period', STATE.period);
  if (reportType === 'customers') {
    query.set('search', document.getElementById('customer-search-input')?.value.trim() || '');
  }
  if (reportType === 'tickets') {
    query.set('ticket_status', document.getElementById('ticket-status-filter')?.value || 'all');
    query.set('priority', document.getElementById('ticket-priority-filter')?.value || 'all');
    query.set('category', document.getElementById('ticket-category-filter')?.value || 'all');
    query.set('channel', document.getElementById('ticket-channel-filter')?.value || 'all');
    query.set('search', document.getElementById('ticket-search-input')?.value.trim() || '');
  }
  if (reportType === 'activity') {
    query.set('execution_status', document.getElementById('execution-status-filter')?.value || '');
  }

  const originalText = button.textContent;
  STATE.isExporting = true;
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  button.textContent = t.export_loading;
  try {
    const response = await fetch(`/api/dashboard/reports/${reportType}/excel?${query.toString()}`, {
      headers: STATE.token ? { Authorization: `Bearer ${STATE.token}` } : {}
    });
    if (response.status === 401) {
      clearSession();
      throw new Error('Session expired or unauthorized');
    }
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      if (response.status === 403 && error.detail === PASSWORD_CHANGE_REQUIRED) {
        showPasswordModal(true);
      }
      throw new Error(error.detail || t.export_error);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') || '';
    const filename = disposition.match(/filename="([^"]+)"/i)?.[1] || 'NexaServe_Report.xlsx';
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showExportToast(t.export_success);
  } catch (error) {
    showExportToast(error.message || t.export_error, true);
  } finally {
    STATE.isExporting = false;
    button.removeAttribute('aria-busy');
    button.disabled = false;
    button.textContent = originalText || t.export_report;
  }
}

function refreshCurrentView() {
  STATE.period = document.getElementById('global-date-filter').value;
  STATE.program = document.getElementById('global-program-filter').value;

  switch (STATE.currentView) {
    case 'executive': loadExecutiveKPIs(); loadRAGEvaluationCard(); break;
    case 'customers': loadCustomers(); break;
    case 'conversations': loadConversations(); break;
    case 'tickets': loadTickets(); break;
    case 'n8n': loadN8nData(); break;
    case 'simulator': loadSimulator(); break;
    case 'rag': loadRAGMetrics(); break;
    case 'kb': loadKBMetrics(); break;
    case 'health': loadSystemHealth(); break;
    case 'activity': loadRecentActivity(); break;
  }
}

// --- 1. EXECUTIVE KPIS ---
async function loadRAGEvaluationCard() {
  const card = document.getElementById('rag-evaluation-card');
  if (!card) return;
  const t = I18N[STATE.currentLang] || I18N.en;
  card.innerHTML = `<div class="rag-eval-loading" role="status">${escapeHtml(t.rag_eval_loading)}</div>`;
  try {
    const data = await apiRequest('/api/dashboard/rag/evaluation-summary');
    const status = ['HEALTHY', 'NEEDS_IMPROVEMENT', 'STALE', 'BLOCKED', 'NOT_EVALUATED'].includes(data.status)
      ? data.status : 'NOT_EVALUATED';
    const metric = data.pass_rate === null ? '—' : `${(Number(data.pass_rate) * 100).toFixed(1)}%`;
    const timestamp = data.last_evaluated_at ? escapeHtml(data.last_evaluated_at) : '—';
    const runtime = data.runtime_identity ? escapeHtml(data.runtime_identity) : 'Unknown';
    const corpus = data.corpus_version ? escapeHtml(data.corpus_version) : 'Unknown';
    const reason = data.reason ? `<p class="rag-eval-reason">${escapeHtml(data.reason)}</p>` : '';
    card.innerHTML = `
      <div class="rag-eval-head">
        <div><h2>${escapeHtml(t.rag_eval_title)}</h2><p>${escapeHtml(t.rag_eval_definition)}</p></div>
        <span class="rag-eval-status status-${status.toLowerCase()}" role="status">${escapeHtml(status.replaceAll('_', ' '))}</span>
      </div>
      <div class="rag-eval-body">
        <div class="rag-eval-primary"><span>${escapeHtml(data.metric_name || t.rag_eval_unavailable)}</span><strong>${metric}</strong></div>
        <dl class="rag-eval-facts">
          <div><dt>${escapeHtml(t.rag_eval_cases)}</dt><dd>${Number(data.evaluated_cases || 0)} evaluated / ${Number(data.planned_cases || 0)} planned</dd></div>
          <div><dt>Pass / fail / blocked</dt><dd>${Number(data.passed || 0)} / ${Number(data.failed || 0)} / ${Number(data.blocked || 0)}</dd></div>
          <div><dt>Last evaluation</dt><dd>${timestamp}${data.time_zone ? ` <small>(${escapeHtml(data.time_zone)})</small>` : ''}</dd></div>
          <div><dt>${escapeHtml(t.rag_eval_runtime)}</dt><dd>${runtime}</dd></div>
          <div><dt>${escapeHtml(t.rag_eval_corpus)}</dt><dd>${corpus}</dd></div>
        </dl>
      </div>
      ${reason}
      <div class="rag-eval-actions">
        <button class="btn-link" type="button" onclick="switchView('rag')">${escapeHtml(t.rag_eval_details)}</button>
        <button class="btn-link" type="button" onclick="loadRAGEvaluationCard()" aria-label="${escapeHtml(t.rag_eval_refresh)}">↻ ${escapeHtml(t.rag_eval_refresh)}</button>
      </div>`;
  } catch (error) {
    card.innerHTML = `<div class="rag-eval-unavailable" role="alert">${escapeHtml(t.rag_eval_unavailable)} <button class="btn-link" type="button" onclick="loadRAGEvaluationCard()">Retry</button></div>`;
  }
}

async function loadExecutiveKPIs() {
  const container = document.getElementById('executive-kpi-grid');
  const t = I18N[STATE.currentLang] || I18N.en;
  container.innerHTML = `<div style="color:var(--text-muted);">${STATE.currentLang === 'ar' ? 'جارٍ تحميل البيانات المباشرة...' : 'Querying live database...'}</div>`;

  try {
    const data = await apiRequest(`/api/dashboard/summary?period=${STATE.period}&program=${STATE.program}`);
    const unitMs = t.unit_ms || ' ms';

    container.innerHTML = `
      <div class="kpi-card">
        <span class="kpi-label">${t.kpi_total_customers}</span>
        <span class="kpi-value">${data.total_customers.toLocaleString()}</span>
        <span class="kpi-sub">${t.kpi_sub_total_customers}</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-label">${t.kpi_active_convs}</span>
        <span class="kpi-value">${data.active_conversations.toLocaleString()}</span>
        <span class="kpi-sub">${t.kpi_sub_active_convs}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">${t.kpi_total_convs}</span>
        <span class="kpi-value">${data.total_conversations.toLocaleString()}</span>
        <span class="kpi-sub">${t.kpi_sub_total_convs}</span>
      </div>
      <div class="kpi-card warning">
        <span class="kpi-label">${t.kpi_open_tickets}</span>
        <span class="kpi-value">${data.open_tickets.toLocaleString()}</span>
        <span class="kpi-sub">${t.kpi_sub_open_tickets}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">${t.kpi_pending_tickets}</span>
        <span class="kpi-value">${data.pending_tickets.toLocaleString()}</span>
        <span class="kpi-sub">${t.kpi_sub_pending_tickets}</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-label">${t.kpi_resolved_tickets}</span>
        <span class="kpi-value">${data.resolved_tickets.toLocaleString()}</span>
        <span class="kpi-sub">${t.kpi_sub_resolved_tickets}</span>
      </div>
      <div class="kpi-card alert">
        <span class="kpi-label">${t.kpi_sla_breaches}</span>
        <span class="kpi-value" style="color:#F87171;">${data.sla_breaches.toLocaleString()}</span>
        <span class="kpi-sub">${t.kpi_sub_sla_breaches}</span>
      </div>
      <div class="kpi-card warning">
        <span class="kpi-label">${t.kpi_escalated_convs}</span>
        <span class="kpi-value">${data.escalated_conversations.toLocaleString()}</span>
        <span class="kpi-sub">${t.kpi_sub_escalated_convs}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">${t.kpi_avg_response_time}</span>
        <span class="kpi-value">${formatMetric(data.avg_response_time_ms, unitMs)}</span>
        <span class="kpi-sub">${t.kpi_sub_avg_response_time}</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-label">${t.kpi_rag_success_rate}</span>
        <span class="kpi-value">${formatMetric(data.rag_success_rate, '%')}</span>
        <span class="kpi-sub">${t.kpi_sub_rag_success_rate}</span>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">Failed to load KPIs: ${escapeHtml(err.message)}</div>`;
  }
}

// --- 2. CUSTOMERS ---
function debounceCustomerSearch(e) {
  clearTimeout(STATE.customerSearchTimeout);
  STATE.customerSearchTimeout = setTimeout(() => {
    STATE.customerPage = 1;
    loadCustomers();
  }, 350);
}

async function loadCustomers() {
  const tbody = document.getElementById('customers-table-body');
  const search = document.getElementById('customer-search-input').value.trim();
  tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">Loading customer registry...</td></tr>';

  try {
    const data = await apiRequest(`/api/dashboard/customers?program=${STATE.program}&search=${encodeURIComponent(search)}&page=${STATE.customerPage}&limit=10`);

    if (data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No matching customer records found.</td></tr>';
      return;
    }

    tbody.innerHTML = data.items.map(c => `
      <tr>
        <td style="font-family:monospace; font-size:0.75rem; color:var(--text-muted);">${c.id.substring(0,8)}...</td>
        <td><button class="btn-page" onclick="openCustomerProfile('${c.id}')" style="font-weight:600;">${escapeHtml(c.full_name)}</button></td>
        <td><code>${escapeHtml(c.phone_masked || 'N/A')}</code></td>
        <td><span class="badge ${c.program === 'DEPI' ? 'badge-depi' : 'badge-digilians'}">${escapeHtml(c.program)}</span></td>
        <td>${c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}</td>
        <td>${c.last_interaction ? new Date(c.last_interaction).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'N/A'}</td>
        <td>${c.conversation_count}</td>
        <td>${c.open_tickets > 0 ? `<span style="color:#F87171; font-weight:700;">${c.open_tickets}</span>` : '0'}</td>
        <td><span class="badge ${c.customer_status === 'Active' ? 'badge-resolved' : 'badge-pending'}">${escapeHtml(c.customer_status)}</span></td>
      </tr>
    `).join('');

    renderPagination('customers-pagination', data.page, data.pages, (p) => {
      STATE.customerPage = p;
      loadCustomers();
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</td></tr>`;
  }
}

// --- 3. CONVERSATIONS ---
async function loadConversations() {
  const tbody = document.getElementById('conversations-table-body');
  const kpiBox = document.getElementById('conversation-kpis');
  tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">Loading conversations...</td></tr>';

  try {
    const data = await apiRequest(`/api/dashboard/conversations?period=${STATE.period}&program=${STATE.program}&page=${STATE.convPage}&limit=10`);

    // Render Metrics
    kpiBox.innerHTML = `
      <div class="kpi-card"><span class="kpi-label">Total Convs</span><span class="kpi-value">${data.metrics.total_conversations}</span></div>
      <div class="kpi-card success"><span class="kpi-label">Today</span><span class="kpi-value">${data.metrics.conversations_today}</span></div>
      <div class="kpi-card"><span class="kpi-label">This Week</span><span class="kpi-value">${data.metrics.conversations_this_week}</span></div>
      <div class="kpi-card warning"><span class="kpi-label">Escalation Rate</span><span class="kpi-value">${data.metrics.escalation_rate}%</span></div>
      <div class="kpi-card"><span class="kpi-label">Avg Turns</span><span class="kpi-value">${data.metrics.avg_conversation_length} msgs</span></div>
    `;

    // Render Charts
    renderConvCharts(data.charts);

    if (data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No conversations found.</td></tr>';
      return;
    }

    tbody.innerHTML = data.items.map(c => `
      <tr>
        <td style="font-family:monospace; font-size:0.75rem; color:var(--text-muted);">${c.id.substring(0,8)}...</td>
        <td style="font-weight:600;">${escapeHtml(c.customer_name)}</td>
        <td><span class="badge ${c.program === 'DEPI' ? 'badge-depi' : 'badge-digilians'}">${escapeHtml(c.program)}</span></td>
        <td><span class="badge badge-normal">${escapeHtml(c.channel)}</span></td>
        <td><code>${escapeHtml(c.intent)}</code></td>
        <td>${Math.round(c.avg_confidence * 100)}%</td>
        <td><span class="badge ${c.status === 'active' ? 'badge-resolved' : 'badge-pending'}">${escapeHtml(c.status)}</span></td>
        <td>${c.created_at ? new Date(c.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : 'N/A'}</td>
        <td>
          <button class="btn-page" onclick="openConversationDetail('${c.id}')">View</button>
        </td>
      </tr>
    `).join('');

    renderPagination('conversations-pagination', data.page, data.pages, (p) => {
      STATE.convPage = p;
      loadConversations();
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderConvCharts(charts) {
  // 1. Time chart
  const ctxTime = document.getElementById('chart-conv-time');
  if (STATE.charts.time) STATE.charts.time.destroy();
  STATE.charts.time = new Chart(ctxTime, {
    type: 'line',
    data: {
      labels: charts.conversations_over_time.map(x => x.date_label),
      datasets: [{
        label: 'Conversations',
        data: charts.conversations_over_time.map(x => x.count),
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59, 130, 246, 0.15)',
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9CA3AF' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9CA3AF' } }
      }
    }
  });

  // 2. Program Pie
  const ctxProg = document.getElementById('chart-prog-pie');
  if (STATE.charts.prog) STATE.charts.prog.destroy();
  STATE.charts.prog = new Chart(ctxProg, {
    type: 'doughnut',
    data: {
      labels: charts.program_distribution.map(x => x.label),
      datasets: [{
        data: charts.program_distribution.map(x => x.count),
        backgroundColor: ['#2563EB', '#8B5CF6', '#06B6D4', '#10B981']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#9CA3AF' } }
      }
    }
  });
}

function debounceTicketSearch() {
  clearTimeout(STATE.ticketSearchTimeout);
  STATE.ticketSearchTimeout = setTimeout(() => {
    STATE.ticketPage = 1;
    loadTickets();
  }, 350);
}

// --- 4. TICKETS ---
async function loadTickets() {
  const tbody = document.getElementById('tickets-table-body');
  const status = document.getElementById('ticket-status-filter')?.value || 'all';
  const priority = document.getElementById('ticket-priority-filter')?.value || 'all';
  const category = document.getElementById('ticket-category-filter')?.value || 'all';
  const channel = document.getElementById('ticket-channel-filter')?.value || 'all';
  const search = document.getElementById('ticket-search-input')?.value.trim() || '';
  const sortRaw = document.getElementById('ticket-sort-filter')?.value || 'created_at:desc';
  const [sortBy, sortDir] = sortRaw.split(':');

  tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;">Loading tickets...</td></tr>';

  try {
    const params = new URLSearchParams({
      status: status,
      priority: priority,
      category: category,
      channel: channel,
      search: search,
      sort_by: sortBy || 'created_at',
      sort_dir: sortDir || 'desc',
      program: STATE.program,
      page: STATE.ticketPage,
      limit: 10
    });

    const data = await apiRequest(`/api/dashboard/tickets?${params.toString()}`);

    // Update KPI counters if overview elements exist
    if (data.metrics) {
      const elTotal = document.getElementById('kpi-ticket-total');
      const elOpen = document.getElementById('kpi-ticket-open');
      const elPending = document.getElementById('kpi-ticket-pending');
      const elBreached = document.getElementById('kpi-ticket-breached');
      const elResolved = document.getElementById('kpi-ticket-resolved');
      if (elTotal) elTotal.innerText = data.metrics.total ?? (data.total || 0);
      if (elOpen) elOpen.innerText = data.metrics.open ?? 0;
      if (elPending) elPending.innerText = data.metrics.pending ?? 0;
      if (elBreached) elBreached.innerText = data.metrics.breached ?? 0;
      if (elResolved) elResolved.innerText = data.metrics.resolved ?? 0;
    }

    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="empty-state">No tickets matching selected filters.</td></tr>';
      return;
    }

    tbody.innerHTML = data.items.map(t => {
      let slaClass = 'badge-normal';
      if (t.sla_status === 'BREACHED') slaClass = 'badge-open';
      else if (t.sla_status === 'AT_RISK') slaClass = 'badge-pending';

      const displayTitle = t.title || t.reason || 'Support Request';
      const truncatedTitle = displayTitle.length > 45 ? displayTitle.substring(0, 42) + '...' : displayTitle;

      return `
        <tr>
          <td>
            <a href="javascript:void(0)" onclick="openTicketDetailsModal('${t.id}')" style="color:#60A5FA; font-weight:700; text-decoration:none;">
              ${escapeHtml(t.ticket_number)}
            </a>
          </td>
          <td>
            <div style="font-weight:600;">${escapeHtml(truncatedTitle)}</div>
            ${t.reason && t.reason !== displayTitle ? `<div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(t.reason.length > 60 ? t.reason.substring(0, 57) + '...' : t.reason)}</div>` : ''}
          </td>
          <td>
            <div style="font-weight:600;">${escapeHtml(t.customer_name || 'Unknown')}</div>
            <span class="badge ${t.program === 'DEPI' ? 'badge-depi' : 'badge-digilians'}">${escapeHtml(t.program || 'DEPI')}</span>
          </td>
          <td><span class="badge badge-normal">${escapeHtml(t.source_channel || t.channel || 'whatsapp')}</span></td>
          <td>${escapeHtml(STATE.currentLang === 'ar' ? (t.category_name_ar || t.category_name || '') : (t.category_name || ''))}</td>
          <td><span class="badge badge-${escapeHtml(t.priority)}">${escapeHtml(t.priority)}</span></td>
          <td><span class="badge badge-${escapeHtml(t.status)}">${escapeHtml(t.status)}</span></td>
          <td>${escapeHtml(t.assigned_agent || 'Unassigned')}</td>
          <td>
            <span class="badge ${slaClass}">${escapeHtml(t.sla_status || 'ON_TRACK')}</span>
            <div style="font-size:0.7rem; color:var(--text-muted);">${t.sla_deadline ? new Date(t.sla_deadline).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) : ''}</div>
          </td>
          <td>${t.created_at ? new Date(t.created_at).toLocaleDateString() : 'N/A'}</td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn-icon" style="font-size:0.75rem; padding:4px 8px; background:rgba(59,130,246,0.2); color:#60A5FA; border:1px solid rgba(59,130,246,0.4); border-radius:var(--radius-sm); cursor:pointer;" onclick="openTicketDetailsModal('${t.id}')" title="Inspect Full Lifecycle & Timeline">
                🔍 Details
              </button>
              <button class="btn-icon" style="font-size:0.75rem; padding:4px 8px; background:var(--primary); color:#fff; border-radius:var(--radius-sm); border:none; cursor:pointer;" onclick="openTicketModal(${jsArg(t.id)}, ${jsArg(t.ticket_number)}, ${jsArg(t.customer_name || 'Customer')})" title="Quick Respond / Resolve">
                💬
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    renderPagination('tickets-pagination', data.page, data.pages, (p) => {
      STATE.ticketPage = p;
      loadTickets();
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</td></tr>`;
  }
}


// --- 5. RAG & AI QUALITY ---
async function loadRAGMetrics() {
  const kpiGrid = document.getElementById('rag-kpi-grid');
  kpiGrid.innerHTML = '<div>Loading RAG metrics...</div>';

  try {
    const data = await apiRequest('/api/dashboard/rag');

    kpiGrid.innerHTML = `
      <div class="kpi-card"><span class="kpi-label">Total RAG Queries</span><span class="kpi-value">${data.rag_queries.toLocaleString()}</span></div>
      <div class="kpi-card success"><span class="kpi-label">Grounded Answers</span><span class="kpi-value">${data.grounded_answers.toLocaleString()}</span></div>
      <div class="kpi-card"><span class="kpi-label">Safe Deflections</span><span class="kpi-value">${data.safe_deflections}</span></div>
      <div class="kpi-card warning"><span class="kpi-label">Clarifications</span><span class="kpi-value">${data.clarification_requests}</span></div>
      <div class="kpi-card alert"><span class="kpi-label">Escalations</span><span class="kpi-value">${data.escalations}</span></div>
      <div class="kpi-card"><span class="kpi-label">Vector Retrieval</span><span class="kpi-value">${formatMetric(data.average_retrieval_latency_ms, ' ms')}</span></div>
      <div class="kpi-card"><span class="kpi-label">Avg LLM Latency</span><span class="kpi-value">${formatMetric(data.average_llm_latency_ms, ' ms')}</span></div>
      <div class="kpi-card"><span class="kpi-label">Latency p50 / p95</span><span class="kpi-value" style="font-size:1.4rem;">${formatMetric(data.p50_latency_ms)} / ${formatMetric(data.p95_latency_ms)} ms</span></div>
      <div class="kpi-card"><span class="kpi-label">Cache Hit Rate</span><span class="kpi-value">${formatMetric(data.cache_hit_rate, '%')}</span></div>
      <div class="kpi-card"><span class="kpi-label">Fallbacks / Errors</span><span class="kpi-value">${data.fallback_count} / ${data.error_count}</span></div>
      <div class="kpi-card alert"><span class="kpi-label">LLM failures</span><span class="kpi-value">${data.llm_failure_count}</span></div>
    `;

    const notMeasured = I18N[STATE.currentLang].status_not_measured || 'Not measured';
    document.getElementById('depi-leakage-rate').textContent = data.program_isolation.depi_leakage == null ? notMeasured : `${data.program_isolation.depi_leakage}%`;
    document.getElementById('digilians-leakage-rate').textContent = data.program_isolation.digilians_leakage == null ? notMeasured : `${data.program_isolation.digilians_leakage}%`;

    // Render Confidence Distribution Bar
    const ctxConf = document.getElementById('chart-confidence');
    if (STATE.charts.conf) STATE.charts.conf.destroy();
    STATE.charts.conf = new Chart(ctxConf, {
      type: 'bar',
      data: {
        labels: data.confidence_distribution.map(x => x.bracket),
        datasets: [{
          label: 'Messages',
          data: data.confidence_distribution.map(x => x.count),
          backgroundColor: '#06B6D4',
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#9CA3AF' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9CA3AF' } }
        }
      }
    });
  } catch (err) {
    kpiGrid.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</div>`;
  }
}

// --- 6. KNOWLEDGE BASE ---
async function loadKBMetrics() {
  const kpiGrid = document.getElementById('kb-kpi-grid');
  kpiGrid.innerHTML = '<div>Loading knowledge base analytics...</div>';

  try {
    const data = await apiRequest('/api/dashboard/knowledge-base');

    kpiGrid.innerHTML = `
      <div class="kpi-card"><span class="kpi-label">Total Documents</span><span class="kpi-value">${data.total_kb_documents}</span></div>
      <div class="kpi-card success"><span class="kpi-label">Active Documents</span><span class="kpi-value">${data.active_documents}</span></div>
      <div class="kpi-card success"><span class="kpi-label">Embedding Status</span><span class="kpi-value" style="color:#34D399;">${data.embedding_status}</span><span class="kpi-sub">Synchronized with pgvector</span></div>
      <div class="kpi-card"><span class="kpi-label">Last Ingestion</span><span class="kpi-value" style="font-size:1.1rem;">${data.last_ingestion_time ? new Date(data.last_ingestion_time).toLocaleDateString() : 'N/A'}</span></div>
      <div class="kpi-card"><span class="kpi-label">Last Verified</span><span class="kpi-value" style="font-size:1.1rem;">${data.last_update_time ? new Date(data.last_update_time).toLocaleDateString() : 'N/A'}</span></div>
    `;

    const progBox = document.getElementById('kb-prog-list');
    progBox.innerHTML = data.documents_by_program.map(p => `
      <div style="display:flex; justify-content:space-between; padding: 8px 12px; background:var(--bg-subtle); border-radius:var(--radius-sm);">
        <span style="font-weight:600;">${escapeHtml(p.program)}</span>
        <span class="badge badge-normal">${p.count} docs</span>
      </div>
    `).join('');

    const srcBox = document.getElementById('kb-source-list');
    srcBox.innerHTML = data.documents_by_source.map(s => `
      <div style="display:flex; justify-content:space-between; padding: 8px 12px; background:var(--bg-subtle); border-radius:var(--radius-sm);">
        <span style="font-size:0.85rem; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(s.source)}</span>
        <span class="badge badge-normal">${s.count} docs</span>
      </div>
    `).join('');
  } catch (err) {
    kpiGrid.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</div>`;
  }
}

// --- 7. SYSTEM HEALTH ---
async function loadSystemHealth() {
  const grid = document.getElementById('health-grid-cards');
  const badge = document.getElementById('overall-health-badge');
  grid.innerHTML = '<div>Checking system health...</div>';

  try {
    const data = await apiRequest('/api/dashboard/system-health');

    badge.innerText = data.overall_status;
    badge.className = `badge badge-${data.overall_status.toLowerCase()}`;

    grid.innerHTML = data.services.map(s => `
      <div class="health-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:700; font-size:0.95rem;">${escapeHtml(s.name)}</span>
          <div style="display:flex; align-items:center; gap:6px;">
            <span class="status-dot ${escapeHtml(s.status.toLowerCase())}"></span>
            <span style="font-size:0.75rem; font-weight:700;">${escapeHtml(s.status)}</span>
          </div>
        </div>
        <div style="font-size:0.8rem; color:var(--text-muted); display:flex; justify-content:space-between; margin-top:8px;">
          <span>Latency:</span>
          <strong>${s.latency_ms !== null ? s.latency_ms + ' ms' : 'N/A'}</strong>
        </div>
        <div style="font-size:0.7rem; color:var(--text-subtle);">
          Last check: ${new Date(s.last_check).toLocaleTimeString()}
        </div>
        ${s.error ? `<div style="font-size:0.75rem; color:#F87171; margin-top:6px;">${escapeHtml(s.error)}</div>` : ''}
      </div>
    `).join('');
  } catch (err) {
    grid.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</div>`;
  }
}

// --- 8. RECENT ACTIVITY ---
async function loadRecentActivity() {
  await loadRecentExecutions();
  const tbody = document.getElementById('activity-table-body');
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading audit trail...</td></tr>';

  try {
    const data = await apiRequest('/api/dashboard/activity?limit=30');

    tbody.innerHTML = data.items.map(a => `
      <tr>
        <td style="font-family:monospace; color:var(--text-muted);">${escapeHtml(a.id)}</td>
        <td><code>${escapeHtml(a.event_type)}</code></td>
        <td style="font-size:0.8rem;">${escapeHtml(a.workflow_name)}</td>
        <td><span class="badge badge-normal">${escapeHtml(a.channel || 'system')}</span></td>
        <td style="max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(a.description)}</td>
        <td>${a.latency_ms ? a.latency_ms + ' ms' : '-'}</td>
        <td style="font-size:0.75rem; color:var(--text-muted);">${a.created_at ? new Date(a.created_at).toLocaleTimeString() : 'N/A'}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadRecentExecutions() {
  const tbody = document.getElementById('execution-table-body');
  const panel = document.getElementById('execution-detail-panel');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading executions...</td></tr>';
  try {
    const status = document.getElementById('execution-status-filter')?.value || '';
    const query = new URLSearchParams({limit: '50'});
    if (status) query.set('status', status);
    const data = await apiRequest(`/api/dashboard/executions?${query.toString()}`);
    if (!data.items.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">${escapeHtml(I18N[STATE.currentLang].no_executions)}</td></tr>`;
      return;
    }
    tbody.innerHTML = data.items.map(item => `
      <tr>
        <td><code>${escapeHtml(item.request_id)}</code><br><small>${escapeHtml(item.execution_id)}</small></td>
        <td>${escapeHtml(item.workflow_name)}</td>
        <td>${escapeHtml(item.channel)}</td>
        <td>${escapeHtml(item.program || '—')}</td>
        <td><span class="badge badge-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
        <td>${formatMetric(item.latency_ms, ' ms')}</td>
        <td>${item.created_at ? escapeHtml(new Date(item.created_at).toLocaleString()) : 'N/A'}</td>
        <td><button class="btn-icon" data-request-id="${escapeHtml(item.request_id)}" onclick="openExecutionDetail(this.dataset.requestId)">${escapeHtml(I18N[STATE.currentLang].inspect)}</button>
          ${item.n8n_url ? `<a href="${escapeHtml(item.n8n_url)}" target="_blank" rel="noopener noreferrer">↗</a>` : ''}</td>
      </tr>`).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</td></tr>`;
  }
}

async function openExecutionDetail(requestId) {
  const panel = document.getElementById('execution-detail-panel');
  panel.style.display = 'block';
  panel.innerHTML = '<div>Loading request trace...</div>';
  try {
    const data = await apiRequest(`/api/dashboard/executions/${encodeURIComponent(requestId)}`);
    panel.innerHTML = `
      <h3>Request ${escapeHtml(data.request_id)} · ${escapeHtml(data.status)}</h3>
      <ol>${data.events.map(event => {
        const details = Object.entries(event.details || {}).map(([key, value]) =>
          `<span><strong>${escapeHtml(key)}:</strong> ${escapeHtml(Array.isArray(value) ? value.join(', ') : value)}</span>`
        ).join(' · ');
        const sources = (event.details?.source_urls || []).filter(url => /^https:\/\/(?:[a-z0-9-]+\.)*gov\.eg(?:\/|$)/i.test(url));
        return `<li><code>${escapeHtml(event.event_type)}</code> — ${escapeHtml(event.workflow_name)} — ${escapeHtml(event.latency_ms ?? 'N/A')} ms ${details}${sources.map(url => ` · <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Official source</a>`).join('')}</li>`;
      }).join('')}</ol>
      ${data.n8n_url ? `<a href="${escapeHtml(data.n8n_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(I18N[STATE.currentLang].open_trace)}</a>` : ''}
      <button class="btn-icon" onclick="document.getElementById('execution-detail-panel').style.display='none'">×</button>`;
  } catch (err) {
    panel.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</div>`;
  }
}

// --- 9. CONVERSATION DETAIL MODAL ---
async function openCustomerProfile(customerId, page = 1) {
  const modal = document.getElementById('conv-modal');
  const body = document.getElementById('modal-conv-body');
  modal.style.display = 'flex';
  body.innerHTML = '<div>Loading customer profile...</div>';
  try {
    const data = await apiRequest(`/api/dashboard/customers/${encodeURIComponent(customerId)}?page=${page}&limit=20`);
    const customer = data.customer;
    body.innerHTML = `
      <section style="background:var(--bg-subtle);padding:16px;border-radius:var(--radius-md);">
        <h4>${escapeHtml(customer.full_name || 'Customer')}</h4>
        <div style="color:var(--text-muted);">Phone: <code>${escapeHtml(customer.phone_masked || 'N/A')}</code> · Email: <code>${escapeHtml(customer.email_masked || 'N/A')}</code></div>
        <div style="margin-top:6px;">Program: ${escapeHtml(customer.program || 'UNKNOWN')} · Language: ${escapeHtml(customer.preferred_language || 'N/A')}</div>
      </section>
      <section><h4>Conversations (${data.total})</h4>
        ${data.conversations.length ? `<div style="display:flex;flex-direction:column;gap:8px;">${data.conversations.map(c => `
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;background:var(--bg-subtle);padding:12px;border-radius:var(--radius-sm);">
            <div><strong>${escapeHtml(c.channel)} · ${escapeHtml(c.status)}</strong><div style="font-size:.8rem;color:var(--text-muted);">${c.created_at ? new Date(c.created_at).toLocaleString() : 'Time unavailable'} · ${c.message_count} messages</div></div>
            <button class="btn-page" onclick="openConversationDetail('${c.id}')">Open</button>
          </div>`).join('')}</div>` : '<div class="empty-state">No conversations found.</div>'}
        <div style="display:flex;justify-content:space-between;margin-top:12px;">
          <button class="btn-page" ${page <= 1 ? 'disabled' : ''} onclick="openCustomerProfile('${customerId}',${page - 1})">Previous</button>
          <span>Page ${page} of ${Math.max(1, data.pages)}</span>
          <button class="btn-page" ${page >= data.pages ? 'disabled' : ''} onclick="openCustomerProfile('${customerId}',${page + 1})">Next</button>
        </div>
      </section>`;
  } catch (err) {
    body.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</div>`;
  }
}

async function openConversationDetail(convId, page = 1) {
  const modal = document.getElementById('conv-modal');
  const body = document.getElementById('modal-conv-body');
  modal.style.display = 'flex';
  body.innerHTML = '<div>Loading conversation session...</div>';

  try {
    const data = await apiRequest(`/api/dashboard/conversations/${encodeURIComponent(convId)}?page=${page}&limit=50`);

    body.innerHTML = `
      <!-- Customer Card -->
      <div style="background:var(--bg-subtle); padding:16px; border-radius:var(--radius-md); display:flex; justify-content:space-between; flex-wrap:wrap; gap:12px;">
        <div>
          <div style="font-weight:700; font-size:1.05rem;">${escapeHtml(data.customer.full_name)}</div>
          <div style="font-size:0.8rem; color:var(--text-muted);">Phone: <code>${escapeHtml(data.customer.phone_masked || 'N/A')}</code> | Email: <code>${escapeHtml(data.customer.email_masked || 'N/A')}</code></div>
        </div>
        <div style="display:flex; gap:8px;">
          <span class="badge ${data.customer.program === 'DEPI' ? 'badge-depi' : 'badge-digilians'}">${escapeHtml(data.customer.program)}</span>
          <span class="badge badge-normal">${escapeHtml(data.conversation.channel)}</span>
        </div>
      </div>

      <!-- Automated Summary -->
      <div>
        <h4 style="font-size:0.85rem; color:var(--text-muted); margin-bottom:6px;">Conversation Summary:</h4>
        <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); padding:12px; border-radius:var(--radius-sm); font-size:0.85rem;">
          ${escapeHtml(data.summary)}
        </div>
      </div>

      <!-- Turn by Turn Messages -->
      <div>
        <h4 style="font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;">Messages (${data.message_total}):</h4>
        <div style="display:flex; flex-direction:column; gap:10px; max-height:300px; overflow-y:auto; padding-right:8px;">
          ${data.messages.map(m => `
            <div style="padding:12px; border-radius:var(--radius-sm); background:${m.sender_type === 'customer' ? 'var(--bg-subtle)' : 'rgba(37,99,235,0.1)'}; border:1px solid ${m.sender_type === 'customer' ? 'var(--border-color)' : 'rgba(37,99,235,0.2)'};">
              <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">
                <span style="font-weight:700; text-transform:uppercase;">${m.sender_type === 'customer' ? 'Incoming customer' : m.sender_type === 'agent' ? 'Outgoing agent' : 'Outgoing assistant'} ${m.confidence ? `(Confidence: ${Math.round(m.confidence * 100)}%)` : ''} ${m.metadata?.delivery_status ? `· ${escapeHtml(m.metadata.delivery_status)}` : ''}</span>
                <span>${m.created_at ? new Date(m.created_at).toLocaleString() : 'Time unavailable'}</span>
              </div>
              <div style="font-size:0.85rem;white-space:pre-wrap;">${escapeHtml(m.content)}</div>
              ${m.metadata && m.metadata.rag_evidence ? `<div style="margin-top:6px; font-size:0.75rem; color:#60A5FA;"><strong>RAG Sources:</strong> ${escapeHtml(JSON.stringify(m.metadata.rag_evidence))}</div>` : ''}
            </div>
          `).join('')}
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:10px;"><button class="btn-page" ${page <= 1 ? 'disabled' : ''} onclick="openConversationDetail('${convId}',${page - 1})">Previous messages</button><span>Page ${page} of ${Math.max(1, data.message_pages)}</span><button class="btn-page" ${page >= data.message_pages ? 'disabled' : ''} onclick="openConversationDetail('${convId}',${page + 1})">Next messages</button></div>
      </div>

      <!-- Attached Tickets -->
      <div>
        <h4 style="font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;">Attached Tickets (${data.tickets.length}):</h4>
        ${data.tickets.length === 0 ? '<div style="font-size:0.8rem; color:var(--text-subtle);">No escalation tickets filed for this conversation.</div>' : `
          <div style="display:flex; flex-direction:column; gap:8px;">
            ${data.tickets.map(t => `
              <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-subtle); padding:10px; border-radius:var(--radius-sm);">
                <div>
                  <button class="btn-page" onclick="openTicketDetailsModal('${encodeURIComponent(t.ticket_number)}')">${escapeHtml(t.ticket_number)}</button> - <span style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(t.reason)}</span>
                </div>
                <div style="display:flex; gap:6px;">
                  <span class="badge badge-${escapeHtml(t.priority)}">${escapeHtml(t.priority)}</span>
                  <span class="badge badge-${escapeHtml(t.status)}">${escapeHtml(t.status)}</span>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</div>`;
  }
}

function closeConvModal() {
  document.getElementById('conv-modal').style.display = 'none';
}

// Pagination Component
function renderPagination(elementId, current, total, onSelect) {
  const container = document.getElementById(elementId);
  if (!container || total <= 1) {
    if (container) container.innerHTML = '';
    return;
  }

  container.innerHTML = `
    <span>Page ${current} of ${total}</span>
    <div class="page-controls">
      <button class="btn-page" ${current <= 1 ? 'disabled' : ''} onclick="(${onSelect.toString()})(${current - 1})">Previous</button>
      <button class="btn-page" ${current >= total ? 'disabled' : ''} onclick="(${onSelect.toString()})(${current + 1})">Next</button>
    </div>
  `;
}

// --- 9. N8N AUTOMATION VIEW ---
async function loadN8nData() {
  const kpiGrid = document.getElementById('n8n-kpi-grid');
  const wfTbody = document.getElementById('n8n-workflows-body');
  const execTbody = document.getElementById('n8n-executions-body');

  kpiGrid.innerHTML = '<div style="color:var(--text-muted);">Querying n8n REST API...</div>';
  wfTbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading workflows...</td></tr>';
  execTbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading executions...</td></tr>';

  try {
    const overview = await apiRequest('/api/dashboard/n8n/overview');

    kpiGrid.innerHTML = `
      <div class="kpi-card ${overview.connected ? 'success' : 'error'}">
        <span class="kpi-label">n8n Engine Link</span>
        <span class="kpi-value">${overview.connected ? 'ONLINE' : 'OFFLINE'}</span>
        <span class="kpi-sub">HTTP ${overview.api_code || 0} API Status</span>
      </div>
      <div class="kpi-card info">
        <span class="kpi-label">Total Workflows</span>
        <span class="kpi-value">${overview.total_workflows}</span>
        <span class="kpi-sub">Loaded in instance</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-label">Active Workflows</span>
        <span class="kpi-value">${overview.active_workflows}</span>
        <span class="kpi-sub">Ready for webhook ingress</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Webhook Health</span>
        <span class="kpi-value">${overview.health_status}</span>
        <span class="kpi-sub">Gateway responsive</span>
      </div>
    `;

    document.getElementById('n8n-wf-count').innerText = `${overview.total_workflows} Workflows`;

    const wfData = await apiRequest('/api/dashboard/n8n/workflows');
    if (wfData.items.length === 0) {
      wfTbody.innerHTML = '<tr><td colspan="7" class="empty-state">No workflows registered.</td></tr>';
    } else {
      wfTbody.innerHTML = wfData.items.map(wf => `
        <tr>
          <td><code>${escapeHtml(wf.id)}</code></td>
          <td style="font-weight:600;">${escapeHtml(wf.name)}</td>
          <td><span class="badge">${wf.nodes_count} nodes</span></td>
          <td>${(wf.tags && wf.tags.length) ? wf.tags.map(t => `<span class="badge" style="background:var(--bg-card-hover);">${escapeHtml(t)}</span>`).join(' ') : '<span style="color:var(--text-subtle);">None</span>'}</td>
          <td>${wf.updated_at ? new Date(wf.updated_at).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) : 'N/A'}</td>
          <td>
            <label class="switch">
              <input type="checkbox" ${wf.active ? 'checked' : ''} onchange="toggleWorkflow(${jsArg(wf.id)}, ${wf.active === true})">
              <span class="slider"></span>
            </label>
          </td>
          <td>
            <a href="${escapeHtml(wf.n8n_url)}" target="_blank" rel="noopener noreferrer" class="btn-icon" style="text-decoration:none; padding:4px 8px; font-size:0.8rem; background:var(--bg-subtle);" title="Open in n8n">
              ↗ Canvas
            </a>
          </td>
        </tr>
      `).join('');
    }

    const execData = await apiRequest('/api/dashboard/n8n/executions?limit=15');
    if (execData.items.length === 0) {
      execTbody.innerHTML = '<tr><td colspan="7" class="empty-state">No executions recorded yet.</td></tr>';
    } else {
      execTbody.innerHTML = execData.items.map(ex => {
        let stBadge = 'badge-normal';
        if (ex.status === 'success') stBadge = 'badge-resolved';
        else if (ex.status === 'error') stBadge = 'badge-open';
        else if (ex.status === 'running') stBadge = 'badge-pending';

        return `
          <tr>
            <td><strong>#${escapeHtml(ex.id)}</strong></td>
            <td><code>${escapeHtml(ex.workflow_id || 'N/A')}</code></td>
            <td><span class="badge">${escapeHtml(ex.mode)}</span></td>
            <td><span class="badge ${stBadge}">${escapeHtml(ex.status.toUpperCase())}</span></td>
            <td>${ex.started_at ? new Date(ex.started_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'}) : 'N/A'}</td>
            <td>${ex.duration_ms !== null ? ex.duration_ms + ' ms' : (ex.finished ? 'N/A' : 'Running...')}</td>
            <td>
              ${ex.n8n_url ? `<a href="${escapeHtml(ex.n8n_url)}" target="_blank" rel="noopener noreferrer" class="btn-icon" style="text-decoration:none; padding:4px 8px; font-size:0.75rem; background:var(--primary); color:#fff; border-radius:var(--radius-sm);">Inspect ↗</a>` : '-'}
            </td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    kpiGrid.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${escapeHtml(err.message)}</div>`;
  }
}

async function toggleWorkflow(workflowId, currentState) {
  const action = currentState ? 'deactivate' : 'activate';
  try {
    await apiRequest(`/api/dashboard/n8n/workflows/${encodeURIComponent(workflowId)}/${action}`, { method: 'POST' });
    loadN8nData();
  } catch (err) {
    alert(`Failed to ${action} workflow: ${err.message}`);
    loadN8nData();
  }
}

// --- 10. LIVE AI SIMULATOR VIEW ---
function loadSimulator() {
  setTimeout(() => {
    const input = document.getElementById('sim-chat-input');
    if (input) input.focus();
  }, 100);
}

function sendQuickPrompt(promptText) {
  const input = document.getElementById('sim-chat-input');
  if (input) {
    input.value = promptText;
    document.getElementById('sim-chat-form').dispatchEvent(new Event('submit'));
  }
}

function clearSimChat() {
  const container = document.getElementById('sim-messages-container');
  container.innerHTML = `
    <div class="chat-bubble bot">
      تم تفريغ المحادثة. يمكنك إرسال استفسار جديد لاختباره مع بوابة n8n.
      <div class="chat-meta"><span>NexaServe AI System</span></div>
    </div>
  `;
  document.getElementById('sim-trace-box').innerText = '// Awaiting new query...';
  document.getElementById('sim-trace-intent').innerText = '-';
  document.getElementById('sim-trace-confidence').innerText = '-';
  document.getElementById('sim-trace-program').innerText = '-';
  document.getElementById('sim-trace-latency').innerText = '-';
  document.getElementById('sim-telemetry-badge').innerText = 'Ready';
  document.getElementById('sim-telemetry-badge').style.background = 'var(--bg-subtle)';
}

async function handleSimSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('sim-chat-input');
  const sendBtn = document.getElementById('sim-send-btn');
  const msg = input.value.trim();
  if (!msg) return;

  const prog = document.getElementById('sim-program-select').value;
  const channel = document.getElementById('sim-channel-select').value;
  const container = document.getElementById('sim-messages-container');
  const traceBox = document.getElementById('sim-trace-box');
  const latencyBadge = document.getElementById('sim-latency-badge');
  const telemBadge = document.getElementById('sim-telemetry-badge');

  const userBubble = document.createElement('div');
  userBubble.className = 'chat-bubble user';
  userBubble.innerHTML = `${escapeHtml(msg)}<div class="chat-meta"><span>You (${channel})</span></div>`;
  container.appendChild(userBubble);
  container.scrollTop = container.scrollHeight;

  input.value = '';
  sendBtn.disabled = true;
  sendBtn.innerText = 'Invoking n8n... ⏳';
  latencyBadge.innerText = 'Routing through n8n...';
  telemBadge.innerText = 'EXECUTING';
  telemBadge.style.background = 'var(--accent-amber)';

  const typingBubble = document.createElement('div');
  typingBubble.className = 'chat-bubble bot';
  typingBubble.id = 'sim-typing-bubble';
  typingBubble.innerHTML = 'جاري المعالجة عبر بوابة n8n ونموذج الذكاء الاصطناعي... ⏳';
  container.appendChild(typingBubble);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await apiRequest('/api/dashboard/n8n/simulate', {
      method: 'POST',
      body: JSON.stringify({
        message: msg,
        program: prog,
        channel: channel,
        full_name: 'Simulator Admin Tester',
        phone_number: '+201000000000'
      })
    });

    typingBubble.remove();

    const n8nResp = res.response || {};
    let botReplyText = '';

    if (typeof n8nResp === 'string') {
      botReplyText = n8nResp;
    } else if (n8nResp.reply) {
      botReplyText = n8nResp.reply;
    } else if (n8nResp.message) {
      botReplyText = n8nResp.message;
    } else if (n8nResp.status === 'escalated') {
      botReplyText = `تم تصعيد طلبك بنجاح للموظف البشري. رقم التذكرة: ${n8nResp.ticket_number || 'N/A'}`;
    } else if (n8nResp.customer_message) {
      botReplyText = n8nResp.customer_message;
    } else {
      botReplyText = JSON.stringify(n8nResp, null, 2);
    }

    const botBubble = document.createElement('div');
    botBubble.className = 'chat-bubble bot';
    botBubble.innerHTML = `
      ${escapeHtml(botReplyText)}
      <div class="chat-meta">
        <span>Intent: ${n8nResp.intent || res.intent || 'RAG'}</span>
        <span>${res.latency_ms} ms</span>
        ${n8nResp.ticket_number ? `<span style="color:#F59E0B;">#${n8nResp.ticket_number}</span>` : ''}
      </div>
    `;
    container.appendChild(botBubble);
    container.scrollTop = container.scrollHeight;

    document.getElementById('sim-trace-intent').innerText = n8nResp.intent || 'general_support';
    document.getElementById('sim-trace-confidence').innerText = n8nResp.confidence ? (n8nResp.confidence * 100).toFixed(0) + '%' : (res.success ? '98%' : 'N/A');
    document.getElementById('sim-trace-program').innerText = prog;
    document.getElementById('sim-trace-latency').innerText = `${res.latency_ms} ms`;
    latencyBadge.innerText = `Turn finished in ${res.latency_ms} ms`;
    telemBadge.innerText = 'SUCCESS';
    telemBadge.style.background = 'var(--accent-emerald)';

    const traceLog = {
      http_status: res.status_code,
      execution_latency_ms: res.latency_ms,
      request_id: res.request_id || n8nResp.request_id,
      execution_id: res.execution_id || n8nResp.execution_id,
      n8n_raw_response: n8nResp,
      correlated_audit_trail: res.trace || []
    };
    traceBox.innerText = JSON.stringify(traceLog, null, 2);

  } catch (err) {
    typingBubble.remove();
    const errBubble = document.createElement('div');
    errBubble.className = 'chat-bubble bot';
    errBubble.style.borderColor = 'var(--accent-rose)';
    errBubble.innerHTML = `<span style="color:var(--accent-rose);">Error executing n8n gateway: ${escapeHtml(err.message)}</span>`;
    container.appendChild(errBubble);
    latencyBadge.innerText = 'Failed';
    telemBadge.innerText = 'ERROR';
    telemBadge.style.background = 'var(--accent-rose)';
    traceBox.innerText = `// Execution failed: ${err.message}`;
  } finally {
    sendBtn.disabled = false;
    sendBtn.innerText = 'Send Inquiry 🚀';
    input.focus();
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
  });
}

// --- 11. TICKET HITL RESOLUTION MODAL ---
function openTicketModal(ticketId, ticketNum, custName) {
  document.getElementById('modal-ticket-id').value = ticketId;
  document.getElementById('modal-ticket-info').innerText = `${ticketNum} - ${custName}`;
  document.getElementById('modal-ticket-message').value = '';
  document.getElementById('ticket-modal').style.display = 'flex';
}

function closeTicketModal() {
  document.getElementById('ticket-modal').style.display = 'none';
}

async function handleTicketRespondSubmit(e) {
  e.preventDefault();
  const ticketId = document.getElementById('modal-ticket-id').value;
  const action = document.getElementById('modal-ticket-action').value;
  const message = document.getElementById('modal-ticket-message').value.trim();
  const submitBtn = document.getElementById('modal-ticket-btn');

  if (!message) return;

  submitBtn.disabled = true;
  submitBtn.innerText = 'Dispatching to n8n & Customer... ⏳';

  try {
    const res = await apiRequest(`/api/dashboard/tickets/${ticketId}/respond`, {
      method: 'POST',
      body: JSON.stringify({
        response_message: message,
        action: action,
        agent_name: STATE.user ? (STATE.user.full_name || STATE.user.username) : 'Operations Agent'
      })
    });

    closeTicketModal();
    alert(`Ticket ${res.ticket_number} successfully updated! Dispatched to n8n (HTTP ${res.n8n_status_code || 200}).`);
    loadTickets();
  } catch (err) {
    alert(`Failed to resolve ticket: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerText = 'Dispatch Response to n8n & Customer 🚀';
  }
}

// --- 12. COMPREHENSIVE TICKET DETAILS MODAL ---
let currentTicketData = null;

async function openTicketDetailsModal(ticketId) {
  STATE.selectedTicketId = ticketId;
  const modal = document.getElementById('ticket-details-modal');
  if (!modal) return;
  modal.style.display = 'flex';

  // Show loading state
  document.getElementById('td-modal-number').innerText = 'Loading ticket...';
  document.getElementById('td-tab-timeline').innerHTML = '<div style="padding:12px; color:var(--text-muted);">Loading conversation timeline...</div>';
  document.getElementById('td-tab-events').innerHTML = '<div style="padding:12px; color:var(--text-muted);">Loading lifecycle events...</div>';

  try {
    const data = await apiRequest(`/api/dashboard/tickets/${ticketId}`);
    currentTicketData = data;

    // Header info
    document.getElementById('td-modal-number').innerText = data.ticket_number || 'TICK-N/A';
    
    const statusBadge = document.getElementById('td-modal-status-badge');
    statusBadge.className = `badge badge-${data.status}`;
    statusBadge.innerText = (data.status || 'open').toUpperCase();

    const priBadge = document.getElementById('td-modal-priority-badge');
    priBadge.className = `badge badge-${data.priority}`;
    priBadge.innerText = (data.priority || 'medium').toUpperCase();

    const catBadge = document.getElementById('td-modal-category-badge');
    catBadge.innerText = data.category || 'General';

    const chanBadge = document.getElementById('td-modal-channel-badge');
    chanBadge.innerText = data.channel || data.source_channel || 'WhatsApp';

    // Meta Grid
    document.getElementById('td-modal-customer').innerText = data.customer ? (data.customer.full_name || 'Citizen') : 'Customer';
    document.getElementById('td-modal-phone').innerText = data.customer ? (data.customer.phone_masked || data.customer.phone_number || 'N/A') : 'N/A';
    
    document.getElementById('td-modal-sla-status').innerText = data.sla_status || 'ON_TRACK';
    document.getElementById('td-modal-sla-time').innerText = data.sla_deadline ? new Date(data.sla_deadline).toLocaleString() : 'No SLA limit';

    document.getElementById('td-modal-team').innerText = data.assigned_team || 'DEPI Support Team';
    document.getElementById('td-modal-agent').innerText = data.assigned_agent || 'Unassigned';

    document.getElementById('td-modal-created').innerText = data.created_at ? new Date(data.created_at).toLocaleString() : 'N/A';
    document.getElementById('td-modal-updated').innerText = data.updated_at ? `Updated: ${new Date(data.updated_at).toLocaleTimeString()}` : '';

    // Title & Reason
    document.getElementById('td-modal-title').innerText = data.title || data.reason || 'Support Request';
    document.getElementById('td-modal-reason').innerText = data.reason || 'No specific description provided.';

    // Populate Tab 1: Timeline
    renderTicketTimeline(data.messages || [], data.reason);

    // Populate Tab 2: Events
    renderTicketEvents(data.timeline || []);

    // Populate Tab 3: Notes
    renderTicketNotes(data.internal_notes);

    // Populate Tab 4: Actions Form
    const selStatus = document.getElementById('td-action-status');
    if (selStatus) selStatus.value = data.status || 'open';
    const selPriority = document.getElementById('td-action-priority');
    if (selPriority) selPriority.value = data.priority || 'medium';
    const txtAgent = document.getElementById('td-action-agent');
    if (txtAgent) txtAgent.value = data.assigned_agent || (STATE.user ? (STATE.user.full_name || STATE.user.username) : '');

    switchTicketTab('timeline');
  } catch (err) {
    alert(`Failed to load ticket details: ${err.message}`);
    closeTicketDetailsModal();
  }
}

function closeTicketDetailsModal() {
  const modal = document.getElementById('ticket-details-modal');
  if (modal) modal.style.display = 'none';
  STATE.selectedTicketId = null;
  currentTicketData = null;
}

function switchTicketTab(tabName) {
  const tabs = ['timeline', 'events', 'notes', 'actions'];
  tabs.forEach(t => {
    const pane = document.getElementById(`td-tab-${t}`);
    const btn = document.getElementById(`tab-btn-${t}`);
    if (pane) pane.style.display = (t === tabName) ? (t === 'timeline' || t === 'events' ? 'flex' : 'flex') : 'none';
    if (btn) {
      if (t === tabName) {
        btn.style.background = 'var(--primary)';
        btn.style.color = '#fff';
      } else {
        btn.style.background = 'transparent';
        btn.style.color = 'var(--text-muted)';
      }
    }
  });
}

function renderTicketTimeline(messages, initialReason) {
  const container = document.getElementById('td-tab-timeline');
  if (!container) return;

  if ((!messages || messages.length === 0) && !initialReason) {
    container.innerHTML = '<div style="padding:16px; color:var(--text-muted); text-align:center;">No conversation messages correlated.</div>';
    return;
  }

  let html = '';
  if (initialReason && (!messages || messages.length === 0)) {
    html += `
      <div class="chat-bubble user" style="max-width:85%; background:rgba(59,130,246,0.15); border:1px solid rgba(59,130,246,0.3); padding:10px 14px; border-radius:12px; margin-bottom:8px;">
        <div style="font-size:0.75rem; color:#60A5FA; margin-bottom:4px; font-weight:600;">Customer Ingress Message</div>
        <div style="font-size:0.9rem; line-height:1.4;">${escapeHtml(initialReason)}</div>
      </div>
    `;
  }

  (messages || []).forEach(m => {
    const isBot = m.sender === 'bot' || m.sender === 'system';
    const isAgent = m.sender === 'agent' || m.sender === 'human';
    let bubbleClass = 'user';
    let borderStyle = 'background:rgba(59,130,246,0.15); border:1px solid rgba(59,130,246,0.3);';
    let senderLabel = m.sender || 'Customer';

    if (isBot) {
      bubbleClass = 'bot';
      borderStyle = 'background:rgba(255,255,255,0.05); border:1px solid var(--border-color); align-self:flex-start;';
      senderLabel = '🤖 NexaServe AI Bot';
    } else if (isAgent) {
      bubbleClass = 'agent';
      borderStyle = 'background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.4); align-self:flex-start;';
      senderLabel = `👨‍💼 Agent (${m.sender_name || 'Support'})`;
    } else {
      borderStyle = 'background:rgba(59,130,246,0.15); border:1px solid rgba(59,130,246,0.3); align-self:flex-end;';
    }

    const timeStr = m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '';

    html += `
      <div style="max-width:85%; ${borderStyle} padding:10px 14px; border-radius:12px; margin-bottom:8px;">
        <div style="display:flex; justify-content:space-between; gap:12px; font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">
          <strong>${escapeHtml(senderLabel)}</strong>
          <span>${timeStr}</span>
        </div>
        <div style="font-size:0.88rem; line-height:1.45; white-space:pre-wrap;">${escapeHtml(m.message || m.content || '')}</div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderTicketEvents(events) {
  const container = document.getElementById('td-tab-events');
  if (!container) return;

  if (!events || events.length === 0) {
    container.innerHTML = '<div style="padding:16px; color:var(--text-muted); text-align:center;">No lifecycle events logged yet.</div>';
    return;
  }

  container.innerHTML = events.map(e => {
    let icon = '📜';
    if (e.event_type === 'created') icon = '🆕';
    else if (e.event_type === 'status_change') icon = '🔄';
    else if (e.event_type === 'assignment') icon = '👤';
    else if (e.event_type === 'internal_note') icon = '📝';
    else if (e.event_type === 'agent_reply') icon = '💬';
    else if (e.event_type === 'customer_followup') icon = '📥';

    const actor = e.actor_name ? `${e.actor_name} (${e.actor_type})` : (e.actor_type || 'System');
    const timeStr = e.created_at ? new Date(e.created_at).toLocaleString() : '';
    const detailsStr = e.details ? (typeof e.details === 'object' ? JSON.stringify(e.details) : e.details) : '';

    return `
      <div style="display:flex; gap:10px; align-items:flex-start; background:rgba(255,255,255,0.02); padding:8px 12px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
        <span style="font-size:1.1rem;">${icon}</span>
        <div style="flex:1;">
          <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted);">
            <strong style="color:var(--text-main); text-transform:uppercase;">${escapeHtml((e.event_type || '').replace(/_/g, ' '))}</strong>
            <span>${timeStr}</span>
          </div>
          <div style="font-size:0.8rem; color:var(--text-subtle); margin-top:2px;">by ${escapeHtml(actor)}</div>
          ${detailsStr ? `<div style="font-size:0.8rem; color:var(--text-muted); margin-top:4px; font-family:monospace; background:rgba(0,0,0,0.2); padding:4px 8px; border-radius:4px;">${escapeHtml(detailsStr)}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function renderTicketNotes(notes) {
  const box = document.getElementById('td-notes-list');
  if (!box) return;
  if (!notes || !notes.trim()) {
    box.innerText = 'No internal notes recorded.';
  } else {
    box.innerText = notes;
  }
}

async function submitTicketInternalNote() {
  const input = document.getElementById('td-new-note');
  if (!input) return;
  const note = input.value.trim();
  if (!note || !STATE.selectedTicketId) return;

  const agentName = STATE.user ? (STATE.user.full_name || STATE.user.username) : 'Operations Agent';

  try {
    await apiRequest(`/api/dashboard/tickets/${STATE.selectedTicketId}/notes`, {
      method: 'POST',
      body: JSON.stringify({
        note: note,
        agent_name: agentName
      })
    });

    input.value = '';
    // Reload ticket details
    await openTicketDetailsModal(STATE.selectedTicketId);
    switchTicketTab('notes');
  } catch (err) {
    alert(`Failed to add note: ${err.message}`);
  }
}

async function submitTicketUpdateAction() {
  if (!STATE.selectedTicketId) return;

  const status = document.getElementById('td-action-status').value;
  const priority = document.getElementById('td-action-priority').value;
  const agent = document.getElementById('td-action-agent').value.trim();

  try {
    await apiRequest(`/api/dashboard/tickets/${STATE.selectedTicketId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        status: status,
        priority: priority,
        assigned_agent: agent
      })
    });

    alert('Ticket updated successfully!');
    await openTicketDetailsModal(STATE.selectedTicketId);
    loadTickets();
  } catch (err) {
    alert(`Failed to update ticket: ${err.message}`);
  }
}

async function submitTicketReplyAction(action) {
  if (!STATE.selectedTicketId) return;
  const msgInput = document.getElementById('td-action-reply-msg');
  const msg = msgInput.value.trim();
  if (!msg) {
    alert('Please enter a response message to dispatch to the customer.');
    return;
  }

  const agentName = STATE.user ? (STATE.user.full_name || STATE.user.username) : 'Operations Agent';

  try {
    const res = await apiRequest(`/api/dashboard/tickets/${STATE.selectedTicketId}/respond`, {
      method: 'POST',
      body: JSON.stringify({
        response_message: msg,
        action: action,
        agent_name: agentName
      })
    });

    msgInput.value = '';
    alert(`Reply dispatched successfully via n8n (Ticket ${res.ticket_number})!`);
    await openTicketDetailsModal(STATE.selectedTicketId);
    loadTickets();
  } catch (err) {
    alert(`Failed to dispatch reply: ${err.message}`);
  }
}

