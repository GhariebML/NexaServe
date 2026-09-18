// Categorize ticket based on customer message keywords
const triggerData = $input.first().json;
const message = (triggerData.customer_message || triggerData.message || '').toLowerCase();

const categoryKeywords = {
  enrollment: ['تسجيل', 'register', 'enroll', 'sign up', 'قبول', 'admission', 'كيفية التسجيل', 'رابط التسجيل', 'apply'],
  training: ['تدريب', 'training', 'course', 'program', 'المسار', 'track', 'المسارات', 'learn', 'skills'],
  lms: ['lms', 'platform', 'تعلم', 'e-learning', 'المنصة', 'course access', 'dashboard', 'login platform'],
  exams: ['exam', 'امتحان', 'test', 'seb', 'الامتحانات', 'quiz', 'exam schedule', 'exam date'],
  certificates: ['certificate', 'شهادة', 'accreditation', 'certification', 'الشهادات', 'certificate download', 'print certificate'],
  technical: ['technical', 'bug', 'issue', 'technical support', 'تقني', 'infrastructure', 'error', 'not working'],
  account: ['account', 'profile', 'حساب', 'username', 'password', 'reset', 'update profile', 'account settings'],
  payments: ['payment', 'fee', 'مدفوعات', 'cost', 'price', 'fees', 'billing', 'invoice', 'دفع'],
  complaint: ['complaint', 'شكوى', 'angry', 'frustrated', 'problem', 'مشكلة', 'موظف', 'سيئة', 'unsatisfied'],
  partnership: ['partner', 'partnership', 'collaboration', 'شراكة', 'university', 'academic', 'جامعة'],
  general: ['hello', 'hi', 'help', 'عام', 'general', 'about', 'ما هو', 'what is', 'info', 'معلومات']
};

let bestCategory = 'general';
let bestScore = 0;
for (const [cat, keywords] of Object.entries(categoryKeywords)) {
  let score = 0;
  for (const kw of keywords) {
    if (message.includes(kw)) score++;
  }
  if (score > bestScore) {
    bestScore = score;
    bestCategory = cat;
  }
}

return [{
  json: {
    category_id: bestCategory,
    category_name: bestCategory,
    confidence: Math.min(1.0, 0.3 + bestScore * 0.2),
    keywords_matched: bestScore,
    customer_message: triggerData.customer_message || triggerData.message || ''
  }
}];
