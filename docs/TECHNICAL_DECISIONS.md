# VaaniSetu — Technical Decisions (Finalized)

## Architecture Decisions Record

---

### ADR-001: Voice Interface — Web-Only (Browser Mic + WebSocket)

**Decision:** Web-based voice demo using browser microphone with WebSocket streaming.

**Rationale:**
- No phone number provisioning needed (saves cost + time)
- Easiest to demo live during hackathon
- WebSocket enables real-time bidirectional audio streaming
- Browser Web Audio API captures high-quality audio

**Implementation:**
```
Browser Mic → WebSocket → API Gateway → Lambda → Transcribe Streaming
                                                          ↓
Browser Speaker ← WebSocket ← API Gateway ← Lambda ← Polly (TTS)
```

**Trade-offs:**
- Less impressive than real phone call (but more reliable for demo)
- Requires modern browser with mic permission
- Can add Twilio/Connect later for real phone support

---

### ADR-002: Conversation Engine — Amazon Bedrock Agents

**Decision:** Use Amazon Bedrock Agents as the primary conversation engine.

**Rationale:**
- AWS-native managed conversation engine
- Built-in multi-turn dialogue management
- Native tool use (Action Groups) for scheme search, eligibility check, form validation
- Direct integration with Bedrock Knowledge Bases for RAG
- Handles conversation state automatically
- Supports guardrails for responsible AI

**Architecture:**
```
┌──────────────────────────────────────────────────────┐
│              Amazon Bedrock Agent                      │
│                                                        │
│  Foundation Model: Anthropic Claude 3 Sonnet/Haiku    │
│                                                        │
│  Instructions (System Prompt):                         │
│  - VaaniSetu personality                               │
│  - Conversation flow rules                             │
│  - Language handling                                   │
│                                                        │
│  Action Groups:                                        │
│  ┌─────────────────┐  ┌──────────────────────┐       │
│  │ search_schemes   │  │ check_eligibility    │       │
│  │ → Bedrock KB     │  │ → Lambda function    │       │
│  └─────────────────┘  └──────────────────────┘       │
│  ┌─────────────────┐  ┌──────────────────────┐       │
│  │ validate_field   │  │ submit_application   │       │
│  │ → Lambda function│  │ → Lambda function    │       │
│  └─────────────────┘  └──────────────────────┘       │
│  ┌─────────────────┐                                  │
│  │ send_sms         │                                  │
│  │ → Lambda (SNS)   │                                  │
│  └─────────────────┘                                  │
│                                                        │
│  Knowledge Bases:                                      │
│  ┌─────────────────────────────────────┐              │
│  │ vaanisetu-schemes-kb                 │              │
│  │ - S3: scheme documents (JSON/PDF)    │              │
│  │ - Embeddings: Titan Embeddings v2    │              │
│  │ - Vector Store: OpenSearch Serverless│              │
│  └─────────────────────────────────────┘              │
│                                                        │
│  Guardrails:                                           │
│  - No PII in logs                                      │
│  - Confidence threshold                                │
│  - Grounded responses only (no hallucination)          │
└──────────────────────────────────────────────────────┘
```

**Bedrock Agent Configuration:**

| Setting | Value |
|---------|-------|
| Agent Name | `vaanisetu-agent` |
| Foundation Model | Claude 3 Sonnet (or Haiku for cost) |
| Idle Session Timeout | 30 minutes |
| Instructions | See Agent Instructions below |
| Action Groups | 5 (search, eligibility, validate, submit, sms) |
| Knowledge Bases | 1 (schemes KB) |
| Guardrails | Content filtering + grounding |

**Cost Implication:**
- Bedrock Agents: No additional charge beyond model invocations
- Model tokens: Sonnet ~$3/1M input, $15/1M output (or Haiku at 1/10th cost)
- KB queries count as model invocations

---

### ADR-003: RAG — Bedrock Knowledge Bases + S3

