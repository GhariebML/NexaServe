/* === IMPROVED DEPI-SPECIALIZED DETERMINISTIC ENTITY RESOLVER & ARABIC NORMALIZER === */
const input = $input.first()?.json || {};
const rawMsg = input.customer_message || input.sanitized_message || '';

// Conservative Arabic Normalization
let normalized = rawMsg
  .replace(/[ً-ٰٟ]/g, '') // Tashkeel
  .replace(/ـ/g, '')               // Tatweel
  .replace(/[إأآٱ]/g, 'ا')              // Alef variants
  .replace(/ى/g, 'ي')                   // Alef Maqsura
  .replace(/\s+/g, ' ')
  .trim();

const msgLower = normalized.toLowerCase();
const isAr = /[؀-ۿ]/.test(rawMsg);
const locale = input.locale || (isAr ? 'ar' : 'en');
const history = input.conversation_history || [];

// Check conversation history for prior DEPI context
let programResolvedFromHistory = false;
for (const h of history) {
  const c = (h.content || '').toLowerCase();
  if (c.includes('depi') || c.includes('debi') || c.includes('رواد مصر') || c.includes('بناة مصر')) {
    programResolvedFromHistory = true;
    break;
  }
}

// Digilians entity detection (Out-of-scope)
const digiliansEntities = [
  'الرواد الرقميون', 'رواد رقميون', 'مبادرة الرواد الرقميون', 'برنامج الرواد الرقميون',
  'digital pioneers initiative', 'digilians'
];
const isDigiliansQuery = digiliansEntities.some(ent => msgLower.includes(ent));

// Comparison phrases
const comparisonPhrases = [
  'الفرق بين', 'مقارنة بين', 'مقارنه بين', 'ايه الفرق', 'ما الفرق',
  'difference between', 'compare', 'comparison', 'versus', 'vs'
];
const isComparisonQuery = comparisonPhrases.some(phrase => msgLower.includes(phrase));

// Explicit DEBI entities (Digital Egypt Builders Initiative)
const debiSpecificEntities = [
  'بناة مصر الرقمية', 'مبادرة بناة مصر', 'منحة بناة مصر', 'منحة بناة مصر الرقمية',
  'digital egypt builders initiative', 'debi', 'ماجستير بناة مصر'
];
const hasExplicitDebi = debiSpecificEntities.some(ent => msgLower.includes(ent)) ||
  ((msgLower.includes('ماجستير') || msgLower.includes('master')) && !msgLower.includes('depi') && !msgLower.includes('رواد مصر'));

// Explicit DEPI entities (Digital Egypt Pioneers Initiative)
const depiSpecificEntities = [
  'رواد مصر الرقمية', 'مبادرة رواد مصر', 'منحة رواد مصر', 'منحة رواد مصر الرقمية',
  'digital egypt pioneers initiative', 'depi'
];
const hasExplicitDepi = depiSpecificEntities.some(ent => msgLower.includes(ent));

let programScope = 'DEPI';
let isAmbiguous = false;
let isOutOfScope = false;

// Improved Scope Detection: Explicitly detect out-of-scope based on exclusive entities
if (hasExplicitDebi && !hasExplicitDepi) {
  programScope = 'DEBI';
  isOutOfScope = true;
} else if (isDigiliansQuery && !hasExplicitDepi) {
  programScope = 'DIGILIANS';
  isOutOfScope = true;
} else if (isComparisonQuery) {
  programScope = 'COMPARISON';
  isOutOfScope = true;
} else {
  programScope = 'DEPI';
}

