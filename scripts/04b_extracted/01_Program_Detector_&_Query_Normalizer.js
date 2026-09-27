/* === MULTI-TIER DETERMINISTIC ENTITY RESOLVER & ARABIC NORMALIZER === */
const input = $input.first()?.json || {};
const rawMsg = input.customer_message || input.sanitized_message || '';

// Conservative Arabic Normalization (NFKC, strip diacritics/tatweel, normalize Alef, keep Taa Marbuta)
let normalized = rawMsg
  .replace(/[\u064B-\u065F\u0670]/g, '') // Tashkeel
  .replace(/\u0640/g, '')               // Tatweel
  .replace(/[إأآٱ]/g, 'ا')              // Alef variants
  .replace(/ى/g, 'ي')                   // Alef Maqsura
  .replace(/\s+/g, ' ')
  .trim();

const msgLower = normalized.toLowerCase();
const isAr = /[\u0600-\u06FF]/.test(rawMsg);
const locale = input.locale || (isAr ? 'ar' : 'en');

// TIER 1: Explicit Initiative Comparison
const comparisonPhrases = [
  'الفرق بين', 'مقارنة بين', 'مقارنه بين', 'ايه الفرق', 'ما الفرق', 'الفرق', 'مقارنة', 'مقارنه',
  'difference between', 'compare', 'comparison', 'versus', 'vs'
];
const isComparisonIntent = comparisonPhrases.some(phrase => msgLower.includes(phrase));

// TIER 2: Exact Multi-Word Entities & Specific Aliases
// Digilians (الرواد الرقميون)
const digiliansEntities = [
  'الرواد الرقميون', 'رواد رقميون', 'مبادرة الرواد الرقميون', 'برنامج الرواد الرقميون',
  'digital pioneers initiative', 'digilians'
];
// DEBI (بناة مصر الرقمية)
const debiEntities = [
  'بناة مصر الرقمية', 'رواد مصر الرقمية', 'مبادرة بناة مصر الرقمية', 'مبادرة رواد مصر الرقمية',
  'digital egypt builders initiative', 'digital egypt pioneers initiative', 'debi', 'depi'
];

let hasDigiliansEntity = digiliansEntities.some(ent => msgLower.includes(ent));
let hasDebiEntity = debiEntities.some(ent => msgLower.includes(ent));

// TIER 3: Program-Specific Institutional Phrases
const digiliansPhrases = ['الاكاديمية العسكرية', 'الأكاديمية العسكرية', 'military academy', '18 الى 32', '18-32', 'digilians.gov.eg'];
const debiPhrases = ['جامعة اوتاوا', 'جامعة كوينز', 'ottawa', 'queens', 'ماجستير دولي', 'international master', 'debi.gov.eg', 'depi.gov.eg'];

if (!hasDigiliansEntity && digiliansPhrases.some(p => msgLower.includes(p))) {
  hasDigiliansEntity = true;
}
if (!hasDebiEntity && debiPhrases.some(p => msgLower.includes(p))) {
  hasDebiEntity = true;
}

// RESOLUTION
let programScope = 'GENERAL';
let isAmbiguous = false;

if (isComparisonIntent || (hasDigiliansEntity && hasDebiEntity)) {
  programScope = 'COMPARISON';
} else if (hasDebiEntity && !hasDigiliansEntity) {
  programScope = 'DEBI';
} else if (hasDigiliansEntity && !hasDebiEntity) {
  programScope = 'DIGILIANS';
} else {
  // Query asks about generic admissions/tracks/requirements without specifying program
  const admissionTerms = [
    'شروط', 'التقديم', 'تقديم', 'قبول', 'القبول', 'تسجيل', 'التسجيل', 'مسار', 'مسارات', 'تخصص', 'تخصصات',
    'منحة', 'تدريب', 'شهادة', 'admission', 'requirement', 'requirements', 'apply', 'eligibility', 'tracks'
  ];
  const hasAdmissionTopic = admissionTerms.some(term => msgLower.includes(term));
  if (hasAdmissionTopic) {
    programScope = 'AMBIGUOUS';
    isAmbiguous = true;
  } else {
    programScope = 'COMMON';
  }
}

// Topic routing is deterministic and only narrows evidence within the resolved program.
let topicCategory = '';
if (programScope === 'DEBI' || programScope === 'DIGILIANS') {
  const isConditions = ['شروط', 'شرط', 'اهلية', 'أهلية', 'التقديم', 'قبول', 'التقدير', 'معدل', 'السن', 'عمر', 'المؤهلة', 'مؤهلة', 'المطلوب', 'مطلوب', 'مستوى', 'gpa', 'grade', 'age', 'required', 'requirements', 'requirement', 'eligibility', 'eligible', 'apply', 'admission', 'who can', 'من يستطيع', 'لغير خريجي'].some(term => msgLower.includes(term));
  const isBenefits = ['منحة', 'Graphic', '.subplot', 'benefit', 'benefits', 'grant', 'grants', '研学'].some(term => msgLower.includes(term));
  const isTracks = ['مسار', 'مسارات', 'SAT', 'specialization', 'specializations', 'tracks', 'track', 'absence', 'absence', 'absence'].some(term => msgLower.includes(term));
  const isOnlineTraining = ['أونلاين', 'اونلاين', 'عن بعد', 'online', 'remote'].some(term => msgLower.includes(term));
  const prefix = programScope === 'DEBI' ? 'debi_' : 'depi_';
  if (isConditions) topicCategory = prefix + 'conditions';
  else if (isBenefits) topicCategory = prefix + 'benefits';
  else if (isTracks) topicCategory = prefix + 'tracks';
  else if (isOnlineTraining) topicCategory = programScope === 'DEBI' ? 'debi_training' : 'depi_study_system';
}
if (programScope === 'DEBI' && (msgLower.includes('من المؤهل') || msgLower.includes('who is eligible'))) topicCategory = '';

let programFilter = "program IN ('DIGILIANS', 'COMMON') AND category NOT IN ('disambiguation', 'comparison')";
if (programScope === 'DEBI') {
  programFilter = "program IN ('DEBI', 'COMMON') AND category NOT IN ('disambiguation', 'comparison')";
} else if (programScope === 'COMPARISON') {
  programFilter = "program IN ('DIGILIANS', 'DEBI', 'COMMON')";
} else if (programScope === 'AMBIGUOUS') {
  programFilter = "category IN ('disambiguation', 'comparison')";
} else if (programScope === 'COMMON') {
  programFilter = "program IN ('DIGILIANS', 'DEBI', 'COMMON')";
}

const disambiguationReply = locale === 'ar'
  ? "هل تقصد مبادرة الرواد الرقميون (Digilians) أم مبادرة رواد مصر الرقمية (DEBI/DEPI)؟ يرجى تحديد المبادرة لتقديم الشروط الدقيقة المعتمدة."
  : "Do you mean Digital Pioneers Initiative (Digilians) or Digital Egypt Builders/Pioneers Initiative (DEBI/DEPI)? Please specify the initiative for verified admission details.";

return [{
  json: {
    ...input,
    customer_message: rawMsg,
    normalized_message: normalized,
    locale: locale,
    program_scope: programScope,
    program_filter: programFilter,
    topic_category: topicCategory,
    is_ambiguous: isAmbiguous,
    disambiguation_reply: disambiguationReply
  }
}];