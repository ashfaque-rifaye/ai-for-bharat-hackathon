import type { Session, Scheme } from '../types';
import { API_ENDPOINT } from '../config';

/** Response shape from POST /benefit-summary */
export interface BenefitSummaryResponse {
    totalAnnualBenefit: number;
    eligibleCount: number;
    eligibleSchemes: {
        schemeId: string;
        name: string;
        category: string;
        benefitAmount: number;
        benefitDescription: string;
        confidence: number;
        missingInfo: string[];
    }[];
    synergies: {
        id: string;
        label: string;
        description: string;
        schemes: string[];
        allMatched: boolean;
    }[];
    summaryText: string;
}

/** Response shape from GET /analytics */
export interface AnalyticsResponse {
    totalSessions: number;
    activeSessions: number;
    averageMessagesPerSession: number;
    languageDistribution: Record<string, number>;
    conversationStateDistribution: Record<string, number>;
    topSchemes: { schemeId: string; count: number }[];
    totalMessages: number;
}

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_ENDPOINT;
  }

  // ── Sessions ──────────────────────────────────────────────────────

  async createSession(language: string = 'hi-IN', phoneNumber?: string): Promise<Session> {
    const res = await fetch(`${this.baseUrl}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language, phoneNumber }),
    });
    if (!res.ok) throw new Error(`Create session failed: ${res.status}`);
    return res.json();
  }

  async getSession(sessionId: string): Promise<Session> {
    const res = await fetch(`${this.baseUrl}/sessions/${sessionId}`);
    if (!res.ok) throw new Error(`Get session failed: ${res.status}`);
    return res.json();
  }

  async sendMessage(sessionId: string, message: string, language?: string): Promise<{
    response: string;
    conversationState?: string;
    matchedSchemes?: unknown[];
    formProgress?: unknown;
    applicationId?: string;
    sentiment?: { sentiment: string; scores: Record<string, number> };
    detectedLanguage?: string;
  }> {
    const res = await fetch(`${this.baseUrl}/sessions/${sessionId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, language }),
    });
    if (!res.ok) throw new Error(`Send message failed: ${res.status}`);
    return res.json();
  }

  // ── Schemes ───────────────────────────────────────────────────────

  async getSchemes(): Promise<Scheme[]> {
    const res = await fetch(`${this.baseUrl}/schemes`);
    if (!res.ok) throw new Error(`Get schemes failed: ${res.status}`);
    const data = await res.json();
    return data.schemes || data;
  }

  async getScheme(schemeId: string): Promise<Scheme> {
    const res = await fetch(`${this.baseUrl}/schemes/${schemeId}`);
    if (!res.ok) throw new Error(`Get scheme failed: ${res.status}`);
    return res.json();
  }

  async searchSchemes(query: string, language?: string): Promise<Scheme[]> {
    const res = await fetch(`${this.baseUrl}/schemes/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, language }),
    });
    if (!res.ok) throw new Error(`Search schemes failed: ${res.status}`);
    const data = await res.json();
    return data.schemes || data;
  }

  // ── Voice (Polly TTS + Transcribe STT) ─────────────────────────────

  async synthesizeSpeech(text: string, language: string = 'hi-IN'): Promise<{
    audio: string;
    contentType: string;
    language: string;
  }> {
    const res = await fetch(`${this.baseUrl}/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language, outputFormat: 'mp3' }),
    });
    if (!res.ok) throw new Error(`Synthesize speech failed: ${res.status}`);
    return res.json();
  }

  async transcribeAudio(audioBase64: string, language: string = 'hi-IN'): Promise<{
    text: string;
    language: string;
    confidence: number;
  }> {
    const res = await fetch(`${this.baseUrl}/transcribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio: audioBase64, language }),
    });
    if (!res.ok) throw new Error(`Transcribe audio failed: ${res.status}`);
    return res.json();
  }

  // ── Applications ──────────────────────────────────────────────────

  async getApplication(applicationId: string) {
    const res = await fetch(`${this.baseUrl}/applications/${applicationId}`);
    if (!res.ok) throw new Error(`Get application failed: ${res.status}`);
    return res.json();
  }

  // ── Benefit Stacking ─────────────────────────────────────────────

  async getBenefitSummary(
    sessionId: string,
    userProfile: Record<string, unknown>,
    language: string = 'hi-IN',
  ): Promise<BenefitSummaryResponse> {
    const res = await fetch(`${this.baseUrl}/benefit-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId, userProfile, language }),
    });
    if (!res.ok) throw new Error(`Benefit summary failed: ${res.status}`);
    return res.json();
  }

  // ── Analytics ──────────────────────────────────────────────────────

  async getAnalytics(): Promise<AnalyticsResponse> {
    const res = await fetch(`${this.baseUrl}/analytics`);
    if (!res.ok) throw new Error(`Get analytics failed: ${res.status}`);
    return res.json();
  }

  // ── PDF Generation ──────────────────────────────────────────────

  async generatePdf(
    type: 'benefit-summary' | 'application-confirmation',
    payload: {
      sessionId?: string;
      userProfile?: Record<string, unknown>;
      language?: string;
      applicationData?: Record<string, unknown>;
      schemeData?: Record<string, unknown>;
    },
  ): Promise<{ url: string; fileName: string; sizeBytes: number }> {
    const res = await fetch(`${this.baseUrl}/generate-pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type, ...payload }),
    });
    if (!res.ok) throw new Error(`Generate PDF failed: ${res.status}`);
    return res.json();
  }

  // ── Health ────────────────────────────────────────────────────────

  async healthCheck(): Promise<{ status: string }> {
    const res = await fetch(`${this.baseUrl}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return res.json();
  }
}

export const apiService = new ApiService();
