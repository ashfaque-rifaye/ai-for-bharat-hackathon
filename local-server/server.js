// VaaniSetu — Local Mock API Server
// Simulates backend Lambda responses for frontend development
// Start: cd local-server && npm install && npm start

import express from 'express';
import cors from 'cors';
import { randomUUID } from 'crypto';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = 4000;
const WS_PORT = 4001;

app.use(cors());
app.use(express.json());

// ── In-memory stores ────────────────────────────────────────────────
const sessions = new Map();
const applications = new Map();

// ── Load seed schemes ───────────────────────────────────────────────
let schemes = [];
try {
  const seedDir = join(__dirname, '..', 'infrastructure', 'seed-data', 'schemes');
  const files = readdirSync(seedDir).filter(f => f.endsWith('.json'));
  schemes = files.map(f => JSON.parse(readFileSync(join(seedDir, f), 'utf-8')));
  console.log(`Loaded ${schemes.length} seed schemes`);
} catch (e) {
  console.warn('Could not load seed schemes, using sample data');
  schemes = [
    {
      scheme_id: 'pm_kisan',
      name: { en: 'PM-KISAN', hi: 'पीएम-किसान' },
      category: 'agriculture',
      description: { en: 'Income support to farmer families', hi: 'किसान परिवारों को आय सहायता' },
      benefits: { en: ['₹6000 per year in 3 installments'], hi: ['3 किस्तों में प्रति वर्ष ₹6000'] },
      eligibility: { min_age: 18, max_income: 200000, occupation: ['farmer'] }
    }
  ];
}

// ── Mock AI Responses ───────────────────────────────────────────────
const MOCK_RESPONSES = {
  'hi-IN': {
    GREETING: 'नमस्कार! मैं वाणी सेतु हूँ। मैं आपकी सरकारी योजनाएं खोजने में मदद कर सकती हूँ। कृपया बताएं आपको किस तरह की सहायता चाहिए?',
    NEED_ASSESSMENT: 'मैं समझ रही हूँ। क्या आप मुझे अपनी स्थिति के बारे में कुछ और बता सकते हैं? जैसे — आपका व्यवसाय, उम्र, और मासिक आय?',
    SCHEME_MATCH: 'आपकी जानकारी के आधार पर, मुझे कुछ योजनाएं मिली हैं जो आपके लिए उपयुक्त हो सकती हैं। क्या आप इनके बारे में विस्तार से जानना चाहेंगे?',
    ELIGIBILITY_CHECK: 'चलिए पात्रता जाँच करते हैं। कृपया अपना आधार नंबर बताएं।',
    FORM_FILL: 'अब आवेदन फॉर्म भरते हैं। कृपया अपना पूरा नाम बताएं।',
    REVIEW: 'आपका आवेदन तैयार है। कृपया सभी जानकारी जाँच लें। क्या सब सही है?',
    COMPLETE: 'आपका आवेदन सफलतापूर्वक जमा हो गया है! आवेदन संख्या: APP-{appId}। आपको SMS से पुष्टि मिलेगी।',
  },
  'en-IN': {
    GREETING: 'Hello! I am VaaniSetu. I can help you discover government schemes. Please tell me what kind of assistance you need.',
    NEED_ASSESSMENT: 'I understand. Can you tell me more about yourself? Like your occupation, age, and monthly income?',
    SCHEME_MATCH: 'Based on your information, I found some schemes that may suit you. Would you like to know more about them?',
    ELIGIBILITY_CHECK: 'Let\'s check eligibility. Please share your Aadhaar number.',
    FORM_FILL: 'Now let\'s fill the application form. Please tell me your full name.',
    REVIEW: 'Your application is ready. Please verify all the information. Is everything correct?',
    COMPLETE: 'Your application has been submitted successfully! Application number: APP-{appId}. You will receive an SMS confirmation.',
  },
  'ta-IN': {
    GREETING: 'வணக்கம்! நான் வாணி சேது. அரசுத் திட்டங்களைக் கண்டறிய உங்களுக்கு உதவ முடியும். உங்களுக்கு என்ன வகையான உதவி தேவை என்று கூறுங்கள்.',
    NEED_ASSESSMENT: 'புரிகிறது. உங்களைப் பற்றி மேலும் கூற முடியுமா? உங்கள் தொழில், வயது மற்றும் மாத வருமானம்?',
    SCHEME_MATCH: 'உங்கள் தகவலின் அடிப்படையில், உங்களுக்குப் பொருத்தமான சில திட்டங்களைக் கண்டறிந்தேன்.',
    ELIGIBILITY_CHECK: 'தகுதியை சரிபார்ப்போம். உங்கள் ஆதார் எண்ணைக் கூறுங்கள்.',
    FORM_FILL: 'இப்போது விண்ணப்பப் படிவத்தை நிரப்புவோம். உங்கள் முழுப்பெயரைக் கூறுங்கள்.',
    REVIEW: 'உங்கள் விண்ணப்பம் தயாராக உள்ளது. தகவலை சரிபார்க்கவும்.',
    COMPLETE: 'உங்கள் விண்ணப்பம் வெற்றிகரமாக சமர்ப்பிக்கப்பட்டது! விண்ணப்ப எண்: APP-{appId}.',
  }
};

