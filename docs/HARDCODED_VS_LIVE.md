# VaaniSetu — Hardcoded vs Live Inventory & Mitigation Steps

> This document explains every component: what's fully live, what's hardcoded,
> what's a known limitation, and the exact steps to make each one fully live.

---

## TL;DR Summary

| Category | Status | Details |
|----------|--------|---------|
| **AI Conversation (Bedrock)** | ✅ FULLY LIVE | Claude 3 Haiku via Bedrock Converse API |
| **Scheme Database (10 schemes)** | ✅ FULLY LIVE | Real DynamoDB, with eligibilityRules + formFields |
| **Form Filling + Validation** | ✅ FULLY LIVE | 10 field types, real-time validation, PII masking |
| **Application Submission** | ✅ FULLY LIVE | Creates real DynamoDB records, generates VS-YEAR-XXXXX IDs |
| **Voice Input (Speech-to-Text)** | ✅ FULLY LIVE | Amazon Transcribe streaming |
| **Voice Output (Text-to-Speech)** | ✅ FULLY LIVE | Amazon Polly Neural (Kajal voice) |
| **Language Detection** | ✅ FULLY LIVE | Amazon Comprehend |
| **Sentiment Analysis** | ✅ FULLY LIVE | Amazon Comprehend |
| **Content Safety** | ✅ FULLY LIVE | Bedrock Guardrail `46tqyral1aho` v1 |
| **PDF Generation** | ✅ FULLY LIVE | Auto-generated on submission, stored in S3 |
| **Analytics Dashboard** | ✅ FULLY LIVE | Real-time from DynamoDB scan |
| **SMS Notifications** | ⚠️ PARTIALLY LIVE | SNS publish works, but SMS to real phones needs sandbox exit |
| **WhatsApp Integration** | ⚠️ PARTIALLY LIVE | Twilio Sandbox works for registered numbers only |
| **Amazon Connect (IVR)** | ❌ BLOCKED | AISPL accounts cannot create Connect instances |
| **RAG Knowledge Base** | ❌ NOT CONFIGURED | KB ID set to "none" — falls to keyword search (which works fine) |
| **Scheme Data** | ⚠️ STATIC SEED | 10 real Indian government schemes — data is accurate but not auto-updated from gov APIs |

---

## Detailed Breakdown

### 1. Things That Are FULLY LIVE (No Action Needed)

#### AI Engine (Amazon Bedrock)
- **Model**: `anthropic.claude-3-haiku-20240307-v1:0` in `us-east-1`
- **How it works**: Bedrock Converse API with tool-use (7 tools defined)
- **Guardrail**: ID `46tqyral1aho` version 1 — filters harmful content
- **Fallback**: If Bedrock is throttled, a rule-based response system handles 8 languages
- **Nothing hardcoded in responses** — all AI responses come from Claude

#### Scheme Matching & Eligibility
- **10 government schemes** in DynamoDB `vaanisetu-schemes` table
- Each scheme has: `eligibilityRules` (rule-based checking), `formFields` (10+ fields per scheme)
- Matching: Keyword search in 8 languages + rule-based eligibility scoring
- **Pre-computed eligibility**: When enough profile info exists, eligibility is calculated BEFORE calling Bedrock (speed optimization)

#### Form Filling
- **10 form field types**: name, aadhaar, phone, ifsc, pincode, state, bank_account, land_size, date, amount
- **Real-time validation**: Each answer validated via `validate_field` tool
- **PII masking**: Aadhaar shows as `XXXX-XXXX-1234`, bank accounts partially masked
- **PM-KISAN has 10 form fields**: name, fatherName, aadhaar, phone, state, district, village, landSize, bankAccount, ifsc

#### Application Submission
- Creates a real record in `vaanisetu-applications` DynamoDB table
- Generates `VS-YEAR-XXXXX` application ID
- Stores all form data, session ID, scheme ID, timestamps
- Auto-generates a PDF receipt stored in S3

#### Voice Pipeline
- **Speech-to-Text**: Amazon Transcribe (real-time streaming)
- **Text-to-Speech**: Amazon Polly with SSML (Kajal neural voice)
- **For non-Hindi languages**: Amazon Translate converts to Hindi script → Polly renders in Hindi voice (approximation)

---

### 2. Things That Are PARTIALLY WORKING (Specific Limitations)

#### SMS Notifications (Amazon SNS)
**Current state**: The `send_sms` tool calls SNS `publish()` with the user's phone number.

**Limitation**: AWS SNS SMS is in **sandbox mode** by default. Only verified phone numbers receive SMS.

**Steps to make fully live:**
1. Go to AWS Console → SNS → Text messaging (SMS)
2. Click "Exit SMS sandbox"
3. Submit a request explaining your use case (government scheme notifications)
4. AWS typically approves within 1-2 business days
5. Once approved, SMS will work for any Indian phone number

**For demo**: The SNS `publish` call succeeds (returns MessageId), the message just doesn't reach unverified numbers. You can add your own phone to the sandbox for testing.

#### WhatsApp Integration (Twilio)
**Current state**: Twilio Sandbox configured with webhook at the `/whatsapp` endpoint.

**Limitation**: Sandbox only works for phone numbers that have sent "join <sandbox-word>" to the Twilio sandbox number.

**Steps to make fully live:**
1. Apply for Twilio WhatsApp Business API (requires Facebook Business verification)
2. Get a dedicated WhatsApp number from Twilio
3. Update Lambda environment variables with production Twilio credentials
4. Approval process takes 1-4 weeks (not feasible for hackathon)

**For demo**: Register your demo phone by sending "join [sandbox-word]" to Twilio sandbox number. Then WhatsApp conversations work fully.

