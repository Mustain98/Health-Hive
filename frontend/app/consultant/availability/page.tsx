"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { AvailabilityRuleRead, AvailabilityRuleCreate } from "@/lib/types";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function AvailabilityPage() {
    const [rules, setRules] = useState<AvailabilityRuleRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState<string | null>(null);

    // Form state
    const [showAddModal, setShowAddModal] = useState(false);
    const [selectedDay, setSelectedDay] = useState(0);
    const [startTime, setStartTime] = useState("09:00");
    const [endTime, setEndTime] = useState("17:00");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadRules();
    }, []);

    async function loadRules() {
        try {
            const data = await apiFetch<AvailabilityRuleRead[]>("/api/consultants/me/availability");
            setRules(data);
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }

    async function handleAddRule() {
        if (!startTime || !endTime) {
            setMessage("Please fill in all fields");
            return;
        }

        setSubmitting(true);
        setMessage(null);

        try {
            const newRule: AvailabilityRuleCreate = {
                day_of_week: selectedDay,
                start_time: startTime,
                end_time: endTime,
                timezone: "Asia/Dhaka",
                consultation_duration: 30,
            };

            await apiFetch("/api/consultants/me/availability", {
                method: "POST",
                body: newRule,
            });

            setMessage("Time slot added successfully");
            setShowAddModal(false);
            setStartTime("09:00");
            setEndTime("17:00");
            await loadRules();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSubmitting(false);
        }
    }

    async function handleDeleteRule(ruleId: number) {
        if (!confirm("Are you sure you want to delete this time slot?")) return;

        setMessage(null);
        try {
            await apiFetch(`/api/consultants/me/availability/${ruleId}`, {
                method: "DELETE",
            });
            setMessage("Time slot deleted");
            await loadRules();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        }
    }

    async function handleToggleActive(rule: AvailabilityRuleRead) {
        setMessage(null);
        try {
            await apiFetch(`/api/consultants/me/availability/${rule.id}`, {
                method: "PATCH",
                body: { is_active: !rule.is_active },
            });
            await loadRules();
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        }
    }

    // Group rules by day
    const rulesByDay: Record<number, AvailabilityRuleRead[]> = {};
    for (let i = 0; i < 7; i++) {
        rulesByDay[i] = rules.filter((r) => r.day_of_week === i);
    }

    if (loading) {
        return <div className="text-center py-12">Loading availability...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Availability Settings</h1>
                    <p className="mt-2 text-sm text-gray-600">
                        Set your weekly availability for consultations
                    </p>
                </div>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                    + Add Time Slot
                </button>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {/* Weekly Schedule */}
            <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Weekly Schedule</h2>

                <div className="space-y-4">
                    {DAYS.map((dayName, dayIndex) => (
                        <div key={dayIndex} className="border-b border-gray-200 pb-4 last:border-0">
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <h3 className="font-medium text-gray-900 mb-2">{dayName}</h3>

                                    {rulesByDay[dayIndex].length === 0 ? (
                                        <p className="text-sm text-gray-500">No availability set</p>
                                    ) : (
                                        <div className="space-y-2">
                                            {rulesByDay[dayIndex].map((rule) => (
                                                <div
                                                    key={rule.id}
                                                    className={`flex items-center gap-3 p-3 rounded-md border ${rule.is_active
                                                        ? "bg-green-50 border-green-200"
                                                        : "bg-gray-50 border-gray-200 opacity-60"
                                                        }`}
                                                >
                                                    <div className="flex-1">
                                                        <span className="font-medium text-gray-900">
                                                            {rule.start_time} – {rule.end_time}
                                                        </span>
                                                        {!rule.is_active && (
                                                            <span className="ml-2 text-xs text-gray-500">(Inactive)</span>
                                                        )}
                                                    </div>

                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={() => handleToggleActive(rule)}
                                                            className="px-3 py-1 text-sm rounded-md bg-white border border-gray-300 hover:bg-gray-50"
                                                        >
                                                            {rule.is_active ? "Disable" : "Enable"}
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteRule(rule.id as unknown as number)}
                                                            className="px-3 py-1 text-sm rounded-md text-red-700 bg-red-100 hover:bg-red-200"
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Add Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Add Availability Slot</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Day</label>
                                <select
                                    value={selectedDay}
                                    onChange={(e) => setSelectedDay(parseInt(e.target.value))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                                >
                                    {DAYS.map((day, idx) => (
                                        <option key={idx} value={idx}>
                                            {day}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Start Time</label>
                                <input
                                    type="time"
                                    value={startTime}
                                    onChange={(e) => setStartTime(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">End Time</label>
                                <input
                                    type="time"
                                    value={endTime}
                                    onChange={(e) => setEndTime(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowAddModal(false)}
                                disabled={submitting}
                                className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAddRule}
                                disabled={submitting}
                                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
                            >
                                {submitting ? "Adding..." : "Add Slot"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
