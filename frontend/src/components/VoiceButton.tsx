import { useAppStore } from '../store/useAppStore';
import { cn } from '../lib/utils';

interface Props {
  onPress: () => void;
  onRelease: () => void;
}

export function VoiceButton({ onPress, onRelease }: Props) {
  const { isRecording, isProcessing, isPlaying } = useAppStore();

  const isActive = isRecording;
  const isDisabled = isProcessing || isPlaying;

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Voice visualization */}
      {isActive && (
        <div className="flex items-center gap-1 h-8">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="voice-indicator animate-voice-wave"
              style={{
                animationDelay: `${i * 0.15}s`,
                height: '4px',
              }}
            />
          ))}
        </div>
      )}

      {/* Main button */}
      <button
        onMouseDown={onPress}
        onMouseUp={onRelease}
        onMouseLeave={onRelease}
        onTouchStart={onPress}
        onTouchEnd={onRelease}
        disabled={isDisabled}
        className={cn(
          'relative w-14 h-14 sm:w-20 sm:h-20 rounded-full flex items-center justify-center',
          'transition-all duration-200 shadow-lg',
          isActive && 'scale-110',
          isDisabled
            ? 'bg-gray-300 cursor-not-allowed'
            : isActive
              ? 'bg-red-500 shadow-red-200'
              : 'bg-saffron hover:bg-saffron-dark shadow-orange-200 active:scale-95',
        )}
      >
        {/* Pulse ring when recording */}
        {isActive && (
          <div className="absolute inset-0 rounded-full bg-red-400 animate-pulse-ring opacity-40" />
        )}

        {/* Mic icon */}
        <svg
          className="w-8 h-8 text-white relative z-10"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          {isProcessing ? (
            // Loading dots
            <g>
              <circle cx="6" cy="12" r="1.5" fill="currentColor" className="animate-bounce" style={{ animationDelay: '0s' }} />
              <circle cx="12" cy="12" r="1.5" fill="currentColor" className="animate-bounce" style={{ animationDelay: '0.2s' }} />
              <circle cx="18" cy="12" r="1.5" fill="currentColor" className="animate-bounce" style={{ animationDelay: '0.4s' }} />
            </g>
          ) : (
            // Microphone
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z M19 10v2a7 7 0 0 1-14 0v-2 M12 19v4 M8 23h8"
            />
          )}
        </svg>
      </button>

      {/* Label */}
      <p className="text-sm text-gray-500 font-medium">
        {isProcessing
          ? 'Processing...'
          : isPlaying
            ? 'Speaking...'
            : isActive
              ? 'Listening...'
              : 'Hold to speak'}
      </p>
    </div>
  );
}
