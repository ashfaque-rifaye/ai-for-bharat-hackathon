# VaaniSetu — System Architecture

## 1. Architecture Principles

1. **Serverless-first** — No servers to manage, pay only for usage (critical with $100 budget)
2. **Event-driven** — Loosely coupled services communicating via events
3. **Voice-native** — Every feature designed for voice interaction first, text second
4. **Multi-language by design** — Language is a first-class concept, not an afterthought
5. **Fail gracefully** — Always have a fallback (AI → human, voice → text, online → queued)

---

## 2. Component Architecture

### 2.1 Voice Gateway

```
                    ┌──────────────────────┐
                    │   Phone / Browser     │
                    └──────────┬───────────┘
                               │ Audio Stream
                               ▼
                    ┌──────────────────────┐
                    │  API Gateway          │
                    │  (WebSocket API)      │
                    │                       │
                    │  Routes:              │
                    │  $connect → Lambda    │
                    │  $disconnect → Lambda │
                    │  audioChunk → Lambda  │
                    │  message → Lambda     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Connection Manager   │
                    │  Lambda               │
                    │                       │
                    │  - Create session     │
                    │  - Store connectionId │
                    │  - Route to processor │
                    └──────────────────────┘
```

**Design Decisions:**
- WebSocket API Gateway for real-time bidirectional audio streaming
- Each connection gets a unique `connectionId` for pushing responses back
- Connection metadata stored in DynamoDB for session management

### 2.2 Speech Processing Pipeline

```
Audio In                                              Audio Out
   │                                                      ▲
   ▼                                                      │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  Amazon      │    │  Language     │    │  Amazon      │  │
│  Transcribe  │───▶│  Router      │    │  Polly       │  │
│  Streaming   │    │              │    │  Neural      │  │
│              │    │  Detects     │    │              │  │
│  Real-time   │    │  language    │    │  Voices:     │  │
│  STT with    │    │  from first  │    │  hi-IN Aditi │  │
│  language    │    │  utterance   │    │  ta-IN -----│  │
│  detection   │    │              │    │  en-IN Raveena│ │
└──────────────┘    └──────┬───────┘    └──────▲───────┘  │
                           │                   │          │
                           ▼                   │          │
                    ┌──────────────┐    ┌──────┴───────┐  │
                    │  Transcript  │    │  Response     │  │
                    │  (text)      │───▶│  Generator    │──┘
                    │              │    │  (AI text)    │
                    └──────────────┘    └──────────────┘
```

**Language Support Matrix:**

| Language | Transcribe Code | Polly Voice | Neural? |
|----------|----------------|-------------|---------|
| Hindi | hi-IN | Aditi / Kajal | Yes (Kajal) |
| Tamil | ta-IN | — (use Translate+Polly) | Partial |
| English (India) | en-IN | Raveena / Kajal | Yes |
| Telugu | te-IN | — | Partial |
| Bengali | bn-IN | — | Partial |

**Fallback Strategy:**
- If Transcribe doesn't support a language natively → use `auto` detection
- If Polly doesn't have a neural voice → use standard voice
- If neither works → use Amazon Translate to convert to Hindi/English, process, translate back

### 2.3 AI Conversation Engine

