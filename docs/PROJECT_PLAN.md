# VaaniSetu (वाणी सेतु) - Project Plan

## 1. Vision & Scope for Hackathon

**Goal:** Build a working prototype of VaaniSetu — an AI-powered voice-first platform that converts government scheme documents into interactive voice conversations in local Indian languages.

**Hackathon Constraint:** $100 AWS credits, limited time → focus on a **vertical slice** that demonstrates the core value proposition end-to-end.

---

## 2. What We'll Build (Hackathon MVP)

### Core Flow (Happy Path)
```
User calls → Language detected → Conversational AI understands need
→ Matches eligible schemes → Asks form questions → Generates application
→ Sends SMS confirmation
```

### MVP Feature Set (Priority 1 — Must Have)
| # | Feature | Description |
|---|---------|-------------|
| 1 | **Voice Input/Output** | Accept voice call, transcribe speech, respond with synthesized voice |
| 2 | **Language Support (3 languages)** | Hindi, Tamil, English for pilot |
| 3 | **Scheme Knowledge Base** | 10-15 popular central govt schemes (PM-KISAN, RKVY, PM Awas, etc.) |
| 4 | **Conversational AI** | Multi-turn dialogue with context retention, intent understanding |
| 5 | **Eligibility Matching** | Ask ≤5 questions → match to eligible schemes |
| 6 | **Guided Form Filling** | Conversational form completion with validation |
| 7 | **SMS Confirmation** | Send summary + checklist after call |

### Nice-to-Have (Priority 2 — If Time Permits)
| # | Feature | Description |
|---|---------|-------------|
| 8 | Follow-up call scheduling | Automated reminder calls |
| 9 | Status tracking | Check application status on callback |
| 10 | Admin dashboard | View analytics, manage schemes |
| 11 | Aadhaar verification mock | Simulated identity verification |

### Out of Scope for Hackathon
- Real eDistrict/UIDAI API integration
- Real toll-free number provisioning
- Biometric authentication
- 10,000 concurrent call handling
- Full 12-language support

---

## 3. Architecture Overview

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Phone    │  │ Web Demo     │  │ WebSocket Test Client │ │
│  │ (Twilio) │  │ (React SPA)  │  │ (for development)     │ │
│  └────┬─────┘  └──────┬───────┘  └───────────┬───────────┘ │
└───────┼───────────────┼───────────────────────┼─────────────┘
        │               │                       │
        ▼               ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    VOICE GATEWAY LAYER                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Amazon API Gateway (WebSocket)              │   │
│  │           + REST API for web interface                 │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              AWS Lambda (Python)                       │   │
│  │         Call Orchestrator / Session Manager            │   │
│  └──────┬──────────┬──────────┬──────────┬──────────┘   │
└─────────┼──────────┼──────────┼──────────┼──────────────────┘
          │          │          │          │
          ▼          ▼          ▼          ▼
