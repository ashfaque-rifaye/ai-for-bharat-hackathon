import { useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { apiService } from '../services/api';
import { cn, timeAgo, getText } from '../lib/utils';
import { SCHEME_CATEGORIES } from '../config';
import type { SchemeMatch, Language, FormProgress } from '../types';

// Small emoji indicators for Comprehend sentiment — visible on user bubbles
const SENTIMENT_EMOJI: Record<string, string> = {
    POSITIVE: '😊',
    NEGATIVE: '😟',
    MIXED: '🤔',
    NEUTRAL: '',
};

interface ChatTranscriptProps {
    /** Called when user clicks a scheme card — sends "I want to apply for X" */
    onSendMessage: (text: string) => void;
}

export function ChatTranscript({ onSendMessage }: ChatTranscriptProps) {
    const { messages, isProcessing, language, selectedScheme, setSelectedScheme } = useAppStore();
    const { updateMessage } = useAppStore();
    const audioPlayer = useAudioPlayer();
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isProcessing]);

    /**
     * Play / stop TTS for a specific assistant message.
     * If the message already has audio cached, plays it immediately.
     * Otherwise fetches from Polly first.
     */
    const handlePlayAudio = useCallback(
        async (msgId: string, text: string, existingAudio?: string, existingContentType?: string) => {
            if (audioPlayer.isMessagePlaying(msgId)) {
                audioPlayer.stop();
                return;
            }

            if (existingAudio) {
                audioPlayer.play(msgId, existingAudio, existingContentType || 'audio/mpeg');
                return;
            }

            try {
                const tts = await apiService.synthesizeSpeech(text, language);
                if (tts.audio) {
                    updateMessage(msgId, { audio: tts.audio, contentType: tts.contentType });
                    audioPlayer.play(msgId, tts.audio, tts.contentType);
                }
            } catch (err) {
                console.warn('TTS playback failed:', err);
            }
        },
        [audioPlayer, language, updateMessage],
    );

    /**
     * User clicked a scheme card → select it in the store AND send a message
     * to the AI so the conversation advances to the next step.
     */
    const handleSchemeSelect = useCallback(
        (scheme: SchemeMatch) => {
            setSelectedScheme(scheme.schemeId);
            const schemeName = getText(scheme.name, language);
            onSendMessage(`I want to apply for ${schemeName}`);
        },
        [language, onSendMessage, setSelectedScheme],
    );

    if (messages.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center text-gray-400">
                    <svg className="w-16 h-16 mx-auto mb-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <p className="text-lg font-medium">Start a conversation</p>
                    <p className="text-sm mt-1">Press the mic button or type a message</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
            <div className="max-w-3xl mx-auto">
                {messages.map((msg) => (
                    <div key={msg.id}>
                        {/* ── Message Bubble ─────────────────────── */}
                        <div
                            className={cn(
                                'flex gap-2 sm:gap-3 mb-3 sm:mb-4',
                                msg.role === 'user'
                                    ? 'ml-auto flex-row-reverse max-w-[90%] sm:max-w-[75%]'
                                    : 'max-w-[90%] sm:max-w-[80%]',
                            )}
                        >
                            {/* Avatar */}
                            <div
                                className={cn(
                                    'w-7 h-7 sm:w-8 sm:h-8 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] sm:text-xs font-bold',
                                    msg.role === 'assistant'
                                        ? 'bg-gradient-to-br from-saffron to-orange-600 text-white'
                                        : 'bg-gray-200 text-gray-600',
                                )}
                            >
                                {msg.role === 'assistant' ? 'VS' : 'You'}
                            </div>

                            {/* Bubble */}
                            <div
                                className={cn(
                                    'rounded-2xl px-3 py-2 sm:px-4 sm:py-3 shadow-sm',
                                    msg.role === 'assistant'
                                        ? 'bg-white border border-gray-100 rounded-tl-sm'
                                        : 'bg-saffron text-white rounded-tr-sm',
                                )}
                            >
                                <p className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                                {/* Footer row: time + sentiment badge + speaker button */}
                                <div className="flex items-center gap-2 mt-1">
                                    <p
                                        className={cn(
                                            'text-[9px] sm:text-[10px]',
                                            msg.role === 'assistant' ? 'text-gray-400' : 'text-orange-100',
                                        )}
                                    >
                                        {timeAgo(msg.timestamp)}
                                    </p>

                                    {msg.role === 'user' && msg.sentiment?.sentiment && (
                                        <span
                                            className="text-[10px] sm:text-xs opacity-80"
                                            title={`Mood: ${msg.sentiment.sentiment}`}
                                        >
                                            {SENTIMENT_EMOJI[msg.sentiment.sentiment] || ''}
                                        </span>
                                    )}

                                    {msg.role === 'assistant' && (
                                        <button
                                            onClick={() => handlePlayAudio(msg.id, msg.content, msg.audio, msg.contentType)}
                                            className="ml-auto p-1 rounded-full hover:bg-gray-100 transition-colors group"
                                            title="Play aloud"
                                            aria-label="Play this message aloud"
                                        >
                                            {audioPlayer.isMessagePlaying(msg.id) ? (
                                                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-saffron" fill="currentColor" viewBox="0 0 24 24">
                                                    <rect x="6" y="6" width="12" height="12" rx="1" />
                                                </svg>
                                            ) : (
                                                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-400 group-hover:text-saffron transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072M17.95 6.05a8 8 0 010 11.9M11 5L6 9H2v6h4l5 4V5z" />
                                                </svg>
                                            )}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* ── Inline Scheme Cards (below the AI message) ──── */}
                        {msg.role === 'assistant' && msg.metadata?.matchedSchemes && msg.metadata.matchedSchemes.length > 0 && (
                            <InlineSchemeCards
                                schemes={msg.metadata.matchedSchemes}
                                language={language}
                                selectedScheme={selectedScheme}
                                onSelect={handleSchemeSelect}
                            />
                        )}

                        {/* ── Inline Form Progress ──────────────────────── */}
                        {msg.role === 'assistant' && msg.metadata?.formProgress && (
                            <InlineFormProgress
                                progress={msg.metadata.formProgress}
                                language={language}
                            />
                        )}

                        {/* ── Application Confirmation ──────────────────── */}
                        {msg.role === 'assistant' && msg.metadata?.applicationId && (
                            <InlineApplicationConfirmation
                                applicationId={msg.metadata.applicationId}
                                language={language}
                            />
                        )}
                    </div>
                ))}

                {/* Typing indicator */}
                {isProcessing && (
                    <div className="flex gap-2 sm:gap-3 max-w-[80%]">
                        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-saffron to-orange-600 flex items-center justify-center text-white text-[10px] sm:text-xs font-bold flex-shrink-0">
                            VS
                        </div>
                        <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-3 py-2 sm:px-4 sm:py-3 shadow-sm">
                            <div className="flex gap-1.5">
                                <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
                                <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }} />
                                <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }} />
                            </div>
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>
        </div>
    );
}

