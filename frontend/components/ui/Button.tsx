// frontend/components/ui/Button.tsx
"use client";

import { ButtonHTMLAttributes } from "react";
import clsx from "clsx";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
};

export function Button({ children, loading, className, ...rest }: Props) {
  return (
    <button
      {...rest}
      disabled={loading || rest.disabled}
      className={clsx(
        "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium",
        "border border-transparent bg-blue-600 text-white hover:bg-blue-700",
        "disabled:opacity-60 disabled:cursor-not-allowed",
        className
      )}
    >
      {loading ? "Loading..." : children}
    </button>
  );
}
