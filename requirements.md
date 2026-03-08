# VaaniSetu (वाणी सेतु - Voice Bridge) - Requirements Document

## 1. Executive Summary

### 1.1 Project Overview
VaaniSetu is an AI-powered voice-first platform that converts government scheme documents into interactive voice conversations in local Indian languages. The system enables rural citizens to access, understand, and apply for government schemes through natural phone conversations, eliminating literacy and digital access barriers.

### 1.2 Problem Statement
- **Scale**: 250+ central government schemes with ₹1.2 lakh Cr allocated annually
- **Barrier**: 64% rural literacy rate, only 12% English fluency
- **Impact**: 40% of allocated funds remain unclaimed (CAG report 2024)
- **Current Pain**: 4-6 hours average time to apply (travel + queues), 18% completion rate

### 1.3 Solution
A toll-free voice interface that:
- Conducts natural conversations in 12+ Indian languages
- Matches citizens to eligible schemes through conversational AI
- Auto-fills government forms through guided questions
- Provides SMS confirmations with actionable checklists
- Follows up to ensure application completion

### 1.4 Success Metrics (6 Months)
- **Scheme Awareness**: 23% → 65% rural citizens
- **Application Completion**: 18% → 72%
- **Time to Apply**: 4-6 hours → 8 minutes
- **Unclaimed Benefits**: ₹48,000 Cr/year → ₹15,000 Cr/year
- **Cost per Application**: ₹450 → ₹12
- **Pilot Goal**: 50,000 farmers file applications in 3 months

---

## 2. User Stories & Acceptance Criteria

### 2.1 Voice Interaction & Language Support

#### User Story 2.1.1: Multi-Language Voice Conversation
**As a** rural farmer who speaks only Hindi/Tamil/Bengali  
**I want to** call a toll-free number and speak in my native language  
**So that** I can access government schemes without needing English literacy

**Acceptance Criteria:**
- AC 2.1.1.1: System supports 12+ Indian languages (Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu)
- AC 2.1.1.2: Language is auto-detected within first 5 seconds of conversation
- AC 2.1.1.3: User can explicitly switch language mid-conversation by saying "Change language to [language]"
- AC 2.1.1.4: Speech-to-text accuracy ≥ 90% for supported languages
- AC 2.1.1.5: Text-to-speech output sounds natural with proper pronunciation of local terms
- AC 2.1.1.6: System handles regional dialects and accents within each language

#### User Story 2.1.2: Natural Conversation Flow
**As a** farmer unfamiliar with government terminology  
**I want to** describe my needs in simple, everyday language  
**So that** the system understands my intent without requiring formal knowledge

**Acceptance Criteria:**
- AC 2.1.2.1: System interprets vague requests (e.g., "I need money for seeds" → Agricultural Input Subsidy)
- AC 2.1.2.2: AI asks clarifying questions when intent is ambiguous
- AC 2.1.2.3: System handles multi-turn conversations with context retention across 20+ exchanges
- AC 2.1.2.4: User can interrupt AI at any point to ask questions or provide corrections
- AC 2.1.2.5: System handles filler words, pauses, and natural speech patterns
- AC 2.1.2.6: Conversation completes within 8-12 minutes for standard scheme applications

### 2.2 Scheme Discovery & Eligibility

#### User Story 2.2.1: Intelligent Scheme Matching
**As a** citizen unaware of available schemes  
**I want** the system to identify schemes I'm eligible for based on my situation  
**So that** I don't miss benefits I qualify for

**Acceptance Criteria:**
- AC 2.2.1.1: System maintains database of 250+ central and state government schemes
- AC 2.2.1.2: Semantic search matches user needs to relevant schemes with ≥ 85% accuracy
- AC 2.2.1.3: System asks minimum necessary questions to determine eligibility (≤ 5 questions)
- AC 2.2.1.4: Multiple eligible schemes are presented in order of benefit amount
- AC 2.2.1.5: System explains each scheme in simple language (< 30 seconds per scheme)
- AC 2.2.1.6: User can ask "Why am I eligible?" and receive clear explanation

