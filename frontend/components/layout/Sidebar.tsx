"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    Target,
    Utensils,
    CalendarDays,
    Users,
    Settings,
    Shield,
    UserPlus,
    LogOut
} from "lucide-react";
import { useAuth } from "@/components/guards/AuthGuard";
import { logout } from "@/lib/auth";

export function Sidebar({ isOpen }: { isOpen: boolean }) {
    const pathname = usePathname();
    const { user } = useAuth();

    const links = [
        { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
        { name: "Goal", href: "/goal", icon: Target },
        { name: "Nutrition", href: "/nutrition", icon: Utensils },
        { name: "Appointments", href: "/appointments", icon: CalendarDays },
        { name: "Consultants", href: "/consultants", icon: Users },
    ];

    return (
        <div
            className={`fixed left-0 top-16 h-[calc(100vh-4rem)] bg-white border-r flex flex-col justify-between overflow-y-auto transition-transform duration-300 ease-in-out w-64 z-20 ${isOpen ? "translate-x-0" : "-translate-x-full"
                }`}
        >
            <div className="px-4 py-6">    
                <nav className="space-y-1">
                    {links.map((link) => {
                        const Icon = link.icon;
                        const isActive = pathname === link.href || pathname?.startsWith(link.href + "/");
                        return (
                            <Link
                                key={link.href}
                                href={link.href}
                                className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors ${isActive
                                    ? "bg-blue-50 text-blue-700"
                                    : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                                    }`}
                            >
                                <Icon className={`h-5 w-5 ${isActive ? "text-blue-600" : "text-gray-400 group-hover:text-gray-500"}`} />
                                {link.name}
                            </Link>
                        );
                    })}

                    <div className="pt-4 mt-4 border-t border-gray-100">
                        {user?.user_type === 'consultant' ? (
                            <Link
                                href="/consultant/profile"
                                className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors ${pathname?.startsWith("/consultant") ? "bg-purple-50 text-purple-700" : "text-gray-700 hover:bg-gray-100"
                                    }`}
                            >
                                <Shield className="h-5 w-5" />
                                Consultant Portal
                            </Link>
                        ) : (
                            <Link
                                href="/apply-consultant"
                                className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors ${pathname === "/apply-consultant" ? "bg-green-50 text-green-700" : "text-gray-700 hover:bg-gray-100"
                                    }`}
                            >
                                <UserPlus className="h-5 w-5" />
                                Apply as Consultant
                            </Link>
                        )}
                    </div>
                </nav>
            </div>

            <div className="p-4 border-t bg-gray-50">
                <div className="flex items-center gap-3">
                    <div className="h-9 w-9 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-medium text-sm">
                        {user?.full_name?.charAt(0) || user?.username?.charAt(0) || "U"}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{user?.full_name || user?.username}</p>
                        <p className="text-xs text-gray-500 truncate capitalize">{user?.user_type}</p>
                    </div>
                    <button
                        onClick={logout}
                        className="text-gray-400 hover:text-red-600 p-1 rounded-full hover:bg-red-50 transition-colors"
                        title="Logout"
                    >
                        <LogOut className="h-5 w-5" />
                    </button>
                </div>
            </div>
        </div>
    );
}