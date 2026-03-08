import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { getText, cn } from '../lib/utils';
import { SCHEME_CATEGORIES } from '../config';
import type { SchemeMatch, Language } from '../types';

export function SchemeCards() {
    const { matchedSchemes, language, selectedScheme, setSelectedScheme } = useAppStore();
    const [collapsed, setCollapsed] = useState(false);

    if (matchedSchemes.length === 0) return null;

    return (
        <div className="px-3 sm:px-4 py-2 bg-white border-b border-gray-100">
            {/* Header row — tap to collapse */}
            <button
                onClick={() => setCollapsed(!collapsed)}
                className="w-full flex items-center justify-between mb-1"
            >
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {language === 'hi-IN' ? 'मिलती-जुलती योजनाएँ' : language === 'ta-IN' ? 'பொருத்தமான திட்டங்கள்' : 'Matched Schemes'}
                    <span className="ml-1.5 text-saffron">({matchedSchemes.length})</span>
                </h3>
                <svg
                    className={cn(
                        'w-4 h-4 text-gray-400 transition-transform',
                        collapsed && '-rotate-90',
                    )}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {/* Cards — collapsible */}
            {!collapsed && (
                <div className="flex gap-2 sm:gap-3 overflow-x-auto pb-2 -mx-1 px-1 snap-x snap-mandatory">
                    {matchedSchemes.map((scheme) => (
                        <SchemeCard
                            key={scheme.schemeId}
                            scheme={scheme}
                            language={language}
                            isSelected={selectedScheme === scheme.schemeId}
                            onSelect={() => setSelectedScheme(scheme.schemeId)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

function SchemeCard({
    scheme,
    language,
    isSelected,
    onSelect,
}: {
    scheme: SchemeMatch;
    language: Language;
    isSelected: boolean;
    onSelect: () => void;
}) {
    const categoryLabel = SCHEME_CATEGORIES[scheme.category]?.[language] || scheme.category;

    return (
        <button
            onClick={onSelect}
            className={cn(
                'flex-shrink-0 w-44 sm:w-56 bg-white rounded-xl border p-3 sm:p-4 text-left',
                'transition-all hover:shadow-md snap-start',
                isSelected
                    ? 'ring-2 ring-saffron border-saffron shadow-md'
                    : 'border-gray-100 shadow-sm',
            )}
        >
            {/* Category badge */}
            <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-medium bg-orange-50 text-saffron-dark mb-1.5">
                {categoryLabel}
            </span>

            {/* Name */}
            <h4 className="font-semibold text-xs sm:text-sm text-gray-900 line-clamp-2 mb-0.5">
                {getText(scheme.name, language)}
            </h4>

            {/* Description */}
            <p className="text-[10px] sm:text-xs text-gray-500 line-clamp-2">
                {getText(scheme.shortDescription, language)}
            </p>
        </button>
    );
}
