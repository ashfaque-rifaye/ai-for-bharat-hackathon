# 🌉 VaaniSetu (वाणी सेतु) — Voice Bridge

> AI-powered voice-first platform that converts government scheme documents into interactive voice conversations in local Indian languages.

<p align="center">
  <strong>Connecting Rural India to Government Schemes Through Voice</strong>
</p>

---

## 🎯 The Problem

| Metric | Current State |
|--------|--------------|
| Government schemes | 250+ central schemes, ₹1.2 lakh Cr allocated annually |
| Rural literacy | 64% literacy rate, only 12% English fluency |
| Unclaimed funds | **40% of allocated funds remain unclaimed** (CAG 2024) |
| Time to apply | 4-6 hours (travel + queues), 18% completion rate |

**Millions of eligible citizens miss government benefits because they can't read forms, navigate portals, or understand English-language bureaucracy.**

---

## 💡 The Solution

VaaniSetu is a **toll-free voice interface** that:

1. 🗣️ **Speaks your language** — Natural conversations in Hindi, Tamil, English (12+ planned)
2. 🔍 **Finds your schemes** — AI matches citizens to eligible schemes through simple questions
3. 📝 **Fills your forms** — Guided conversational form completion with validation
4. 📱 **Sends confirmation** — SMS with application ID, checklist, and next steps
5. 📞 **Follows up** — Automated calls to ensure application completion

### How It Works

```
👨‍🌾 Farmer calls VaaniSetu
   │
   ├─ "नमस्ते! मुझे खेती के लिए पैसे चाहिए"
   │   (Hello! I need money for farming)
   │
   ├─ AI asks 4-5 simple questions about their situation
   │
   ├─ Matches to PM-KISAN, RKVY, Fasal Bima Yojana
   │
   ├─ Guides through form filling conversationally
   │
   ├─ Generates application, sends SMS confirmation
   │
   └─ 📱 SMS: "आवेदन ID: VS-2026-00123 | अगला कदम: ..."
```

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Phone /    │────▶│  API Gateway │────▶│   Lambda     │
│   Browser    │◀────│  (WebSocket) │◀────│  Orchestrator│
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌────────────────────────────┼────────────────────┐
                     │                            │                    │
                     ▼                            ▼                    ▼
              ┌──────────────┐          ┌──────────────┐     ┌──────────────┐
              │   Amazon     │          │   Amazon     │     │   Amazon     │
              │  Transcribe  │          │   Bedrock    │     │    Polly     │
              │  (Speech→Text)│         │  (Claude AI) │     │  (Text→Speech)│
              └──────────────┘          └──────┬───────┘     └──────────────┘
                                               │
                                    ┌──────────┼──────────┐
                                    ▼          ▼          ▼
                             ┌──────────┐┌──────────┐┌──────────┐
                             │ DynamoDB ││ Bedrock  ││ Amazon   │
                             │(Sessions)││ KB (RAG) ││ SNS(SMS) │
                             └──────────┘└──────────┘└──────────┘