#### User Story 2.2.2: Eligibility Verification
**As a** farmer with specific land/income constraints  
**I want** to know immediately if I qualify for a scheme  
**So that** I don't waste time on ineligible applications

**Acceptance Criteria:**
- AC 2.2.2.1: System checks eligibility criteria in real-time during conversation
- AC 2.2.2.2: Clear explanation provided when user is ineligible (e.g., "This scheme requires < 2 acres, you have 5 acres")
- AC 2.2.2.3: Alternative schemes suggested when primary choice is ineligible
- AC 2.2.2.4: Eligibility rules updated weekly from government sources
- AC 2.2.2.5: System handles edge cases (e.g., joint land ownership, seasonal income)

### 2.3 Form Filling & Data Collection

#### User Story 2.3.1: Guided Form Completion
**As a** citizen who cannot read forms  
**I want** the system to ask me questions and fill the form for me  
**So that** I can complete applications without visiting offices

**Acceptance Criteria:**
- AC 2.3.1.1: System asks form questions in conversational language (not bureaucratic terms)
- AC 2.3.1.2: Each question includes context (e.g., "I need your Aadhaar to verify identity")
- AC 2.3.1.3: System validates input in real-time (e.g., Aadhaar format, bank IFSC)
- AC 2.3.1.4: User can skip optional fields by saying "I don't know" or "Skip"
- AC 2.3.1.5: System pre-fills data from Aadhaar/DigiLocker when available
- AC 2.3.1.6: Progress indicator provided (e.g., "3 more questions remaining")

#### User Story 2.3.2: Ambiguity Handling
**As a** user who gives vague or incomplete answers  
**I want** the system to clarify and guide me to correct responses  
**So that** my form is filled accurately

**Acceptance Criteria:**
- AC 2.3.2.1: System detects ambiguous answers (e.g., "village bank" → "Which branch?")
- AC 2.3.2.2: Provides examples when user is confused (e.g., "Bank name like SBI, HDFC, or Gramin Bank")
- AC 2.3.2.3: Repeats question in simpler terms if user says "I don't understand"
- AC 2.3.2.4: Allows user to correct previous answers (e.g., "Change my land size to 3 acres")
- AC 2.3.2.5: Confirms critical information by repeating back (e.g., "You said 2 acres, correct?")

#### User Story 2.3.3: Document Explanation
**As a** citizen unfamiliar with official documents  
**I want** explanations of what each document is and where to get it  
**So that** I can gather required paperwork confidently

**Acceptance Criteria:**
- AC 2.3.3.1: System explains each required document in local context (e.g., "Land paper is called Khsara or 7/12 in your area")
- AC 2.3.3.2: Provides instructions on where to obtain missing documents
- AC 2.3.3.3: User can ask "What is [document name]?" at any time
- AC 2.3.3.4: Alternative documents suggested when primary is unavailable
- AC 2.3.3.5: Visual descriptions provided for illiterate users (e.g., "It's a green booklet with your photo")

### 2.4 Verification & Submission

#### User Story 2.4.1: Pre-Submission Review
**As a** user who completed the form  
**I want** to review all information before submission  
**So that** I can catch and correct any mistakes

**Acceptance Criteria:**
- AC 2.4.1.1: System reads back all captured information in summary format
- AC 2.4.1.2: User can request changes to specific fields without restarting
- AC 2.4.1.3: Critical fields (Aadhaar, bank account) are confirmed twice
- AC 2.4.1.4: User provides explicit verbal consent before submission
- AC 2.4.1.5: Option to receive SMS with form details for offline review

#### User Story 2.4.2: Identity Verification
**As a** government system  
**I want** to verify user identity through Aadhaar  
**So that** applications are authentic and fraud is prevented

**Acceptance Criteria:**
- AC 2.4.2.1: Aadhaar number validated against UIDAI database in real-time
- AC 2.4.2.2: OTP sent to Aadhaar-linked mobile for verification
- AC 2.4.2.3: User speaks OTP, system validates within 5 minutes
- AC 2.4.2.4: Fallback to biometric verification if OTP fails (future phase)
- AC 2.4.2.5: Privacy notice provided before Aadhaar verification

