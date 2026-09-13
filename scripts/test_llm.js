const testPrompts = [
  {
    category: "Order Lookup",
    input: "فين الأوردر بتاعي رقم ORD-8891؟",
    expected: "ORDER_LOOKUP"
  },
  {
    category: "FAQ Query",
    input: "ما هي مواعيد العمل لديكم وسياسة التوصيل؟",
    expected: "FAQ_QUERY"
  },
  {
    category: "Human Escalation",
    input: "الاوردر فيه مشكلة وعاوز اكلم حد من خدمة العملاء حالا",
    expected: "HUMAN_ESCALATION"
  }
];

const SYSTEM_PROMPT = `You are NexaServe AI Intent Engine for customer service.
Analyze the user message and output strictly valid JSON with this schema:
{
  "intent": "ORDER_LOOKUP" | "FAQ_QUERY" | "HUMAN_ESCALATION" | "GENERAL_SUPPORT",
  "confidence": 0.0 to 1.0,
  "entities": {
    "order_id": string or null
  },
  "summary": "Arabic summary"
}
Output strictly valid JSON only.`;

async function testLLM() {
  console.log("=================================================");
  console.log("🚀 Testing Local LLM (qwen2.5:3b) via Ollama API");
  console.log("=================================================");

  let totalTime = 0;

  for (const tc of testPrompts) {
    console.log(`\nTesting: [${tc.category}] "${tc.input}"`);
    const prompt = `<|im_start|>system\n${SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n${tc.input}<|im_end|>\n<|im_start|>assistant\n`;
    
    const startTime = Date.now();
    try {
      const response = await fetch("http://cs-ollama:11434/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "qwen2.5:3b",
          prompt: prompt,
          format: "json",
          stream: false,
          options: {
            temperature: 0.1,
            num_predict: 150
          }
        })
      });

      const latency = Date.now() - startTime;
      totalTime += latency;
      const data = await response.json();
      console.log(`⏱️ Latency: ${latency}ms`);
      console.log(`🤖 Output: ${data.response.trim()}`);
      
      const parsed = JSON.parse(data.response);
      if (parsed.intent === tc.expected) {
        console.log(`✅ Intent correctly identified as: ${parsed.intent}`);
      } else {
        console.log(`⚠️ Expected ${tc.expected}, got: ${parsed.intent}`);
      }
    } catch (err) {
      console.error("❌ Error:", err.message);
    }
  }

  console.log("\n=================================================");
  console.log(`📊 Average Latency: ${(totalTime / testPrompts.length).toFixed(1)}ms`);
  console.log("=================================================");
}

testLLM();
