"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import AuthGuard, { useAuth } from "@/components/guards/AuthGuard";
import { logout } from "@/lib/auth";

export default function UserLayout({ children }: { children: ReactNode }) {
    return (
        <AuthGuard>
            <div className="min-h-screen bg-gray-50">
                <UserNav />
                <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    {children}
                </main>
            </div>
        </AuthGuard>
    );
}

function UserNav() {
    const pathname = usePathname();
    const user = useAuth();

    const navItems = [
        { name: "Dashboard", href: "/dashboard" },
        { name: "Profile", href: "/profile" },
        { name: "Goal", href: "/goal" },
        { name: "Nutrition", href: "/nutrition" },
        { name: "Consultants", href: "/consultants" },
        { name: "Appointments", href: "/appointments" },
        { name: "Permissions", href: "/permissions" },
    ];

    return (
        <nav className="bg-white shadow">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                    <div className="flex">
                        <div className="flex-shrink-0 flex items-center">
                            <Link href="/dashboard" className="text-xl font-bold text-blue-600">
                                Health Hive
                            </Link>
                        </div>
                        <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                            {navItems.map((item) => (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`${pathname === item.href
                                        ? "border-blue-500 text-gray-900"
                                        : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                                        } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                                >
                                    {item.name}
                                </Link>
                            ))}
                        </div>
                    </div>
                    <div className="flex items-center space-x-4">
                        {user?.user_type === "consultant" ? (
                            <Link
                                href="/consultant/profile"
                                className="text-sm font-medium text-blue-600 hover:text-blue-500"
                            >
                                Consultant Portal
                            </Link>
                        ) : (
                            <Link
                                href="/apply-consultant"
                                className="text-sm font-medium text-green-600 hover:text-green-500"
                            >
                                Become a Consultant
                            </Link>
                        )}
                        <span className="text-sm text-gray-600">
                            {user?.full_name || user?.username}
                        </span>
                        <button
                            onClick={logout}
                            className="text-sm font-medium text-gray-500 hover:text-gray-700"
                        >
                            Logout
                        </button>
                    </div>
                </div>
            </div>
        </nav>
    );
}