#### User Story 2.4.3: Form Submission
**As a** user who completed verification  
**I want** my form submitted to the government portal automatically  
**So that** I don't need to visit offices for submission

**Acceptance Criteria:**
- AC 2.4.3.1: Form data submitted to eDistrict API in real-time
- AC 2.4.3.2: Unique application reference ID generated and provided to user
- AC 2.4.3.3: Submission confirmation received within 30 seconds
- AC 2.4.3.4: If submission fails, user is notified and data is queued for retry
- AC 2.4.3.5: User receives SMS with reference ID and submission timestamp

### 2.5 Post-Submission Support

#### User Story 2.5.1: SMS Confirmation & Checklist
**As a** user who submitted the form  
**I want** an SMS with next steps and required documents  
**So that** I know exactly what to do next

**Acceptance Criteria:**
- AC 2.5.1.1: SMS sent within 1 minute of call completion
- AC 2.5.1.2: SMS contains: Application ID, scheme name, document checklist, office address, office hours
- AC 2.5.1.3: SMS in user's preferred language
- AC 2.5.1.4: Documents listed with local names (e.g., "Khsara/7/12" not "Land Record")
- AC 2.5.1.5: Office address includes landmark and counter number
- AC 2.5.1.6: SMS includes helpline number for queries

#### User Story 2.5.2: Follow-Up Calls
**As a** user who may forget or face obstacles  
**I want** the system to call me and check on my progress  
**So that** I complete the application process successfully

**Acceptance Criteria:**
- AC 2.5.2.1: Automated follow-up call placed 7 days after initial call
- AC 2.5.2.2: AI asks: "Did you submit documents? Any problems?"
- AC 2.5.2.3: If user reports issues, AI provides solutions or escalates to human agent
- AC 2.5.2.4: If user hasn't submitted, AI offers to resend SMS or provide reminders
- AC 2.5.2.5: Second follow-up at 14 days if first follow-up indicates pending action
- AC 2.5.2.6: User can opt-out of follow-ups by saying "Don't call again"

#### User Story 2.5.3: Status Tracking
**As a** user waiting for scheme approval  
**I want** to check my application status anytime  
**So that** I know when to expect benefits

**Acceptance Criteria:**
- AC 2.5.3.1: User can call back and say "Check my application status"
- AC 2.5.3.2: System retrieves status using phone number or application ID
- AC 2.5.3.3: Status updates include: Submitted, Under Review, Approved, Rejected, Funds Disbursed
- AC 2.5.3.4: If rejected, reason is explained in simple language
- AC 2.5.3.5: Estimated timeline provided for pending applications
- AC 2.5.3.6: Proactive SMS sent when status changes to Approved or Rejected

### 2.6 System Reliability & Performance

#### User Story 2.6.1: High Availability
**As a** user calling from a remote area  
**I want** the system to be available 24/7  
**So that** I can call at my convenience

**Acceptance Criteria:**
- AC 2.6.1.1: System uptime ≥ 99.5% (excluding planned maintenance)
- AC 2.6.1.2: Toll-free number accessible from all Indian telecom operators
- AC 2.6.1.3: Call queue management with estimated wait time (< 2 minutes)
- AC 2.6.1.4: Graceful degradation: If AI fails, call routes to human agent
- AC 2.6.1.5: System handles 10,000 concurrent calls
- AC 2.6.1.6: Planned maintenance windows announced 48 hours in advance via SMS

#### User Story 2.6.2: Data Privacy & Security
**As a** user sharing sensitive personal information  
**I want** my data to be secure and private  
**So that** I can trust the system with my details

**Acceptance Criteria:**
- AC 2.6.2.1: Voice recordings deleted immediately after transcription
- AC 2.6.2.2: Transcripts encrypted at rest and in transit (AES-256)
- AC 2.6.2.3: PII (Aadhaar, bank details) masked in logs and analytics
- AC 2.6.2.4: Data retention policy: Form data deleted 90 days after scheme approval/rejection
- AC 2.6.2.5: User can request data deletion by calling helpline
- AC 2.6.2.6: Compliance with IT Act 2000 and Aadhaar Act 2016
- AC 2.6.2.7: Privacy notice played at start of call

