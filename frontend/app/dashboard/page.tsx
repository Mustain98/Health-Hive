"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/components/guards/AuthGuard";
import type { DailyLogForm, PlanRead, UserDataRead } from "@/lib/types";
import {
  ListChecks,
  FolderKanban,
  Sparkles,
  ClipboardList,
  Users,
  Activity,
  CheckCircle2,
  Circle,
  ArrowRight,
  Flame,
  User as UserIcon,
} from "lucide-react";

const localDate = () => new Date().toLocaleDateString("en-CA");

const ACTIVITY_LABEL: Record<string, string> = {
  sedentary: "Sedentary",
  light: "Lightly active",
  moderate: "Moderately active",
  active: "Active",
  very_active: "Very active",
};

const QUICK_ACTIONS = [
  { href: "/plan-setup", icon: Sparkles, title: "Plan Setup (AI)", desc: "Chat to build or adjust your plan", primary: true },
  { href: "/meal-plan", icon: ClipboardList, title: "Meal Plan", desc: "See this week's menus" },
  { href: "/daily-goals", icon: ListChecks, title: "Log Today", desc: "Tick goals & log calories" },
  { href: "/consultants", icon: Users, title: "Find Experts", desc: "Book a verified consultant" },
];

function fadeIn(i: number) {
  return {
    initial: { opacity: 0, y: 14 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.35, delay: i * 0.06 },
  };
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [today, setToday] = useState<DailyLogForm | null>(null);
  const [activePlan, setActivePlan] = useState<PlanRead | null>(null);
  const [metrics, setMetrics] = useState<UserDataRead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [todayRes, plansRes, metricsRes] = await Promise.allSettled([
          apiFetch<DailyLogForm>(`/api/daily-goals/today?date=${localDate()}`).catch(() => null),
          apiFetch<PlanRead[]>("/api/plans").catch(() => []),
          apiFetch<UserDataRead>("/api/user-data/me").catch(() => null),
        ]);
        if (todayRes.status === "fulfilled") setToday(todayRes.value);
        if (plansRes.status === "fulfilled")
          setActivePlan((plansRes.value || []).find((p) => p.active) ?? null);
        if (metricsRes.status === "fulfilled") setMetrics(metricsRes.value);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="text-center py-16 text-gray-500">Loading…</div>;

  const goals = today?.daily_goals ?? [];
  const doneCount = goals.filter((g) => g.completed).length;
  const pct = goals.length ? Math.round((doneCount / goals.length) * 100) : 0;
  const deficit = today ? (today.calories_in ?? 0) - (today.calories_out ?? 0) : 0;
  const bmi =
    metrics?.weight_kg && metrics?.height_cm
      ? metrics.weight_kg / (metrics.height_cm / 100) ** 2
      : null;

  const firstName = (user?.full_name || user?.username || "").split(" ")[0];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          {firstName ? `Welcome back, ${firstName}` : "Dashboard"}
        </h1>
        <p className="mt-1 text-sm text-gray-500">Here's where things stand today.</p>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Today's goals */}
        <motion.section
          {...fadeIn(0)}
          className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <ListChecks className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-semibold text-gray-900">Today's goals</h2>
                <p className="text-xs text-gray-500">{doneCount} of {goals.length} done</p>
              </div>
            </div>
            <Link href="/daily-goals" className="text-sm font-medium text-emerald-600 hover:text-emerald-700 whitespace-nowrap">
              Log today →
            </Link>
          </div>

          {goals.length > 0 ? (
            <>
              <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-gray-100">
                <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${pct}%` }} />
              </div>
              <ul className="mt-4 space-y-2">
                {goals.slice(0, 5).map((g) => (
                  <li key={g.id} className="flex items-center gap-2 text-sm">
                    {g.completed ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                    ) : (
                      <Circle className="h-4 w-4 shrink-0 text-gray-300" />
                    )}
                    <span className={g.completed ? "text-gray-400 line-through" : "text-gray-700"}>{g.name}</span>
                    {g.target_value != null && (
                      <span className="ml-auto text-xs text-gray-400">
                        {g.value ?? 0}/{g.target_value} {g.unit ?? ""}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
              {(today?.calories_in || today?.calories_out) ? (
                <div className="mt-4 flex items-center gap-2 rounded-xl bg-gray-50 px-3 py-2 text-sm">
                  <Flame className="h-4 w-4 text-amber-500" />
                  <span className="text-gray-600">
                    {deficit <= 0 ? "Deficit" : "Surplus"}
                  </span>
                  <span className={`ml-auto font-semibold ${deficit <= 0 ? "text-emerald-600" : "text-red-500"}`}>
                    {deficit > 0 ? "+" : ""}{deficit} kcal
                  </span>
                </div>
              ) : null}
            </>
          ) : (
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-500">No goals scheduled for today.</p>
              <Link href="/daily-goals" className="mt-2 inline-block text-sm font-medium text-emerald-600 hover:text-emerald-700">
                Add a daily goal →
              </Link>
            </div>
          )}
        </motion.section>

        {/* Active plan overview */}
        <motion.section
          {...fadeIn(1)}
          className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <FolderKanban className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-semibold text-gray-900">Your plan</h2>
                <p className="text-xs text-gray-500">{activePlan ? activePlan.name : "No active plan"}</p>
              </div>
            </div>
            <Link href="/plans" className="text-sm font-medium text-emerald-600 hover:text-emerald-700 whitespace-nowrap">
              View →
            </Link>
          </div>

          {activePlan ? (
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Milestone</p>
                <p className="mt-0.5 text-gray-700">
                  {activePlan.milestone?.name || (activePlan.milestone?.milestone_type || "").replace(/_/g, " ") || "—"}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Nutrition</p>
                <p className="mt-0.5 text-gray-700">
                  {activePlan.nutrition_target
                    ? <>{activePlan.nutrition_target.calories_kcal} kcal <span className="text-gray-400">· P{Math.round(activePlan.nutrition_target.protein_g)} C{Math.round(activePlan.nutrition_target.carbs_g)} F{Math.round(activePlan.nutrition_target.fat_g)}</span></>
                    : "—"}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Meals / day</p>
                <p className="mt-0.5 text-gray-700">
                  {activePlan.meal_setting ? `${activePlan.meal_setting.timed_meals_per_day} · ${activePlan.meal_setting.name}` : "—"}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Daily goals</p>
                <p className="mt-0.5 text-gray-700">{activePlan.daily_goals.length}</p>
              </div>
              {activePlan.missing.length > 0 && (
                <div className="col-span-2 flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                  <span>Incomplete setup</span>
                  <Link href="/plan-setup" className="font-semibold hover:underline">Finish →</Link>
                </div>
              )}
            </div>
          ) : (
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-500">You don't have an active plan yet.</p>
              <Link href="/plan-setup" className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700">
                <Sparkles className="h-4 w-4" /> Build your plan with AI
              </Link>
            </div>
          )}
        </motion.section>
      </div>

      {/* Body metrics */}
      <motion.section
        {...fadeIn(2)}
        className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <Activity className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-semibold text-gray-900">Body metrics</h2>
              <p className="text-xs text-gray-500">Used to personalize your plan</p>
            </div>
          </div>
          <Link href="/profile" className="text-sm font-medium text-emerald-600 hover:text-emerald-700 whitespace-nowrap">
            Update →
          </Link>
        </div>

        {metrics && (metrics.age || metrics.weight_kg || metrics.height_cm || metrics.activity_level) ? (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Age", value: metrics.age != null ? `${metrics.age}` : "—" },
              { label: "Weight", value: metrics.weight_kg != null ? `${metrics.weight_kg} kg` : "—" },
              { label: "Height", value: metrics.height_cm != null ? `${metrics.height_cm} cm` : "—" },
              { label: "BMI", value: bmi != null ? bmi.toFixed(1) : "—" },
            ].map((m) => (
              <div key={m.label} className="rounded-xl bg-gray-50 p-3 text-center">
                <p className="text-lg font-bold text-gray-900">{m.value}</p>
                <p className="text-[11px] uppercase tracking-wide text-gray-400">{m.label}</p>
              </div>
            ))}
            <div className="col-span-2 sm:col-span-4 text-sm text-gray-500">
              Activity: <span className="text-gray-700">{metrics.activity_level ? ACTIVITY_LABEL[metrics.activity_level] : "not set"}</span>
            </div>
          </div>
        ) : (
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">Add your body metrics for a more accurate plan.</p>
            <Link href="/profile" className="mt-2 inline-block text-sm font-medium text-emerald-600 hover:text-emerald-700">
              Add metrics →
            </Link>
          </div>
        )}
      </motion.section>

      {/* Consultant portal banner */}
      {user?.user_type === "consultant" && (
        <div className="rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 p-6 text-white shadow-sm">
          <h2 className="text-xl font-bold">Consultant Portal</h2>
          <p className="mt-1 text-emerald-50 text-sm">Manage your clients, appointments, and applications.</p>
          <Link href="/consultant/profile" className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-white px-5 py-2.5 text-sm font-medium text-emerald-700 hover:bg-emerald-50">
            Go to Consultant Dashboard <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}

      {/* Quick actions */}
      <motion.section {...fadeIn(3)}>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">Quick actions</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {QUICK_ACTIONS.map((a) => (
            <Link
              key={a.href}
              href={a.href}
              className={`group rounded-2xl border p-5 transition-colors ${
                a.primary
                  ? "border-emerald-200 bg-emerald-50 hover:bg-emerald-100"
                  : "border-gray-100 bg-white hover:border-emerald-200"
              }`}
            >
              <span className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${a.primary ? "bg-emerald-600 text-white" : "bg-emerald-50 text-emerald-600"}`}>
                <a.icon className="h-5 w-5" />
              </span>
              <div className="mt-3 font-semibold text-gray-900">{a.title}</div>
              <p className="mt-0.5 text-sm text-gray-500">{a.desc}</p>
            </Link>
          ))}
        </div>
      </motion.section>
    </div>
  );
}
