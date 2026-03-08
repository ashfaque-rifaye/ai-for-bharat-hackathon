# VaaniSetu — Demo Script (Hackathon Presentation)

## Presentation: 5 Minutes Total

---

## Slide 1: Problem (30 seconds)

**Title:** "₹48,000 Crore Goes Unclaimed Every Year"

**Script:**
> "India has 250+ government schemes spending ₹1.2 lakh crore annually. But 40% of these funds go unclaimed. Why? Because 64% of rural citizens can't read the forms, only 12% speak English, and it takes 4-6 hours of travel and queues to apply. The people who need these schemes most are the ones who can't access them."

---

## Slide 2: Solution (30 seconds)

**Title:** "VaaniSetu — Voice Bridge to Government Schemes"

**Script:**
> "VaaniSetu is a voice-first AI platform. Citizens call a toll-free number, speak in their own language — Hindi, Tamil, Bengali — and our AI understands their needs, matches them to eligible schemes, fills their forms through conversation, and sends an SMS with everything they need to complete the process. No literacy required. No English required. No smartphone required."

---

## Slide 3: Live Demo (2.5 minutes)

### Demo Scenario: Ramesh, a wheat farmer from Bihar

**Setup:** Open web demo, select Hindi

**Demo Flow:**

**[AI Greets - 10s]**
> 🤖 "नमस्ते! मैं वाणी सेतु हूँ, आपकी AI सहायक। मैं आपको सरकारी योजनाओं के बारे में बताने और आवेदन करने में मदद कर सकती हूँ। आपकी क्या मदद कर सकती हूँ?"
>
> ("Hello! I am VaaniSetu, your AI assistant. I can help you learn about government schemes and apply for them. How can I help you?")

**[User speaks - 5s]**
> 👨‍🌾 "मुझे खेती के लिए पैसे चाहिए" 
> ("I need money for farming")

**[AI asks profiling questions - 30s]**
> 🤖 "ज़रूर! आपकी मदद करने के लिए मुझे कुछ जानकारी चाहिए। आपके पास कितनी ज़मीन है?"
> ("Sure! I need some information to help you. How much land do you have?")

> 👨‍🌾 "2 एकड़" ("2 acres")

> 🤖 "आपकी सालाना आमदनी लगभग कितनी है?"
> ("What is your approximate annual income?")

> 👨‍🌾 "डेढ़ लाख" ("1.5 lakh")

> 🤖 "आपके परिवार में कितने सदस्य हैं?"
> ("How many members in your family?")

> 👨‍🌾 "पाँच" ("Five")

**[AI matches schemes - 20s]** *(Show scheme cards appearing on screen)*
> 🤖 "रमेश जी, आपके लिए 3 योजनाएं मिली हैं:
> 1. **पीएम किसान** — हर साल ₹6,000 तीन किश्तों में
> 2. **फसल बीमा** — आपकी फसल का बीमा कम प्रीमियम पर
> 3. **मृदा स्वास्थ्य कार्ड** — मुफ्त मिट्टी जांच
>
> क्या आप पीएम किसान के लिए आवेदन करना चाहेंगे?"

**[User selects scheme - 5s]**
> 👨‍🌾 "हाँ, पीएम किसान" ("Yes, PM Kisan")

**[AI fills form - 45s]** *(Show form progress bar filling up)*
> 🤖 "बहुत अच्छा! चलिए आवेदन भरते हैं। आपका पूरा नाम बताइए?"
> ("Great! Let's fill the application. What is your full name?")

> 👨‍🌾 "रमेश कुमार" ("Ramesh Kumar")

> 🤖 "आपका आधार नंबर?" ("Your Aadhaar number?")

> 👨‍🌾 "1234 5678 9012"

> 🤖 "आधार नंबर 1234-5678-9012, सही है?" ("Aadhaar 1234-5678-9012, correct?")

> 👨‍🌾 "हाँ" ("Yes")

> 🤖 "बैंक का नाम?" ("Bank name?")

