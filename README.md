# VaaniSetu (वाणी सेतु - Voice Bridge)

> AI-powered voice-first platform that converts government scheme documents into interactive voice conversations in local Indian languages.

## 📋 Documentation Overview

This directory contains comprehensive documentation for the VaaniSetu project:

### Core Documents

1. **[requirements.md](./requirements.md)** - Complete requirements specification
   - 25+ user stories with detailed acceptance criteria
   - Functional and non-functional requirements
   - Success metrics and constraints
   - Risk analysis and mitigation strategies

2. **[design.md](./design.md)** - Technical design document
   - System architecture (4-layer design)
   - Component specifications for all AWS services
   - Integration patterns and data flows
   - Security architecture and deployment strategy
   - Cost estimation and testing strategy

3. **[architecture-diagram.md](./architecture-diagram.md)** - Visual architecture documentation
   - Multiple architecture diagrams (PNG format)
   - Detailed data flow diagrams
   - Component interaction patterns
   - Scalability and disaster recovery architecture

4. **[tasks.md](./tasks.md)** - Implementation task list
   - Phased implementation plan
   - Task dependencies and priorities

### Architecture Diagrams

**Recommended (Professional Quality):**
- **[architecture-final.png](./architecture-final.png)** - Clean vertical layout with numbered flow (1-9)
- **[architecture-horizontal.png](./architecture-horizontal.png)** - Horizontal layout for presentations

**Additional Views:**
- **[architecture-clean.png](./architecture-clean.png)** - Detailed view with all components
- **[architecture.png](./architecture.png)** - Complete AWS architecture
- **[architecture-flow.png](./architecture-flow.png)** - Step-by-step flow diagram
- **[architecture-simple.png](./architecture-simple.png)** - Simplified overview

### Source Files (Graphviz .dot)

- **[architecture-final.dot](./architecture-final.dot)** - Source for final architecture
- **[architecture-horizontal.dot](./architecture-horizontal.dot)** - Source for horizontal layout
- **[architecture-clean.dot](./architecture-clean.dot)** - Source for clean architecture
- **[architecture.dot](./architecture.dot)** - Source for complete architecture
- **[architecture-flow.dot](./architecture-flow.dot)** - Source for flow diagram
- **[architecture-simple.dot](./architecture-simple.dot)** - Source for simplified diagram

## 🎯 Project Overview

### Problem
- 250+ government schemes with ₹1.2 lakh Cr allocated annually
- 40% of funds remain unclaimed due to literacy barriers
- 64% rural literacy rate, only 12% English fluency
- Current process: 4-6 hours with 18% completion rate

### Solution
Voice-first AI system that:
- Conducts natural conversations in 12+ Indian languages
- Matches citizens to eligible schemes through conversational AI
- Auto-fills government forms through guided questions
- Provides SMS confirmations with actionable checklists
- Follows up to ensure application completion

### Impact (6 Months Target)
- **Application Completion**: 18% → 72%
- **Time to Apply**: 4-6 hours → 8 minutes
- **Cost per Application**: ₹450 → ₹12
- **Unclaimed Benefits**: ₹48,000 Cr → ₹15,000 Cr

## 🏗️ Architecture Highlights

### Technology Stack
- **Voice Layer**: Amazon Connect, Transcribe, Polly
- **AI Layer**: Amazon Bedrock (Claude Sonnet 4), OpenSearch
- **Integration**: API Gateway, Lambda, SNS, EventBridge
- **Data**: DynamoDB, S3, RDS Aurora
- **Security**: KMS, Secrets Manager, IAM

### Key Features
- 12+ Indian language support with real-time translation
- 250+ government scheme database with semantic search
- Natural conversation flow with context retention
- Aadhaar-based identity verification
- Multi-state eDistrict integration
- Automated follow-up system

## 📊 Quick Stats

