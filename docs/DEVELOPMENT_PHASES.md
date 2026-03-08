# VaaniSetu — Development Phases & Sprint Plan

## Overview

Total estimated effort: **8-10 days** (solo developer / small team)
Approach: **Vertical slice first** — get one complete flow working end-to-end, then expand

---

## Phase 1: Foundation & Infrastructure (Day 1-2)

### Goals
- Project scaffolding
- AWS infrastructure deployed via CDK
- Scheme data seeded
- Basic API working

### Tasks

#### Day 1: Project Setup
| # | Task | Time | Output |
|---|------|------|--------|
| 1.1 | Initialize CDK project (Python) | 1h | `infrastructure/cdk/` |
| 1.2 | Create `DataStack` — DynamoDB tables + S3 buckets | 1.5h | 3 DynamoDB tables, 2 S3 buckets |
| 1.3 | Create IAM roles and policies | 1h | Least-privilege roles for Lambda |
| 1.4 | Write scheme seed data (10 schemes, 3 languages) | 2h | `seed-data/schemes/*.json` |
| 1.5 | Create seed script to populate DynamoDB | 1h | `scripts/seed_data.py` |
| 1.6 | Deploy DataStack to AWS | 0.5h | Verify DynamoDB + S3 created |

#### Day 2: Basic API
| # | Task | Time | Output |
|---|------|------|--------|
| 2.1 | Create shared models (Pydantic) | 1h | `backend/shared/models.py` |
| 2.2 | Create orchestrator Lambda (session CRUD) | 2h | POST/GET /sessions |
| 2.3 | Create `ApiStack` — REST API Gateway + Lambda | 1.5h | REST endpoints deployed |
| 2.4 | Create scheme list/search Lambda | 1.5h | GET/POST /schemes |
| 2.5 | Test API endpoints with curl/Postman | 1h | Verified working |

### Deliverables
- [x] CDK infrastructure deployed
- [x] DynamoDB tables with 10 seeded schemes
- [x] REST API for sessions and schemes
- [x] Basic Lambda functions

---

## Phase 2: AI Conversation Engine (Day 3-4)

### Goals
- Bedrock Claude integration working
- Conversation state machine implemented
- Scheme matching via RAG
- Eligibility checking

### Tasks

#### Day 3: Bedrock Integration
| # | Task | Time | Output |
|---|------|------|--------|
| 3.1 | Set up Bedrock access (model access requests) | 0.5h | Claude 3 Haiku enabled |
| 3.2 | Create AI engine Lambda with Bedrock client | 2h | `backend/lambdas/ai_engine/` |
| 3.3 | Design and test system prompt | 2h | `prompts.py` with tested prompts |
| 3.4 | Implement conversation state machine | 2h | `conversation.py` |
| 3.5 | Test basic conversation flow (text-based) | 1h | Working text conversation |

#### Day 4: RAG & Eligibility
| # | Task | Time | Output |
|---|------|------|--------|
| 4.1 | Upload scheme docs to S3 | 0.5h | Scheme PDFs/JSONs in S3 |
| 4.2 | Set up Bedrock Knowledge Base | 1.5h | KB created and synced |
| 4.3 | Implement scheme search (RAG) | 2h | `scheme_matcher.py` |
| 4.4 | Implement eligibility rule engine | 2h | `eligibility.py` |
| 4.5 | Implement form field extraction | 1.5h | `form_filler.py` |
| 4.6 | End-to-end text conversation test | 1h | Full flow working via text |

### Deliverables
- [x] Bedrock Claude conversations working
- [x] RAG-based scheme search functional
- [x] Eligibility matching working
- [x] Complete text-based conversation flow

---

## Phase 3: Voice Pipeline (Day 5-6)

### Goals
- Real-time speech-to-text working
- Text-to-speech responses
- WebSocket API for streaming
- Language detection

### Tasks

#### Day 5: Speech Services
| # | Task | Time | Output |
|---|------|------|--------|
| 5.1 | Amazon Transcribe streaming integration | 2.5h | `voice_processor/transcribe.py` |
| 5.2 | Amazon Polly TTS integration | 1.5h | `voice_processor/polly.py` |
| 5.3 | Language detection logic | 1h | Auto-detect Hindi/Tamil/English |
| 5.4 | Audio format handling (PCM, opus, mp3) | 1h | Encode/decode audio |
| 5.5 | Test STT + TTS pipeline | 1.5h | Audio in → Text → Audio out |

#### Day 6: WebSocket API
| # | Task | Time | Output |
|---|------|------|--------|
| 6.1 | Create `VoiceStack` — WebSocket API Gateway | 2h | WSS endpoint deployed |
| 6.2 | Implement connection manager Lambda | 1.5h | $connect, $disconnect handlers |
| 6.3 | Implement audio chunk processor | 2h | audioChunk → Transcribe → AI → Polly |
| 6.4 | Wire voice pipeline to AI engine | 1.5h | Full voice conversation flow |
| 6.5 | Test with WebSocket client | 1h | Voice conversation working |

