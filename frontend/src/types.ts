// ── Types for VaaniSetu frontend ─────────────────────────────────────

export type Language = 'hi-IN' | 'en-IN' | 'ta-IN' | 'bn-IN' | 'te-IN' | 'mr-IN' | 'kn-IN' | 'ml-IN';

export type ConversationState =
  | 'GREETING'
  | 'NEED_ASSESSMENT'
  | 'SCHEME_MATCH'
  | 'ELIGIBILITY_CHECK'
  | 'FORM_FILL'
  | 'REVIEW'
  | 'SUBMIT'
  | 'COMPLETE';

export interface SentimentResult {
  sentiment: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | 'MIXED';
  scores: {
    positive?: number;
    negative?: number;
    neutral?: number;
    mixed?: number;
  };
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  language?: Language;
  audio?: string;       // base64 encoded
  contentType?: string;
  sentiment?: SentimentResult;  // Comprehend sentiment on user messages
  metadata?: MessageMetadata;   // Inline UI data (schemes, form progress, etc.)
}

/**
 * Extra data attached to assistant messages so ChatTranscript can render
 * inline scheme cards, form progress bars, and application confirmations
 * right inside the chat flow.
 */
export interface MessageMetadata {
  matchedSchemes?: SchemeMatch[];
  formProgress?: FormProgress;
  applicationId?: string;
  conversationState?: ConversationState;
}

export interface Session {
  sessionId: string;
  language: Language;
  status: string;
  conversationState: ConversationState;
  conversationHistory: Message[];
  userProfile: Record<string, string>;
  matchedSchemes: SchemeMatch[];
  formData: Record<string, string>;
  createdAt: string;
}

export interface Scheme {
  schemeId: string;
  name: MultiLangText;
  description: MultiLangText;
  shortDescription: MultiLangText;
  category: string;
  benefits: SchemeBenefit[];
  eligibilityRules: EligibilityRule[];
  formFields: FormField[];
  requiredDocuments: RequiredDocument[];
}

export interface SchemeMatch {
  schemeId: string;
  name: MultiLangText;
  category: string;
  matchScore: number;
  eligibility: string;
  shortDescription: MultiLangText;
}

export interface MultiLangText {
  en: string;
  hi: string;
  ta: string;
  bn?: string;
  te?: string;
  mr?: string;
  kn?: string;
  ml?: string;
}

export interface SchemeBenefit {
  type: string;
  description: MultiLangText;
  amount?: string;
}

export interface EligibilityRule {
  field: string;
  operator: string;
  value: string | number | string[];
  description: MultiLangText;
}

export interface FormField {
  fieldId: string;
  name: string;
  type: string;
  required: boolean;
  question: MultiLangText;
  validation?: Record<string, unknown>;
}

export interface RequiredDocument {
  name: string;
  description: MultiLangText;
  mandatory: boolean;
}

export interface WSMessage {
  type: string;
  text?: string;
  audio?: string;
  contentType?: string;
  sessionId?: string;
  language?: Language;
  conversationState?: ConversationState;
  matchedSchemes?: SchemeMatch[];
  formProgress?: FormProgress;
  applicationId?: string;
  message?: string;
}

export interface FormProgress {
  totalFields: number;
  completedFields: number;
  currentField?: FormField;
  percentage: number;
}

export interface AppConfig {
  apiEndpoint: string;
  wsEndpoint: string;
  language: Language;
}