┌────────────┐┌───────────┐┌──────────┐┌──────────────┐
│  SPEECH    ││    AI     ││  DATA    ││ NOTIFICATION │
│  LAYER     ││   LAYER   ││  LAYER   ││    LAYER     │
│            ││           ││          ││              │
│ Amazon     ││ Amazon    ││ DynamoDB ││ Amazon SNS   │
│ Transcribe ││ Bedrock   ││ (Session ││ (SMS)        │
│ (STT)      ││ (Claude)  ││  + Forms)││              │
│            ││           ││          ││              │
│ Amazon     ││ Amazon    ││ S3       ││              │
│ Polly      ││ Bedrock   ││ (Scheme  ││              │
│ (TTS)      ││ Knowledge ││  Docs)   ││              │
│            ││ Bases     ││          ││              │
│ Amazon     ││           ││ OpenSrch ││              │
│ Translate  ││           ││ Srvless  ││              │
│ (fallback) ││           ││ (Vector) ││              │
└────────────┘└───────────┘└──────────┘└──────────────┘
```

### AWS Services Mapping

| Layer | AWS Service | Purpose | Est. Cost |
|-------|-------------|---------|-----------|
| **Voice Gateway** | API Gateway (WebSocket + REST) | Handle voice connections | ~$2 |
| **Compute** | Lambda (Python 3.12) | Orchestration, business logic | ~$5 |
| **Speech-to-Text** | Amazon Transcribe Streaming | Real-time Hindi/Tamil/English STT | ~$15 |
| **Text-to-Speech** | Amazon Polly (Neural) | Natural voice synthesis in Indian languages | ~$10 |
| **Translation** | Amazon Translate | Language detection + fallback translation | ~$5 |
| **Conversational AI** | Amazon Bedrock (Claude 3 Sonnet/Haiku) | Intent understanding, scheme matching, form filling | ~$30 |
| **Knowledge Base** | Amazon Bedrock Knowledge Bases | RAG over scheme documents | ~$8 |
| **Vector Store** | Amazon OpenSearch Serverless | Embeddings for scheme search | ~$10 |
| **Session Store** | DynamoDB | Conversation state, form data, user sessions | ~$3 |
| **Document Store** | S3 | Scheme PDFs, audio files, form templates | ~$1 |
| **SMS** | Amazon SNS | SMS confirmations and reminders | ~$3 |
| **Monitoring** | CloudWatch | Logs, metrics, alarms | ~$2 |
| **Auth** | Cognito | Admin dashboard authentication | ~$1 |
| **Frontend** | Amplify / S3 + CloudFront | Web demo hosting | ~$2 |
| **IaC** | CDK / SAM | Infrastructure as Code | Free |
| | | **TOTAL ESTIMATE** | **~$97** |

---

## 4. Tech Stack

### Backend
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Runtime | **Python 3.12** | Best AWS SDK support, ML ecosystem |
| Framework | **AWS Lambda + API Gateway** | Serverless, pay-per-use, auto-scaling |
| IaC | **AWS CDK (Python)** | Type-safe, reusable constructs |
| AI/LLM | **Amazon Bedrock (Claude 3)** | Best multilingual reasoning |
| RAG | **Bedrock Knowledge Bases** | Managed RAG pipeline |
| Embeddings | **Titan Embeddings v2** | AWS-native, cost-effective |

### Frontend (Web Demo)
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | **React 18 + TypeScript** | Industry standard, fast dev |
| UI Library | **Tailwind CSS + shadcn/ui** | Beautiful, accessible components |
| Voice | **Web Audio API + WebSocket** | Browser-based voice capture |
| State | **Zustand** | Lightweight state management |
| Build | **Vite** | Fast builds |

### Voice Pipeline
| Step | Technology | Latency Target |
|------|-----------|---------------|
| Audio Capture | WebRTC / Twilio | <100ms |
| Speech-to-Text | Amazon Transcribe Streaming | <2s |
| Language Detection | Amazon Transcribe Auto | <5s |
| AI Processing | Bedrock Claude 3 Haiku | <2s |
| Scheme Search | Bedrock KB + OpenSearch | <1s |
| Text-to-Speech | Amazon Polly Neural | <1s |
| Audio Playback | WebSocket stream | <200ms |
| **Total Round Trip** | | **<5s** |

---

## 5. Data Model

### DynamoDB Tables

#### `vaanisetu-sessions`
```json
{
  "sessionId": "uuid",           // Partition Key
  "phoneNumber": "+91XXXXXXXXXX",
  "language": "hi-IN",
  "status": "active|completed|abandoned",
  "conversationHistory": [
    { "role": "user", "content": "...", "timestamp": "..." },
    { "role": "assistant", "content": "...", "timestamp": "..." }
  ],
  "detectedIntent": "scheme_inquiry|form_fill|status_check",
  "matchedSchemes": ["PM-KISAN", "RKVY"],
  "formData": {
    "name": "...",
    "aadhaar": "XXXX-XXXX-1234",
    "landSize": "2 acres",
    "bankAccount": "...",
    "ifsc": "..."
  },
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601",
  "ttl": 7776000
}
```

#### `vaanisetu-schemes`
```json
{
  "schemeId": "PM-KISAN",          // Partition Key
  "name": {
    "en": "PM Kisan Samman Nidhi",
    "hi": "पीएम किसान सम्मान निधि",
    "ta": "பிரதம மந்திரி கிசான் சம்மான் நிதி"
  },
  "description": { "en": "...", "hi": "...", "ta": "..." },
  "eligibility": {
    "rules": [
      { "field": "occupation", "operator": "eq", "value": "farmer" },
      { "field": "landSize", "operator": "lte", "value": 5, "unit": "acres" },
      { "field": "annualIncome", "operator": "lte", "value": 200000 }
    ]
  },
  "benefits": {
    "amount": 6000,
    "frequency": "annual",
    "installments": 3
  },
  "requiredDocuments": [
    { "id": "aadhaar", "name": { "en": "Aadhaar Card", "hi": "आधार कार्ड" }, "mandatory": true },
    { "id": "landRecord", "name": { "en": "Land Record (7/12)", "hi": "खसरा/7/12" }, "mandatory": true },
    { "id": "bankPassbook", "name": { "en": "Bank Passbook", "hi": "बैंक पासबुक" }, "mandatory": true }
  ],
  "formFields": [
    { "id": "name", "type": "text", "question": { "en": "What is your full name?", "hi": "आपका पूरा नाम क्या है?" } },
    { "id": "aadhaar", "type": "aadhaar", "question": { "en": "What is your Aadhaar number?", "hi": "आपका आधार नंबर क्या है?" } }
  ],
  "category": "agriculture",
  "ministry": "Ministry of Agriculture",
  "deadline": "2026-03-31",
  "isActive": true,
  "updatedAt": "ISO8601"
}
```

#### `vaanisetu-applications`
```json
{
  "applicationId": "VS-2026-XXXXX",  // Partition Key
  "sessionId": "uuid",
  "phoneNumber": "+91XXXXXXXXXX",
  "schemeId": "PM-KISAN",
  "formData": { },
  "status": "draft|submitted|under_review|approved|rejected",
  "submittedAt": "ISO8601",
  "smsHistory": [
    { "type": "confirmation", "sentAt": "ISO8601", "messageId": "..." }
  ],
  "followUpSchedule": [
    { "scheduledAt": "ISO8601", "status": "pending|completed|skipped" }
  ],
  "createdAt": "ISO8601"
}
```

---

## 6. API Design

### WebSocket API (Voice Channel)
```
wss://api.vaanisetu.in/voice