const STATE_FLOW = [
  'GREETING', 'NEED_ASSESSMENT', 'SCHEME_MATCH',
  'ELIGIBILITY_CHECK', 'FORM_FILL', 'REVIEW', 'COMPLETE'
];

// ── Health ───────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', mode: 'local-dev', timestamp: new Date().toISOString() });
});

// ── Sessions ─────────────────────────────────────────────────────────
app.post('/sessions', (req, res) => {
  const { language = 'hi-IN', phoneNumber } = req.body;
  const localeResponses = MOCK_RESPONSES[language] || MOCK_RESPONSES['en-IN'];
  const session = {
    sessionId: randomUUID(),
    language,
    phoneNumber,
    conversationState: 'GREETING',
    stateIndex: 0,
    matchedSchemes: [],
    formData: {},
    createdAt: new Date().toISOString(),
    ttl: Math.floor(Date.now() / 1000) + 86400,
    greeting: localeResponses['GREETING'],
  };
  sessions.set(session.sessionId, session);
  console.log(`[Session] Created ${session.sessionId} (${language})`);
  res.json(session);
});

app.get('/sessions/:sessionId', (req, res) => {
  const session = sessions.get(req.params.sessionId);
  if (!session) return res.status(404).json({ error: 'Session not found' });
  res.json(session);
});

// ── Messages (orchestrator mock) ─────────────────────────────────────
app.post('/sessions/:sessionId/message', (req, res) => {
  const session = sessions.get(req.params.sessionId);
  if (!session) return res.status(404).json({ error: 'Session not found' });

  const userMessage = req.body.message || req.body.text || '';
  const lang = req.body.language || session.language || 'hi-IN';

  // Advance state by one step per message
  if (session.stateIndex < STATE_FLOW.length - 1) {
    session.stateIndex += 1;
  }
  session.conversationState = STATE_FLOW[session.stateIndex];

  // Pick matched schemes when in SCHEME_MATCH state
  if (session.conversationState === 'SCHEME_MATCH' && session.matchedSchemes.length === 0) {
    session.matchedSchemes = schemes.slice(0, 3).map(s => ({
      schemeId: s.schemeId,
      name: s.name || { en: s.schemeId, hi: s.schemeId },
      category: s.category || 'agriculture',
      matchScore: parseFloat((Math.random() * 0.3 + 0.7).toFixed(2)),
      eligibility: 'eligible',
      shortDescription: s.shortDescription || s.description || { en: 'Government welfare scheme', hi: 'सरकारी कल्याण योजना' },
    }));
  }

  // Generate a mock application ID in COMPLETE state
  let applicationId;
  if (session.conversationState === 'COMPLETE') {
    applicationId = `APP-${Date.now().toString(36).toUpperCase()}`;
    applications.set(applicationId, {
      applicationId,
      sessionId: session.sessionId,
      status: 'submitted',
      scheme: session.matchedSchemes[0]?.schemeId || 'PM-KISAN',
      submittedAt: new Date().toISOString(),
    });
  }

  const localeResponses = MOCK_RESPONSES[lang] || MOCK_RESPONSES['en-IN'];
  let responseText = localeResponses[session.conversationState] || localeResponses['GREETING'];
  if (applicationId) {
    responseText = responseText.replace('{appId}', applicationId);
  }

  console.log(`[Message] ${session.sessionId} | ${userMessage.slice(0, 40)} → ${session.conversationState}`);

  res.json({
    response: responseText,
    conversationState: session.conversationState,
    matchedSchemes: session.matchedSchemes,
    formProgress: session.conversationState === 'FORM_FILL'
      ? { completedFields: 2, totalFields: 5, percentage: 40, currentField: 'name' }
      : undefined,
    applicationId,
  });
});

