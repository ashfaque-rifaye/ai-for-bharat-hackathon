import { useState, type FormEvent } from 'react';
import { useAppStore } from '../store/useAppStore';

interface Props {
  onSend: (text: string) => void;
}

export function TextInput({ onSend }: Props) {
  const [text, setText] = useState('');
  const { isProcessing } = useAppStore();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isProcessing) return;
    onSend(text.trim());
    setText('');
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={useAppStore.getState().language === 'hi-IN' ? 'यहाँ टाइप करें...' : 'Type here...'}
        disabled={isProcessing}
        className="flex-1 min-w-0 px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl border border-gray-200 bg-white
                   text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-saffron/40 focus:border-saffron
                   disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <button
        type="submit"
        disabled={!text.trim() || isProcessing}
        className="px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl bg-saffron text-white font-medium text-sm
                   hover:bg-saffron-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </button>
    </form>
  );
}
