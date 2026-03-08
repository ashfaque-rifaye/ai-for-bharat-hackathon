import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { MultiLangText, Language } from '../types';

/** Merge Tailwind classes safely */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Get text in the current language from a MultiLangText object */
export function getText(text: MultiLangText | string | undefined, language: Language): string {
  if (!text) return '';
  if (typeof text === 'string') return text;

  const langKey = language.split('-')[0] as 'hi' | 'en' | 'ta';
  return text[langKey] || text.hi || text.en || '';
}

/** Format time ago */
export function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