> 👨‍🌾 "स्टेट बैंक" ("State Bank")

> *(Continue for remaining fields...)*
> *(Progress indicator: "अभी 3 और सवाल बाकी हैं" — "3 more questions remain")*

**[AI confirms and submits - 15s]**
> 🤖 "रमेश जी, आपकी जानकारी: नाम - रमेश कुमार, आधार - XXXX-XXXX-9012, बैंक - SBI, ज़मीन - 2 एकड़। सब सही है?"
> ("Ramesh ji, your information: Name - Ramesh Kumar, Aadhaar - XXXX-XXXX-9012, Bank - SBI, Land - 2 acres. All correct?")

> 👨‍🌾 "हाँ, सही है" ("Yes, correct")

**[Show SMS Preview - 10s]**
> 🤖 "आवेदन जमा हो गया! आपका आवेदन नंबर VS-2026-00123 है। SMS भेज दिया गया है।"

> 📱 **SMS Preview on screen:**
> ```
> वाणी सेतु - आवेदन पुष्टि
> आवेदन ID: VS-2026-00123
> योजना: पीएम किसान सम्मान निधि
> 
> ज़रूरी दस्तावेज़:
> ✅ आधार कार्ड
> ✅ खसरा/7/12 (ज़मीन का कागज़)
> ✅ बैंक पासबुक
> 
> जमा करें: ब्लॉक कार्यालय, सदर
> समय: सोम-शुक्र 10am-5pm
> काउंटर: 3 (कृषि विभाग)
> 
> हेल्पलाइन: 1800-XXX-XXXX
> ```

---

## Slide 4: Architecture (30 seconds)

**Title:** "Powered by AWS"

**Script:**
> "Under the hood, VaaniSetu uses Amazon Transcribe for real-time speech recognition in Indian languages, Amazon Bedrock with Claude for conversational AI and scheme matching via RAG, Amazon Polly for natural voice synthesis, and DynamoDB for session management. Everything is serverless — Lambda, API Gateway — so it scales from 1 to 100,000 calls automatically. Total cost: ₹12 per application versus ₹450 today."

**Show:** Architecture diagram with AWS service logos

---

## Slide 5: Impact & Future (30 seconds)

**Title:** "From ₹450 to ₹12 — 97% Cost Reduction"

**Script:**
> "In our pilot, we target 50,000 farmers completing applications in 3 months. That's ₹33 crore in benefits unlocked. 
>
> Next phase: expand to 12 languages, 250+ schemes, integrate with eDistrict for direct submission, and add Aadhaar OTP verification. Our vision: every Indian citizen, regardless of literacy or language, can access every benefit they deserve — just by making a phone call."

**End with:** "VaaniSetu — सबकी पहुँच, सबका अधिकार" (Access for all, Rights for all)

---

## Backup Slides (If Questions)

### Technical Questions
- **Q: How do you handle dialects?** → Transcribe handles major dialects; we fall back to nearest recognized language
- **Q: What about low-bandwidth areas?** → Voice calls work on 2G; no data needed
- **Q: How accurate is the AI?** → 90%+ STT accuracy, 95%+ scheme matching, human fallback at <70% confidence
- **Q: What about privacy?** → Voice deleted after transcription, PII encrypted, Aadhaar masked

### Business Questions
- **Q: How will you scale?** → Serverless auto-scales; add schemes via admin dashboard
- **Q: Cost at scale?** → ~$0.15/call at 1M calls/day
- **Q: What about state schemes?** → Phase 2; same architecture, add state scheme databases

---

## Demo Checklist (Before Presentation)

- [ ] Web demo deployed and accessible
- [ ] Microphone working
- [ ] Hindi Transcribe verified working
- [ ] Bedrock responses fast (<3s)
- [ ] Polly Hindi voice sounds natural
- [ ] SMS preview working
- [ ] Scheme data seeded (10 schemes)
- [ ] Test full flow once before demo
- [ ] Backup: Pre-recorded video if live demo fails
