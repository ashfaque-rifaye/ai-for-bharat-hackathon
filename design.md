# VaaniSetu - Design Document

## Architecture Diagram

### Primary Architecture (Vertical Layout)
![VaaniSetu AWS Architecture - Final](./architecture-final.png)

### Alternative View (Horizontal Layout)
![VaaniSetu AWS Architecture - Horizontal](./architecture-horizontal.png)

*Professional AWS architecture diagrams showing all components, numbered data flows (1-9 for main conversation flow), and color-coded layers. See [architecture-diagram.md](./architecture-diagram.md) for additional views and detailed flow descriptions.*

**Legend:**
- 🔵 **Blue**: Voice Processing Layer (Connect, Transcribe, Polly)
- 🟣 **Purple**: AI Core (Lambda, Bedrock, OpenSearch)
- 🟢 **Green**: Integration Layer (API Gateway, SNS, EventBridge)
- 🔴 **Red**: External Government APIs (Aadhaar, eDistrict)
- 🟠 **Orange**: Data Storage (DynamoDB, S3, RDS)
- ⚫ **Gray**: Monitoring & Security (CloudWatch, KMS)

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

VaaniSetu follows a microservices architecture deployed on AWS, consisting of four primary layers:

```
┌─────────────────────────────────────────────────────────────┐
│                        USER LAYER                            │
│  Rural Citizens → Basic Mobile Phones → Toll-Free Number    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      VOICE LAYER (AWS)                       │
│  Amazon Connect → Transcribe → Polly → Contact Flows        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    AI ORCHESTRATION LAYER                    │
│  Amazon Bedrock (Claude Sonnet 4) → Lambda Functions        │
│  Titan Embeddings → Vector Search → DynamoDB                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    INTEGRATION LAYER                         │
│  API Gateway → Lambda → External APIs (Aadhaar, eDistrict)  │
│  SNS (SMS) → EventBridge (Scheduling) → Step Functions      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                             │
│  DynamoDB → S3 → RDS Aurora → OpenSearch → CloudWatch       │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **Voice-First**: Optimized for phone calls, not screen interactions
2. **Serverless**: Auto-scaling, pay-per-use, minimal operational overhead
3. **Resilient**: Graceful degradation, human fallback, retry mechanisms
4. **Secure**: Encryption, PII masking, compliance with Indian data laws
5. **Observable**: Comprehensive logging, monitoring, and analytics

---

## 2. Component Design

### 2.1 Voice Layer


#### 2.1.1 Amazon Connect (Call Management)

**Purpose**: Handle incoming calls, route to appropriate flows, manage call state

**Configuration**:
- **Instance**: VaaniSetu-Production (US East 1 for low latency to India)
- **Phone Number**: Toll-free 1800-XXX-XXXX (provisioned via AWS or telecom partner)
- **Contact Flows**:
  - `MainFlow`: Initial greeting, language detection, route to AI
  - `FallbackFlow`: Human agent escalation when AI fails
  - `StatusCheckFlow`: Quick status lookup without full conversation
  - `DisconnectFlow`: Cleanup and logging on call end

**Key Features**:
- **Queue Management**: Max wait time 2 minutes, callback option
- **Call Recording**: Enabled for quality assurance (with consent)
- **Metrics**: Real-time dashboard for call volume, wait times, abandonment rate

**Integration Points**:
- Lambda functions for custom logic (language detection, session management)
- Lex bot for simple DTMF-based navigation (fallback)
- CloudWatch for logging and monitoring

#### 2.1.2 Amazon Transcribe (Speech-to-Text)

**Purpose**: Convert user speech to text in real-time

**Configuration**:
- **Streaming API**: Real-time transcription with < 2 second latency
- **Languages**: 12 Indian languages (hi-IN, ta-IN, te-IN, bn-IN, mr-IN, gu-IN, kn-IN, ml-IN, pa-IN, or-IN, as-IN, ur-IN)
- **Custom Vocabulary**: 5,000+ domain-specific terms (scheme names, document types, agricultural terms)
- **Profanity Filtering**: Disabled (may interfere with legitimate words)

**Accuracy Optimization**:
- **Acoustic Model**: Fine-tuned on rural Indian speech patterns
- **Language Model**: Trained on government scheme documents and FAQs
- **Post-Processing**: Custom Lambda for spell correction and entity normalization

**Output Format**:
```json
{
  "transcript": "मुझे बीज के लिए पैसा चाहिए",
  "confidence": 0.92,
  "language": "hi-IN",
  "alternatives": [
    {"transcript": "मुझे बीच के लिए पैसा चाहिए", "confidence": 0.78}
  ]
}
```

#### 2.1.3 Amazon Polly (Text-to-Speech)

**Purpose**: Convert AI responses to natural-sounding speech

**Configuration**:
- **Voice Engine**: Neural TTS for natural prosody
- **Voices**: 
  - Hindi: Aditi (female), Kajal (female)
  - Tamil: Not available natively (use custom voice via Polly Brand Voice)
  - Bengali: Not available natively (use custom voice)
- **SSML Support**: For emphasis, pauses, and pronunciation control

**Voice Customization**:
- **Speaking Rate**: 0.9x (slightly slower for clarity)
- **Pitch**: Default (neutral)
- **Pauses**: 500ms after questions, 300ms after statements
- **Emphasis**: Key information (amounts, dates, document names)

**Example SSML**:
```xml
<speak>
  आपको <emphasis level="strong">₹3,000</emphasis> मिल सकते हैं।
  <break time="500ms"/>
  क्या मैं आपकी मदद से फॉर्म भरूं?