/* ══════════════════════════════════════════════════════════════════════
 * Inline sub-components rendered INSIDE the chat flow
 * ══════════════════════════════════════════════════════════════════════ */

/**
 * InlineSchemeCards — Clickable scheme cards shown right below the AI's
 * "Here are your matched schemes" message. Clicking one sends:
 *   "I want to apply for {scheme name}"
 * which triggers the backend to advance to ELIGIBILITY_CHECK → FORM_FILL.
 */
function InlineSchemeCards({
    schemes,
    language,
    selectedScheme,
    onSelect,
}: {
    schemes: SchemeMatch[];
    language: Language;
    selectedScheme: string | null;
    onSelect: (scheme: SchemeMatch) => void;
}) {
    return (
        <div className="ml-9 sm:ml-11 mb-4">
            <p className="text-[10px] text-gray-500 uppercase tracking-wide font-semibold mb-2">
                {language === 'hi-IN' ? '👆 योजना चुनने के लिए टैप करें' : '👆 Tap a scheme to apply'}
            </p>
            <div className="flex gap-2 sm:gap-3 overflow-x-auto pb-2 snap-x snap-mandatory">
                {schemes.map((scheme) => {
                    const isSelected = selectedScheme === scheme.schemeId;
                    const categoryLabel = SCHEME_CATEGORIES[scheme.category]?.[language] || scheme.category;

                    return (
                        <button
                            key={scheme.schemeId}
                            onClick={() => onSelect(scheme)}
                            className={cn(
                                'flex-shrink-0 w-44 sm:w-56 rounded-xl border p-3 sm:p-4 text-left',
                                'transition-all hover:shadow-md snap-start',
                                isSelected
                                    ? 'ring-2 ring-saffron border-saffron shadow-md bg-orange-50'
                                    : 'border-gray-200 shadow-sm bg-white hover:border-saffron/50',
                            )}
                        >
                            {/* Category badge */}
                            <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-medium bg-orange-50 text-saffron-dark mb-1.5">
                                {categoryLabel}
                            </span>

                            {/* Match score */}
                            {scheme.matchScore > 0 && (
                                <span className="inline-block ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-green-50 text-green-700">
                                    {Math.round(scheme.matchScore * 100)}% match
                                </span>
                            )}

                            {/* Name */}
                            <h4 className="font-semibold text-xs sm:text-sm text-gray-900 line-clamp-2 mb-0.5 mt-1">
                                {getText(scheme.name, language)}
                            </h4>

                            {/* Description */}
                            <p className="text-[10px] sm:text-xs text-gray-500 line-clamp-2">
                                {getText(scheme.shortDescription, language)}
                            </p>

                            {/* Eligibility badge */}
                            {scheme.eligibility && (
                                <span className={cn(
                                    'inline-block mt-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium',
                                    scheme.eligibility === 'eligible'
                                        ? 'bg-green-50 text-green-700'
                                        : scheme.eligibility === 'likely_eligible'
                                            ? 'bg-yellow-50 text-yellow-700'
                                            : 'bg-gray-100 text-gray-600',
                                )}>
                                    {scheme.eligibility === 'eligible' ? '✓ Eligible' :
                                     scheme.eligibility === 'likely_eligible' ? '~ Likely Eligible' :
                                     scheme.eligibility}
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

/**
 * InlineFormProgress — Shows a progress bar for form filling right in the
 * chat flow, so the user sees "Field 3 of 10 — 30%" after each AI response.
 */
function InlineFormProgress({
    progress,
    language,
}: {
    progress: FormProgress;
    language: Language;
}) {
    if (progress.totalFields === 0) return null;

    const pct = progress.percentage || Math.round((progress.completedFields / progress.totalFields) * 100);

    return (
        <div className="ml-9 sm:ml-11 mb-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 max-w-xs">
                <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] sm:text-xs font-medium text-blue-800">
                        {language === 'hi-IN' ? '📝 फॉर्म प्रगति' : '📝 Form Progress'}
                    </span>
                    <span className="text-[10px] sm:text-xs text-blue-600 font-semibold">
                        {progress.completedFields}/{progress.totalFields} ({pct}%)
                    </span>
                </div>
                <div className="w-full bg-blue-100 rounded-full h-2 overflow-hidden">
                    <div
                        className="bg-blue-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                    />
                </div>
                {progress.currentField && (
                    <p className="text-[10px] text-blue-600 mt-1">
                        {language === 'hi-IN' ? 'अगला: ' : 'Next: '}
                        {typeof progress.currentField === 'object' && 'name' in progress.currentField
                            ? progress.currentField.name
                            : String(progress.currentField)}
                    </p>
                )}
            </div>
        </div>
    );
}

/**
 * InlineApplicationConfirmation — Shows a success card with the application ID
 * when the user reaches the COMPLETE state. This is the "wow moment."
 */
function InlineApplicationConfirmation({
    applicationId,
    language,
}: {
    applicationId: string;
    language: Language;
}) {
    return (
        <div className="ml-9 sm:ml-11 mb-4">
            <div className="bg-green-50 border border-green-300 rounded-xl px-4 py-3 max-w-sm shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">🎉</span>
                    <span className="text-sm font-bold text-green-800">
                        {language === 'hi-IN' ? 'आवेदन सफल!' : 'Application Submitted!'}
                    </span>
                </div>
                <div className="bg-white rounded-lg px-3 py-2 border border-green-200">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider">
                        {language === 'hi-IN' ? 'आवेदन संख्या' : 'Application ID'}
                    </p>
                    <p className="text-sm sm:text-base font-mono font-bold text-green-700 mt-0.5">
                        {applicationId}
                    </p>
                </div>
                <p className="text-[10px] text-green-600 mt-2">
                    {language === 'hi-IN'
                        ? '📌 इस नंबर को सुरक्षित रखें। SMS/WhatsApp अपडेट भी भेजे जाएंगे।'
                        : '📌 Save this number. You will also receive SMS/WhatsApp updates.'}
                </p>
            </div>
        </div>
    );
}
