// ── Configuration ────────────────────────────────────────────────────

// ── API Mode ─────────────────────────────────────────────────────────
// Set VITE_API_MODE=local  → uses local mock server (port 4000)
// Set VITE_API_MODE=prod   → uses production AWS API Gateway
// Default: "prod" (uses the real Bedrock AI backend)
const API_MODE = import.meta.env.VITE_API_MODE || 'prod';
const isDev = import.meta.env.DEV;

const PROD_API = 'https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod';
const PROD_WS = 'wss://o4m08dq7pb.execute-api.us-east-1.amazonaws.com/prod';

export const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT
  || (API_MODE === 'local' ? (isDev ? '/api' : '') : PROD_API);

export const WS_ENDPOINT = import.meta.env.VITE_WS_ENDPOINT
  || (API_MODE === 'local' ? (isDev ? 'ws://localhost:4001' : '') : PROD_WS);

export const DEFAULT_LANGUAGE = 'hi-IN' as const;

export const LANGUAGES = {
  'hi-IN': { label: 'हिन्दी', labelEn: 'Hindi', flag: '🇮🇳' },
  'en-IN': { label: 'English', labelEn: 'English', flag: '🇮🇳' },
  'ta-IN': { label: 'தமிழ்', labelEn: 'Tamil', flag: '🇮🇳' },
  'bn-IN': { label: 'বাংলা', labelEn: 'Bengali', flag: '🇮🇳' },
  'te-IN': { label: 'తెలుగు', labelEn: 'Telugu', flag: '🇮🇳' },
  'mr-IN': { label: 'मराठी', labelEn: 'Marathi', flag: '🇮🇳' },
  'kn-IN': { label: 'ಕನ್ನಡ', labelEn: 'Kannada', flag: '🇮🇳' },
  'ml-IN': { label: 'മലയാളം', labelEn: 'Malayalam', flag: '🇮🇳' },
} as const;

export const CONVERSATION_STATE_LABELS: Record<string, Record<string, string>> = {
  GREETING: { 'hi-IN': 'स्वागत', 'en-IN': 'Welcome', 'ta-IN': 'வரவேற்பு', 'bn-IN': 'স্বাগতম', 'te-IN': 'స్వాగతం', 'mr-IN': 'स्वागत', 'kn-IN': 'ಸ್ವಾಗತ', 'ml-IN': 'സ്വാഗതം' },
  NEED_ASSESSMENT: { 'hi-IN': 'आवश्यकता जानना', 'en-IN': 'Need Assessment', 'ta-IN': 'தேவை மதிப்பீடு', 'bn-IN': 'প্রয়োজন মূল্যায়ন', 'te-IN': 'అవసర అంచనా', 'mr-IN': 'गरज मूल्यांकन', 'kn-IN': 'ಅಗತ್ಯ ಮೌಲ್ಯಮಾಪನ', 'ml-IN': 'ആവശ്യ വിലയിരുത്തൽ' },
  SCHEME_MATCH: { 'hi-IN': 'योजना खोज', 'en-IN': 'Scheme Match', 'ta-IN': 'திட்டப் பொருத்தம்', 'bn-IN': 'প্রকল্প অনুসন্ধান', 'te-IN': 'పథకం అన్వేషణ', 'mr-IN': 'योजना शोध', 'kn-IN': 'ಯೋಜನೆ ಹುಡುಕು', 'ml-IN': 'പദ്ധതി തിരയൽ' },
  ELIGIBILITY_CHECK: { 'hi-IN': 'पात्रता जाँच', 'en-IN': 'Eligibility Check', 'ta-IN': 'தகுதி சோதனை', 'bn-IN': 'যোগ্যতা যাচাই', 'te-IN': 'అర్హత తనిఖీ', 'mr-IN': 'पात्रता तपासणी', 'kn-IN': 'ಅರ್ಹತೆ ಪರಿಶೀಲನೆ', 'ml-IN': 'യോഗ്യത പരിശോധന' },
  FORM_FILL: { 'hi-IN': 'फॉर्म भरना', 'en-IN': 'Form Filling', 'ta-IN': 'படிவம் நிரப்புதல்', 'bn-IN': 'ফর্ম পূরণ', 'te-IN': 'ఫారం నింపడం', 'mr-IN': 'फॉर्म भरणे', 'kn-IN': 'ಫಾರ್ಮ್ ಭರ್ತಿ', 'ml-IN': 'ഫോം പൂരിപ്പിക്കൽ' },
  REVIEW: { 'hi-IN': 'समीक्षा', 'en-IN': 'Review', 'ta-IN': 'மதிப்பாய்வு', 'bn-IN': 'পর্যালোচনা', 'te-IN': 'సమీక్ష', 'mr-IN': 'आढावा', 'kn-IN': 'ವಿಮರ್ಶೆ', 'ml-IN': 'അവലോകനം' },
  SUBMIT: { 'hi-IN': 'जमा करना', 'en-IN': 'Submit', 'ta-IN': 'சமர்ப்பிக்கவும்', 'bn-IN': 'জমা দিন', 'te-IN': 'సమర్పించండి', 'mr-IN': 'सबमिट करा', 'kn-IN': 'ಸಲ್ಲಿಸಿ', 'ml-IN': 'സമർപ്പിക്കുക' },
  COMPLETE: { 'hi-IN': 'पूर्ण', 'en-IN': 'Complete', 'ta-IN': 'நிறைவடைந்தது', 'bn-IN': 'সম্পূর্ণ', 'te-IN': 'పూర్తయింది', 'mr-IN': 'पूर्ण', 'kn-IN': 'ಪೂರ್ಣ', 'ml-IN': 'പൂർത്തിയായി' },
};

