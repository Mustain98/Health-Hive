"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useAuth } from "@/components/guards/AuthGuard";
import { logout } from "@/lib/auth";
import {
  User,
  LogOut,
  Bot,
  UtensilsCrossed,
  Stethoscope,
  TrendingUp,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";

const FEATURES = [
  {
    icon: Bot,
    title: "AI Plan Coach",
    desc: "Chat your way to a full plan — milestone, daily goals, nutrition target, and meals.",
    tint: "bg-emerald-50 text-emerald-600",
    ring: "hover:border-emerald-200",
  },
  {
    icon: UtensilsCrossed,
    title: "Smart meal plans",
    desc: "AI builds exact daily menus that actually hit your calories and macros.",
    tint: "bg-sky-50 text-sky-600",
    ring: "hover:border-sky-200",
  },
  {
    icon: Stethoscope,
    title: "Real experts",
    desc: "Book verified nutritionists and trainers, and meet them over live video.",
    tint: "bg-amber-50 text-amber-600",
    ring: "hover:border-amber-200",
  },
  {
    icon: TrendingUp,
    title: "Daily tracking",
    desc: "Log intake, watch your streaks, and see your deficit update in real time.",
    tint: "bg-violet-50 text-violet-600",
    ring: "hover:border-violet-200",
  },
];

export default function LandingPage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* Top Nav */}
      <header className="sticky top-0 z-30 border-b bg-white/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo is rendered by AppShell at top-left */}
            <div />
            <div className="flex items-center gap-2">
              {user ? (
                <div className="flex items-center gap-3">
                  <Link
                    href="/dashboard"
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    <User className="h-4 w-4" />
                    <span>{user.full_name || user.username}</span>
                  </Link>
                  <button
                    onClick={logout}
                    className="p-2 text-sm font-medium rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50"
                    title="Logout"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    Login
                  </Link>
                  <Link
                    href="/register"
                    className="px-4 py-2 text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700"
                  >
                    Get started
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute -top-32 left-1/2 h-80 w-[820px] -translate-x-1/2 rounded-full bg-emerald-100 blur-3xl opacity-70" />
          <div className="absolute top-24 left-1/3 h-72 w-[620px] -translate-x-1/2 rounded-full bg-teal-100 blur-3xl opacity-60" />
        </div>

        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-24 sm:py-28 text-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <span className="inline-flex items-center gap-2 rounded-full border bg-white px-3 py-1 text-xs font-medium text-emerald-700">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Your entire health journey — one hive
            </span>

            <h1 className="mt-6 text-4xl sm:text-6xl font-bold tracking-tight">
              Eat right, <span className="text-emerald-600">guided by AI</span>.
            </h1>

            <p className="mx-auto mt-5 max-w-xl text-lg text-gray-600 leading-relaxed">
              An AI coach builds your nutrition plan just by chatting with you —
              then real experts help keep you on track.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row justify-center gap-3">
              <Link
                href="/register"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-md text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700"
              >
                Get started <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/consultants"
                className="inline-flex items-center justify-center px-6 py-3 rounded-md text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
              >
                Browse experts
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Feature cards */}
      <section className="border-t bg-gray-50">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-16">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className={`rounded-2xl border bg-white p-6 shadow-sm transition-colors ${f.ring}`}
              >
                <div className={`inline-flex h-11 w-11 items-center justify-center rounded-xl ${f.tint}`}>
                  <f.icon className="h-5 w-5" />
                </div>
                <div className="mt-4 font-semibold">{f.title}</div>
                <p className="mt-1.5 text-sm text-gray-600 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust strip */}
      <section className="border-t bg-white">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-16 text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h2 className="mt-5 text-2xl sm:text-3xl font-bold">The AI drafts, you decide.</h2>
          <p className="mx-auto mt-3 max-w-xl text-gray-600 leading-relaxed">
            Nothing goes live until you approve it. And if a goal looks risky, Health Hive
            won&apos;t guess — it routes you to a real, verified professional.
          </p>
        </div>
      </section>

      {/* CTA + footer */}
      <section className="border-t bg-gray-50">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-14">
          <div className="rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 p-8 sm:p-10 text-white">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div>
                <h3 className="text-2xl font-bold">Start your journey today</h3>
                <p className="mt-2 text-white/90 text-sm">
                  Build a plan in one chat, then track it every day.
                </p>
              </div>
              <Link
                href="/register"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-md text-sm font-medium bg-white text-emerald-700 hover:bg-emerald-50 whitespace-nowrap"
              >
                Create account <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>

          <footer className="mt-10 text-center text-xs text-gray-500">
            © {new Date().getFullYear()} Health Hive — plan smart, eat right, stay accountable.
          </footer>
        </div>
      </section>
    </div>
  );
}