Messages:
  Client → Server:
    { "action": "startSession", "language": "auto" }
    { "action": "audioChunk", "data": "<base64 audio>" }
    { "action": "endTurn" }
    { "action": "switchLanguage", "language": "ta-IN" }
    { "action": "endSession" }

  Server → Client:
    { "type": "languageDetected", "language": "hi-IN" }
    { "type": "transcription", "text": "...", "isFinal": true }
    { "type": "aiResponse", "text": "...", "audio": "<base64>" }
    { "type": "schemeMatch", "schemes": [...] }
    { "type": "formProgress", "completed": 3, "total": 8 }
    { "type": "applicationSubmitted", "id": "VS-2026-XXXXX" }
    { "type": "error", "message": "..." }
```

### REST API (Admin + Web)
```
POST   /api/sessions              - Create new session
GET    /api/sessions/{id}         - Get session details
POST   /api/sessions/{id}/message - Send text message (web demo)
GET    /api/schemes               - List all schemes
GET    /api/schemes/{id}          - Get scheme details
POST   /api/schemes/search        - Semantic scheme search
GET    /api/applications/{id}     - Get application status
POST   /api/applications          - Submit application
GET    /api/admin/analytics       - Dashboard analytics
```

---

## 7. Prompt Engineering Strategy

### System Prompt (Core)
```
You are VaaniSetu (वाणी सेतु), a friendly AI assistant that helps Indian 
citizens discover and apply for government schemes through natural conversation.

PERSONALITY:
- Speak like a helpful village elder — warm, patient, respectful
- Use simple language, avoid bureaucratic jargon
- Address user respectfully (आप/நீங்கள்)
- Be encouraging ("That's great!", "Don't worry, I'll help")

CONVERSATION FLOW:
1. Greet and identify language
2. Understand user's situation (occupation, family, land, income)
3. Match to eligible schemes (use knowledge base)
4. Explain top 3 schemes in simple terms
5. Help fill application form through questions
6. Confirm all details and submit
7. Provide next steps

RULES:
- Never fabricate scheme information — only use knowledge base
- If unsure, say "Let me check that for you" and search
- Always confirm critical info (Aadhaar, bank details) by repeating back
- If confidence < 70%, offer to connect to human agent
- Keep each response under 3 sentences for voice
- Always tell user how many questions remain
```

### Eligibility Matching Prompt
```
Given the user profile:
{user_profile}

And the scheme eligibility criteria:
{scheme_criteria}

