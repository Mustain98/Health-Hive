"use client";

import { ReactNode, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import AuthGuard, { useAuth } from "@/components/guards/AuthGuard";
import ConsultantGuard from "@/components/guards/ConsultantGuard";
import { logout } from "@/lib/auth";

export default function ConsultantLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <ConsultantGuard>
        <div className="min-h-screen bg-gray-50">
          <ConsultantNav />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
        </div>
      </ConsultantGuard>
    </AuthGuard>
  );
}

function ConsultantNav() {
  const pathname = usePathname();
  const user = useAuth();
  const [open, setOpen] = useState(false);

  const navItems = [
    { name: "My Profile", href: "/consultant/profile" },
    { name: "Applications", href: "/consultant/applications" },
    { name: "Appointments / Sessions", href: "/consultant/appointments" }, // ✅ clearer
  ];

  return (
    <nav className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center gap-3">
            <Link href="/consultant/profile" className="text-xl font-bold text-blue-600">
              Health Hive - Consultant
            </Link>

            {/* ✅ Mobile menu button */}
            <button
              className="sm:hidden px-3 py-2 rounded-md border text-sm"
              onClick={() => setOpen((v) => !v)}
            >
              Menu
            </button>
          </div>

          {/* Desktop nav */}
          <div className="hidden sm:flex sm:space-x-8 items-center">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`${
                  pathname === item.href
                    ? "border-blue-500 text-gray-900"
                    : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                {item.name}
              </Link>
            ))}
          </div>

          <div className="flex items-center space-x-4">
            <Link
              href="/dashboard"
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
            >
              User Portal
            </Link>
            <span className="text-sm text-gray-600">{user?.full_name || user?.username}</span>
            <button
              onClick={logout}
              className="text-sm font-medium text-gray-500 hover:text-gray-700"
            >
              Logout
            </button>
          </div>
        </div>

        {/* ✅ Mobile dropdown links */}
        {open && (
          <div className="sm:hidden pb-4 pt-2 space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`block px-3 py-2 rounded-md text-sm font-medium ${
                  pathname === item.href
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-700 hover:bg-gray-50"
                }`}
              >
                {item.name}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}