```

**Built on AWS:** Lambda, Bedrock (Claude 3), Transcribe, Polly, DynamoDB, API Gateway, SNS, S3

---

## 📊 Impact Targets (6 Months)

| Metric | Before | After |
|--------|--------|-------|
| Scheme Awareness | 23% | **65%** |
| Application Completion | 18% | **72%** |
| Time to Apply | 4-6 hours | **8 minutes** |
| Unclaimed Benefits | ₹48,000 Cr/yr | **₹15,000 Cr/yr** |
| Cost per Application | ₹450 | **₹12** |

**Pilot Goal:** 50,000 farmers file applications in 3 months

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI/LLM** | Amazon Bedrock (Claude 3 Haiku/Sonnet) |
| **RAG** | Bedrock Knowledge Bases + Titan Embeddings |
| **Speech-to-Text** | Amazon Transcribe Streaming |
| **Text-to-Speech** | Amazon Polly Neural |
| **Translation** | Amazon Translate |
| **Backend** | AWS Lambda (Python 3.12) |
| **API** | API Gateway (WebSocket + REST) |
| **Database** | DynamoDB |
| **Storage** | S3 |
| **SMS** | Amazon SNS |
| **Frontend** | React + TypeScript + Tailwind |
| **IaC** | AWS CDK (Python) |

---

## 📁 Project Structure

```
VaaniSetu/
├── docs/                              # Documentation
│   ├── PROJECT_PLAN.md
│   ├── ARCHITECTURE.md
│   ├── AWS_COST_ESTIMATION.md
│   ├── DEVELOPMENT_PHASES.md
│   └── TECHNICAL_DECISIONS.md
├── infrastructure/
│   ├── cdk/                           # AWS CDK (Python)
│   │   ├── app.py                     # CDK entry point
│   │   ├── cdk.json
│   │   ├── requirements.txt
│   │   └── stacks/
│   │       ├── data_stack.py          # DynamoDB + S3
│   │       ├── api_stack.py           # REST + WebSocket + Lambdas
│   │       └── ai_stack.py            # Bedrock Knowledge Base
│   └── seed-data/
│       └── schemes/                   # 10 scheme JSONs (trilingual)
├── backend/
│   ├── shared/                        # Common code (layer)
│   │   ├── models.py                  # Pydantic models
│   │   ├── constants.py               # Enums & config
│   │   ├── utils.py                   # Validation & PII masking
│   │   └── aws_clients.py             # Boto3 wrappers
│   └── lambdas/
│       ├── orchestrator/              # REST API handler + session mgmt
│       ├── ai_engine/                 # Bedrock Claude conversation engine
│       │   ├── handler.py             # Bedrock converse + tool use
│       │   ├── prompts.py             # System & state prompts
│       │   ├── scheme_matcher.py      # RAG + keyword search
│       │   ├── eligibility.py         # Rule-based eligibility check
│       │   └── form_filler.py         # Form validation & progress
│       ├── voice_processor/           # WebSocket voice pipeline
│       │   ├── handler.py             # WS connect/disconnect/audio
│       │   ├── transcribe.py          # Amazon Transcribe STT
│       │   └── polly.py               # Amazon Polly Neural TTS
│       └── notification/              # SMS dispatch
│           ├── handler.py             # SNS publisher
│           └── templates.py           # Trilingual SMS templates
├── frontend/                          # React + TypeScript + Tailwind
│   ├── src/
│   │   ├── App.tsx                    # Main app (voice + chat)
│   │   ├── components/                # UI components
│   │   ├── hooks/                     # useWebSocket, useAudioRecorder
│   │   ├── services/                  # REST API client
│   │   ├── store/                     # Zustand state
│   │   └── types.ts
│   ├── package.json
│   └── vite.config.ts
└── scripts/
    └── seed_data.py                   # DynamoDB + S3 seeder
```

---

## 🚀 Getting Started

### Prerequisites
- AWS Account with $100 credits
- AWS CLI configured
- Python 3.12+
- Node.js 18+
- AWS CDK CLI (`npm install -g aws-cdk`)

### Setup
```bash
# Clone repository
git clone <repo-url>
cd VaaniSetu

# Install CDK dependencies
cd infrastructure/cdk
pip install -r requirements.txt

# Deploy infrastructure
cdk bootstrap
cdk deploy --all

# Seed scheme data
cd ../../scripts
python seed_data.py

# Start frontend
cd ../frontend
npm install
npm run dev
```

---

## 🗓️ Development Phases

| Phase | Duration | Focus | Status |
|-------|----------|-------|--------|
| **Phase 1** | Day 1-2 | Infrastructure + API | ✅ Complete |
| **Phase 2** | Day 3-4 | AI Engine + RAG | ✅ Complete |
| **Phase 3** | Day 5-6 | Voice Pipeline | ✅ Complete |
| **Phase 4** | Day 7-8 | Web Demo + SMS | ✅ Complete |
| **Phase 5** | Day 9-10 | Testing + Submission | ⬜ Not Started |

---

## 🌐 Languages Supported (MVP)

| Language | STT | TTS | AI Chat | Status |
|----------|-----|-----|---------|--------|
| Hindi (हिन्दी) | ✅ | ✅ | ✅ | Phase 1 |
| Tamil (தமிழ்) | ✅ | ⚠️ | ✅ | Phase 1 |
| English (India) | ✅ | ✅ | ✅ | Phase 1 |
| Telugu, Bengali, Marathi... | — | — | — | Phase 2 |

---

## 🏛️ Government Schemes (MVP - 10 Schemes)

| Scheme | Category | Benefit |
|--------|----------|---------|
| PM-KISAN | Agriculture | ₹6,000/year |
| PM Awas Yojana | Housing | ₹1.2 lakh |
| RKVY | Agriculture | Variable |
| PM Fasal Bima | Insurance | Crop coverage |
| Soil Health Card | Agriculture | Free testing |
| PM Ujjwala | Energy | Free LPG |
| Ayushman Bharat | Healthcare | ₹5 lakh/year |
| PM Mudra | Finance | Loans to ₹10L |
| Sukanya Samriddhi | Savings | High interest |
| PM Garib Kalyan Anna | Food | Free ration |

---

## 👥 Team

Built for **AWS AI for Bharat Hackathon**

---

## 📄 License

This project is built for hackathon demonstration purposes.