</speak>
```

---

### 2.2 AI Orchestration Layer

#### 2.2.1 Amazon Bedrock (Conversational AI)

**Purpose**: Core conversational intelligence, intent understanding, response generation

**Model Selection**:
- **Primary**: Claude Sonnet 4 (Anthropic)
  - Reasoning: Best multilingual support, strong instruction following, low hallucination
  - Context Window: 200K tokens (sufficient for long conversations + scheme database)
  - Cost: $3 per 1M input tokens, $15 per 1M output tokens
- **Fallback**: Claude Haiku (faster, cheaper for simple queries)

**Prompt Engineering**:

**System Prompt**:
```
You are VaaniSetu, an AI assistant helping rural Indian citizens access government schemes.

ROLE:
- Speak in simple, conversational language
- Be patient and empathetic
- Explain bureaucratic terms in local context
- Never use English unless user requests

CONSTRAINTS:
- Only discuss government schemes in your database
- If unsure, say "I'm not certain, let me connect you to an expert"
- Always confirm critical information (Aadhaar, bank details)
- Respect user's time (aim for 8-10 minute calls)

CONVERSATION FLOW:
1. Greet warmly, ask about their need
2. Match to eligible schemes (max 3 options)
3. Explain eligibility and benefits clearly
4. Guide through form filling with context for each question
5. Review all information before submission
6. Provide clear next steps

TONE:
- Friendly but professional
- Use "आप" (formal you) in Hindi
- Avoid jargon (say "ज़मीन का कागज़" not "भूमि अभिलेख")
```

**Few-Shot Examples** (included in prompt):
```
User: "मुझे बीज के लिए पैसा चाहिए"
Assistant: "ठीक है। आपके पास कितनी ज़मीन है?"

User: "गांव वाला बैंक"
Assistant: "ठीक है, ग्रामीण बैंक। शाखा का नाम क्या है?"