### 2.7 Responsible AI & Transparency

#### User Story 2.7.1: Explainability
**As a** user interacting with AI  
**I want** to understand why certain questions are asked  
**So that** I trust the system and provide accurate information

**Acceptance Criteria:**
- AC 2.7.1.1: User can ask "Why do you need this?" for any question
- AC 2.7.1.2: AI provides clear, non-technical explanation (e.g., "Bank details are needed to transfer money to your account")
- AC 2.7.1.3: System discloses it's AI at start of call: "I am VaaniSetu, an AI assistant"
- AC 2.7.1.4: User can request human agent at any time by saying "Talk to a person"

#### User Story 2.7.2: Accuracy & Fallback
**As a** user depending on AI for critical information  
**I want** the system to be accurate and escalate when uncertain  
**So that** I receive correct guidance

**Acceptance Criteria:**
- AC 2.7.2.1: AI confidence threshold: If < 70% confidence, escalate to human agent
- AC 2.7.2.2: System says "I'm not sure, let me connect you to an expert" when uncertain
- AC 2.7.2.3: Scheme eligibility accuracy ≥ 95% (validated against manual checks)
- AC 2.7.2.4: Form field accuracy ≥ 98% (validated against submitted forms)
- AC 2.7.2.5: Human agent reviews 10% of AI-completed forms randomly for quality assurance

---

## 3. Functional Requirements

### 3.1 Voice Layer
- **FR 3.1.1**: Toll-free number (1800-XXX-XXXX) accessible from all Indian networks
- **FR 3.1.2**: Call routing with IVR fallback for system failures
- **FR 3.1.3**: Real-time speech-to-text transcription with < 2 second latency
- **FR 3.1.4**: Text-to-speech synthesis with natural prosody and emotion
- **FR 3.1.5**: Call recording for quality assurance (with user consent)
- **FR 3.1.6**: DTMF support for users unable to use voice (e.g., speech impairments)

### 3.2 AI Layer
- **FR 3.2.1**: Conversational AI with context retention across multi-turn dialogues
- **FR 3.2.2**: Intent classification for 50+ user intents (scheme inquiry, status check, complaint, etc.)
- **FR 3.2.3**: Entity extraction (names, numbers, dates, locations)
- **FR 3.2.4**: Semantic search across 250+ schemes with relevance ranking
- **FR 3.2.5**: Eligibility rule engine with 500+ conditional logic rules
- **FR 3.2.6**: Form field validation (format, range, dependencies)
- **FR 3.2.7**: Sentiment analysis to detect user frustration and escalate

### 3.3 Integration Layer
- **FR 3.3.1**: Aadhaar API integration for identity verification (UIDAI)
- **FR 3.3.2**: eDistrict API integration for form submission (state portals)
- **FR 3.3.3**: DigiLocker API for fetching existing documents (optional)
- **FR 3.3.4**: SMS Gateway for confirmations and reminders
- **FR 3.3.5**: Payment gateway integration for application fees (if applicable)
- **FR 3.3.6**: CRM integration for human agent handoff

### 3.4 Data Layer
- **FR 3.4.1**: Scheme database with fields: name, description, eligibility, benefits, documents, deadlines
- **FR 3.4.2**: Office location database with addresses, hours, contact numbers
- **FR 3.4.3**: FAQ database with 10,000+ questions and answers
- **FR 3.4.4**: User session database for conversation history and form data
- **FR 3.4.5**: Analytics database for usage metrics and performance tracking

