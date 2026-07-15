import Link from "next/link";

/**
 * Health Hive brand mark: an emerald hexagon "hive" cell with a small bee accent,
 * plus the wordmark. Replaces the old plain blue "H" box.
 */
export function Logo({
  href = "/",
  showWord = true,
  size = 40,
}: {
  href?: string | null;
  showWord?: boolean;
  size?: number;
}) {
  const mark = (
    <span className="flex items-center gap-2">
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 drop-shadow-sm"
        aria-hidden
      >
        {/* Hexagon hive cell */}
        <path
          d="M20 2.5 33.5 10.25v15.5L20 33.5 6.5 25.75v-15.5L20 2.5Z"
          fill="hsl(158 64% 42%)"
        />
        <path
          d="M20 6 30.4 12v12L20 30 9.6 24V12L20 6Z"
          fill="hsl(158 64% 52%)"
        />
        {/* Bee body */}
        <ellipse cx="20" cy="19.5" rx="5.6" ry="4.2" fill="#fde68a" />
        <path d="M17 16.2h6M16.4 19.5h7.2M17 22.8h6" stroke="#1f2937" strokeWidth="1.4" strokeLinecap="round" />
        {/* Wings */}
        <ellipse cx="15.4" cy="15.6" rx="2.4" ry="1.6" fill="#ffffff" opacity="0.9" transform="rotate(-25 15.4 15.6)" />
        <ellipse cx="24.6" cy="15.6" rx="2.4" ry="1.6" fill="#ffffff" opacity="0.9" transform="rotate(25 24.6 15.6)" />
      </svg>
      {showWord && (
        <span className="text-xl font-bold tracking-tight text-gray-900">
          Health <span className="text-emerald-600">Hive</span>
        </span>
      )}
    </span>
  );

  if (!href) return mark;
  return (
    <Link href={href} className="flex items-center hover:opacity-80 transition-opacity">
      {mark}
    </Link>
  );
}
