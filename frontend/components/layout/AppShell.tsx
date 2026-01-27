"use client";

import { useState } from "react";
import { useAuth } from "@/components/guards/AuthGuard";
import { Sidebar } from "./Sidebar";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import Link from "next/link";

export function AppShell({ children }: { children: React.ReactNode }) {
    const { user, loading } = useAuth();
    const [sidebarOpen, setSidebarOpen] = useState(true);

    if (loading) {
        return <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500">Loading application...</div>;
    }

    // If not logged in, show with fixed logo but no sidebar
    if (!user) {
        return (
            <div className="min-h-screen bg-gray-50">
                {/* Fixed Logo */}
                <div className="fixed left-4 top-4 z-50">
                    <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <div className="h-10 w-10 bg-blue-600 rounded-lg flex items-center justify-center shadow-md">
                            <span className="text-white font-bold text-xl">H</span>
                        </div>
                        <span className="text-xl font-bold text-gray-900">Health Hive</span>
                    </Link>
                </div>
                <main className="min-h-screen">{children}</main>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 flex">
            {/* Fixed Top Bar with Logo and Toggle */}
            <div className="fixed top-0 left-0 right-0 h-16 bg-white border-b z-50 flex items-center px-4 gap-3">
                <button
                    onClick={() => setSidebarOpen(!sidebarOpen)}
                    className="p-2 rounded-md hover:bg-gray-200 text-gray-600 focus:outline-none"
                    title="Toggle Sidebar"
                >
                    <Menu className="h-6 w-6" />
                </button>
                
                <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                    <div className="h-10 w-10 bg-blue-600 rounded-lg flex items-center justify-center shadow-md">
                        <span className="text-white font-bold text-xl">H</span>
                    </div>
                    <span className="text-xl font-bold text-gray-900">Health Hive</span>
                </Link>
            </div>

            <Sidebar isOpen={sidebarOpen} />

            <div className={`flex-1 transition-all duration-300 ease-in-out ${sidebarOpen ? 'ml-64' : 'ml-0'} pt-16`}>
                <main className="max-w-7xl mx-auto px-8 pb-8 pt-6">
                    {children}
                </main>
            </div>
        </div>
    );
}