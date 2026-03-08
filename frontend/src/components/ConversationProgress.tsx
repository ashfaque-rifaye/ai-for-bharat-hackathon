import { useAppStore } from '../store/useAppStore';
import { CONVERSATION_STATE_LABELS } from '../config';

export function ConversationProgress() {
  const { conversationState, language, formProgress } = useAppStore();

  const states = [
    'GREETING',
    'NEED_ASSESSMENT',
    'SCHEME_MATCH',
    'ELIGIBILITY_CHECK',
    'FORM_FILL',
    'REVIEW',
    'SUBMIT',
    'COMPLETE',
  ];

  const currentIndex = states.indexOf(conversationState);

  return (
    <div className="px-3 sm:px-4 py-2 sm:py-3 bg-white border-b border-gray-100">
      {/* Progress bar */}
      <div className="flex items-center gap-0.5 sm:gap-1 mb-1.5">
        {states.map((state, i) => (
          <div
            key={state}
            className={`
              h-1 flex-1 rounded-full transition-all duration-300
              ${i <= currentIndex ? 'bg-saffron' : 'bg-gray-200'}
            `}
          />
        ))}
      </div>

      {/* Current state label */}
      <div className="flex justify-between items-center">
        <p className="text-[10px] sm:text-xs font-medium text-gray-600">
          {CONVERSATION_STATE_LABELS[conversationState]?.[language] || conversationState}
        </p>

        {/* Form progress if in FORM_FILL state */}
        {formProgress && conversationState === 'FORM_FILL' && (
          <p className="text-[10px] sm:text-xs text-gray-400">
            {formProgress.completedFields}/{formProgress.totalFields}
            {' '}
            ({formProgress.percentage}%)
          </p>
        )}
      </div>
    </div>
  );
}
