import * as React from 'react';
import { cn } from '../../lib/utils';

export type TextareaProps =
  React.TextareaHTMLAttributes<HTMLTextAreaElement>;

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      className={cn(
        [
          'flex min-h-24 w-full rounded-md border border-[var(--at-rule-2)]',
          'bg-[var(--at-cream-elev)] px-3 py-2 font-sans text-sm text-[var(--at-ink-1)]',
          'placeholder:text-[var(--at-ink-4)]',
          'focus-visible:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/15',
          'disabled:cursor-not-allowed disabled:opacity-50',
        ],
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Textarea.displayName = 'Textarea';

export { Textarea };
