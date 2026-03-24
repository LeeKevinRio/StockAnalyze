import { Skeleton } from '@/components/ui/skeleton';

export function Loading() {
  return (
    <div className="flex w-full flex-col items-center gap-6 py-12">
      {/* Spinning loader + text */}
      <div className="flex items-center gap-2 text-muted-foreground">
        <svg
          className="h-5 w-5 animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <span className="text-sm">載入中...</span>
      </div>

      {/* Skeleton rows mimicking content */}
      <div className="w-full max-w-2xl space-y-4 px-4">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <div className="flex gap-4 pt-2">
          <Skeleton className="h-24 w-1/3" />
          <Skeleton className="h-24 w-1/3" />
          <Skeleton className="h-24 w-1/3" />
        </div>
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-full" />
      </div>
    </div>
  );
}