Determine if the user is eligible. Return:
1. eligible: true/false
2. confidence: 0-100
3. reason: Simple explanation in {language}
4. missing_info: Fields needed for definitive answer
```

---

## 8. Development Phases

### Phase 1: Foundation (Days 1-2) ✅ START HERE
```
├── Project setup (CDK, Lambda, API Gateway)
├── DynamoDB tables creation
├── S3 bucket for scheme documents
├── Basic Lambda functions (session management)
├── Scheme data seeding (10 schemes in 3 languages)
└── Basic REST API endpoints
```

### Phase 2: AI Core (Days 3-4)
```
├── Bedrock Claude integration
├── System prompt engineering
├── Conversation state machine
├── Scheme knowledge base setup (Bedrock KB + OpenSearch)
├── RAG pipeline for scheme search
├── Eligibility rule engine
└── Form field extraction & validation
```

### Phase 3: Voice Pipeline (Days 5-6)
```
├── Amazon Transcribe streaming integration
├── Amazon Polly TTS integration
├── Language detection
├── WebSocket API for real-time voice
├── Audio chunking and streaming
└── End-to-end voice conversation flow
```

### Phase 4: Web Demo & Polish (Days 7-8)
```
├── React web interface
│   ├── Voice recording UI
│   ├── Conversation transcript display
│   ├── Scheme cards with details
│   ├── Form progress visualization
│   └── SMS preview
├── SMS integration (SNS)
├── Error handling & edge cases
└── Demo preparation
```

### Phase 5: Testing & Demo (Days 9-10)
```
├── End-to-end testing (3 languages)
├── Performance optimization
├── Demo script preparation
├── Video recording
└── Submission documentation
```

---

## 9. Project Structure
```
VaaniSetu/
├── README.md
├── docs/
│   ├── PROJECT_PLAN.md          ← You are here
│   ├── ARCHITECTURE.md
│   ├── API_SPEC.md
│   └── DEMO_SCRIPT.md
├── infrastructure/
│   ├── cdk/
│   │   ├── app.py
│   │   ├── cdk.json
│   │   ├── requirements.txt
│   │   └── stacks/
│   │       ├── __init__.py
│   │       ├── api_stack.py
│   │       ├── data_stack.py
│   │       ├── ai_stack.py
│   │       └── voice_stack.py
│   └── seed-data/
│       ├── schemes/
│       │   ├── pm_kisan.json
│       │   ├── pm_awas.json
│       │   ├── rkvy.json
│       │   └── ...
│       └── seed_schemes.py
├── backend/
│   ├── lambdas/
│   │   ├── orchestrator/
│   │   │   ├── handler.py          # Main conversation orchestrator
│   │   │   ├── session_manager.py  # Session CRUD
│   │   │   ├── conversation.py     # Conversation state machine
│   │   │   └── requirements.txt
│   │   ├── voice_processor/
│   │   │   ├── handler.py          # WebSocket voice handler
│   │   │   ├── transcribe.py       # STT wrapper
│   │   │   ├── polly.py            # TTS wrapper
│   │   │   └── requirements.txt
│   │   ├── ai_engine/
│   │   │   ├── handler.py          # Bedrock integration
│   │   │   ├── prompts.py          # Prompt templates
│   │   │   ├── scheme_matcher.py   # RAG + eligibility
│   │   │   ├── form_filler.py      # Form extraction
│   │   │   └── requirements.txt
│   │   ├── notification/
│   │   │   ├── handler.py          # SMS sender
│   │   │   └── templates.py        # SMS templates
│   │   └── admin/
│   │       ├── handler.py          # Admin API
│   │       └── requirements.txt
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── models.py               # Pydantic models
│   │   ├── aws_clients.py          # Boto3 client wrappers
│   │   ├── constants.py            # Enums, constants
│   │   └── utils.py                # Helpers
│   └── tests/
│       ├── test_orchestrator.py
│       ├── test_ai_engine.py
│       ├── test_voice.py
│       └── test_eligibility.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   │   └── logo.svg
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── VoiceInterface.tsx   # Mic button, waveform
│       │   ├── ChatTranscript.tsx   # Conversation display
│       │   ├── SchemeCard.tsx       # Scheme info cards
│       │   ├── FormProgress.tsx     # Form completion tracker
│       │   ├── LanguageSelector.tsx # Language picker
│       │   └── SMSPreview.tsx       # SMS preview panel
│       ├── hooks/
│       │   ├── useVoice.ts         # WebSocket + audio
│       │   ├── useSession.ts       # Session management
│       │   └── useSchemes.ts       # Scheme data
│       ├── services/
│       │   ├── api.ts              # REST API client
│       │   ├── websocket.ts        # WebSocket client
│       │   └── audio.ts            # Audio processing
│       ├── stores/
│       │   └── conversationStore.ts
│       ├── types/
│       │   └── index.ts
│       └── styles/
│           └── globals.css
└── scripts/
    ├── deploy.sh
    ├── seed_data.py
    └── test_voice.py