User: "ज़मीन का कागज़ क्या होता है?"
Assistant: "यह वो कागज़ है जिसपर लिखा है कि ज़मीन आपकी है। इसे 'खसरा' या '7/12' भी कहते हैं।"
```

**Inference Configuration**:
```json
{
  "temperature": 0.3,
  "top_p": 0.9,
  "max_tokens": 500,
  "stop_sequences": ["User:", "Human:"]
}
```

#### 2.2.2 Semantic Search (Titan Embeddings + OpenSearch)

**Purpose**: Match user intent to relevant schemes from 250+ options

**Architecture**:
1. **Embedding Generation**: Amazon Titan Embeddings v2
   - Input: User query + conversation context
   - Output: 1024-dimensional vector
2. **Vector Store**: Amazon OpenSearch Service with k-NN plugin
   - Index: `schemes-index` with 250 scheme documents
   - Search: Cosine similarity, return top 5 matches
3. **Re-ranking**: Claude Sonnet evaluates top 5 for final selection

**Scheme Document Structure**:
```json
{
  "scheme_id": "RKVY-2024",
  "name": "Rashtriya Krishi Vikas Yojana",
  "name_hi": "राष्ट्रीय कृषि विकास योजना",
  "description": "Agricultural development scheme for farmers",
  "keywords": ["agriculture", "farming", "seeds", "fertilizer", "subsidy"],
  "keywords_hi": ["कृषि", "खेती", "बीज", "खाद", "सब्सिडी"],
  "eligibility": {
    "land_size": {"min": 0, "max": 5, "unit": "acres"},
    "income": {"max": 200000, "unit": "INR/year"},
    "category": ["farmer", "agricultural_laborer"]
  },
  "benefits": {
    "amount": 3000,
    "type": "one-time",
    "currency": "INR"
  },
  "required_documents": ["aadhaar", "land_record", "bank_passbook"],
  "embedding": [0.123, -0.456, ...] // 1024-dim vector
}
```

**Search Query Example**:
```python
user_query = "मुझे बीज के लिए पैसा चाहिए"
context = "User has 2 acres of land, farmer"
combined_query = f"{user_query} {context}"

# Generate embedding
embedding = bedrock.invoke_titan_embeddings(combined_query)

# Search OpenSearch
results = opensearch.search(
    index="schemes-index",
    body={
        "query": {
            "knn": {
                "embedding": {
                    "vector": embedding,
                    "k": 5
                }
            }
        }
    }
)

# Re-rank with Claude
final_scheme = bedrock.invoke_claude(
    prompt=f"User needs: {user_query}. Top matches: {results}. Which is best?"
)
```

#### 2.2.3 Conversation State Management

**Purpose**: Track conversation context, form progress, user data across turns

**Storage**: Amazon DynamoDB

**Session Schema**:
```json
{
  "session_id": "uuid-1234",
  "phone_number": "+91XXXXXXXXXX",
  "language": "hi-IN",
  "start_time": "2026-02-08T10:30:00Z",
  "state": "form_filling", // greeting, scheme_selection, form_filling, review, completed
  "conversation_history": [
    {"role": "assistant", "content": "नमस्ते! मैं वाणीसेतु हूं।", "timestamp": "..."},
    {"role": "user", "content": "मुझे बीज के लिए पैसा चाहिए", "timestamp": "..."}
  ],
  "selected_scheme": "RKVY-2024",
  "form_data": {
    "name": "Lakshmi Devi",
    "aadhaar": "XXXX-XXXX-1234",
    "land_size": 2,
    "bank_name": "Gramin Bank",
    "bank_branch": "Rajpur"
  },
  "form_progress": {
    "total_fields": 10,
    "completed_fields": 7,
    "current_field": "bank_account_number"
  },
  "metadata": {
    "call_duration": 480, // seconds
    "transcription_confidence_avg": 0.91,
    "ai_confidence_avg": 0.87
  }
}
```

**TTL**: Sessions expire after 24 hours of inactivity

---

### 2.3 Integration Layer

#### 2.3.1 Aadhaar Verification (UIDAI API)

**Purpose**: Verify user identity before form submission

**API**: UIDAI Authentication API (eKYC)

**Flow**:
1. User provides Aadhaar number (spoken, transcribed)
2. System validates format (12 digits, checksum)
3. OTP request sent to Aadhaar-linked mobile
4. User speaks OTP (6 digits)
5. System verifies OTP with UIDAI
6. On success, fetch basic details (name, DOB, address)

**Implementation**:
```python
# Lambda function: aadhaar-verification
import boto3
import requests

