import { useCallback, useEffect, useRef, useState } from 'react';
import { Header } from './components/Header';
import { ChatTranscript } from './components/ChatTranscript';
import { VoiceButton } from './components/VoiceButton';
import { TextInput } from './components/TextInput';
import { ConversationProgress } from './components/ConversationProgress';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { useWebSocket } from './hooks/useWebSocket';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { useAppStore } from './store/useAppStore';
import { apiService } from './services/api';

function App() {
  const {
    sessionId,
    language,
    isConnected,
    autoPlayAudio,
    setSessionId,
    addMessage,
    updateMessage,
    setProcessing,
    setConversationState,
    setMatchedSchemes,
    setFormProgress,
    setApplicationId,
    setRecording,
    setAutoPlayAudio,
    setLanguage,
  } = useAppStore();

  const ws = useWebSocket();
  const recorder = useAudioRecorder();
  const audioPlayer = useAudioPlayer();
  const [useVoice, setUseVoice] = useState(true);
  // WS mode disabled for now — REST with AI fallback is reliable
  const wsMode = false;
  const wsModeRef = useRef(false);  // Ref for synchronous reads in effects

  // ── Text-to-Speech helper ──────────────────────────────────────────
  // Fetches Polly audio for an assistant message, attaches it to the message,
  // and auto-plays if the user has the "read aloud" toggle enabled.
  const fetchAndPlayTTS = useCallback(
    async (messageId: string, text: string) => {
      try {
        const tts = await apiService.synthesizeSpeech(text, language);
        if (tts.audio) {
          updateMessage(messageId, { audio: tts.audio, contentType: tts.contentType });
          if (autoPlayAudio) {
            audioPlayer.play(messageId, tts.audio, tts.contentType);
          }
        }
      } catch (err) {
        console.warn('TTS fetch failed (non-blocking):', err);
      }
    },
    [language, autoPlayAudio, audioPlayer, updateMessage],
  );

  // ── Text message handler ──────────────────────────────────────────
  const handleSendText = useCallback(async (text: string) => {
    if (wsMode && isConnected) {
      ws.sendTextMessage(text);
    } else if (sessionId) {
      setProcessing(true);
      const userMsgId = crypto.randomUUID();
      addMessage({
        id: userMsgId,
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      });

      try {
        const result = await apiService.sendMessage(sessionId, text, language);
        setProcessing(false);

        if (result.sentiment) {
          updateMessage(userMsgId, { sentiment: result.sentiment as any });
        }

        const msgId = crypto.randomUUID();
        addMessage({
          id: msgId,
          role: 'assistant',
          content: result.response,
          timestamp: new Date().toISOString(),
          // Attach metadata so ChatTranscript can render inline UI:
          // scheme cards, form progress bar, application confirmation
          metadata: {
            matchedSchemes: result.matchedSchemes as any,
            formProgress: result.formProgress as any,
            applicationId: result.applicationId,
            conversationState: result.conversationState as any,
          },
        });

        fetchAndPlayTTS(msgId, result.response);

        if (result.conversationState) {
          setConversationState(result.conversationState as any);
        }
        if (result.matchedSchemes) {
          setMatchedSchemes(result.matchedSchemes as any);
        }
        if (result.formProgress) {
          setFormProgress(result.formProgress as any);
        }
        if (result.applicationId) {
          setApplicationId(result.applicationId);
        }
        if (result.detectedLanguage && result.detectedLanguage !== language) {
          setLanguage(result.detectedLanguage as any);
        }
      } catch (err) {
        setProcessing(false);
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '⚠️ Something went wrong. Please try again.',
          timestamp: new Date().toISOString(),
        });
      }
    }
  }, [wsMode, isConnected, sessionId, language, ws, fetchAndPlayTTS]);

  // ── Start session (REST) ──────────────────────────────────────────
  const { setConnected } = useAppStore();
  const startRestSession = useCallback(async () => {
    try {
      const session = await apiService.createSession(language);
      setSessionId(session.sessionId);
      setConnected(true);  // Mark as connected for the status dot in Header

      // Use the greeting returned by the backend (single source of truth)
      const greetingText = (session as any).greeting || 'Hello! I am VaaniSetu. How can I help you?';
      const msgId = crypto.randomUUID();
      addMessage({
        id: msgId,
        role: 'assistant',
        content: greetingText,
        timestamp: new Date().toISOString(),
      });

      // Auto-play the greeting via TTS
      fetchAndPlayTTS(msgId, greetingText);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  }, [language, fetchAndPlayTTS]);

  // ── Initialize ────────────────────────────────────────────────────
  // Guard against React StrictMode double-mount: without this ref,
  // startRestSession() fires twice → two greeting messages.
  const sessionStarted = useRef(false);
  useEffect(() => {
    if (sessionStarted.current) return;
    sessionStarted.current = true;
    startRestSession();
  }, []);

  // Auto-start WS session when connected (only fires in WS mode)
  useEffect(() => {
    if (wsModeRef.current && isConnected && !sessionId) {
      ws.startSession(language);
    }
  }, [isConnected, sessionId]);

  // ── Voice recording handlers ──────────────────────────────────────
  const handleVoicePress = useCallback(async () => {
    try {
      await recorder.startRecording();
      setRecording(true);
    } catch {
      console.error('Mic access denied');
    }
  }, [recorder]);

  const handleVoiceRelease = useCallback(async () => {
    setRecording(false);
    const audioB64 = await recorder.stopRecording();
    if (!audioB64) return;

    if (wsMode) {
      ws.sendAudioChunk(audioB64);
    } else {
      // REST fallback: transcribe audio via API, then send as text message
      try {
        setProcessing(true);
        const result = await apiService.transcribeAudio(audioB64, language);
        setProcessing(false);

        if (result.text && result.text.trim()) {
          // Auto-switch language if Transcribe detected a different one
          if (result.language && result.language !== language) {
            setLanguage(result.language as any);
          }
          // Show what the user said as a user message, then send it
          handleSendText(result.text.trim());
        } else {
          addMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: language === 'hi-IN'
              ? '⚠️ आवाज़ समझ नहीं आई। कृपया दोबारा बोलें।'
              : '⚠️ Could not understand the audio. Please try again.',
            timestamp: new Date().toISOString(),
          });
        }
      } catch (err) {
        setProcessing(false);
        console.error('Transcription failed:', err);
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: language === 'hi-IN'
            ? '⚠️ आवाज़ पहचान में त्रुटि। कृपया दोबारा प्रयास करें।'
            : '⚠️ Voice recognition error. Please try again.',
          timestamp: new Date().toISOString(),
        });
      }
    }
  }, [recorder, wsMode, ws, language, handleSendText, addMessage, setProcessing]);

  return (
    <div className="h-[100dvh] flex flex-col bg-gray-50">
      <Header />

      {/* Progress */}
      {sessionId && <ConversationProgress />}

      {/* Chat — schemes, form progress, and application status are rendered
          INLINE within the chat transcript, not as separate sections above */}
      <ChatTranscript onSendMessage={handleSendText} />

      {/* Analytics — fixed-position floating icon (bottom-left), not in layout flow */}
      <AnalyticsDashboard />

      {/* Input area — safe area inset for mobile notch/home bar */}
      <div className="bg-white border-t border-gray-100 px-3 sm:px-4 py-2 sm:py-4 pb-[env(safe-area-inset-bottom,8px)]">
        <div className="max-w-3xl mx-auto">
          {useVoice ? (
            <div className="flex items-end gap-2 sm:gap-4">
              <div className="flex-1 min-w-0">
                <TextInput onSend={handleSendText} />
              </div>
              <VoiceButton onPress={handleVoicePress} onRelease={handleVoiceRelease} />
            </div>
          ) : (
            <TextInput onSend={handleSendText} />
          )}

          {/* Toggle voice/text mode + auto-play toggle */}
          <div className="flex justify-center gap-4 mt-2 sm:mt-3">
            <button
              onClick={() => setUseVoice(!useVoice)}
              className="text-[10px] sm:text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              {useVoice ? 'Hide voice button' : 'Show voice button'}
            </button>
            <button
              onClick={() => setAutoPlayAudio(!autoPlayAudio)}
              className={`text-[10px] sm:text-xs transition-colors ${
                autoPlayAudio ? 'text-saffron hover:text-orange-700' : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              {autoPlayAudio ? '🔊 Auto-read ON' : '🔇 Auto-read OFF'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
