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
  program: 'all',
  charts: {},
  customerSearchTimeout: null,
  customerPage: 1,
  convPage: 1,
  ticketPage: 1
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
    nav_executive: "Executive KPIs",
    nav_customers: "Customers & Students",
    nav_conversations: "Conversations",
    nav_tickets: "Tickets & HITL",
    nav_rag: "RAG & AI Quality",
    nav_kb: "Knowledge Base",
    nav_health: "System Health",
    nav_activity: "Recent Activity",
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
    btn_view_details: "View Details"
  },
  ar: {
    ops_center: "مركز العمليات والتحكم",
    login_sub: "منصة الدعم الفني الموحدة لوزارة الاتصالات",
    lbl_username: "اسم المستخدم",
    lbl_password: "كلمة المرور",
    btn_login: "تسجيل الدخول للنظام",
    btn_logout: "خروج",
    nav_executive: "المؤشرات التنفيذية",
    nav_customers: "العملاء والطلاب",
    nav_conversations: "المحادثات المباشرة",
    nav_tickets: "التذاكر والدعم البشري",
    nav_rag: "جودة الذكاء الاصطناعي و RAG",
    nav_kb: "قاعدة المعرفة والوثائق",
    nav_health: "سلامة وخوادم النظام",
    nav_activity: "سجل العمليات الأخير",
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
    btn_view_details: "عرض التفاصيل"
  }
};