// ── Schemes ──────────────────────────────────────────────────────────
app.get('/schemes', (req, res) => {
  res.json({ schemes });
});

app.get('/schemes/:schemeId', (req, res) => {
  const scheme = schemes.find(s => s.schemeId === req.params.schemeId);
  if (!scheme) return res.status(404).json({ error: 'Scheme not found' });
  res.json(scheme);
});

app.post('/schemes/search', (req, res) => {
  const query = (req.body.query || '').toLowerCase();
  const results = schemes.filter(s => {
    const name = JSON.stringify(s.name || {}).toLowerCase();
    const desc = JSON.stringify(s.description || {}).toLowerCase();
    return name.includes(query) || desc.includes(query);
  });
  res.json({ schemes: results.length > 0 ? results : schemes.slice(0, 3) });
});

// ── Voice: TTS Synthesize (Polly mock) ───────────────────────────────
app.post('/synthesize', (req, res) => {
  const { text = '', language = 'hi-IN' } = req.body;
  // Return a tiny valid MP3 silence (~0.1s) encoded as base64
  // This lets the AudioPlayer work without actually calling Polly
  const SILENCE_MP3_B64 = 'SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABhgC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAAAYYoRwBHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=';
  console.log(`[Synthesize] text="${text.slice(0, 40)}..." lang=${language}`);
  res.json({
    audio: SILENCE_MP3_B64,
    contentType: 'audio/mpeg',
    language,
  });
});

// ── Voice: Transcribe (mock STT) ─────────────────────────────────────
app.post('/transcribe', (req, res) => {
  const { language = 'hi-IN' } = req.body;
  // Return a mock transcription based on language
  const mockTexts = {
    'hi-IN': 'मुझे किसान योजना के बारे में बताइए',
    'en-IN': 'Tell me about farmer schemes',
    'ta-IN': 'விவசாய திட்டங்களைப் பற்றி சொல்லுங்கள்',
  };
  const text = mockTexts[language] || mockTexts['en-IN'];
  console.log(`[Transcribe] lang=${language} → "${text}"`);
  res.json({ text, language, confidence: 0.92 });
});

// ── Benefit Summary ──────────────────────────────────────────────────
app.post('/benefit-summary', (req, res) => {
  const { sessionId, language = 'hi-IN' } = req.body;
  const session = sessions.get(sessionId);
  const matched = session?.matchedSchemes || [];

  const eligibleSchemes = matched.map((s, i) => {
    const scheme = schemes.find(sc => sc.schemeId === s.schemeId) || {};
    return {
      schemeId: s.schemeId,
      name: scheme.name?.en || s.name?.en || s.schemeId,
      category: scheme.category || 'agriculture',
      benefitAmount: [6000, 120000, 200000, 500000][i % 4],
      benefitDescription: scheme.benefits?.[0]?.description?.en || 'Annual financial assistance',
      confidence: 0.85 + (i * 0.03),
      missingInfo: [],
    };
  });

  const totalAnnual = eligibleSchemes.reduce((sum, s) => sum + s.benefitAmount, 0);

  res.json({
    totalAnnualBenefit: totalAnnual,
    eligibleCount: eligibleSchemes.length,
    eligibleSchemes,
    synergies: matched.length >= 2 ? [{
      id: 'farmer-income-shield',
      label: language.startsWith('hi') ? 'किसान आय कवच' : 'Farmer Income Shield',
      description: language.startsWith('hi')
        ? 'इन योजनाओं का संयुक्त लाभ आपकी आय को सुरक्षित करता है'
        : 'These schemes together protect your income from multiple risks',
      schemes: matched.slice(0, 2).map(s => s.schemeId),
      allMatched: true,
    }] : [],
    summaryText: language.startsWith('hi')
      ? `आप ${eligibleSchemes.length} योजनाओं के लिए पात्र हैं, कुल वार्षिक लाभ ₹${totalAnnual.toLocaleString('en-IN')}`
      : `You are eligible for ${eligibleSchemes.length} schemes with total annual benefits of ₹${totalAnnual.toLocaleString('en-IN')}`,
  });
});

