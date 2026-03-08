/**
 * BenefitSummary — Shows combined eligible scheme benefits with synergies.
 *
 * This panel appears once the AI has matched schemes for the user.  It renders:
 *  1. A big "total annual benefit" number — the wow factor.
 *  2. A list of eligible schemes with individual amounts.
 *  3. Any detected synergy clusters (e.g. "Farmer Income Shield").
 *
 * It fetches data lazily from POST /benefit-summary when triggered.
 */

import { useCallback, useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { apiService, type BenefitSummaryResponse } from '../services/api';

/** Format a number in Indian comma grouping: 1,23,456 */
const formatINR = (n: number): string => {
    const s = n.toString();
    if (s.length <= 3) return s;
    const last3 = s.slice(-3);
    let rest = s.slice(0, -3);
    const groups: string[] = [];
    while (rest.length > 0) {
        groups.unshift(rest.slice(-2));
        rest = rest.slice(0, -2);
    }
    return groups.join(',') + ',' + last3;
};

export function BenefitSummary() {
    const { sessionId, language, matchedSchemes } = useAppStore();
    const [data, setData] = useState<BenefitSummaryResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [collapsed, setCollapsed] = useState(false);
    const [pdfLoading, setPdfLoading] = useState(false);

    // Fetch benefit summary whenever matched schemes change
    const fetchSummary = useCallback(async () => {
        if (!sessionId || matchedSchemes.length === 0) return;

        // Build a minimal user profile from matched schemes context
        // (The real profile lives server-side in the session)
        setLoading(true);
        setError(null);
        try {
            const result = await apiService.getBenefitSummary(
                sessionId,
                {}, // server will pull profile from session
                language,
            );
            setData(result);
        } catch (err) {
            console.warn('Benefit summary fetch failed:', err);
            setError('Could not load benefit summary');
        } finally {
            setLoading(false);
        }
    }, [sessionId, matchedSchemes.length, language]);

    useEffect(() => {
        fetchSummary();
    }, [fetchSummary]);

    // Don't render until there are matched schemes
    if (matchedSchemes.length === 0) return null;

    // Loading state
    if (loading && !data) {
        return (
            <div className="mx-3 sm:mx-4 mt-2">
                <div className="max-w-3xl mx-auto bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-4 animate-pulse">
                    <div className="h-4 bg-green-200 rounded w-1/3 mb-2" />
                    <div className="h-8 bg-green-200 rounded w-1/2" />
                </div>
            </div>
        );
    }

    if (!data || data.eligibleCount === 0) return null;

    const CATEGORY_EMOJI: Record<string, string> = {
        agriculture: '🌾',
        housing: '🏠',
        healthcare: '🏥',
        finance: '💰',
        food: '🍚',
        energy: '🔥',
        savings: '🏦',
        insurance: '🛡️',
        education: '📚',
    };

    return (
        <div className="mx-3 sm:mx-4 mt-2">
            <div className="max-w-3xl mx-auto bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl overflow-hidden">
                {/* Header — always visible */}
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-green-100/50 transition-colors"
                >
                    <div className="flex items-center gap-2">
                        <span className="text-lg">💡</span>
                        <span className="text-xs sm:text-sm font-semibold text-green-800">
                            {language.startsWith('hi') ? 'कुल वार्षिक लाभ' : 'Total Annual Benefits'}
                        </span>
                    </div>
                    <div className="flex items-center gap-3">
                        <span className="text-lg sm:text-xl font-bold text-green-700">
                            ₹{formatINR(data.totalAnnualBenefit)}
                        </span>
                        <span className="text-[10px] text-green-600 bg-green-100 px-1.5 py-0.5 rounded-full">
                            {data.eligibleCount} {language.startsWith('hi') ? 'योजनाएं' : 'schemes'}
                        </span>
                        <svg
                            className={`w-4 h-4 text-green-600 transition-transform ${collapsed ? '' : 'rotate-180'}`}
                            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                    </div>
                </button>

                {/* Expanded details */}
                {!collapsed && (
                    <div className="px-4 pb-3 space-y-3 border-t border-green-200">
                        {/* Scheme list */}
                        <div className="grid gap-2 mt-3">
                            {data.eligibleSchemes.map((s) => (
                                <div
                                    key={s.schemeId}
                                    className="flex items-center justify-between bg-white rounded-lg px-3 py-2 shadow-sm"
                                >
                                    <div className="flex items-center gap-2 min-w-0">
                                        <span className="text-sm">{CATEGORY_EMOJI[s.category] || '📋'}</span>
                                        <span className="text-xs sm:text-sm text-gray-700 truncate">{s.name}</span>
                                    </div>
                                    <span className="text-xs sm:text-sm font-semibold text-green-700 whitespace-nowrap ml-2">
                                        {s.benefitAmount > 0 ? `₹${formatINR(s.benefitAmount)}` : '—'}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Synergy clusters */}
                        {data.synergies.length > 0 && (
                            <div className="space-y-2">
                                <p className="text-[10px] sm:text-xs font-semibold text-green-800 uppercase tracking-wider">
                                    {language.startsWith('hi') ? '🔗 योजना सिनर्जी' : '🔗 Scheme Synergies'}
                                </p>
                                {data.synergies.map((syn) => (
                                    <div
                                        key={syn.id}
                                        className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
                                    >
                                        <p className="text-xs sm:text-sm font-medium text-amber-800">
                                            {syn.label}
                                            {syn.allMatched && (
                                                <span className="ml-1 text-[10px] bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded-full">
                                                    ✓ {language.startsWith('hi') ? 'पूर्ण' : 'Full Match'}
                                                </span>
                                            )}
                                        </p>
                                        <p className="text-[10px] sm:text-xs text-amber-700 mt-0.5">{syn.description}</p>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Error / retry */}
                        {error && (
                            <p className="text-xs text-red-500">{error}</p>
                        )}

                        {/* Download PDF Button */}
                        <button
                            onClick={async () => {
                                if (!sessionId) return;
                                setPdfLoading(true);
                                try {
                                    const result = await apiService.generatePdf('benefit-summary', {
                                        sessionId,
                                        userProfile: {},
                                        language,
                                    });
                                    window.open(result.url, '_blank');
                                } catch (err) {
                                    console.warn('PDF generation failed:', err);
                                } finally {
                                    setPdfLoading(false);
                                }
                            }}
                            disabled={pdfLoading}
                            className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white text-xs sm:text-sm font-medium rounded-lg px-4 py-2 transition-colors"
                        >
                            {pdfLoading ? (
                                <>
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                    </svg>
                                    {language.startsWith('hi') ? 'PDF बना रहे हैं...' : 'Generating PDF...'}
                                </>
                            ) : (
                                <>
                                    📄 {language.startsWith('hi') ? 'लाभ रिपोर्ट डाउनलोड करें' : 'Download Benefit Report'}
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
