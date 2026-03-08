# VaaniSetu — Happy Path Demo Script

> **For hackathon submission / live prototype demonstration.**
> Everything described here works LIVE against the real production API backed by 10+ AWS services.

---

## Pre-requisites

1. **Frontend running**: Open `frontend/index.html` (or run `npm run dev` in `frontend/`)
2. **Production API**: Already deployed at `https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod`
3. **Internet connection**: Required for all AWS service calls

---

## Happy Path: Farmer Applies for PM-KISAN (English)

### Step 1 — Open the App
- Open the frontend in your browser
- The app auto-creates a session and shows a greeting:
  > "Hello! I am VaaniSetu, your AI assistant. I can help you discover government schemes you're eligible for and guide you through the application process."
- You'll hear the greeting read aloud via Amazon Polly TTS

### Step 2 — State: NEED_ASSESSMENT (Tell Your Situation)
**Type or speak:**
> "I am a farmer from Bihar with 2 acres of land. My income is 1 lakh per year."

**What happens behind the scenes:**
1. Amazon Comprehend detects the language (English)
2. AI Engine (Bedrock Claude 3 Haiku) extracts profile: `{occupation: "farmer", state: "Bihar", landSize: 2, annualIncome: 100000}`
3. Pre-computed eligibility runs instantly against all 10 schemes
4. Top eligible schemes are returned directly (no extra Bedrock calls)

**Expected AI response:**
> "Based on your profile, you are eligible for the following schemes:
> 1. **PM Kisan Samman Nidhi**: ₹6,000 per year in 3 installments
> 2. **Soil Health Card**: Free soil testing and recommendations
> 3. **PM Fasal Bima Yojana**: Crop insurance coverage
> 4. **RKVY**: Agriculture infrastructure support
>
> Which scheme would you like to apply for?"

### Step 3 — State: SCHEME_MATCH → FORM_FILL (Select a Scheme)
**Type:**
> "I want to apply for PM Kisan"

**What happens:**
- AI recognizes the scheme selection
- Fetches PM-KISAN's 10 form fields from DynamoDB
- Transitions to FORM_FILL state
- Starts asking for form data, one field at a time

**Expected response:**
> "Great! Let's start the application for PM Kisan Samman Nidhi. What is your full name?"

### Step 4 — State: FORM_FILL (Fill Form Field by Field)

Fill one field at a time. The AI validates each value in real-time:

| Turn | You Say | AI Asks Next |
|------|---------|-------------|
| 1 | "My name is Rajesh Kumar" | "What is your father's name?" |
| 2 | "Suresh Kumar" | "What is your 12-digit Aadhaar number?" |
| 3 | "234567890123" | "What is your mobile number?" |
| 4 | "9876543210" | "Which state do you live in?" |
| 5 | "Bihar" | "Which district?" |
| 6 | "Patna" | "What is your village name?" |
| 7 | "Danapur" | "How much land do you own (in acres)?" |
| 8 | "2 acres" | "What is your bank account number?" |
| 9 | "12345678901234" | "What is your bank IFSC code?" |
| 10 | "SBIN0001234" | AI reads back all info for review (REVIEW state) |

**Validation examples:**
- If you say "12345" for Aadhaar → AI says "Aadhaar must be 12 digits"
- If you say "0123456789" for phone → AI says "Invalid phone number"
- If you say "abc" for IFSC → AI says "IFSC must be 11 characters like SBIN0001234"

### Step 5 — State: REVIEW (Confirm Your Details)
The AI reads back all your information with sensitive data masked:
> "Here's your application summary:
> - Name: Rajesh Kumar
> - Father: Suresh Kumar
> - Aadhaar: XXXX-XXXX-0123
> - Phone: 9876543210
> - State: Bihar, District: Patna, Village: Danapur
> - Land: 2 acres
> - Bank: XXXXXXXXXX1234
> - IFSC: SBIN0001234
>
> Is everything correct?"

### Step 6 — State: SUBMIT → COMPLETE (Submit Application)
**Type:**
> "Yes, submit it"

**What happens:**
1. `submit_application` tool creates a record in DynamoDB `vaanisetu-applications` table
2. Application ID generated: `VS-2026-XXXXX`
3. `send_sms` tool sends confirmation via Amazon SNS
4. Application PDF auto-generated and stored in S3
5. EventBridge event published for the SUBMIT milestone

