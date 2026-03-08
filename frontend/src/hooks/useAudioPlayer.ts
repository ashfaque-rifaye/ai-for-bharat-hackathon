/**
 * useAudioPlayer — thin wrapper around the browser's Audio API.
 *
 * Why a custom hook?
 *   We need a single shared Audio instance so that only one message plays at
 *   a time.  The hook exposes play / stop / isPlaying, and automatically
 *   updates the global Zustand `isPlaying` flag so the UI can react.
 */

import { useCallback, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';

export function useAudioPlayer() {
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const playingIdRef = useRef<string | null>(null);
    const { setPlaying } = useAppStore();

    /** Play a base64-encoded audio clip for a specific message ID. */
    const play = useCallback(
        (messageId: string, audioBase64: string, contentType: string = 'audio/mpeg') => {
            // Stop any currently-playing clip first
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }

            try {
                const audio = new Audio(`data:${contentType};base64,${audioBase64}`);

                audio.onplay = () => {
                    playingIdRef.current = messageId;
                    setPlaying(true);
                };

                audio.onended = () => {
                    playingIdRef.current = null;
                    setPlaying(false);
                };

                audio.onerror = () => {
                    playingIdRef.current = null;
                    setPlaying(false);
                };

                audioRef.current = audio;
                audio.play();
            } catch (err) {
                console.error('Audio playback failed:', err);
                setPlaying(false);
            }
        },
        [setPlaying],
    );

    /** Stop playback. */
    const stop = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        playingIdRef.current = null;
        setPlaying(false);
    }, [setPlaying]);

    /** Check whether a specific message is currently playing. */
    const isMessagePlaying = useCallback(
        (messageId: string) => playingIdRef.current === messageId,
        [],
    );

    return { play, stop, isMessagePlaying };
}