def verify_aadhaar(aadhaar_number, otp):
    # Call UIDAI API
    response = requests.post(
        "https://api.uidai.gov.in/auth/otp/verify",
        headers={"Authorization": f"Bearer {get_uidai_token()}"},
        json={
            "aadhaar": aadhaar_number,
            "otp": otp,
            "consent": "Y"
        }
    )
    
    if response.status_code == 200:
        # Store verified data in DynamoDB
        dynamodb.put_item(
            TableName="verified-users",
            Item={
                "aadhaar": aadhaar_number,
                "name": response.json()["name"],
                "verified_at": datetime.now().isoformat()
            }
        )
        return {"success": True, "data": response.json()}
    else:
        return {"success": False, "error": "Verification failed"}
```

**Error Handling**:
- Invalid Aadhaar: "यह आधार नंबर सही नहीं है। कृपया फिर से बताएं।"
- OTP expired: "OTP समय समाप्त हो गया। मैं नया OTP भेज रहा हूं।"
- API failure: "अभी सिस्टम में समस्या है। क्या आप 10 मिनट बाद फिर कॉल कर सकते हैं?"

#### 2.3.2 eDistrict Form Submission

**Purpose**: Submit completed forms to state government portals

**Challenge**: Each state has different API (no unified standard)

**Solution**: Adapter pattern with state-specific implementations

**Architecture**:
```
Lambda (form-submission-orchestrator)
  ↓
State Router (based on user location)
  ↓
├── Adapter: Uttar Pradesh eDistrict API
├── Adapter: Tamil Nadu TNeGA API
├── Adapter: West Bengal eDistrict API
└── Adapter: Generic (for states without API → email/PDF)
```

**Example Adapter (UP eDistrict)**:
```python
class UPeDistrictAdapter:
    def submit_form(self, scheme_id, form_data, documents):
        # Transform to UP API format
        payload = {
            "serviceId": self.map_scheme_to_service(scheme_id),
            "applicantDetails": {
                "name": form_data["name"],
                "aadhaar": form_data["aadhaar"],
                "mobile": form_data["phone"]
            },
            "documents": [
                {"type": "AADHAAR", "url": documents["aadhaar_url"]},
                {"type": "LAND_RECORD", "url": documents["land_url"]}
            ]
        }
        
        response = requests.post(
            "https://edistrict.up.gov.in/api/v1/applications",
            headers={"X-API-Key": os.environ["UP_API_KEY"]},
            json=payload
        )
        
        return {
            "application_id": response.json()["applicationNumber"],
            "status": "submitted",
            "tracking_url": response.json()["trackingUrl"]
        }
```

**Fallback for States Without API**:
- Generate PDF from form data
- Email to designated government email
- Store in S3 for manual processing
- Notify user: "आपका फॉर्म तैयार है। मैंने इसे सरकारी ऑफिस को भेज दिया है।"

#### 2.3.3 SMS Notifications (Amazon SNS)

**Purpose**: Send confirmations, reminders, and status updates

**Configuration**:
- **Service**: Amazon SNS with SMS capability
- **Sender ID**: "VAANISETU" (registered with telecom operators)
- **Languages**: Unicode support for Hindi, Tamil, Bengali, etc.

**Message Templates**:

**Application Confirmation (Hindi)**:
```
VaaniSetu: आपका आवेदन सफल!
योजना: {scheme_name}
आवेदन नंबर: {app_id}
जमा करें:
1. आधार कॉपी
2. ज़मीन का कागज़
3. बैंक पासबुक
कहाँ: {office_address}
समय: {office_hours}
मदद: 1800-XXX-XXXX
```

**Follow-Up Reminder (Day 7)**:
```
VaaniSetu: क्या आपने दस्तावेज़ जमा किए?
आवेदन: {app_id}
अगर नहीं, तो कृपया {office_address} जाएं।
समय: {office_hours}
सवाल? कॉल करें: 1800-XXX-XXXX
```

**Status Update (Approved)**:
```
VaaniSetu: बधाई! आपका आवेदन स्वीकृत।
योजना: {scheme_name}
राशि: ₹{amount}
आपके खाते में 7 दिन में आएगी।
```

**Implementation**:
```python
# Lambda function: send-sms
def send_confirmation_sms(phone_number, language, data):
    template = get_template("confirmation", language)
    message = template.format(**data)
    
    sns.publish(
        PhoneNumber=phone_number,
        Message=message,
        MessageAttributes={
            "AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": "VAANISETU"},
            "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
        }
    )
