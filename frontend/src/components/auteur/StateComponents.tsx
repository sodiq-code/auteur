/**
 * Auteur — shared UI state components (blueprint Section 30.4 design system).
 * Loading skeletons, empty states, error states — used across all views.
 */
"use client";

import { Loader2, AlertCircle, Film, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

// --------------------------------------------------------------------------- //
// Loading skeleton
// --------------------------------------------------------------------------- //

export function LoadingSkeleton({ rows = 3, className = "" }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="h-4 w-3/4 rounded bg-zinc-800" />
          <div className="mt-2 h-3 w-1/2 rounded bg-zinc-800/60" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="animate-pulse rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
      <div className="aspect-video rounded-md bg-zinc-800" />
      <div className="mt-3 h-4 w-2/3 rounded bg-zinc-800" />
      <div className="mt-2 h-3 w-1/2 rounded bg-zinc-800/60" />
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-8 text-sm text-zinc-500">
      <Loader2 className="h-4 w-4 animate-spin text-teal-400" />
      {label}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Empty state
// --------------------------------------------------------------------------- //

export function EmptyState({
  icon: Icon = Film,
  title = "Nothing here yet",
  description = "",
  ctaLabel,
  onCta,
}: {
  icon?: typeof Film;
  title?: string;
  description?: string;
  ctaLabel?: string;
  onCta?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-full bg-zinc-900 border border-zinc-800">
        <Icon className="h-5 w-5 text-zinc-600" />
      </div>
      <h3 className="mt-4 text-sm font-medium text-zinc-300">{title}</h3>
      {description && <p className="mt-1 max-w-xs text-xs text-zinc-500">{description}</p>}
      {ctaLabel && onCta && (
        <button
          onClick={onCta}
          className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-teal-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 transition hover:bg-teal-400"
        >
          {ctaLabel}
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Error state
// --------------------------------------------------------------------------- //

export function ErrorState({
  title = "Something went wrong",
  message = "",
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-full bg-amber-500/10 border border-amber-500/30">
        <AlertCircle className="h-5 w-5 text-amber-400" />
      </div>
      <h3 className="mt-4 text-sm font-medium text-amber-200">{title}</h3>
      {message && <p className="mt-1 max-w-xs text-xs text-amber-200/60">{message}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-300 transition hover:bg-amber-500/20"
        >
          <Loader2 className="h-3.5 w-3.5" />
          Try again
        </button>
      )}
    </div>
  );
}
