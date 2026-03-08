import { useCallback, useEffect, useState } from 'react';
import { apiService, type AnalyticsResponse } from '../services/api';

/**
 * AnalyticsDashboard — Small floating icon (bottom-left) that opens a
 * popup panel with platform usage stats.
 *
 * Why: Hackathon judges can see real usage data on demand without it
 * cluttering the main chat interface.
 */

const LANGUAGE_LABELS: Record<string, string> = {
    'hi-IN': 'हिन्दी',
    'en-IN': 'English',
    'ta-IN': 'தமிழ்',
    'bn-IN': 'বাংলা',
    'te-IN': 'తెలుగు',
    'mr-IN': 'मराठी',
    'kn-IN': 'ಕನ್ನಡ',
    'ml-IN': 'മലയാളം',
    'hi': 'हिन्दी',
};

const STATE_LABELS: Record<string, string> = {
    GREETING: 'Greeting',
    NEED_ASSESSMENT: 'Need Assessment',
    SCHEME_MATCH: 'Scheme Matching',
    ELIGIBILITY_CHECK: 'Eligibility Check',
    FORM_FILL: 'Form Filling',
    REVIEW: 'Review',
    SUBMIT: 'Submission',
    COMPLETE: 'Complete',
    ERROR: 'Error',
};

export const AnalyticsDashboard = (): JSX.Element => {
    const [data, setData] = useState<AnalyticsResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [open, setOpen] = useState(false);
    const [error, setError] = useState('');

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const result = await apiService.getAnalytics();
            setData(result);
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch once when panel is first opened
    useEffect(() => {
        if (open && !data && !loading) {
            fetchData();
        }
    }, [open, data, loading, fetchData]);

    const fmt = (n: number): string => n.toLocaleString('en-IN');

    const barPct = (count: number, total: number): string =>
        total > 0 ? `${Math.round((count / total) * 100)}%` : '0%';

    return (
        <>
            {/* ── Small floating icon (bottom-left) ────────────────── */}
            <button
                onClick={() => setOpen(!open)}
                className="fixed bottom-4 left-4 z-50 w-10 h-10 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg flex items-center justify-center transition-all hover:scale-110"
                title="Platform Analytics"
                aria-label="Toggle analytics panel"
            >
                <span className="text-sm">📊</span>
            </button>

            {/* ── Floating popup panel ─────────────────────────────── */}
            {open && (
                <>
                    {/* Backdrop — click to close */}
                    <div
                        className="fixed inset-0 z-40 bg-black/20"
                        onClick={() => setOpen(false)}
                    />

                    <div className="fixed bottom-16 left-4 z-50 w-80 sm:w-96 max-h-[70vh] overflow-y-auto bg-white border border-indigo-200 rounded-xl shadow-2xl">
                        {/* Panel header */}
                        <div className="flex items-center justify-between px-4 py-3 border-b border-indigo-100 bg-indigo-50 rounded-t-xl sticky top-0">
                            <span className="text-sm font-semibold text-indigo-800 flex items-center gap-2">
                                📊 Platform Analytics
                            </span>
                            <button
                                onClick={() => setOpen(false)}
                                className="text-indigo-400 hover:text-indigo-700 transition-colors"
                                aria-label="Close analytics"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        <div className="p-3 sm:p-4">
                            {loading && (
                                <div className="flex items-center gap-2 text-sm text-gray-500">
                                    <div className="animate-spin w-4 h-4 border-2 border-indigo-300 border-t-indigo-600 rounded-full" />
                                    Loading analytics...
                                </div>
                            )}

                            {error && (
                                <div className="text-sm text-red-600">
                                    Error: {error}
                                    <button onClick={fetchData} className="ml-2 underline">Retry</button>
                                </div>
                            )}

                            {data && !loading && (
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-2">
                                        <MetricCard label="Total Sessions" value={fmt(data.totalSessions)} icon="🗂️" />
                                        <MetricCard label="Active Sessions" value={fmt(data.activeSessions)} icon="🟢" />
                                        <MetricCard label="Total Messages" value={fmt(data.totalMessages)} icon="💬" />
                                        <MetricCard label="Avg Msgs/Session" value={String(data.averageMessagesPerSession)} icon="📈" />
                                    </div>

                                    <div>
                                        <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                                            Language Distribution
                                        </h4>
                                        <div className="space-y-1.5">
                                            {Object.entries(data.languageDistribution)
                                                .sort((a, b) => b[1] - a[1])
                                                .map(([lang, count]) => (
                                                    <div key={lang} className="flex items-center gap-2 text-xs">
                                                        <span className="w-16 text-gray-600 truncate">
                                                            {LANGUAGE_LABELS[lang] || lang}
                                                        </span>
                                                        <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
                                                            <div
                                                                className="bg-indigo-400 h-full rounded-full transition-all"
                                                                style={{ width: barPct(count, data.totalSessions) }}
                                                            />
                                                        </div>
                                                        <span className="w-8 text-right text-gray-500">{count}</span>
                                                    </div>
                                                ))}
                                        </div>
                                    </div>

                                    {data.topSchemes.length > 0 && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                                                Top Schemes
                                            </h4>
                                            <div className="space-y-1.5">
                                                {data.topSchemes.map(({ schemeId, count }) => (
                                                    <div key={schemeId} className="flex items-center gap-2 text-xs">
                                                        <span className="w-32 text-gray-600 truncate font-mono">
                                                            {schemeId}
                                                        </span>
                                                        <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
                                                            <div
                                                                className="bg-saffron h-full rounded-full transition-all"
                                                                style={{ width: barPct(count, data.topSchemes[0].count) }}
                                                            />
                                                        </div>
                                                        <span className="w-8 text-right text-gray-500">{count}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    <div>
                                        <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                                            Conversation Funnel
                                        </h4>
                                        <div className="flex flex-wrap gap-2">
                                            {Object.entries(data.conversationStateDistribution)
                                                .sort((a, b) => b[1] - a[1])
                                                .map(([state, count]) => (
                                                    <span
                                                        key={state}
                                                        className="inline-flex items-center gap-1 bg-gray-100 rounded-full px-2.5 py-1 text-xs text-gray-700"
                                                    >
                                                        {STATE_LABELS[state] || state}
                                                        <span className="bg-indigo-200 text-indigo-800 rounded-full px-1.5 text-[10px] font-medium">
                                                            {count}
                                                        </span>
                                                    </span>
                                                ))}
                                        </div>
                                    </div>

                                    <button
                                        onClick={fetchData}
                                        className="text-xs text-indigo-500 hover:text-indigo-700 underline"
                                    >
                                        ↻ Refresh
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </>
    );
};

/** Small stat card for top-line metrics. */
const MetricCard = ({ label, value, icon }: { label: string; value: string; icon: string }): JSX.Element => (
    <div className="bg-gradient-to-br from-indigo-50 to-white border border-indigo-100 rounded-lg p-2.5 text-center">
        <div className="text-lg">{icon}</div>
        <div className="text-lg font-bold text-indigo-900">{value}</div>
        <div className="text-[10px] text-gray-500 leading-tight">{label}</div>
    </div>
);