// ── Analytics ─────────────────────────────────────────────────────────
app.get('/analytics', (req, res) => {
  const allSessions = [...sessions.values()];
  const langDist = {};
  const stateDist = {};
  const schemeCount = {};
  let totalMessages = 0;

  allSessions.forEach(s => {
    langDist[s.language] = (langDist[s.language] || 0) + 1;
    stateDist[s.conversationState] = (stateDist[s.conversationState] || 0) + 1;
    totalMessages += (s.stateIndex || 0) + 1;
    (s.matchedSchemes || []).forEach(m => {
      schemeCount[m.schemeId] = (schemeCount[m.schemeId] || 0) + 1;
    });
  });

  const topSchemes = Object.entries(schemeCount)
    .map(([schemeId, count]) => ({ schemeId, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  res.json({
    totalSessions: allSessions.length,
    activeSessions: allSessions.filter(s => s.conversationState !== 'COMPLETE').length,
    averageMessagesPerSession: allSessions.length > 0 ? Math.round(totalMessages / allSessions.length) : 0,
    languageDistribution: langDist,
    conversationStateDistribution: stateDist,
    topSchemes,
    totalMessages,
  });
});

// ── PDF Generation (mock) ────────────────────────────────────────────
app.post('/generate-pdf', (req, res) => {
  const { type = 'benefit-summary' } = req.body;
  res.json({
    url: '#mock-pdf',
    fileName: `vaanisetu-${type}-${Date.now()}.pdf`,
    sizeBytes: 45000,
  });
});

// ── Applications ─────────────────────────────────────────────────────
app.get('/applications/:applicationId', (req, res) => {
  const app_record = applications.get(req.params.applicationId);
  if (!app_record) return res.status(404).json({ error: 'Application not found' });
  res.json(app_record);
});

// ── Start HTTP Server ────────────────────────────────────────────────
const httpServer = createServer(app);
httpServer.listen(PORT, () => {
  console.log(`\n  VaaniSetu Local API: http://localhost:${PORT}`);
  console.log(`  Health: http://localhost:${PORT}/health`);
});

// ── WebSocket Server (voice simulation) ──────────────────────────────
const wss = new WebSocketServer({ port: WS_PORT });

wss.on('connection', (ws) => {
  console.log('[WS] Client connected');
  let sessionId = null;

  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString());
      // Frontend uses msg.action (camelCase), support both old and new protocol
      const action = msg.action || msg.type;
      console.log(`[WS] Received action: ${action}`, JSON.stringify(msg).slice(0, 120));

      if (action === 'startSession' || action === 'start_session') {
        sessionId = msg.sessionId || randomUUID();
        const lang = msg.language || 'hi-IN';
        if (!sessions.has(sessionId)) {
          sessions.set(sessionId, {
            sessionId,
            language: lang,
            conversationState: 'GREETING',
            stateIndex: 0,
            matchedSchemes: [],
            formData: {},
            createdAt: new Date().toISOString(),
          });
        }
        // Respond with camelCase type the frontend expects
        ws.send(JSON.stringify({ type: 'sessionStarted', sessionId, language: lang }));

        // Send initial greeting as an aiResponse
        const localeResponses = MOCK_RESPONSES[lang] || MOCK_RESPONSES['en-IN'];
        const greetingText = localeResponses['GREETING'];
        setTimeout(() => {
          ws.send(JSON.stringify({
            type: 'aiResponse',
            text: greetingText,
            conversationState: 'GREETING',
          }));
        }, 300);
        return;
      }

      if (action === 'audioChunk' || action === 'audio_chunk') {
        const sid = msg.sessionId || sessionId;
        const session = sessions.get(sid);
        const lang = session?.language || 'hi-IN';
        const mockText = lang === 'hi-IN'
          ? 'मुझे किसान योजना चाहिए'
          : lang === 'ta-IN'
            ? 'எனக்கு விவசாய திட்டம் வேண்டும்'
            : 'I need a farmer scheme';

        // 1) Send transcription after short delay
        setTimeout(() => {
          ws.send(JSON.stringify({
            type: 'transcription',
            text: mockText,
            isFinal: true,
          }));
        }, 500);

        // 2) Then send AI response (same logic as text_message)
        setTimeout(() => {
          if (!session) {
            ws.send(JSON.stringify({ type: 'error', message: 'Session not found' }));
            return;
          }
          if (session.stateIndex < STATE_FLOW.length - 1) session.stateIndex += 1;
          session.conversationState = STATE_FLOW[session.stateIndex];

          if (session.conversationState === 'SCHEME_MATCH' && session.matchedSchemes.length === 0) {
            session.matchedSchemes = schemes.slice(0, 3).map(s => ({
              schemeId: s.schemeId,
              name: s.name || { en: s.schemeId, hi: s.schemeId },
              category: s.category || 'agriculture',
              matchScore: parseFloat((Math.random() * 0.3 + 0.7).toFixed(2)),
              eligibility: 'eligible',
              shortDescription: s.shortDescription || s.description || { en: 'Government welfare scheme', hi: '\u0938\u0930\u0915\u093e\u0930\u0940 \u0915\u0932\u094d\u092f\u093e\u0923 \u092f\u094b\u091c\u0928\u093e' },
            }));
          }

          const localeResponses = MOCK_RESPONSES[lang] || MOCK_RESPONSES['en-IN'];
          const responseText = localeResponses[session.conversationState] || localeResponses['GREETING'];

          ws.send(JSON.stringify({
            type: 'aiResponse',
            text: responseText,
            conversationState: session.conversationState,
            matchedSchemes: session.matchedSchemes.length > 0 ? session.matchedSchemes : undefined,
          }));
        }, 1200);
        return;
      }

      if (action === 'message' || action === 'text_message') {
        // Frontend sends text in msg.data, old protocol uses msg.text
        const userText = msg.data || msg.text || '';
        const sid = msg.sessionId || sessionId;
        const session = sessions.get(sid);
        if (!session) {
          ws.send(JSON.stringify({ type: 'error', message: 'Session not found' }));
          return;
        }

        const lang = msg.language || session.language || 'hi-IN';
        if (session.stateIndex < STATE_FLOW.length - 1) session.stateIndex += 1;
        session.conversationState = STATE_FLOW[session.stateIndex];

        // Pick matched schemes when in SCHEME_MATCH state
        if (session.conversationState === 'SCHEME_MATCH' && session.matchedSchemes.length === 0) {
          session.matchedSchemes = schemes.slice(0, 3).map(s => ({
            schemeId: s.schemeId,
            name: s.name || { en: s.schemeId, hi: s.schemeId },
            category: s.category || 'agriculture',
            matchScore: parseFloat((Math.random() * 0.3 + 0.7).toFixed(2)),
            eligibility: 'eligible',
            shortDescription: s.shortDescription || s.description || { en: 'Government welfare scheme', hi: '\u0938\u0930\u0915\u093e\u0930\u0940 \u0915\u0932\u094d\u092f\u093e\u0923 \u092f\u094b\u091c\u0928\u093e' },
          }));
        }

        // Generate application ID in COMPLETE state
        let applicationId;
        if (session.conversationState === 'COMPLETE') {
          applicationId = `APP-${Date.now().toString(36).toUpperCase()}`;
          applications.set(applicationId, {
            applicationId,
            sessionId: sid,
            status: 'submitted',
            scheme: session.matchedSchemes[0]?.schemeId || 'PM-KISAN',
            submittedAt: new Date().toISOString(),
          });
        }

        const localeResponses = MOCK_RESPONSES[lang] || MOCK_RESPONSES['en-IN'];
        let responseText = localeResponses[session.conversationState] || localeResponses['GREETING'];
        if (applicationId) {
          responseText = responseText.replace('{appId}', applicationId);
        }

        console.log(`[WS Message] ${sid} | ${userText.slice(0, 40)} → ${session.conversationState}`);

        // Simulate a small delay for realistic feel
        setTimeout(() => {
          ws.send(JSON.stringify({
            type: 'aiResponse',
            text: responseText,
            conversationState: session.conversationState,
            matchedSchemes: session.matchedSchemes.length > 0 ? session.matchedSchemes : undefined,
            formProgress: session.conversationState === 'FORM_FILL'
              ? { completedFields: 2, totalFields: 5, percentage: 40, currentField: 'name' }
              : undefined,
            applicationId,
          }));
        }, 400);
        return;
      }

      if (action === 'switchLanguage') {
        const session = sessions.get(msg.sessionId || sessionId);
        if (session) {
          session.language = msg.language;
          ws.send(JSON.stringify({ type: 'languageSwitched', language: msg.language }));
        }
        return;
      }

      if (action === 'endSession') {
        ws.send(JSON.stringify({ type: 'sessionEnded' }));
        return;
      }

      console.warn('[WS] Unknown action:', action, msg);
    } catch (e) {
      console.error('[WS] Error:', e.message);
    }
  });

  ws.on('close', () => {
    console.log('[WS] Client disconnected');
  });
});

console.log(`  WebSocket: ws://localhost:${WS_PORT}`);
console.log('  ────────────────────────────────────────');
console.log('  Run frontend: cd frontend && npm run dev');
console.log('');