```

---

## 10. Scheme Data (Seed - 10 Schemes)

| # | Scheme | Category | Benefit | Key Eligibility |
|---|--------|----------|---------|-----------------|
| 1 | PM-KISAN | Agriculture | ₹6,000/year | Farmer, <5 acres |
| 2 | PM Awas Yojana (Rural) | Housing | ₹1.2 lakh | BPL, no pucca house |
| 3 | RKVY | Agriculture | Variable | Farmer, state-specific |
| 4 | PM Fasal Bima Yojana | Insurance | Crop loss coverage | Farmer with crop |
| 5 | Soil Health Card | Agriculture | Free testing | Any farmer |
| 6 | PM Ujjwala Yojana | Energy | Free LPG connection | BPL women |
| 7 | Ayushman Bharat | Healthcare | ₹5 lakh/year health cover | BPL families |
| 8 | PM Mudra Yojana | Finance | Loans up to ₹10 lakh | Small business |
| 9 | Sukanya Samriddhi | Savings | High interest savings | Girl child <10 yrs |
| 10 | PM Garib Kalyan Anna | Food | Free ration | BPL ration card |

---

## 11. Demo Script (Hackathon Presentation)

### Scenario: Ramesh, a farmer from Bihar
```
1. Ramesh calls VaaniSetu
2. System: "नमस्ते! मैं वाणी सेतु हूँ, आपकी AI सहायक।"
3. Ramesh: "मुझे खेती के लिए पैसे चाहिए"
4. System detects: Hindi, Intent=scheme_inquiry, Category=agriculture
5. System asks 4 questions (occupation, land, income, family)
6. System matches: PM-KISAN (95%), RKVY (82%), Fasal Bima (78%)
7. Ramesh selects PM-KISAN
8. System guides through 8 form questions
9. Confirms all details, generates application
10. Sends SMS with checklist
```

### Demo Flow (3-5 minutes)
1. **30s** — Problem statement slide
2. **30s** — Architecture overview
3. **120s** — Live voice demo (Hindi conversation)
4. **30s** — Show SMS received
5. **30s** — Impact metrics + scaling plan

---

## 12. Risk Management for Hackathon

| Risk | Mitigation |
|------|-----------|
| Transcribe doesn't support a language well | Fall back to text input in web demo |
| Bedrock latency too high | Use Claude 3 Haiku (fastest), cache common queries |
| $100 credits exhausted | Monitor closely, use free tier where possible |
| Voice pipeline too complex | Fallback: text-based chat demo with TTS on responses only |
| Time crunch | Phase 4 features (web UI) can be minimal; focus on backend |

---

## 13. AWS Free Tier Optimization

| Service | Free Tier | Strategy |
|---------|-----------|----------|
| Lambda | 1M free requests/month | Use aggressively |
| DynamoDB | 25 GB free storage | Well within limits |
| S3 | 5 GB free storage | More than enough |
| API Gateway | 1M REST calls free | Sufficient |
| Transcribe | 60 min/month free | Careful with testing |
| Polly | 5M chars/month free | Good for demo |
| Bedrock | Pay per token only | Use Haiku for cost |
| SNS | 100 SMS free | Enough for demo |

---

## 14. Key Decisions to Make

- [ ] **Voice transport**: WebSocket (custom) vs. Amazon Connect vs. Twilio?
- [ ] **LLM Model**: Claude 3 Haiku (cheap, fast) vs. Sonnet (better quality)?
- [ ] **RAG approach**: Bedrock KB (managed) vs. custom LangChain?
- [ ] **Frontend**: Full React app vs. simple HTML demo?
- [ ] **IaC**: CDK vs. SAM vs. CloudFormation?
- [ ] **Telephony**: Real phone number or web-only demo?

---

## Next Steps
1. Set up AWS CDK project
2. Create DynamoDB tables and seed scheme data
3. Build Bedrock AI engine with conversation flow
4. Integrate voice pipeline (Transcribe + Polly)
5. Build web demo interface
6. Test end-to-end flow
7. Prepare demo video