```
┌─────────────────────────────────────────────────┐
│              AI ENGINE (Lambda)                   │
│                                                   │
│  ┌───────────────┐   ┌───────────────────────┐  │
│  │ Conversation   │   │ Amazon Bedrock         │  │
│  │ State Machine  │──▶│ Claude 3 Haiku/Sonnet  │  │
│  │                │   │                         │  │
│  │ States:        │   │ System Prompt:          │  │
│  │ • GREETING     │   │ - Personality           │  │
│  │ • NEED_ASSESS  │   │ - Conversation rules    │  │
│  │ • SCHEME_MATCH │   │ - Language constraints   │  │
│  │ • ELIGIBILITY  │   │                         │  │
│  │ • FORM_FILL    │   │ Tools:                  │  │
│  │ • REVIEW       │   │ - search_schemes()      │  │
│  │ • SUBMIT       │   │ - check_eligibility()   │  │
│  │ • FOLLOWUP     │   │ - validate_field()      │  │
│  └───────┬───────┘   └───────────┬─────────────┘  │
│          │                       │                  │
│          ▼                       ▼                  │
│  ┌───────────────┐   ┌───────────────────────┐   │
│  │ Session Store  │   │ Knowledge Base         │   │
│  │ (DynamoDB)     │   │ (Bedrock KB)           │   │
│  │                │   │                         │   │
│  │ - History      │   │ - 250+ scheme docs     │   │
│  │ - Form data    │   │ - Eligibility rules    │   │
│  │ - User profile │   │ - FAQ answers          │   │
│  │ - State        │   │ - Document guides      │   │
│  └───────────────┘   └───────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Conversation State Machine:**

```
    ┌──────────┐
    │ GREETING │ ──── Language detected
    └────┬─────┘
         │
         ▼
    ┌──────────────┐
    │ NEED_ASSESS  │ ──── Ask about situation
    │ (≤5 questions)│      (occupation, land, income, family, location)
    └────┬─────────┘
         │
         ▼
    ┌──────────────┐
    │ SCHEME_MATCH │ ──── RAG search + eligibility check
    │              │      Present top 3 schemes
    └────┬─────────┘
         │ User selects scheme
         ▼
    ┌──────────────┐
    │ ELIGIBILITY  │ ──── Detailed eligibility verification
    │ VERIFY       │      Ask missing criteria questions
    └────┬─────────┘
         │ Eligible
         ▼
    ┌──────────────┐
    │ FORM_FILL    │ ──── Guide through form questions
    │ (8-15 fields)│      Validate each field
    └────┬─────────┘
         │
         ▼
    ┌──────────────┐
    │ REVIEW       │ ──── Read back all information
    │              │      Allow corrections
    └────┬─────────┘
         │ Confirmed
         ▼
    ┌──────────────┐
    │ SUBMIT       │ ──── Generate application
    │              │      Send SMS confirmation
    └────┬─────────┘
         │
         ▼
    ┌──────────────┐
    │ COMPLETE     │ ──── Thank user, provide reference ID
    └──────────────┘
```

**Bedrock Tool Use (Function Calling):**

The AI agent will use Claude's tool-use capability to call backend functions:

```python
tools = [
    {
        "name": "search_schemes",
        "description": "Search government schemes matching user's needs",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "User's need in natural language"},
                "category": {"type": "string", "enum": ["agriculture", "housing", "healthcare", "finance", "education", "food", "energy"]},
                "state": {"type": "string", "description": "User's state"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "check_eligibility",
        "description": "Check if user is eligible for a specific scheme",
        "input_schema": {
            "type": "object",
            "properties": {
                "scheme_id": {"type": "string"},
                "user_profile": {"type": "object"}
            },
            "required": ["scheme_id", "user_profile"]
        }
    },
    {
        "name": "validate_field",
        "description": "Validate a form field value",
        "input_schema": {
            "type": "object",
            "properties": {
                "field_type": {"type": "string", "enum": ["aadhaar", "phone", "ifsc", "pincode", "name", "date", "amount"]},
                "value": {"type": "string"}
            },
            "required": ["field_type", "value"]
        }
    },
    {
        "name": "submit_application",
        "description": "Submit completed application form",
        "input_schema": {
            "type": "object",
            "properties": {
                "scheme_id": {"type": "string"},
                "form_data": {"type": "object"}
            },
            "required": ["scheme_id", "form_data"]
        }
    },
    {
        "name": "send_sms",
        "description": "Send SMS to user with application details",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string"},
                "message": {"type": "string"},
                "language": {"type": "string"}
            },
            "required": ["phone_number", "message"]
        }
    }
]
```

### 2.4 Knowledge Base (RAG Pipeline)

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  S3 Bucket   │────▶│ Bedrock KB       │────▶│ OpenSearch       │
│              │     │ Ingestion        │     │ Serverless       │
│  /schemes/   │     │                  │     │                  │
│  - PDFs      │     │ - Chunk docs     │     │ - Vector store   │
│  - JSONs     │     │ - Generate       │     │ - k-NN search    │
│  - FAQs      │     │   embeddings     │     │ - Hybrid search  │
│              │     │   (Titan v2)     │     │                  │
└──────────────┘     └──────────────────┘     └──────────────────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │ Query Pipeline   │
                                              │                  │
                                              │ User: "खेती के  │
                                              │ लिए पैसे चाहिए"  │
                                              │       │          │
                                              │       ▼          │
                                              │ Translate to EN  │
                                              │ (if needed)      │
                                              │       │          │
                                              │       ▼          │
                                              │ Embed query      │
                                              │       │          │
                                              │       ▼          │
                                              │ k-NN search      │
                                              │ (top 5 results)  │
                                              │       │          │
                                              │       ▼          │
                                              │ Rerank + filter  │
                                              │       │          │
                                              │       ▼          │
                                              │ Return schemes   │
                                              └──────────────────┘
```

