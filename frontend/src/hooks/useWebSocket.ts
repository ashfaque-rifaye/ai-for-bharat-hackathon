import { useCallback, useEffect, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import { WS_ENDPOINT } from '../config';
import type { WSMessage, Language, ConversationState, SchemeMatch } from '../types';

/**
 * useWebSocket — manages the WebSocket connection for real-time voice/chat.
 */
export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);
  const {
    sessionId,
    language,
    setSessionId,
    setConnected,
    addMessage,
    setProcessing,
    setConversationState,
    setMatchedSchemes,
    setFormProgress,
    setApplicationId,
    setLanguage,
    setPlaying,
  } = useAppStore();

  // ── Connect ───────────────────────────────────────────────────────
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(WS_ENDPOINT);
    ws.current = socket;

    socket.onopen = () => {
      console.log('[WS] Connected');
      setConnected(true);
    };

    socket.onclose = () => {
      console.log('[WS] Disconnected');
      setConnected(false);
      // Auto-reconnect after 3s
      reconnectTimer.current = window.setTimeout(() => connect(), 3000);
    };

    socket.onerror = (err) => {
      console.error('[WS] Error:', err);
    };

    socket.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        handleMessage(msg);
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };
  }, []);

  // ── Handle incoming messages ──────────────────────────────────────
  const handleMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case 'sessionStarted':
        setSessionId(msg.sessionId ?? null);
        if (msg.language) setLanguage(msg.language as Language);
        break;

      case 'aiResponse':
        setProcessing(false);
        if (msg.text) {
          addMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: msg.text,
            timestamp: new Date().toISOString(),
            audio: msg.audio,
            contentType: msg.contentType,
          });
        }
        if (msg.conversationState) {
          setConversationState(msg.conversationState as ConversationState);
        }
        if (msg.matchedSchemes) {
          setMatchedSchemes(msg.matchedSchemes as SchemeMatch[]);
        }
        if (msg.formProgress) {
          setFormProgress(msg.formProgress);
        }
        if (msg.applicationId) {
          setApplicationId(msg.applicationId);
        }
        // Auto-play audio
        if (msg.audio && msg.contentType) {
          playAudio(msg.audio, msg.contentType);
        }
        break;

      case 'transcription':
        if (msg.text) {
          // Update last user message or add new
          addMessage({
            id: crypto.randomUUID(),
            role: 'user',
            content: msg.text,
            timestamp: new Date().toISOString(),
          });
        }
        break;

      case 'languageDetected':
        if (msg.language) setLanguage(msg.language as Language);
        break;

      case 'languageSwitched':
        if (msg.language) setLanguage(msg.language as Language);
        break;

      case 'sessionEnded':
        setSessionId(null);
        break;

      case 'error':
        console.error('[WS] Server error:', msg.message);
        setProcessing(false);
        break;
    }
  }, [addMessage, setSessionId, setProcessing, setConversationState, setMatchedSchemes, setFormProgress, setApplicationId, setLanguage]);

  // ── Play audio ────────────────────────────────────────────────────
  const playAudio = useCallback((audioB64: string, contentType: string) => {
    try {
      const audioBytes = Uint8Array.from(atob(audioB64), c => c.charCodeAt(0));
      const blob = new Blob([audioBytes], { type: contentType });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      setPlaying(true);
      audio.onended = () => {
        setPlaying(false);
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        setPlaying(false);
        URL.revokeObjectURL(url);
      };
      audio.play().catch(() => setPlaying(false));
    } catch (e) {
      console.error('Audio playback error:', e);
      setPlaying(false);
    }
  }, [setPlaying]);

  // ── Send functions ────────────────────────────────────────────────
  const startSession = useCallback((lang?: Language) => {
    send({ action: 'startSession', language: lang || language });
  }, [language]);

  const sendTextMessage = useCallback((text: string) => {
    setProcessing(true);
    addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    });
    send({ action: 'message', data: text, sessionId, language });
  }, [sessionId, language]);

  const sendAudioChunk = useCallback((audioB64: string) => {
    setProcessing(true);
    send({ action: 'audioChunk', data: audioB64, sessionId });
  }, [sessionId]);

  const switchLanguage = useCallback((lang: Language) => {
    send({ action: 'switchLanguage', language: lang, sessionId });
    setLanguage(lang);
  }, [sessionId]);

  const endSession = useCallback(() => {
    send({ action: 'endSession', sessionId });
  }, [sessionId]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      console.warn('[WS] Not connected, message dropped');
    }
  }, []);

  // ── Cleanup ───────────────────────────────────────────────────────
  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
    ws.current?.close();
    ws.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return {
    connect,
    disconnect,
    startSession,
    sendTextMessage,
    sendAudioChunk,
    switchLanguage,
    endSession,
    playAudio,
  };
}
