"use client";

import { useState } from "react";
import { useAuth } from "@/components/guards/AuthGuard";
import { Sidebar } from "./Sidebar";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
    const { user, loading } = useAuth();
    const [sidebarOpen, setSidebarOpen] = useState(true);

    if (loading) {
        return <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500">Loading application...</div>;
    }

    // If not logged in, just show content (likely login page)
    if (!user) {
        return <main className="min-h-screen bg-gray-50">{children}</main>;
    }

    return (
        <div className="min-h-screen bg-gray-50 flex">
            <Sidebar isOpen={sidebarOpen} />

            <div className={`flex-1 transition-all duration-300 ease-in-out ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
                {/* Top Bar for Toggle */}
                <header className="sticky top-0 z-10 bg-gray-50/80 backdrop-blur-sm px-4 py-3 flex items-center">
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="p-2 rounded-md hover:bg-gray-200 text-gray-600 focus:outline-none"
                        title="Toggle Sidebar"
                    >
                        <Menu className="h-6 w-6" />
                    </button>
                </header>

                <main className="max-w-7xl mx-auto px-8 pb-8 pt-2">
                    {children}
                </main>
            </div>
        </div>
    );
}
