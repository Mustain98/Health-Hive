// frontend/components/ui/Input.tsx
"use client";

import { InputHTMLAttributes } from "react";
import clsx from "clsx";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
};

export function Input({ label, error, className, ...rest }: Props) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <input
        {...rest}
        className={clsx(
          "block w-full rounded-md border border-gray-300 px-3 py-2 text-sm",
          "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
          className
        )}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