### 2.5 Notification System

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Application │────▶│  Lambda      │────▶│  Amazon SNS  │
│  Submitted   │     │  Notification│     │              │
│  (Event)     │     │  Handler     │     │  SMS to      │
│              │     │              │     │  +91XXXXXXXX  │
└──────────────┘     │  Templates:  │     └──────────────┘
                     │  - Confirm   │
                     │  - Reminder  │            │
                     │  - Status    │            ▼
                     │  - Checklist │     ┌──────────────┐
                     └──────────────┘     │  User's      │
                                          │  Phone       │
                                          │              │
                                          │  📱 SMS:     │
                                          │  "आवेदन ID:  │
                                          │  VS-2026-001 │
                                          │  स्थिति:     │
                                          │  जमा किया    │
                                          │  ..."        │
                                          └──────────────┘
```

---

## 3. Data Flow — Complete Call Lifecycle

```
Time    User                    System                        AWS Services
─────   ──────────────────     ────────────────────────       ──────────────
0s      Calls / Opens web  ─── WebSocket connection ───────── API Gateway
                                                              DynamoDB (session)

2s      "नमस्ते"           ─── Audio chunk received ────────── Lambda
                               STT processing ────────────── Transcribe
                               Language: Hindi detected

5s                          ─── "नमस्ते! मैं वाणी सेतु     ── Bedrock (Claude)
                                हूँ। आपकी क्या मदद          ── Polly (TTS)
                                कर सकती हूँ?"

10s     "मुझे खेती के      ─── STT → Text ─────────────────── Transcribe
         लिए पैसे चाहिए"       Intent: scheme_inquiry
                               Category: agriculture

15s                         ─── RAG Search ──────────────────── Bedrock KB
                               Schemes found: PM-KISAN,        OpenSearch
                               RKVY, Fasal Bima

20s                         ─── "आपके लिए 3 योजनाएं        ── Bedrock
                               मिली हैं..."                   Polly

25-60s  Answers 4-5         ─── Eligibility Questions ──────── Bedrock
        profiling questions     Build user profile              DynamoDB

65s                         ─── Eligibility Check ───────────── Lambda
                               PM-KISAN: ✅ Eligible            (rule engine)
                               RKVY: ✅ Eligible
                               Fasal Bima: ❌ No crop

70s     "PM-KISAN चाहिए"    ─── Start Form Fill ────────────── Bedrock

70-     Answers 8-10        ─── Form questions one by one ──── Bedrock
300s    form questions          Validate each field              DynamoDB

310s                        ─── Review all answers ──────────── Bedrock
                               "आपका नाम रमेश कुमार..."       Polly

320s    "हाँ, सही है"        ─── Submit application ──────────── Lambda
                               Generate VS-2026-XXXXX           DynamoDB

325s                        ─── Send SMS ────────────────────── SNS
                               Checklist + Reference ID

330s                        ─── "धन्यवाद रमेश जी!          ── Bedrock
                               आपका आवेदन जमा हो गया।"       Polly

335s    Call ends            ─── Session closed ─────────────── DynamoDB
                                                                CloudWatch
```

---

## 4. Security Architecture

```
┌─────────────────────────────────────────────────┐
│                  SECURITY LAYERS                  │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  TRANSPORT: TLS 1.3 (all connections)       │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  AUTHENTICATION:                             │ │
│  │  - API Key for WebSocket                     │ │
│  │  - Cognito for Admin dashboard               │ │
│  │  - Aadhaar OTP for user identity (Phase 2)   │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  DATA PROTECTION:                            │ │
│  │  - DynamoDB: Encryption at rest (AWS KMS)    │ │
│  │  - S3: Server-side encryption (SSE-S3)       │ │
│  │  - PII fields: Additional application-level  │ │
│  │    encryption (Aadhaar, bank details)         │ │
│  │  - Voice: NOT stored, transcribed & deleted   │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  PII MASKING (in logs/analytics):            │ │
│  │  - Aadhaar: XXXX-XXXX-1234                   │ │
│  │  - Phone: +91XXXXX6789                       │ │
│  │  - Bank A/C: XXXXXXXX5678                    │ │
│  │  - Name: Kept (non-sensitive for analytics)   │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  ACCESS CONTROL:                              │ │
│  │  - Lambda: Least-privilege IAM roles          │ │
│  │  - API Gateway: Usage plans + throttling      │ │
│  │  - DynamoDB: Fine-grained access              │ │
│  │  - Admin: RBAC via Cognito groups             │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  COMPLIANCE:                                  │ │
│  │  - IT Act 2000                                │ │
│  │  - Aadhaar Act 2016                           │ │
│  │  - Privacy notice at call start               │ │
│  │  - Explicit consent before data collection    │ │
│  │  - Data retention: 90 days post-resolution    │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## 5. Deployment Architecture