| Metric | Value |
|--------|-------|
| **Languages Supported** | 12+ Indian languages |
| **Schemes Covered** | 250+ central government schemes |
| **Target Call Duration** | 8-12 minutes |
| **System Uptime** | 99.5% |
| **Concurrent Calls** | 10,000 (scalable to 100,000) |
| **Cost per Call** | ₹12 |
| **Pilot Goal** | 50,000 applications in 3 months |

## 🚀 Getting Started

### For Developers
1. Read [requirements.md](./requirements.md) to understand user needs
2. Review [design.md](./design.md) for technical architecture
3. Check [architecture-diagram.md](./architecture-diagram.md) for visual references
4. Follow [tasks.md](./tasks.md) for implementation plan

### For Stakeholders
1. Review the Project Overview section above
2. View architecture diagrams for system understanding
3. Check success metrics in [requirements.md](./requirements.md)
4. Review cost analysis in [design.md](./design.md)

## 📞 Example Conversation Flow

```
User: Calls 1800-XXX-XXXX
AI: "नमस्ते! मैं वाणीसेतु हूं। आप किस योजना के बारे में जानना चाहते हैं?"
User: "मुझे बीज के लिए पैसा चाहिए"
AI: "ठीक है। आपके पास कितनी ज़मीन है?"
User: "2 एकड़"
AI: "अच्छा। आप 'राष्ट्रीय कृषि विकास योजना' के लिए योग्य हैं।
     आपको ₹3,000 मिल सकते हैं। क्या मैं आपकी मदद से फॉर्म भरूं?"
User: "हां"
[10 questions later...]
AI: "बस! आपका फॉर्म तैयार है। मैंने आपके फोन पर SMS भेजा है।"
```

## 🔐 Security & Compliance

- **Encryption**: AES-256 at rest, TLS 1.3 in transit
- **PII Protection**: Masking in logs, voice recordings deleted after transcription
- **Compliance**: IT Act 2000, Aadhaar Act 2016
- **Data Retention**: 90 days post-approval/rejection
- **Access Control**: Role-based IAM with least privilege

## 📈 Deployment Strategy

### Phase 1: MVP (Month 1-2)
- 1 state (UP), 1 language (Hindi), 10 schemes
- Goal: 1,000 successful applications

### Phase 2: Pilot (Month 3-4)
- 3 states (UP, TN, WB), 3 languages, 50 schemes
- Goal: 50,000 applications, 70% completion rate

### Phase 3: Full Launch (Month 5-6)
- 10 states, 12 languages, 250 schemes
- Goal: 500,000 applications, 72% completion rate

## 🛠️ Regenerating Diagrams

To regenerate the architecture diagrams from source:

```bash
# Navigate to the spec directory
cd .kiro/specs/vaani-setu

# Recommended diagrams (high quality, 200 DPI)
dot -Tpng architecture-final.dot -o architecture-final.png -Gdpi=200
dot -Tpng architecture-horizontal.dot -o architecture-horizontal.png -Gdpi=200

# Additional diagrams
dot -Tpng architecture-clean.dot -o architecture-clean.png -Gdpi=150
dot -Tpng architecture.dot -o architecture.png -Gdpi=150
dot -Tpng architecture-flow.dot -o architecture-flow.png -Gdpi=150
dot -Tpng architecture-simple.dot -o architecture-simple.png -Gdpi=150
```

**Note:** Requires Graphviz installed. On Windows: `winget install graphviz`

## 📝 Document Versions

- **Requirements**: v1.0 (February 8, 2026)
- **Design**: v1.0 (February 8, 2026)
- **Architecture Diagrams**: v1.1 (February 8, 2026) - Updated with professional layouts

## 👥 Team

- **Product Team**: Requirements and user research
- **Engineering Team**: Architecture and implementation
- **AI Team**: Conversational AI and NLP
- **Government Liaison**: Scheme database and API integration
- **Legal Team**: Compliance and data privacy

---

**Last Updated**: February 8, 2026  
**Project Status**: Design Phase Complete, Ready for Implementation