### 3.5 Admin & Monitoring
- **FR 3.5.1**: Admin dashboard for scheme management (add/edit/delete schemes)
- **FR 3.5.2**: Real-time monitoring dashboard (call volume, success rate, errors)
- **FR 3.5.3**: Analytics dashboard (user demographics, popular schemes, drop-off points)
- **FR 3.5.4**: Alert system for system failures, high error rates, or unusual patterns
- **FR 3.5.5**: Audit logs for all data access and modifications

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR 4.1.1**: Call connection time < 5 seconds
- **NFR 4.1.2**: Speech-to-text latency < 2 seconds
- **NFR 4.1.3**: AI response generation < 3 seconds
- **NFR 4.1.4**: End-to-end conversation latency < 5 seconds per exchange
- **NFR 4.1.5**: SMS delivery < 1 minute after call completion
- **NFR 4.1.6**: API response time < 500ms for 95th percentile

### 4.2 Scalability
- **NFR 4.2.1**: Support 10,000 concurrent calls
- **NFR 4.2.2**: Scale to 100,000 concurrent calls within 6 months
- **NFR 4.2.3**: Handle 1 million calls per day
- **NFR 4.2.4**: Database supports 10 million user records
- **NFR 4.2.5**: Auto-scaling based on call volume (scale up/down within 2 minutes)

### 4.3 Availability
- **NFR 4.3.1**: System uptime 99.5% (excluding planned maintenance)
- **NFR 4.3.2**: Planned maintenance windows < 4 hours per month
- **NFR 4.3.3**: Disaster recovery with RPO < 1 hour, RTO < 4 hours
- **NFR 4.3.4**: Multi-region deployment for high availability

### 4.4 Security
- **NFR 4.4.1**: Data encryption at rest (AES-256) and in transit (TLS 1.3)
- **NFR 4.4.2**: PII masking in logs and analytics
- **NFR 4.4.3**: Role-based access control (RBAC) for admin users
- **NFR 4.4.4**: Penetration testing quarterly
- **NFR 4.4.5**: Compliance with ISO 27001, SOC 2, GDPR (for future international expansion)

### 4.5 Usability
- **NFR 4.5.1**: Average call duration 8-12 minutes for standard applications
- **NFR 4.5.2**: User satisfaction score ≥ 4.0/5.0
- **NFR 4.5.3**: First-call resolution rate ≥ 80%
- **NFR 4.5.4**: Call abandonment rate < 5%

### 4.6 Maintainability
- **NFR 4.6.1**: Modular architecture for easy updates
- **NFR 4.6.2**: Scheme database updates deployable without system downtime
- **NFR 4.6.3**: AI model updates with A/B testing capability
- **NFR 4.6.4**: Comprehensive logging for debugging (CloudWatch, ELK stack)

---

## 5. Constraints & Assumptions

### 5.1 Constraints
- **C 5.1.1**: Must comply with Aadhaar Act 2016 and IT Act 2000
- **C 5.1.2**: Must integrate with existing government APIs (eDistrict, UIDAI)
- **C 5.1.3**: Budget: ₹12 per application (vs. ₹450 current cost)
- **C 5.1.4**: Pilot phase limited to 3 states (Hindi, Tamil, Bengali speaking regions)
- **C 5.1.5**: Human agent fallback required for complex cases

### 5.2 Assumptions
- **A 5.2.1**: Users have access to basic mobile phones (not necessarily smartphones)
- **A 5.2.2**: Users have Aadhaar cards and linked mobile numbers
- **A 5.2.3**: Government APIs (eDistrict, UIDAI) are available and reliable
- **A 5.2.4**: Users are willing to share personal information over phone
- **A 5.2.5**: Block offices can handle increased foot traffic for document submission

---

## 6. Out of Scope (Phase 1)

- **OS 6.1**: Biometric authentication (fingerprint, iris scan)
- **OS 6.2**: Video call support for document verification
- **OS 6.3**: Integration with state-specific schemes (only central schemes in Phase 1)
- **OS 6.4**: Mobile app (voice-only via phone call in Phase 1)
- **OS 6.5**: Payment processing for scheme benefits (handled by government systems)
- **OS 6.6**: Multi-user accounts (family/household management)

---

## 7. Dependencies

### 7.1 External Dependencies
- **D 7.1.1**: Amazon Web Services (AWS) for infrastructure
- **D 7.1.2**: UIDAI Aadhaar API for identity verification
- **D 7.1.3**: State eDistrict portals for form submission
- **D 7.1.4**: Telecom operators for toll-free number provisioning
- **D 7.1.5**: SMS gateway provider (e.g., AWS SNS, Twilio)

