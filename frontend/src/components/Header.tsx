import { LanguageSelector } from './LanguageSelector';
import { useAppStore } from '../store/useAppStore';

export function Header() {
  const { isConnected } = useAppStore();

  return (
    <>
      {/* Tricolor border */}
      <div className="tricolor-border" />

      <header className="bg-white border-b border-gray-100 px-3 sm:px-4 py-2 sm:py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          {/* Branding */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Logo */}
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-saffron to-orange-600 flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-base sm:text-lg">व</span>
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-bold text-gray-900 leading-tight">
                वाणी सेतु
              </h1>
              <p className="text-[9px] sm:text-[10px] text-gray-400 font-medium tracking-wider uppercase">
                VaaniSetu
              </p>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2 sm:gap-3">
            <LanguageSelector />

            {/* Connection status dot */}
            <div className="hidden sm:flex items-center gap-1.5">
              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-gray-300'
                }`}
              />
              <span className="text-[10px] text-gray-400">
                {isConnected ? 'Live' : 'Offline'}
              </span>
            </div>
          </div>
        </div>
      </header>
    </>
  );
}