```

---

### 2.4 Data Layer

#### 2.4.1 DynamoDB Tables

**Table 1: Sessions**
- **Purpose**: Store active call sessions and conversation state
- **Partition Key**: `session_id` (UUID)
- **Sort Key**: None
- **TTL**: 24 hours
- **Capacity**: On-demand (auto-scaling)

**Table 2: Applications**
- **Purpose**: Store submitted applications for tracking
- **Partition Key**: `application_id` (UUID)
- **Sort Key**: `created_at` (timestamp)
- **GSI**: `phone_number-index` for user lookup
- **Retention**: 90 days after scheme approval/rejection

**Table 3: Schemes**
- **Purpose**: Master data for all government schemes
- **Partition Key**: `scheme_id`
- **Sort Key**: `version` (for scheme updates)
- **Attributes**: name, description, eligibility, documents, benefits (see 2.2.2)

**Table 4: Users**
- **Purpose**: Store verified user profiles (optional, for repeat users)
- **Partition Key**: `phone_number`
- **Attributes**: name, aadhaar_hash, preferred_language, call_history

#### 2.4.2 S3 Buckets

**Bucket 1: vaanisetu-call-recordings**
- **Purpose**: Store call recordings for quality assurance
- **Lifecycle**: Delete after 30 days
- **Encryption**: SSE-S3
- **Access**: Restricted to QA team

**Bucket 2: vaanisetu-documents**
- **Purpose**: Store user-uploaded documents (if future feature)
- **Lifecycle**: Delete after 90 days
- **Encryption**: SSE-KMS
- **Access**: Restricted to application processing

**Bucket 3: vaanisetu-analytics**
- **Purpose**: Store aggregated analytics data
- **Lifecycle**: Transition to Glacier after 1 year
- **Format**: Parquet (for Athena queries)

#### 2.4.3 RDS Aurora (Optional, for Complex Queries)

**Use Case**: Analytics, reporting, admin dashboard

**Schema**:
```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY,
    phone_number VARCHAR(15),
    scheme_id VARCHAR(50),
    status VARCHAR(20), -- submitted, approved, rejected
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    state VARCHAR(50),
    district VARCHAR(50)
);

CREATE TABLE call_logs (
    id UUID PRIMARY KEY,
    session_id UUID,
    phone_number VARCHAR(15),
    duration INT, -- seconds
    language VARCHAR(10),
    outcome VARCHAR(20), -- completed, abandoned, escalated
    created_at TIMESTAMP
);

CREATE INDEX idx_applications_state ON applications(state, created_at);
CREATE INDEX idx_call_logs_date ON call_logs(created_at);
```

---

### 2.5 Monitoring & Observability

#### 2.5.1 CloudWatch Dashboards

**Dashboard 1: Real-Time Operations**
- Active calls (current count)
- Call queue length
- Average wait time
- Call abandonment rate
- System errors (last 5 minutes)

**Dashboard 2: AI Performance**
- Transcription accuracy (avg confidence score)
- AI response latency (p50, p95, p99)
- Scheme matching accuracy (manual validation sample)
- Human escalation rate

**Dashboard 3: Business Metrics**
- Applications submitted (today, this week, this month)
- Top 10 schemes by volume
- Completion rate by state
- User satisfaction score (from post-call survey)

#### 2.5.2 CloudWatch Alarms

**Critical Alarms** (PagerDuty notification):
- System uptime < 99% (5-minute window)
- Error rate > 5% (5-minute window)
- Call queue > 100 (immediate)
- Aadhaar API failure rate > 10%

**Warning Alarms** (Email notification):
- Average call duration > 15 minutes
- Transcription confidence < 85%
- SMS delivery failure rate > 2%

#### 2.5.3 X-Ray Tracing

**Purpose**: End-to-end request tracing for debugging

**Instrumentation**:
- All Lambda functions
- API Gateway requests
- Bedrock API calls
- External API calls (Aadhaar, eDistrict)

**Sample Trace**:
```
Call Initiated (Amazon Connect)
  ↓ 120ms
