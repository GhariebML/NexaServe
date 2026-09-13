const http = require('http');

const payload = JSON.stringify({
  model: 'qwen2.5:1.5b',
  prompt: 'أنت المساعد الذكي الرسمي لمبادرة الرواد الرقميون (DEPI). أجب بصيغة JSON فقط: {"intent": "general_support", "direct_response": "..."}\nسؤال: ما هي شروط التقديم في المبادرة؟',
  format: 'json',
  stream: false,
  options: {
    num_ctx: 2048,
    temperature: 0.2
  }
});

const req = http.request({
  host: 'cs-ollama',
  port: 11434,
  path: '/api/generate',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload)
  }
}, (res) => {
  let body = '';
  res.on('data', c => body += c);
  res.on('end', () => console.log('STATUS:', res.statusCode, '\nBODY:', body));
});

req.on('error', console.error);
req.write(payload);
req.end();