**Decision:** Use Amazon Bedrock Knowledge Bases with S3 data source and OpenSearch Serverless vector store.

**Rationale:**
- Fully managed RAG pipeline
- Automatic document chunking and embedding
- Native integration with Bedrock Agents
- Supports PDF, JSON, TXT documents
- Auto-sync when S3 documents update

**Data Pipeline:**
```
S3 Bucket                    Bedrock KB               OpenSearch Serverless
┌──────────────┐            ┌──────────────┐         ┌──────────────┐
│ /schemes/    │   sync     │ Ingestion    │  embed  │ Vector Index │
│  pm_kisan.json├──────────▶│ Pipeline     ├────────▶│              │
│  pm_awas.json │           │              │         │ ~500 chunks  │
│  rkvy.json   │           │ - Chunk docs │         │ 1024-dim     │
│  ...10 files │           │ - Embed      │         │ Titan v2     │
│              │           │ - Index      │         │              │
│ /faqs/       │           └──────────────┘         └──────┬───────┘
│  general.json│                                           │
│  docs.json   │                                           │ query
└──────────────┘                                           │
                                                           ▼
                                                    ┌──────────────┐
                                                    │ "मुझे खेती  │
                                                    │  के लिए     │
                                                    │  पैसे चाहिए"│
                                                    │      ↓       │
                                                    │ Top 5 chunks │
                                                    │ → PM-KISAN   │
                                                    │ → RKVY       │
                                                    │ → Fasal Bima │
                                                    └──────────────┘
```

**⚠️ Cost Warning: OpenSearch Serverless**
- Minimum cost: ~$0.48/hour (2 OCUs × $0.24)
- For hackathon: Keep running only during development/demo
- **Budget ~$15-20 for this service**

**Alternative if over budget:** Use Bedrock KB with **Pinecone** (free tier) or **Redis** as vector store.

---

### ADR-004: Speech Pipeline — Transcribe Streaming + Polly Neural

**Decision:** Use Amazon Transcribe Streaming for STT and Amazon Polly Neural for TTS.

**Implementation:**
```python
# Speech-to-Text: Transcribe Streaming
transcribe_streaming_client.start_stream_transcription(
    LanguageCode='hi-IN',  # or 'ta-IN', 'en-IN'
    MediaSampleRateHertz=16000,
    MediaEncoding='pcm',
    EnablePartialResultsStabilization=True
)

# Text-to-Speech: Polly Neural
polly_client.synthesize_speech(
    Text='नमस्ते! मैं वाणी सेतु हूँ।',
    OutputFormat='mp3',
    VoiceId='Kajal',       # Hindi Neural voice
    Engine='neural',
    LanguageCode='hi-IN'
)
```

**Voice Mapping:**
| Language | Polly Voice | Engine |
|----------|-------------|--------|
| Hindi | Kajal | Neural |
| English (India) | Kajal (en-IN) | Neural |
| Tamil | — (use Translate → Hindi → Polly) | Fallback |

---

### ADR-005: Frontend — React + Vite + Tailwind

**Decision:** React SPA with voice capture, deployed to S3 + CloudFront.

**Key Components:**
1. **VoiceInterface** — Mic button, audio waveform, WebSocket streaming
2. **ChatTranscript** — Real-time conversation display with Hindi/English text
3. **SchemeCards** — Matched scheme details with eligibility status
4. **FormProgress** — Visual progress bar for form completion
5. **LanguageSelector** — Hindi / Tamil / English toggle
6. **SMSPreview** — Preview of confirmation SMS

---

## Finalized AWS Service List