### Deliverables
- [x] Real-time STT via Transcribe Streaming
- [x] Natural TTS via Polly Neural
- [x] WebSocket voice streaming API
- [x] End-to-end voice conversation

---

## Phase 4: Web Demo & Notifications (Day 7-8)

### Goals
- React web interface for demo
- Browser-based voice capture
- SMS notifications working
- Polished demo experience

### Tasks

#### Day 7: Frontend
| # | Task | Time | Output |
|---|------|------|--------|
| 7.1 | Initialize React + Vite + Tailwind project | 1h | `frontend/` scaffolded |
| 7.2 | Build VoiceInterface component (mic button, waveform) | 2h | Voice recording UI |
| 7.3 | Build ChatTranscript component | 1.5h | Real-time transcript |
| 7.4 | Build SchemeCard + FormProgress components | 1.5h | Scheme display + progress |
| 7.5 | Implement WebSocket client for voice streaming | 2h | Browser → WS → Backend |

#### Day 8: SMS & Polish
| # | Task | Time | Output |
|---|------|------|--------|
| 8.1 | Implement notification Lambda (SNS SMS) | 1.5h | `notification/handler.py` |
| 8.2 | Create SMS templates (3 languages) | 1h | Confirmation + checklist |
| 8.3 | Build LanguageSelector + SMSPreview | 1h | Frontend components |
| 8.4 | Error handling & edge cases | 2h | Graceful failures |
| 8.5 | UI polish (animations, loading states) | 1.5h | Professional demo |
| 8.6 | Deploy frontend (S3 + CloudFront) | 1h | Public URL |

### Deliverables
- [x] Working web demo with voice support
- [x] SMS confirmations sent after form completion
- [x] Responsive, polished UI
- [x] Deployed and accessible frontend

---

## Phase 5: Testing, Demo & Submission (Day 9-10)

### Goals
- End-to-end testing across languages
- Performance optimization
- Demo video recorded
- Submission ready

### Tasks

#### Day 9: Testing & Optimization
| # | Task | Time | Output |
|---|------|------|--------|
| 9.1 | End-to-end test: Hindi farmer scenario | 1.5h | Full flow verified |
| 9.2 | End-to-end test: Tamil farmer scenario | 1.5h | Full flow verified |
| 9.3 | End-to-end test: English scenario | 1h | Full flow verified |
| 9.4 | Test edge cases (no match, invalid input, timeout) | 1.5h | Graceful handling |
| 9.5 | Performance optimization (Lambda cold starts, caching) | 1.5h | <5s response time |
| 9.6 | Bug fixes | 1h | Issues resolved |

#### Day 10: Demo & Submission
| # | Task | Time | Output |
|---|------|------|--------|
| 10.1 | Write demo script | 1h | `docs/DEMO_SCRIPT.md` |
| 10.2 | Record demo video (3-5 min) | 2h | demo.mp4 |
| 10.3 | Prepare architecture diagram (polished) | 1h | Architecture image |
| 10.4 | Write submission document | 1.5h | Hackathon submission |
| 10.5 | Final deploy and smoke test | 1h | Production-ready |
| 10.6 | Submit! | 0.5h | 🎉 |

### Deliverables
- [x] All scenarios tested
- [x] Demo video recorded
- [x] Submission documentation
- [x] Deployed and working

---

## Critical Path

```
Day 1-2: Foundation ──→ Day 3-4: AI Engine ──→ Day 5-6: Voice ──→ Day 7-8: Demo ──→ Day 9-10: Submit
   │                        │                      │                    │
   │                        │                      │                    │
   ▼                        ▼                      ▼                    ▼
 CDK + DB               Bedrock +              Transcribe +          React +
 + API                  RAG + Rules            Polly + WS            SMS + Polish
```

**If behind schedule:**
1. Drop Tamil support (keep Hindi + English only)
2. Skip WebSocket voice streaming → use REST with file upload
3. Use simpler frontend (plain HTML/JS instead of React)
4. Skip SMS → show confirmation in UI only
5. Pre-record demo instead of live demo

---

## Definition of Done (Per Phase)

| Criteria | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|----------|---------|---------|---------|---------|---------|
| Code committed | ✅ | ✅ | ✅ | ✅ | ✅ |
| Deployed to AWS | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tests passing | ✅ | ✅ | ✅ | ✅ | ✅ |
| Demo-able | — | ✅ (text) | ✅ (voice) | ✅ (web) | ✅ (full) |
| Documentation | Setup docs | AI prompts | Voice docs | User guide | Submission |
