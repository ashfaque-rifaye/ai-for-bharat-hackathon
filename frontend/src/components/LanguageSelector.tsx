import { useAppStore } from '../store/useAppStore';
import { LANGUAGES } from '../config';
import type { Language } from '../types';

interface Props {
  onSwitch?: (lang: Language) => void;
}

export function LanguageSelector({ onSwitch }: Props) {
  const { language, setLanguage } = useAppStore();

  const handleChange = (lang: Language) => {
    setLanguage(lang);
    onSwitch?.(lang);
  };

  return (
    <div className="flex gap-1 sm:gap-1.5 overflow-x-auto scrollbar-hide snap-x snap-mandatory -mx-1 px-1">
      {(Object.entries(LANGUAGES) as [Language, typeof LANGUAGES[Language]][]).map(
        ([code, info]) => (
          <button
            key={code}
            onClick={() => handleChange(code)}
            className={`
              snap-start shrink-0 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all
              ${language === code
                ? 'bg-saffron text-white shadow-sm'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }
            `}
          >
            {info.label}
          </button>
        )
      )}
    </div>
  );
}