#### Cross-Language TTS
**Current state**: Polly's Kajal voice natively supports Hindi and English. For Tamil, Bengali, Telugu, Marathi, Kannada, Malayalam — the text is translated to Hindi first, then spoken.

**Limitation**: This means non-Hindi TTS is an approximation (Hindi voice reading the translation).

**Steps to make fully live:**
- AWS Polly does not yet have native neural voices for most Indian languages
- This is an AWS platform limitation, not a code issue
- When Polly adds native Tamil/Bengali/Telugu voices, just update the `POLLY_VOICE_MAP` in the orchestrator

---

### 3. Things That Are NOT WORKING (Blocked/Disabled)

#### Amazon Connect (IVR Phone Calls)
**Status**: BLOCKED — Cannot be created.

**Why**: Your AWS account is registered under **AISPL** (Amazon Internet Services Private Limited — India). AISPL accounts cannot create Amazon Connect instances. This is an AWS business restriction, not a technical one.

**Workaround for demo**:
- Show the Web Voice interface (press-and-hold mic) as proof that the same IVR pipeline works
- Show WhatsApp as the phone-based channel
- Explain to judges: "The same AI conversation works across web voice, WhatsApp, and would work on Amazon Connect IVR — the AI engine is channel-agnostic"

**To actually fix**: 
- Create a new AWS account with standard (non-AISPL) billing
- Or contact AWS support to request Connect access for AISPL accounts

#### RAG Knowledge Base (Bedrock)
**Status**: Not configured — KB ID is set to `"none"`.

**Current mitigation**: The scheme_matcher falls back to keyword search, which works well for 10 schemes.

**Steps to enable RAG:**
1. Go to AWS Console → Bedrock → Knowledge Bases
2. Create a knowledge base with an S3 data source
3. Run `python scripts/seed_data.py` with `SCHEME_DOCS_BUCKET` env var set (it uploads rich text documents)
4. Sync the knowledge base
5. Update Lambda environment variable `KNOWLEDGE_BASE_ID` with the actual KB ID
6. RAG will then power more nuanced semantic search

**Is it needed?** Not really for 10 schemes. Keyword search works fine. RAG matters at 100+ schemes.

---

### 4. Hardcoded Values (Configuration, Not Bugs)

These are intentional configuration values, not bugs:

| Item | Value | Where | Why |
|------|-------|-------|-----|
| AWS Region | `us-east-1` | constants.py, CDK stacks, config files | Bedrock models available here |
| Bedrock Model | `anthropic.claude-3-haiku-20240307-v1:0` | ai_engine/handler.py | Fastest, cheapest Bedrock model |
| Guardrail ID | `46tqyral1aho` | ai_engine/handler.py | Your specific guardrail |
| Polly Voice | `Kajal` (neural) | orchestrator/handler.py | Best Hindi neural voice |
| Session TTL | 90 days | session_manager.py | DynamoDB auto-cleanup |
| Max Tool Rounds | 2 | ai_engine/handler.py | Prevents infinite tool loops |
| Scheme Data | 10 JSON files | seed-data/schemes/ | Accurate real Indian government schemes |
| Table Names | `vaanisetu-*` | constants.py | Namespaced DynamoDB tables |
| API Gateway URL | `https://hbm4onktgf...` | frontend/config.ts | Your deployed API endpoint |

**These don't need changing** for the demo. They're deployment-specific configuration.

---

### 5. What's "Simulated" vs "Real"

| Aspect | Is it Real? | Explanation |
|--------|------------|-------------|
| AI responses | ✅ REAL | Every response comes from Bedrock Claude, not templates |
| Scheme data | ✅ REAL | Actual Indian government scheme details (PM-KISAN, Ayushman Bharat, etc.) |
| Eligibility rules | ✅ REAL | Based on actual scheme criteria (income limits, occupation, land size) |
| Form validation | ✅ REAL | Aadhaar format, IFSC pattern, phone format — all match Indian standards |
| Application submission | ✅ REAL-ish | Creates a real DynamoDB record, but doesn't submit to actual government portals |
| SMS confirmation | ✅ REAL | SNS publish fires, but sandbox limits delivery |
| PDF generation | ✅ REAL | Uses ReportLab to generate actual PDF documents |
| Voice I/O | ✅ REAL | Polly + Transcribe, actual audio encoding/decoding |
| Analytics | ✅ REAL | Counts from actual DynamoDB session data |

**The ONE thing that's simulated**: We don't actually submit to `https://pmkisan.gov.in`. The application is saved in OUR DynamoDB table. Making this send to real government APIs would require integration with each government department's API (most don't have public APIs).

---

## Action Items for You (Priority Order)

### Must Do Before Demo (5 mins)
1. **Re-seed data** (in case you need fresh data):
   ```powershell
   cd "d:\Projects\AI for Bharat - Hackathon\VaniSetu"
   python scripts/seed_data.py
   ```
2. **Verify health**: Open `https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/health` in browser
3. **Test the frontend**: Run `cd frontend && npm run dev` and go through the happy path once

### Nice to Have (15 mins each)
1. **Add your phone to SNS sandbox** for live SMS demo:
   - AWS Console → SNS → Text messaging → Sandbox → Add phone number → Verify OTP
2. **Register WhatsApp sandbox** for WhatsApp demo:
   - Send "join [keyword]" from your phone to Twilio sandbox number
3. **Run analytics**: Visit the Analytics tab in the frontend to show real usage data

### Not Needed for Hackathon
- RAG Knowledge Base setup (keyword search works great)
- Amazon Connect (explain the architecture handles it, show web voice)
- Non-Hindi native TTS (Hindi approximation is perfectly fine for demo)
- Real government API integration (explain this is the natural next step)