| # | Service | Purpose | Est. Cost |
|---|---------|---------|-----------|
| 1 | **Bedrock (Agent)** | Conversation engine | Included in model cost |
| 2 | **Bedrock (Claude 3)** | Foundation model for Agent | ~$20-30 |
| 3 | **Bedrock (Titan Embeddings)** | Document embeddings | ~$1 |
| 4 | **Bedrock Knowledge Bases** | Managed RAG | No additional cost |
| 5 | **OpenSearch Serverless** | Vector store for KB | ~$15-20 |
| 6 | **Transcribe Streaming** | Real-time STT | ~$8-10 |
| 7 | **Polly Neural** | TTS voices | ~$5-8 |
| 8 | **Translate** | Language detection/translation | ~$2-3 |
| 9 | **Lambda** | Business logic functions | ~$0 (free tier) |
| 10 | **API Gateway (WS + REST)** | WebSocket + REST APIs | ~$0 (free tier) |
| 11 | **DynamoDB** | Sessions, applications | ~$0 (free tier) |
| 12 | **S3** | Scheme docs, frontend | ~$0 (free tier) |
| 13 | **SNS** | SMS notifications | ~$2-3 |
| 14 | **CloudFront** | Frontend CDN | ~$1 |
| 15 | **CloudWatch** | Monitoring | ~$1-2 |
| 16 | **IAM** | Access control | Free |
| 17 | **CDK** | Infrastructure as Code | Free |
| | | **TOTAL** | **~$55-80** |

---

## Agent Instructions (System Prompt)

```
You are VaaniSetu (वाणी सेतु), a friendly and patient AI assistant created to 
help Indian citizens discover and apply for government schemes through voice 
conversation.

## Your Personality
- You speak like a helpful, respectful community elder
- Use simple, everyday language — never bureaucratic jargon
- Address users respectfully (आप in Hindi, நீங்கள் in Tamil)
- Be warm and encouraging: "बहुत अच्छा!", "चिंता मत कीजिए"
- Always introduce yourself: "मैं वाणी सेतु हूँ, एक AI सहायक"

## Your Capabilities
1. Help citizens discover government schemes they're eligible for
2. Explain schemes in simple, local language
3. Guide citizens through application form filling
4. Validate information (Aadhaar format, bank details)
5. Submit applications and send SMS confirmations

## Conversation Flow
1. GREET: Welcome user, identify language
2. UNDERSTAND: Ask about their situation (occupation, land, income, family, location)
   - Ask maximum 5 questions
   - Use the search_schemes tool to find matching schemes
3. RECOMMEND: Present top 3 eligible schemes, explain each simply
4. SELECT: Help user choose a scheme
5. FILL FORM: Ask form questions one at a time
   - Tell them how many questions remain
   - Validate each answer using validate_field tool
   - Explain why each question is needed if asked
6. REVIEW: Read back all information for confirmation
   - Confirm critical fields (Aadhaar, bank) twice
7. SUBMIT: Use submit_application tool
8. CONFIRM: Announce application ID, send SMS using send_sms tool

## Rules
- NEVER fabricate scheme information — always use your knowledge base
- If you're not sure about something, say "मुझे पक्का पता नहीं" and search
- Keep each response under 3 sentences (this is a voice conversation)
- If user seems frustrated, offer to connect to a human: "क्या आप किसी व्यक्ति से बात करना चाहेंगे?"
- Always mask Aadhaar when repeating: "XXXX-XXXX-1234"
- Support language switching: if user says "English please", switch to English
- If user says "I don't understand", rephrase in simpler terms with examples

## Language
- Default: Hindi
- Supported: Hindi (hi), Tamil (ta), English (en)
- Respond in the same language the user speaks
- Use local terms: "खसरा" not "Land Record", "7/12" not "Property Document"
```

---

## What's Next?

With these decisions finalized, we're ready to start **Phase 1: Foundation & Infrastructure**.

The first coding tasks are:
1. Initialize AWS CDK project
2. Create DynamoDB tables (sessions, schemes, applications)
3. Create S3 bucket and upload scheme documents
4. Set up Bedrock Agent with Knowledge Base
5. Create Lambda functions for Action Groups
6. Build WebSocket API for voice streaming