```
┌─────────────────────────── AWS Region: ap-south-1 (Mumbai) ───────────────────────┐
│                                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ CloudFront   │  │ API Gateway  │  │ API Gateway  │  │ Amazon Bedrock       │  │
│  │ (Frontend)   │  │ (REST)       │  │ (WebSocket)  │  │ (ap-south-1)         │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │ Claude 3 Haiku       │  │
│         │                 │                 │          │ Titan Embeddings      │  │
│         ▼                 ▼                 ▼          └──────────────────────┘  │
│  ┌──────────────┐  ┌──────────────────────────────┐                              │
│  │ S3 Bucket    │  │ Lambda Functions              │                              │
│  │ (Static Web) │  │                                │                              │
│  └──────────────┘  │  ┌────────────────────┐       │                              │
│                     │  │ orchestrator       │       │                              │
│  ┌──────────────┐  │  │ voice_processor    │       │                              │
│  │ S3 Bucket    │  │  │ ai_engine          │       │                              │
│  │ (Scheme Docs)│  │  │ notification       │       │                              │
│  └──────────────┘  │  │ admin              │       │                              │
│                     │  └────────────────────┘       │                              │
│  ┌──────────────┐  └──────────────────────────────┘                              │
│  │ DynamoDB     │                                                                 │
│  │ Tables:      │  ┌──────────────────────────────┐                              │
│  │ - sessions   │  │ Amazon OpenSearch Serverless  │                              │
│  │ - schemes    │  │ (Vector Store for RAG)        │                              │
│  │ - apps       │  └──────────────────────────────┘                              │
│  │ - connections│                                                                 │
│  └──────────────┘  ┌──────────────────────────────┐                              │
│                     │ Amazon Transcribe             │                              │
│  ┌──────────────┐  │ Amazon Polly                  │                              │
│  │ CloudWatch   │  │ Amazon Translate               │                              │
│  │ Logs+Metrics │  │ Amazon SNS                     │                              │
│  └──────────────┘  └──────────────────────────────┘                              │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**CDK Stack Breakdown:**

| Stack | Resources | Dependencies |
|-------|-----------|-------------|
| `DataStack` | DynamoDB tables, S3 buckets | None |
| `AIStack` | Bedrock KB, OpenSearch Serverless | DataStack |
| `VoiceStack` | Transcribe config, Polly config | None |
| `ApiStack` | Lambda functions, API Gateway (REST + WS) | DataStack, AIStack, VoiceStack |
| `FrontendStack` | S3 + CloudFront for web app | ApiStack |

---

## 6. Monitoring & Observability

```
┌─────────────────────────────────────────┐
│           CloudWatch Dashboard           │
│                                          │
│  ┌────────────┐  ┌────────────────────┐ │
│  │ Call Volume │  │ Success Rate       │ │
│  │ ████████   │  │ ████████████ 94%   │ │
│  │ ██████     │  │ ███████████        │ │
│  │ ████       │  │ ██████████         │ │
│  └────────────┘  └────────────────────┘ │
│                                          │
│  ┌────────────┐  ┌────────────────────┐ │
│  │ Avg Latency│  │ Error Rate         │ │
│  │   3.2s     │  │   2.1%             │ │
│  └────────────┘  └────────────────────┘ │
│                                          │
│  Key Metrics:                            │
│  - Calls per minute                      │
│  - STT accuracy (confidence scores)      │
│  - AI response latency (p50, p95, p99)   │
│  - Form completion rate                  │
│  - SMS delivery rate                     │
│  - Error rate by function                │
│  - Language distribution                 │
│  - Top requested schemes                 │
│                                          │
│  Alarms:                                 │
│  - Error rate > 5% → PagerDuty           │
│  - Latency p95 > 10s → Warning           │
│  - Lambda errors > 10/min → Critical     │
│  - DynamoDB throttling → Warning         │
└─────────────────────────────────────────┘
```