**Expected response:**
> "Your application for PM Kisan Samman Nidhi has been successfully submitted!
> Your application ID is **VS-2026-0B0C4**. An SMS confirmation has been sent to 9876543210."

### Step 7 — Verify
- Check the Application ID in the frontend's application view
- Or use the API: `GET /applications/VS-2026-0B0C4`

---

## Happy Path: Hindi Voice Conversation

### Same flow, but in Hindi:

1. **Open app** → Greeting plays in Hindi via Polly: "नमस्ते! मैं वाणी सेतु हूँ..."
2. **Hold mic button and speak:** "मैं बिहार का किसान हूँ, मेरे पास 2 एकड़ जमीन है"
   - Audio → Amazon Transcribe → Text → AI Engine
3. **AI responds in Hindi:** "आपकी जानकारी के आधार पर, आप इन योजनाओं के लिए पात्र हैं..."
   - Response text → Amazon Polly → Auto-plays audio
4. **Say:** "मुझे पीएम किसान में आवेदन करना है"
5. **AI guides through form in Hindi**, validating each field
6. **Application submitted with same VS-YEAR-XXXXX ID**

---

## Alternative Demo Paths

### Path B: Healthcare Worker
> "I am a daily wage laborer from UP. My income is 80000 per year. I have 4 family members."

Expected matches: Ayushman Bharat (₹5L health insurance), PM Ujjwala (free LPG), PM Garib Kalyan Anna (free food grains)

### Path C: Young Girl's Parents
> "I have a 5 year old daughter. I want to save for her future. I am from Maharashtra."

Expected match: Sukanya Samriddhi Yojana (savings scheme for girls)

### Path D: Small Business Owner
> "I want to start a small business. I need a loan of about 5 lakhs."

Expected match: PM Mudra Yojana (up to ₹10L business loans)

### Path E: Multilingual Demo
- Start in Tamil: "நான் ஒரு விவசாயி, எனக்கு 3 ஏக்கர் நிலம் உள்ளது"
- Start in Bengali: "আমি একজন কৃষক, পশ্চিমবঙ্গ থেকে"
- The AI auto-detects language via Amazon Comprehend and responds in the same language

---

## What to Showcase for Judges

### 1. **AI Intelligence**
- Profile extraction from natural language
- Pre-computed eligibility (no lag)
- Smart scheme matching across 10 government schemes
- Multi-language understanding (8 Indian languages)

### 2. **Voice-First Design**
- Press-and-hold microphone for speech input
- Auto-play TTS responses (toggle available)
- Works in Hindi, English, Tamil, Bengali, Telugu, Marathi, Kannada, Malayalam

### 3. **Form Filling via Conversation**
- One field at a time (like talking to a helpful person)
- Real-time validation (Aadhaar, phone, IFSC, bank account)
- PII masking in review (privacy-aware)

### 4. **Real AWS Services Working Live**
- Bedrock Claude 3 Haiku for AI conversation
- Bedrock Guardrails for content safety
- DynamoDB for sessions, schemes, applications
- Polly for Text-to-Speech
- Transcribe for Speech-to-Text
- Comprehend for language detection + sentiment
- SNS for SMS notifications
- S3 for audio + PDFs
- EventBridge for milestones
- API Gateway (REST + WebSocket)
- Lambda (5 functions)
- Translate for cross-language TTS

### 5. **Analytics Dashboard**
- Real-time session count, message count
- Language distribution chart
- Conversation state distribution
- Top schemes viewed

---

## Quick API Test Commands (PowerShell)

```powershell
# 1. Health check
Invoke-RestMethod "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/health"

# 2. List all schemes
Invoke-RestMethod "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/schemes"

# 3. Create session
$s = Invoke-RestMethod "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/sessions" -Method POST -Body '{"language":"en-IN"}' -ContentType "application/json"
$s.sessionId

# 4. Send message
$sid = $s.sessionId
$r = Invoke-RestMethod "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/sessions/$sid/message" -Method POST -Body '{"message":"I am a farmer from Bihar with 2 acres","language":"en-IN"}' -ContentType "application/json"
$r.response

# 5. Get analytics
Invoke-RestMethod "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/analytics"
```