// Topic routing: More robust matching
let topicCategory = '';
const conditionsKeywords = ['شروط', 'شرط', 'اهلية', 'أهلية', 'التقديم', 'قبول', 'التقدير', 'معدل', 'السن', 'عمر', 'المؤهلة', 'مؤهلة', 'المطلوب', 'مطلوب', 'مستوى', 'gpa', 'grade', 'age', 'required', 'requirements', 'requirement', 'eligibility', 'eligible', 'apply', 'admission', 'who can', 'من يستطيع', 'لغير خريجي'];
const benefitsKeywords = ['منحة', 'المنحة', 'منح', 'المنح', 'benefit', 'benefits', 'grant', 'grants'];
const tracksKeywords = ['مسار', 'مسارات', 'تخصص', 'تخصصات', 'specialization', 'specializations', 'tracks', 'track', 'data'];
const trainingKeywords = ['أونلاين', 'اونلاين', 'عن بعد', 'online', 'remote', 'تدريب'];
const overviewKeywords = ['تفاصيل', 'معلومات', 'نبذة', 'نبذه', 'عن المبادرة', 'عن مبادرة', 'ايه هي', 'ما هي', 'ماذا عن', 'فكرة', 'اهداف', 'أهداف', 'overview', 'about', 'details', 'info', 'مبادرة', 'المبادرة'];

const matches = (keywords) => keywords.some(kw => msgLower.includes(kw));

if (matches(conditionsKeywords)) topicCategory = (programScope === 'DIGILIANS' ? 'depi_conditions' : 'debi_conditions');
else if (matches(benefitsKeywords)) topicCategory = 'debi_benefits';
else if (matches(tracksKeywords)) topicCategory = 'debi_tracks';
else if (matches(trainingKeywords)) topicCategory = 'debi_training';
else if (matches(overviewKeywords)) topicCategory = 'debi_overview';

// Overrides
if (msgLower.includes('من المؤهل') || msgLower.includes('who is eligible')) topicCategory = 'depi_conditions';

// Improved retrieval filter
const isGeneralSupportQuery = /safe exam browser|\bseb\b|technical support|troubleshoot|browser|install|login|log in|المتصفح|الدعم الفني|مشكلة فنية|تسجيل الدخول/i.test(msgLower);

// Strict scoping for DEPI-authoritative only
const programFilter = isOutOfScope
  ? "FALSE"
  : isGeneralSupportQuery
    ? "program = 'COMMON' AND retrieval_scope = 'GENERAL_SUPPORT'"
    : "program = 'DEPI' AND retrieval_scope = 'DEPI_AUTHORITATIVE' AND category NOT IN ('disambiguation', 'comparison')";

let outOfScopeReply = '';
if (programScope === 'DEBI') {
  outOfScopeReply = locale === 'ar'
    ? 'عذراً، يختص هذا المساعد حصرياً بالمعلومات والخدمات الرسمية لمبادرة رواد مصر الرقمية (DEPI)، ولا يقدم معلومات حول منحة بناة مصر الرقمية (DEBI) لدرجة الماجستير.'
    : 'Sorry, this assistant is specialized exclusively in the Digital Egypt Pioneers Initiative (DEPI) and does not cover the Digital Egypt Builders Initiative (DEBI) Master\'s scholarship.';
} else {
  outOfScopeReply = locale === 'ar'
    ? 'عذراً، يختص هذا المساعد حصرياً بمبادرة رواد مصر الرقمية (DEPI) فقط، ولا يقدم معلومات حول مبادرات أخرى. للاستفسار عن DEPI يسعدنا مساعدتك.'
    : 'Sorry, this assistant is specialized exclusively in the Digital Egypt Pioneers Initiative (DEPI) and does not provide information about other initiatives.';
}

return [{
  json: {
    ...input,
    customer_message: rawMsg,
    normalized_message: normalized,
    locale: locale,
    program_scope: programScope,
    program_filter: programFilter,
    topic_category: topicCategory,
    retrieval_started_ms: Date.now(),
    is_ambiguous: isAmbiguous,
    is_out_of_scope: isOutOfScope,
    out_of_scope_reply: outOfScopeReply,
    program_resolved_from_history: programResolvedFromHistory
  }
}];