### 7.2 Internal Dependencies
- **D 7.2.1**: Scheme database populated and maintained by government liaisons
- **D 7.2.2**: Human agent team trained and available for escalations
- **D 7.2.3**: Legal team approval for privacy policy and terms of service
- **D 7.2.4**: Marketing team for user awareness campaigns

---

## 8. Risks & Mitigation

### 8.1 Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Speech recognition accuracy < 90% for regional dialects | High | Medium | Continuous model training with regional data; human fallback |
| eDistrict API downtime | High | Medium | Queue submissions for retry; notify users of delays |
| Aadhaar API rate limits | Medium | Low | Implement caching; batch verification during off-peak hours |
| AI hallucination (incorrect scheme info) | High | Low | Confidence thresholds; human review of 10% calls |

### 8.2 Operational Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| User distrust of AI | Medium | Medium | Clear disclosure; human agent option; testimonials |
| Low adoption in pilot phase | High | Medium | Partnerships with NGOs; village-level awareness campaigns |
| Scheme database outdated | Medium | Medium | Automated scraping of government websites; weekly manual reviews |
| Human agent capacity insufficient | Medium | High | Auto-scaling agent pool; prioritize complex cases |

### 8.3 Compliance Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Aadhaar data breach | Critical | Low | Encryption, access controls, regular audits |
| Non-compliance with IT Act | High | Low | Legal review before launch; annual compliance audits |
| User consent not properly obtained | Medium | Medium | Explicit verbal consent recorded; privacy notice at call start |

---

## 9. Success Criteria

### 9.1 Pilot Phase (3 Months)
- ✅ 50,000 farmers complete applications via VaaniSetu
- ✅ Application completion rate ≥ 70%
- ✅ User satisfaction score ≥ 4.0/5.0
- ✅ Speech recognition accuracy ≥ 90%
- ✅ System uptime ≥ 99%
- ✅ Cost per application ≤ ₹15

### 9.2 Full Launch (6 Months)
- ✅ 500,000 applications processed
- ✅ Scheme awareness increased to 65% in pilot regions
- ✅ Unclaimed benefits reduced by 30% in pilot regions
- ✅ Average application time reduced to < 10 minutes
- ✅ Expansion to 5 additional states approved

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **Aadhaar** | 12-digit unique identity number issued by UIDAI to Indian residents |
| **eDistrict** | Government portal for online delivery of citizen services |
| **DigiLocker** | Cloud-based platform for storing and sharing digital documents |
| **Khsara/7/12** | Land ownership record document (names vary by state) |
| **Jan Seva Kendra** | Government service center for citizen assistance |
| **Block Office** | Administrative office at sub-district level |
| **RKVY** | Rashtriya Krishi Vikas Yojana (National Agriculture Development Scheme) |
| **PM-KISAN** | Pradhan Mantri Kisan Samman Nidhi (farmer income support scheme) |
| **UIDAI** | Unique Identification Authority of India |
| **CAG** | Comptroller and Auditor General of India |

---

## 11. Appendices

### 11.1 Sample Conversation Flow (Hindi)
See Section 1.3 for detailed example conversation.

### 11.2 Scheme Database Schema
```
Scheme {
  id: UUID
  name: String
  name_local: Map<Language, String>
  description: String
  description_local: Map<Language, String>
  eligibility_rules: List<Rule>
  required_documents: List<Document>
  benefit_amount: Number
  application_deadline: Date
  department: String
  contact_info: ContactInfo
}
```

### 11.3 API Endpoints
- `/api/v1/call/initiate` - Start new call session
- `/api/v1/call/transcribe` - Real-time speech-to-text
- `/api/v1/schemes/search` - Semantic scheme search
- `/api/v1/forms/submit` - Submit completed form
- `/api/v1/status/check` - Check application status

---

**Document Version**: 1.0  
**Last Updated**: February 8, 2026  
**Owner**: VaaniSetu Product Team  
**Reviewers**: Government Liaison, AI Team, Legal Team