export const SCHEME_CATEGORIES: Record<string, Record<string, string>> = {
  agriculture: { 'hi-IN': 'कृषि', 'en-IN': 'Agriculture', 'ta-IN': 'வேளாண்மை', 'bn-IN': 'কৃষি', 'te-IN': 'వ్యవసాయం', 'mr-IN': 'शेती', 'kn-IN': 'ಕೃಷಿ', 'ml-IN': 'കൃഷി' },
  housing: { 'hi-IN': 'आवास', 'en-IN': 'Housing', 'ta-IN': 'வீட்டுவசதி', 'bn-IN': 'আবাসন', 'te-IN': 'గృహనిర్మాణం', 'mr-IN': 'गृहनिर्माण', 'kn-IN': 'ವಸತಿ', 'ml-IN': 'ഭവനനിർമ്മാണം' },
  healthcare: { 'hi-IN': 'स्वास्थ्य', 'en-IN': 'Healthcare', 'ta-IN': 'சுகாதாரம்', 'bn-IN': 'স্বাস্থ্যসেবা', 'te-IN': 'ఆరోగ్యం', 'mr-IN': 'आरोग्य', 'kn-IN': 'ಆರೋಗ್ಯ', 'ml-IN': 'ആരോഗ്യം' },
  education: { 'hi-IN': 'शिक्षा', 'en-IN': 'Education', 'ta-IN': 'கல்வி', 'bn-IN': 'শিক্ষা', 'te-IN': 'విద్య', 'mr-IN': 'शिक्षण', 'kn-IN': 'ಶಿಕ್ಷಣ', 'ml-IN': 'വിദ്യാഭ്യാസം' },
  finance: { 'hi-IN': 'वित्त', 'en-IN': 'Finance', 'ta-IN': 'நிதி', 'bn-IN': 'অর্থ', 'te-IN': 'ఆర్థికం', 'mr-IN': 'वित्त', 'kn-IN': 'ಹಣಕಾಸು', 'ml-IN': 'ധനകാര്യം' },
  insurance: { 'hi-IN': 'बीमा', 'en-IN': 'Insurance', 'ta-IN': 'காப்பீடு', 'bn-IN': 'বীমা', 'te-IN': 'భీమా', 'mr-IN': 'विमा', 'kn-IN': 'ವಿಮೆ', 'ml-IN': 'ഇൻഷുറൻസ്' },
  food: { 'hi-IN': 'खाद्य', 'en-IN': 'Food', 'ta-IN': 'உணவு', 'bn-IN': 'খাদ্য', 'te-IN': 'ఆహారం', 'mr-IN': 'अन्न', 'kn-IN': 'ಆಹಾರ', 'ml-IN': 'ഭക്ഷണം' },
  energy: { 'hi-IN': 'ऊर्जा', 'en-IN': 'Energy', 'ta-IN': 'ஆற்றல்', 'bn-IN': 'শক্তি', 'te-IN': 'శక్తి', 'mr-IN': 'ऊर्जा', 'kn-IN': 'ಶಕ್ತಿ', 'ml-IN': 'ഊർജ്ജം' },
  savings: { 'hi-IN': 'बचत', 'en-IN': 'Savings', 'ta-IN': 'சேமிப்பு', 'bn-IN': 'সঞ্চয়', 'te-IN': 'పొదుపు', 'mr-IN': 'बचत', 'kn-IN': 'ಉಳಿತಾಯ', 'ml-IN': 'സമ്പാദ്യം' },
};
