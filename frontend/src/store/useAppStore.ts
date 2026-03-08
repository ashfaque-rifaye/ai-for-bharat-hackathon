import { create } from 'zustand';
import type { Language, Message, ConversationState, SchemeMatch, FormProgress } from '../types';
import { DEFAULT_LANGUAGE } from '../config';

interface AppState {
  // Session
  sessionId: string | null;
  language: Language;
  conversationState: ConversationState;
  isConnected: boolean;

  // Messages
  messages: Message[];
  isProcessing: boolean;

  // Voice
  isRecording: boolean;
  isPlaying: boolean;
  autoPlayAudio: boolean;  // When true, TTS plays automatically for every AI response

  // Schemes
  matchedSchemes: SchemeMatch[];
  selectedScheme: string | null;

  // Form
  formProgress: FormProgress | null;
  applicationId: string | null;

  // Actions
  setSessionId: (id: string | null) => void;
  setLanguage: (lang: Language) => void;
  setConversationState: (state: ConversationState) => void;
  setConnected: (connected: boolean) => void;
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  setMessages: (messages: Message[]) => void;
  setProcessing: (processing: boolean) => void;
  setRecording: (recording: boolean) => void;
  setPlaying: (playing: boolean) => void;
  setAutoPlayAudio: (on: boolean) => void;
  setMatchedSchemes: (schemes: SchemeMatch[]) => void;
  setSelectedScheme: (schemeId: string | null) => void;
  setFormProgress: (progress: FormProgress | null) => void;
  setApplicationId: (id: string | null) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  language: DEFAULT_LANGUAGE,
  conversationState: 'GREETING' as ConversationState,
  isConnected: false,
  messages: [],
  isProcessing: false,
  isRecording: false,
  isPlaying: false,
  autoPlayAudio: true,  // Default ON — voice-first experience
  matchedSchemes: [],
  selectedScheme: null,
  formProgress: null,
  applicationId: null,
};

export const useAppStore = create<AppState>((set) => ({
  ...initialState,

  setSessionId: (id) => set({ sessionId: id }),
  setLanguage: (lang) => set({ language: lang }),
  setConversationState: (state) => set({ conversationState: state }),
  setConnected: (connected) => set({ isConnected: connected }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m,
      ),
    })),

  setMessages: (messages) => set({ messages }),
  setProcessing: (processing) => set({ isProcessing: processing }),
  setRecording: (recording) => set({ isRecording: recording }),
  setPlaying: (playing) => set({ isPlaying: playing }),
  setAutoPlayAudio: (on) => set({ autoPlayAudio: on }),
  setMatchedSchemes: (schemes) => set({ matchedSchemes: schemes }),
  setSelectedScheme: (schemeId) => set({ selectedScheme: schemeId }),
  setFormProgress: (progress) => set({ formProgress: progress }),
  setApplicationId: (id) => set({ applicationId: id }),

  reset: () => set(initialState),
}));
