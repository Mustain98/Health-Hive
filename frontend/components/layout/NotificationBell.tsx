"use client";

import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { NotificationRead } from "@/lib/types";

const targetFor = (n: NotificationRead) =>
    n.type === "setup_ready" ? "/plan-setup"
        : n.type === "daily_log" ? "/daily-goals"
            : n.type === "consult_referral" ? "/consultants"
                : "#";

export function NotificationBell() {
    const [unread, setUnread] = useState(0);
    const [open, setOpen] = useState(false);
    const [items, setItems] = useState<NotificationRead[]>([]);
    const ref = useRef<HTMLDivElement>(null);

    async function loadCount() {
        try {
            const r = await apiFetch<{ unread: number }>("/api/notifications/unread-count");
            setUnread(r.unread);
        } catch { /* ignore */ }
    }

    useEffect(() => {
        loadCount();
        const t = setInterval(loadCount, 30000); // poll
        return () => clearInterval(t);
    }, []);

    useEffect(() => {
        function onClick(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        }
        document.addEventListener("mousedown", onClick);
        return () => document.removeEventListener("mousedown", onClick);
    }, []);

    async function toggle() {
        const next = !open;
        setOpen(next);
        if (next) {
            try { setItems(await apiFetch<NotificationRead[]>("/api/notifications")); } catch { /* ignore */ }
        }
    }

    async function markRead(id: string) {
        try {
            await apiFetch(`/api/notifications/${id}/read`, { method: "PATCH" });
            setItems((p) => p.map((i) => (i.id === id ? { ...i, read: true } : i)));
            loadCount();
        } catch { /* ignore */ }
    }

    async function markAll() {
        try {
            await apiFetch("/api/notifications/read-all", { method: "POST" });
            setItems((p) => p.map((i) => ({ ...i, read: true })));
            setUnread(0);
        } catch { /* ignore */ }
    }

    return (
        <div className="relative" ref={ref}>
            <button
                onClick={toggle}
                className="relative p-2 rounded-md hover:bg-gray-200 text-gray-600 focus:outline-none"
                title="Notifications"
            >
                <Bell className="h-6 w-6" />
                {unread > 0 && (
                    <span className="absolute top-1 right-1 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
                        {unread > 9 ? "9+" : unread}
                    </span>
                )}
            </button>

            {open && (
                <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
                    <div className="flex items-center justify-between px-4 py-2 border-b sticky top-0 bg-white">
                        <span className="text-sm font-semibold text-gray-800">Notifications</span>
                        {items.some((i) => !i.read) && (
                            <button onClick={markAll} className="text-xs text-blue-600 hover:underline">
                                Mark all read
                            </button>
                        )}
                    </div>
                    {items.length === 0 ? (
                        <p className="px-4 py-6 text-sm text-gray-400 text-center">No notifications</p>
                    ) : (
                        items.map((n) => (
                            <a
                                key={n.id}
                                href={targetFor(n)}
                                onClick={() => markRead(n.id)}
                                className={`block px-4 py-3 border-b last:border-0 hover:bg-gray-50 ${n.read ? "" : "bg-blue-50/40"}`}
                            >
                                <p className="text-sm font-medium text-gray-900">{n.title}</p>
                                {n.body && <p className="text-xs text-gray-500 mt-0.5">{n.body}</p>}
                                <p className="text-[10px] text-gray-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
                            </a>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