// API Fetch Helper with Bearer Token
async function apiRequest(endpoint, options = {}) {
  const headers = options.headers || {};
  if (STATE.token) {
    headers['Authorization'] = `Bearer ${STATE.token}`;
  }
  options.headers = headers;

  const res = await fetch(endpoint, options);
  if (res.status === 401) {
    logout();
    throw new Error('Session expired or unauthorized');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${res.status}`);
  }
  return await res.json();
}

// Initial Boot
document.addEventListener('DOMContentLoaded', () => {
  applyLanguage(STATE.currentLang);
  setupAuthForm();

  if (STATE.token && STATE.user) {
    showAppShell();
  } else {
    showLoginModal();
  }
});

function applyLanguage(lang) {
  STATE.currentLang = lang;
  localStorage.setItem('nexaserve_lang', lang);
  document.documentElement.lang = lang;
  document.documentElement.dir = (lang === 'ar') ? 'rtl' : 'ltr';

  document.getElementById('lang-label').innerText = (lang === 'ar') ? 'EN' : 'عربي';

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (I18N[lang] && I18N[lang][key]) {
      el.innerText = I18N[lang][key];
    }
  });
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
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');

      STATE.token = data.access_token;
      STATE.user = data.user;
      localStorage.setItem('nexaserve_jwt_token', data.access_token);
      localStorage.setItem('nexaserve_user', JSON.stringify(data.user));

      showAppShell();
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

function logout() {
  STATE.token = null;
  STATE.user = null;
  localStorage.removeItem('nexaserve_jwt_token');
  localStorage.removeItem('nexaserve_user');
  showLoginModal();
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

  refreshCurrentView();
}

function refreshCurrentView() {
  STATE.period = document.getElementById('global-date-filter').value;
  STATE.program = document.getElementById('global-program-filter').value;

  switch (STATE.currentView) {
    case 'executive': loadExecutiveKPIs(); break;
    case 'customers': loadCustomers(); break;
    case 'conversations': loadConversations(); break;
    case 'tickets': loadTickets(); break;
    case 'rag': loadRAGMetrics(); break;
    case 'kb': loadKBMetrics(); break;
    case 'health': loadSystemHealth(); break;
    case 'activity': loadRecentActivity(); break;
  }
}

// --- 1. EXECUTIVE KPIS ---
async function loadExecutiveKPIs() {
  const container = document.getElementById('executive-kpi-grid');
  container.innerHTML = '<div style="color:var(--text-muted);">Querying live database...</div>';

  try {
    const data = await apiRequest(`/api/dashboard/summary?period=${STATE.period}&program=${STATE.program}`);
    
    container.innerHTML = `
      <div class="kpi-card">
        <span class="kpi-label">Total Customers</span>
        <span class="kpi-value">${data.total_customers.toLocaleString()}</span>
        <span class="kpi-sub">Registered across channels</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-label">Active Conversations</span>
        <span class="kpi-value">${data.active_conversations.toLocaleString()}</span>
        <span class="kpi-sub">Currently in session</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Total Conversations</span>
        <span class="kpi-value">${data.total_conversations.toLocaleString()}</span>
        <span class="kpi-sub">All-time volume</span>
      </div>
      <div class="kpi-card warning">
        <span class="kpi-label">Open Tickets</span>
        <span class="kpi-value">${data.open_tickets.toLocaleString()}</span>
        <span class="kpi-sub">Awaiting resolution</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Pending Tickets</span>
        <span class="kpi-value">${data.pending_tickets.toLocaleString()}</span>
        <span class="kpi-sub">In progress by agent</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-label">Resolved Tickets</span>
        <span class="kpi-value">${data.resolved_tickets.toLocaleString()}</span>
        <span class="kpi-sub">Successfully closed</span>
      </div>
      <div class="kpi-card alert">
        <span class="kpi-label">SLA Breaches</span>
        <span class="kpi-value" style="color:#F87171;">${data.sla_breaches.toLocaleString()}</span>
        <span class="kpi-sub">Action required immediately</span>
      </div>
      <div class="kpi-card warning">
        <span class="kpi-label">Escalated Convs</span>
        <span class="kpi-value">${data.escalated_conversations.toLocaleString()}</span>
        <span class="kpi-sub">Routed to human tier</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Avg Response Time</span>
        <span class="kpi-value">${data.avg_response_time_ms.toLocaleString()} ms</span>
        <span class="kpi-sub">End-to-end audit latency</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-label">RAG Success Rate</span>
        <span class="kpi-value" style="color:#34D399;">${data.rag_success_rate}%</span>
        <span class="kpi-sub">Strict grounded responses</span>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">Failed to load KPIs: ${err.message}</div>`;
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
        <td style="font-weight:600;">${c.full_name}</td>
        <td><code>${c.phone_masked || 'N/A'}</code></td>
        <td><span class="badge ${c.program === 'DEPI' ? 'badge-depi' : 'badge-digilians'}">${c.program}</span></td>
        <td>${c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}</td>
        <td>${c.last_interaction ? new Date(c.last_interaction).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'N/A'}</td>
        <td>${c.conversation_count}</td>
        <td>${c.open_tickets > 0 ? `<span style="color:#F87171; font-weight:700;">${c.open_tickets}</span>` : '0'}</td>
        <td><span class="badge ${c.customer_status === 'Active' ? 'badge-resolved' : 'badge-pending'}">${c.customer_status}</span></td>
      </tr>
    `).join('');

    renderPagination('customers-pagination', data.page, data.pages, (p) => {
      STATE.customerPage = p;
      loadCustomers();
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty-state" style="color:var(--accent-rose);">${err.message}</td></tr>`;
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
        <td style="font-weight:600;">${c.customer_name}</td>
        <td><span class="badge ${c.program === 'DEPI' ? 'badge-depi' : 'badge-digilians'}">${c.program}</span></td>
        <td><span class="badge badge-normal">${c.channel}</span></td>
        <td><code>${c.intent}</code></td>
        <td>${Math.round(c.avg_confidence * 100)}%</td>
        <td><span class="badge ${c.status === 'active' ? 'badge-resolved' : 'badge-pending'}">${c.status}</span></td>
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
    tbody.innerHTML = `<tr><td colspan="9" class="empty-state" style="color:var(--accent-rose);">${err.message}</td></tr>`;
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

// --- 4. TICKETS ---
async function loadTickets() {
  const tbody = document.getElementById('tickets-table-body');
  const status = document.getElementById('ticket-status-filter').value;
  const priority = document.getElementById('ticket-priority-filter').value;
  tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">Loading tickets...</td></tr>';

  try {
    const data = await apiRequest(`/api/dashboard/tickets?status=${status}&priority=${priority}&program=${STATE.program}&page=${STATE.ticketPage}&limit=10`);

    if (data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No tickets matching selected filters.</td></tr>';
      return;
    }

    tbody.innerHTML = data.items.map(t => {
      let slaClass = 'badge-normal';
      if (t.sla_status === 'BREACHED') slaClass = 'badge-open';
      else if (t.sla_status === 'AT_RISK') slaClass = 'badge-pending';

      return `
        <tr>
          <td><strong style="color:#60A5FA;">${t.ticket_number}</strong></td>
          <td style="font-weight:600;">${t.customer_name}</td>
          <td><span class="badge ${t.program === 'DEPI' ? 'badge-depi' : 'badge-digilians'}">${t.program}</span></td>
          <td><span class="badge badge-${t.priority}">${t.priority}</span></td>
          <td><span class="badge badge-${t.status}">${t.status}</span></td>
          <td>${t.assigned_agent}</td>
          <td>${t.sla_deadline ? new Date(t.sla_deadline).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) : 'None'}</td>
          <td><span class="badge ${slaClass}">${t.sla_status}</span></td>
          <td>${t.created_at ? new Date(t.created_at).toLocaleDateString() : 'N/A'}</td>
        </tr>
      `;
    }).join('');

    renderPagination('tickets-pagination', data.page, data.pages, (p) => {
      STATE.ticketPage = p;
      loadTickets();
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty-state" style="color:var(--accent-rose);">${err.message}</td></tr>`;
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
      <div class="kpi-card"><span class="kpi-label">Vector Retrieval</span><span class="kpi-value">${data.average_retrieval_latency_ms} ms</span></div>
      <div class="kpi-card"><span class="kpi-label">Avg LLM Latency</span><span class="kpi-value">${data.average_llm_latency_ms} ms</span></div>
      <div class="kpi-card"><span class="kpi-label">Latency p50 / p95</span><span class="kpi-value" style="font-size:1.4rem;">${data.p50_latency_ms} / ${data.p95_latency_ms} ms</span></div>
      <div class="kpi-card success"><span class="kpi-label">Cache Hit Rate</span><span class="kpi-value">${data.cache_hit_rate}%</span></div>
      <div class="kpi-card"><span class="kpi-label">Fallbacks / Errors</span><span class="kpi-value">${data.fallback_count} / ${data.error_count}</span></div>
    `;

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
    kpiGrid.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${err.message}</div>`;
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
        <span style="font-weight:600;">${p.program}</span>
        <span class="badge badge-normal">${p.count} docs</span>
      </div>
    `).join('');

    const srcBox = document.getElementById('kb-source-list');
    srcBox.innerHTML = data.documents_by_source.map(s => `
      <div style="display:flex; justify-content:space-between; padding: 8px 12px; background:var(--bg-subtle); border-radius:var(--radius-sm);">
        <span style="font-size:0.85rem; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${s.source}</span>
        <span class="badge badge-normal">${s.count} docs</span>
      </div>
    `).join('');
  } catch (err) {
    kpiGrid.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${err.message}</div>`;
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
          <span style="font-weight:700; font-size:0.95rem;">${s.name}</span>
          <div style="display:flex; align-items:center; gap:6px;">
            <span class="status-dot ${s.status.toLowerCase()}"></span>
            <span style="font-size:0.75rem; font-weight:700;">${s.status}</span>
          </div>
        </div>
        <div style="font-size:0.8rem; color:var(--text-muted); display:flex; justify-content:space-between; margin-top:8px;">
          <span>Latency:</span>
          <strong>${s.latency_ms !== null ? s.latency_ms + ' ms' : 'N/A'}</strong>
        </div>
        <div style="font-size:0.7rem; color:var(--text-subtle);">
          Last check: ${new Date(s.last_check).toLocaleTimeString()}
        </div>
        ${s.error ? `<div style="font-size:0.75rem; color:#F87171; margin-top:6px;">${s.error}</div>` : ''}
      </div>
    `).join('');
  } catch (err) {
    grid.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${err.message}</div>`;
  }
}

// --- 8. RECENT ACTIVITY ---
async function loadRecentActivity() {
  const tbody = document.getElementById('activity-table-body');
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading audit trail...</td></tr>';

  try {
    const data = await apiRequest('/api/dashboard/activity?limit=30');

    tbody.innerHTML = data.items.map(a => `
      <tr>
        <td style="font-family:monospace; color:var(--text-muted);">${a.id}</td>
        <td><code>${a.event_type}</code></td>
        <td style="font-size:0.8rem;">${a.workflow_name}</td>
        <td><span class="badge badge-normal">${a.channel || 'system'}</span></td>
        <td style="max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${a.description}</td>
        <td>${a.latency_ms ? a.latency_ms + ' ms' : '-'}</td>
        <td style="font-size:0.75rem; color:var(--text-muted);">${a.created_at ? new Date(a.created_at).toLocaleTimeString() : 'N/A'}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state" style="color:var(--accent-rose);">${err.message}</td></tr>`;
  }
}

// --- 9. CONVERSATION DETAIL MODAL ---
async function openConversationDetail(convId) {
  const modal = document.getElementById('conv-modal');
  const body = document.getElementById('modal-conv-body');
  modal.style.display = 'flex';
  body.innerHTML = '<div>Loading conversation session...</div>';

  try {
    const data = await apiRequest(`/api/dashboard/conversations/${convId}`);

    body.innerHTML = `
      <!-- Customer Card -->
      <div style="background:var(--bg-subtle); padding:16px; border-radius:var(--radius-md); display:flex; justify-content:space-between; flex-wrap:wrap; gap:12px;">
        <div>
          <div style="font-weight:700; font-size:1.05rem;">${data.customer.full_name}</div>
          <div style="font-size:0.8rem; color:var(--text-muted);">Phone: <code>${data.customer.phone_masked || 'N/A'}</code> | Email: <code>${data.customer.email_masked || 'N/A'}</code></div>
        </div>
        <div style="display:flex; gap:8px;">
          <span class="badge ${data.customer.program === 'DEPI' ? 'badge-depi' : 'badge-digilians'}">${data.customer.program}</span>
          <span class="badge badge-normal">${data.conversation.channel}</span>
        </div>
      </div>

      <!-- Automated Summary -->
      <div>
        <h4 style="font-size:0.85rem; color:var(--text-muted); margin-bottom:6px;">Conversation Summary:</h4>
        <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); padding:12px; border-radius:var(--radius-sm); font-size:0.85rem;">
          ${data.summary}
        </div>
      </div>

      <!-- Turn by Turn Messages -->
      <div>
        <h4 style="font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;">Messages (${data.messages.length}):</h4>
        <div style="display:flex; flex-direction:column; gap:10px; max-height:300px; overflow-y:auto; padding-right:8px;">
          ${data.messages.map(m => `
            <div style="padding:12px; border-radius:var(--radius-sm); background:${m.sender_type === 'customer' ? 'var(--bg-subtle)' : 'rgba(37,99,235,0.1)'}; border:1px solid ${m.sender_type === 'customer' ? 'var(--border-color)' : 'rgba(37,99,235,0.2)'};">
              <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">
                <span style="font-weight:700; text-transform:uppercase;">${m.sender_type} ${m.confidence ? `(Confidence: ${Math.round(m.confidence * 100)}%)` : ''}</span>
                <span>${new Date(m.created_at).toLocaleTimeString()}</span>
              </div>
              <div style="font-size:0.85rem;">${m.content}</div>
              ${m.metadata && m.metadata.rag_evidence ? `<div style="margin-top:6px; font-size:0.75rem; color:#60A5FA;"><strong>RAG Sources:</strong> ${JSON.stringify(m.metadata.rag_evidence)}</div>` : ''}
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Attached Tickets -->
      <div>
        <h4 style="font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;">Attached Tickets (${data.tickets.length}):</h4>
        ${data.tickets.length === 0 ? '<div style="font-size:0.8rem; color:var(--text-subtle);">No escalation tickets filed for this conversation.</div>' : `
          <div style="display:flex; flex-direction:column; gap:8px;">
            ${data.tickets.map(t => `
              <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-subtle); padding:10px; border-radius:var(--radius-sm);">
                <div>
                  <strong>${t.ticket_number}</strong> - <span style="font-size:0.8rem; color:var(--text-muted);">${t.reason}</span>
                </div>
                <div style="display:flex; gap:6px;">
                  <span class="badge badge-${t.priority}">${t.priority}</span>
                  <span class="badge badge-${t.status}">${t.status}</span>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${err.message}</div>`;
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
