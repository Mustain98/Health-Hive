"use client";

import Link from "next/link";
import { useAuth } from "@/components/guards/AuthGuard";
import { logout } from "@/lib/auth";
import { User, LogOut } from "lucide-react";

export default function LandingPage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* Top Nav */}
      <header className="sticky top-0 z-30 border-b bg-white/80 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Empty space - logo is now fixed at top-left */}
            <div></div>

            <nav className="hidden md:flex items-center gap-6 text-sm">
              <a href="#features" className="text-gray-600 hover:text-gray-900">
                Features
              </a>
              <a href="#how" className="text-gray-600 hover:text-gray-900">
                How it works
              </a>
              <a href="#consultants" className="text-gray-600 hover:text-gray-900">
                For consultants
              </a>
            </nav>

            <div className="flex items-center gap-2">
              {user ? (
                // Show user profile when logged in
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
                // Show Login/Get started when not logged in
                <>
                  <Link
                    href="/login"
                    className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                  >
                    Login
                  </Link>
                  <Link
                    href="/register"
                    className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
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
          <div className="absolute -top-24 left-1/2 h-72 w-[800px] -translate-x-1/2 rounded-full bg-blue-100 blur-3xl" />
          <div className="absolute top-40 left-1/3 h-72 w-[700px] -translate-x-1/2 rounded-full bg-indigo-100 blur-3xl" />
        </div>

        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 sm:py-20">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium text-gray-700 bg-white">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                Manual goals & targets • Consultant sessions • Chat + notes
              </div>

              <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">
                Your nutrition journey,
                <span className="text-blue-600"> guided</span> and{" "}
                <span className="text-blue-600">trackable</span>.
              </h1>

              <p className="text-gray-600 text-base sm:text-lg leading-relaxed">
                Set your own goals and nutrition targets manually. Search verified
                consultants, apply for an appointment, and do sessions through chat
                with session notes — with permission-based updates to your goals and targets.
              </p>

              <div className="flex flex-col sm:flex-row gap-3">
                <Link
                  href="/register"
                  className="inline-flex items-center justify-center px-5 py-3 rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  Create account
                </Link>
                <Link
                  href="/consultants"
                  className="inline-flex items-center justify-center px-5 py-3 rounded-md text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                >
                  Browse consultants
                </Link>
              </div>

              <div className="text-xs text-gray-500">
                Consultants can only update your goal/targets if you grant permission.
              </div>
            </div>

            {/* Right card */}
            <div className="bg-white border rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div className="font-semibold">Quick preview</div>
                <div className="text-xs text-gray-500">MVP</div>
              </div>

              <div className="mt-4 grid gap-3">
                <div className="rounded-xl border p-4">
                  <div className="text-sm font-medium">Manual Goal</div>
                  <div className="mt-1 text-xs text-gray-600">
                    Lose / Gain / Maintain + duration
                  </div>
                </div>
                <div className="rounded-xl border p-4">
                  <div className="text-sm font-medium">Manual Nutrition Target</div>
                  <div className="mt-1 text-xs text-gray-600">
                    Calories + macros — editable anytime
                  </div>
                </div>
                <div className="rounded-xl border p-4">
                  <div className="text-sm font-medium">Consultant Session</div>
                  <div className="mt-1 text-xs text-gray-600">
                    Appointment → chat → session note
                  </div>
                </div>
                <div className="rounded-xl border p-4">
                  <div className="text-sm font-medium">Permission Control</div>
                  <div className="mt-1 text-xs text-gray-600">
                    Grant/revoke consultant access to update your targets
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t bg-gray-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
          <div className="max-w-2xl">
            <h2 className="text-2xl sm:text-3xl font-bold">Features</h2>
            <p className="mt-2 text-gray-600">
              Everything you need for manual goal tracking + consultant-guided sessions.
            </p>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                title: "Manual goals",
                desc: "You set and update your goal anytime. No automatic overrides.",
              },
              {
                title: "Manual targets",
                desc: "Calories and macros are editable anytime — simple and clear.",
              },
              {
                title: "Consultant search",
                desc: "Search consultants by name and view their profile details.",
              },
              {
                title: "Chat + notes",
                desc: "Run sessions via chat and store session notes per appointment.",
              },
            ].map((f) => (
              <div key={f.title} className="bg-white rounded-xl border p-5">
                <div className="font-semibold">{f.title}</div>
                <div className="mt-2 text-sm text-gray-600">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
          <h2 className="text-2xl sm:text-3xl font-bold">How it works</h2>
          <div className="mt-8 grid gap-4 lg:grid-cols-3">
            {[
              {
                step: "1",
                title: "Create account",
                desc: "Register and set your profile data, then add goal & nutrition target manually.",
              },
              {
                step: "2",
                title: "Find a consultant",
                desc: "Search a verified consultant, view profile, and apply for an appointment.",
              },
              {
                step: "3",
                title: "Do the session",
                desc: "Consultant schedules time → join chat → receive session note (optional visibility).",
              },
            ].map((s) => (
              <div key={s.step} className="rounded-2xl border p-6">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold">
                    {s.step}
                  </div>
                  <div className="font-semibold">{s.title}</div>
                </div>
                <div className="mt-3 text-sm text-gray-600">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Consultants */}
      <section id="consultants" className="border-t bg-gray-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <div>
              <h2 className="text-2xl sm:text-3xl font-bold">For consultants</h2>
              <p className="mt-2 text-gray-600">
                Manage your profile, accept applications, schedule sessions, chat, and write notes.
                Update client goals/targets only with permission.
              </p>

              <div className="mt-6 flex gap-3">
                <Link
                  href="/apply-consultant"
                  className="px-5 py-3 rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  Apply as consultant
                </Link>
                <Link
                  href="/consultant/profile"
                  className="px-5 py-3 rounded-md text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                >
                  Consultant portal
                </Link>
              </div>

              <div className="mt-3 text-xs text-gray-500">
                Verification can be managed manually in DB for now.
              </div>
            </div>

            <div className="bg-white border rounded-2xl shadow-sm p-6">
              <div className="font-semibold">Consultant workflow</div>
              <ol className="mt-4 space-y-3 text-sm text-gray-700">
                <li>• Create/update profile + add certificates</li>
                <li>• View appointment applications</li>
                <li>• Accept & schedule → join session chat</li>
                <li>• Write session notes (optional visible to user)</li>
                <li>• Update user goal/targets only if permission exists</li>
              </ol>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
          <div className="rounded-2xl border bg-gradient-to-r from-blue-600 to-indigo-600 p-8 text-white">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div>
                <h3 className="text-2xl font-bold">Start your journey today</h3>
                <p className="mt-2 text-white/90 text-sm">
                  Create a goal, set targets, and schedule a session with a consultant.
                </p>
              </div>
              <div className="flex gap-3">
                <Link
                  href="/register"
                  className="px-5 py-3 rounded-md text-sm font-medium bg-white text-blue-700 hover:bg-blue-50"
                >
                  Sign up
                </Link>
                <Link
                  href="/login"
                  className="px-5 py-3 rounded-md text-sm font-medium border border-white/30 hover:bg-white/10"
                >
                  Login
                </Link>
              </div>
            </div>
          </div>

          <footer className="mt-10 text-center text-xs text-gray-500">
            © {new Date().getFullYear()} Health Hive — manual goals, manual nutrition targets, consultant sessions.
          </footer>
        </div>
      </section>
    </div>
  );
}