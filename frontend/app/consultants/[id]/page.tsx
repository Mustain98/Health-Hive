"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/components/guards/AuthGuard";
import type { ConsultantPublicRead, FreeWindowResponse, AppointmentApplicationCreate } from "@/lib/types";

export default function ConsultantDetailPage() {
    const params = useParams();
    const router = useRouter();
    const consultantId = params.id as string;
    const { user } = useAuth();

    const [consultant, setConsultant] = useState<ConsultantPublicRead | null>(null);
    const [loading, setLoading] = useState(true);
    const [selectedDate, setSelectedDate] = useState<string>("");
    const [freeWindows, setFreeWindows] = useState<FreeWindowResponse[]>([]);
    const [loadingWindows, setLoadingWindows] = useState(false);
    const [selectedWindow, setSelectedWindow] = useState<FreeWindowResponse | null>(null);
    const [selectedTime, setSelectedTime] = useState<string>("");
    const [note, setNote] = useState("");
    const [applying, setApplying] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    // Generate next 7 days
    const availableDates = Array.from({ length: 7 }, (_, i) => {
        const date = new Date();
        date.setDate(date.getDate() + i);
        return date.toISOString().split("T")[0];
    });

    useEffect(() => {
        if (availableDates.length > 0) {
            setSelectedDate(availableDates[0]);
        }
    }, []);

    useEffect(() => {
        async function loadConsultant() {
            if (!consultantId) return;

            try {
                const data = await apiFetch<ConsultantPublicRead>(`/api/consultants/${consultantId}`);
                setConsultant(data);
            } catch (error: any) {
                setMessage(`Error loading consultant: ${error.message}`);
            } finally {
                setLoading(false);
            }
        }
        loadConsultant();
    }, [consultantId]);

    function fixDate(d: string): string {
        return d.endsWith("Z") ? d : d + "Z";
    }

    useEffect(() => {
        async function loadFreeWindows() {
            if (!consultantId || !selectedDate) return;

            setLoadingWindows(true);
            setFreeWindows([]);
            setSelectedWindow(null);
            setSelectedTime("");

            try {
                const windows = await apiFetch<FreeWindowResponse[]>(
                    `/api/consultants/${consultantId}/free-windows?date=${selectedDate}`
                );
                // Fix timezone interpretation
                const fixedWindows = windows.map(w => ({
                    start: fixDate(w.start),
                    end: fixDate(w.end)
                }));

                setFreeWindows(fixedWindows);
            } catch (error: any) {
                console.error("Failed to load free windows:", error);
            } finally {
                setLoadingWindows(false);
            }
        }
        loadFreeWindows();
    }, [consultantId, selectedDate]);

    function formatTime(isoString: string): string {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    function formatDate(dateString: string): string {
        const date = new Date(dateString);
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        if (date.toDateString() === today.toDateString()) return "Today";
        if (date.toDateString() === tomorrow.toDateString()) return "Tomorrow";

        return date.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
    }

    function toLocalISOString(date: Date): string {
        const pad = (n: number) => n.toString().padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }

    async function handleApply() {
        if (!consultant || !selectedTime) return;

        setApplying(true);
        setMessage(null);

        try {
            const application: AppointmentApplicationCreate = {
                consultant_user_id: consultant.user_id,
                requested_start_at: selectedTime,
                note_from_user: note || null,
            };

            await apiFetch("/api/appointments/applications", {
                method: "POST",
                body: application,
            });

            setMessage("Application submitted successfully!");
            setTimeout(() => {
                router.push("/me/applications");
            }, 1500);
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setApplying(false);
        }
    }

    if (loading) {
        return <div className="text-center py-12">Loading consultant profile...</div>;
    }

    if (!consultant) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-500">Consultant not found</p>
                <Link href="/consultants" className="text-blue-600 hover:text-blue-500 mt-4 inline-block">
                    ← Back to consultants
                </Link>
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto p-6 space-y-6">
            <Link href="/consultants" className="text-sm text-blue-600 hover:text-blue-500">
                ← Back to consultants
            </Link>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {/* Profile */}
            <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">{consultant.display_name}</h1>
                        {consultant.is_verified && (
                            <span className="inline-block mt-2 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                                ✓ Verified
                            </span>
                        )}
                    </div>
                </div>

                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <p className="text-sm font-medium text-gray-700">Type</p>
                        <p className="mt-1 text-gray-900 capitalize">{consultant.consultant_type.replace("_", " ")}</p>
                    </div>
                    <div>
                        <p className="text-sm font-medium text-gray-700">Qualification</p>
                        <p className="mt-1 text-gray-900">{consultant.highest_qualification}</p>
                    </div>
                    {consultant.graduation_institution && (
                        <div>
                            <p className="text-sm font-medium text-gray-700">Institution</p>
                            <p className="mt-1 text-gray-900">{consultant.graduation_institution}</p>
                        </div>
                    )}
                    {consultant.specialties && (
                        <div>
                            <p className="text-sm font-medium text-gray-700">Specialties</p>
                            <p className="mt-1 text-gray-900">{consultant.specialties}</p>
                        </div>
                    )}
                </div>

                {consultant.bio && (
                    <div className="mt-4">
                        <p className="text-sm font-medium text-gray-700">About</p>
                        <p className="mt-1 text-gray-900 whitespace-pre-line">{consultant.bio}</p>
                    </div>
                )}
            </div>

            {/* Book Appointment */}
            <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Book an Appointment</h2>

                {/* Date Selector */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Select Date</label>
                    <div className="grid grid-cols-3 md:grid-cols-7 gap-2">
                        {availableDates.map((date) => (
                            <button
                                key={date}
                                onClick={() => setSelectedDate(date)}
                                className={`px-4 py-2 text-sm font-medium rounded-md transition ${selectedDate === date
                                    ? "bg-blue-600 text-white"
                                    : "bg-gray-100 text-gray-900 hover:bg-gray-200"
                                    }`}
                            >
                                {formatDate(date)}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Free Windows */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Available Time Slots</label>
                    {loadingWindows ? (
                        <p className="text-sm text-gray-500">Loading availability...</p>
                    ) : freeWindows.length === 0 ? (
                        <p className="text-sm text-gray-500">No available slots for this date</p>
                    ) : (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {freeWindows.map((window, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => {
                                        setSelectedWindow(window);
                                        setSelectedTime(window.start);
                                    }}
                                    className={`px-4 py-3 text-sm rounded-md border-2 transition ${selectedWindow === window
                                        ? "border-blue-600 bg-blue-50 text-blue-900"
                                        : "border-gray-300 bg-white text-gray-900 hover:border-gray-400"
                                        }`}
                                >
                                    <div>{formatTime(window.start)} – {formatTime(window.end)}</div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Time Picker (within selected window) */}
                {selectedWindow && (
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Choose Start Time (within selected slot)
                        </label>
                        <input
                            type="datetime-local"
                            value={selectedTime ? toLocalISOString(new Date(selectedTime)) : ""}
                            onChange={(e) => setSelectedTime(new Date(e.target.value).toISOString())}
                            min={toLocalISOString(new Date(selectedWindow.start))}
                            max={toLocalISOString(new Date(selectedWindow.end))}
                            className="block w-full md:w-1/2 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 px-3 py-2 border"
                        />
                    </div>
                )}

                {/* Note */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Message (Optional)
                    </label>
                    <textarea
                        rows={3}
                        className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 px-3 py-2 border"
                        placeholder="Tell the consultant why you'd like to book..."
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                    />
                </div>

                <button
                    onClick={handleApply}
                    disabled={!selectedTime || applying}
                    className="w-full md:w-auto px-6 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                    {applying ? "Submitting..." : "Submit Application"}
                </button>
            </div>
        </div>
    );
}