Lambda: language-detection
  ↓ 1800ms
Transcribe: speech-to-text
  ↓ 2500ms
Lambda: ai-orchestrator
  ↓ 3200ms (includes Bedrock call)
Bedrock: Claude Sonnet response
  ↓ 800ms
Polly: text-to-speech
  ↓ 200ms
Connect: play audio to user
```

---

## 3. Security Architecture

### 3.1 Data Encryption

**At Rest**:
- DynamoDB: AWS-managed keys (SSE-DynamoDB)
- S3: KMS-managed keys (SSE-KMS)
- RDS: KMS encryption enabled

**In Transit**:
- All API calls: TLS 1.3
- Internal AWS services: AWS PrivateLink

### 3.2 PII Protection

**Masking Strategy**:
- Aadhaar: Store only last 4 digits + hash
- Phone: Mask middle 6 digits in logs (e.g., +91XXXX1234)
- Bank account: Store only last 4 digits

**Example**:
```python
def mask_aadhaar(aadhaar):
    return f"XXXX-XXXX-{aadhaar[-4:]}"

def hash_aadhaar(aadhaar):
    return hashlib.sha256(aadhaar.encode()).hexdigest()
```

### 3.3 Access Control

**IAM Roles**:
- `VaaniSetu-Lambda-Execution`: Minimal permissions for Lambda functions
- `VaaniSetu-Admin`: Full access for admin dashboard
- `VaaniSetu-QA`: Read-only access to call recordings

**API Gateway Authorization**:
- Admin APIs: IAM authentication
- Public APIs: API key + rate limiting (1000 req/min per key)

---

## 4. Deployment Architecture

### 4.1 Multi-Region Setup

**Primary Region**: ap-south-1 (Mumbai) - Low latency to India
**DR Region**: ap-southeast-1 (Singapore) - Failover

**Replication**:
- DynamoDB: Global tables (automatic replication)
- S3: Cross-region replication (CRR)
- RDS: Read replicas in DR region

### 4.2 CI/CD Pipeline

**Tools**: AWS CodePipeline + CodeBuild + CodeDeploy

**Stages**:
1. **Source**: GitHub repository (main branch)
2. **Build**: 
   - Run unit tests (pytest)
   - Build Lambda deployment packages
   - Validate CloudFormation templates
3. **Deploy to Staging**:
   - Deploy to staging environment
   - Run integration tests
   - Run smoke tests (sample calls)
4. **Manual Approval**: Product team reviews staging
5. **Deploy to Production**:
   - Blue/green deployment
   - Canary release (10% traffic for 1 hour)
   - Full rollout if no errors

### 4.3 Infrastructure as Code

**Tool**: AWS CDK (Python)

**Stack Structure**:
```
vaanisetu-cdk/
├── stacks/
│   ├── voice_stack.py        # Connect, Transcribe, Polly
│   ├── ai_stack.py            # Bedrock, Lambda, OpenSearch
│   ├── integration_stack.py   # API Gateway, SNS, EventBridge
│   ├── data_stack.py          # DynamoDB, S3, RDS
│   └── monitoring_stack.py    # CloudWatch, X-Ray
├── app.py                     # CDK app entry point
└── cdk.json                   # CDK configuration
```

---

## 5. Cost Estimation

### 5.1 Per-Call Cost Breakdown (8-minute call)

| Service | Usage | Cost |
|---------|-------|------|
| Amazon Connect | 8 minutes | $0.072 |
| Transcribe | 8 minutes | $0.096 |
| Polly | ~500 characters | $0.002 |
| Bedrock (Claude Sonnet) | ~10K tokens | $0.045 |
| Lambda | ~20 invocations | $0.001 |
| DynamoDB | 50 read/write units | $0.0001 |
| SNS (SMS) | 1 message | $0.005 |
| **Total** | | **₹12** |

### 5.2 Monthly Cost (100K calls)

| Component | Cost (USD) | Cost (INR) |
|-----------|------------|------------|
| Voice Layer | $21,000 | ₹17.5L |
| AI Layer | $4,500 | ₹3.75L |
| Integration | $500 | ₹42K |
| Data Storage | $1,000 | ₹83K |
| Monitoring | $200 | ₹17K |
| **Total** | **$27,200** | **₹22.7L** |

**Cost per call**: ₹22.7 (vs. ₹450 for Jan Seva Kendra)

---

## 6. Correctness Properties

### 6.1 Functional Correctness

**Property 6.1.1: Scheme Matching Accuracy**
- **Specification**: Given user intent and eligibility data, system must return correct scheme(s) with ≥ 95% accuracy
- **Test Strategy**: Property-based testing with 1000 synthetic user profiles
- **Validation**: Manual review by domain experts on 10% sample

**Property 6.1.2: Form Completeness**
- **Specification**: All required fields for a scheme must be collected before submission
- **Test Strategy**: Unit tests for each scheme's required fields
- **Validation**: Pre-submission validation in Lambda function

**Property 6.1.3: Data Integrity**
- **Specification**: User data must not be corrupted during transcription → AI → storage pipeline
- **Test Strategy**: End-to-end integration tests with known inputs
- **Validation**: Checksum validation at each stage

### 6.2 Non-Functional Correctness

**Property 6.2.1: Latency Bounds**
- **Specification**: End-to-end response latency < 5 seconds for 95th percentile
- **Test Strategy**: Load testing with 10K concurrent calls
- **Validation**: CloudWatch metrics + X-Ray traces

**Property 6.2.2: Availability**
- **Specification**: System uptime ≥ 99.5% (excluding planned maintenance)
- **Test Strategy**: Chaos engineering (random component failures)
- **Validation**: CloudWatch uptime metrics over 30-day rolling window

**Property 6.2.3: Security**
- **Specification**: No PII leakage in logs, analytics, or error messages
- **Test Strategy**: Automated log scanning for Aadhaar/phone patterns
- **Validation**: Quarterly security audits

---

## 7. Testing Strategy

### 7.1 Unit Tests
- Lambda functions: pytest with moto (AWS mocking)
- AI prompts: Evaluate on 100 test cases per language
- Data validation: Test all input formats (valid, invalid, edge cases)

### 7.2 Integration Tests
- End-to-end call simulation: Synthetic audio → Transcribe → AI → Polly
- API integration: Mock Aadhaar/eDistrict APIs with test data
- Database: Test DynamoDB queries, indexes, TTL

### 7.3 Load Tests
- Tool: Locust (Python-based load testing)
- Scenario: Ramp up from 100 to 10,000 concurrent calls over 1 hour
- Metrics: Response time, error rate, cost

### 7.4 User Acceptance Testing (UAT)
- Pilot: 100 real farmers in 3 states (UP, TN, WB)
- Feedback: Post-call survey (5 questions, 1-5 rating)
- Iteration: Fix issues, retrain AI, update prompts

---

## 8. Rollout Plan

### Phase 1: MVP (Month 1-2)
- **Scope**: 1 state (UP), 1 language (Hindi), 10 schemes
- **Goal**: Validate core flow, gather feedback
- **Success**: 1,000 successful applications

### Phase 2: Pilot (Month 3-4)
- **Scope**: 3 states (UP, TN, WB), 3 languages, 50 schemes
- **Goal**: Test scalability, multi-language support
- **Success**: 50,000 applications, 70% completion rate

### Phase 3: Full Launch (Month 5-6)
- **Scope**: 10 states, 12 languages, 250 schemes
- **Goal**: National rollout
- **Success**: 500,000 applications, 72% completion rate

---

**Document Version**: 1.0  
**Last Updated**: February 8, 2026  
**Owner**: VaaniSetu Engineering Team
