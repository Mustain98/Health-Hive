"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { UserHealthProfileRead, DietPreference, HealthCondition } from "@/lib/types";

const DIETS: DietPreference[] = ["vegetarian", "vegan", "halal", "kosher", "pescatarian"];
const CONDITIONS: HealthCondition[] = [
    "hypertension", "diabetes", "high_cholesterol", "heart_disease", "kidney_disease", "obesity", "other",
];

function label(s: string) {
    return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function HealthProfilePage() {
    const [diets, setDiets] = useState<DietPreference[]>([]);
    const [conditions, setConditions] = useState<HealthCondition[]>([]);
    const [notes, setNotes] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        (async () => {
            try {
                const p = await apiFetch<UserHealthProfileRead>("/api/health-profile");
                setDiets(p.diet_preferences || []);
                setConditions(p.health_conditions || []);
                setNotes(p.notes || "");
            } catch {
                /* no profile yet */
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    function toggle<T>(list: T[], set: (v: T[]) => void, value: T) {
        set(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
    }

    async function handleSave() {
        setSaving(true);
        setMessage(null);
        try {
            await apiFetch("/api/health-profile", {
                method: "PUT",
                body: { diet_preferences: diets, health_conditions: conditions, notes: notes || null },
            });
            setMessage("Saved ✅ — your meal plans will now consider this.");
        } catch (e: any) {
            setMessage(`Error: ${e.message}`);
        } finally {
            setSaving(false);
        }
    }

    if (loading) return <div className="text-center py-12 text-gray-500">Loading…</div>;

    return (
        <div className="max-w-2xl mx-auto p-6 space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-gray-900">Health & Dietary Profile</h1>
                <p className="mt-1 text-sm text-gray-600">
                    Used by the AI meal planner to personalize and constrain your plans.
                </p>
            </div>

            {message && (
                <div className={`rounded-md p-3 text-sm ${message.startsWith("Error") ? "bg-red-50 text-red-800" : "bg-green-50 text-green-800"}`}>
                    {message}
                </div>
            )}

            <div className="bg-white shadow rounded-lg p-5">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">Dietary preferences</h2>
                <div className="flex flex-wrap gap-2">
                    {DIETS.map((d) => (
                        <button
                            key={d}
                            onClick={() => toggle(diets, setDiets, d)}
                            className={`px-3 py-1.5 rounded-full text-sm border transition ${diets.includes(d) ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"}`}
                        >
                            {label(d)}
                        </button>
                    ))}
                </div>
            </div>

            <div className="bg-white shadow rounded-lg p-5">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">Health conditions</h2>
                <div className="flex flex-wrap gap-2">
                    {CONDITIONS.map((c) => (
                        <button
                            key={c}
                            onClick={() => toggle(conditions, setConditions, c)}
                            className={`px-3 py-1.5 rounded-full text-sm border transition ${conditions.includes(c) ? "bg-red-600 text-white border-red-600" : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"}`}
                        >
                            {label(c)}
                        </button>
                    ))}
                </div>
            </div>

            <div className="bg-white shadow rounded-lg p-5">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">Other notes</h2>
                <textarea
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="e.g. lactose intolerant, prefer low-sodium, dislike spicy food…"
                    className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
            </div>

            <button
                onClick={handleSave}
                disabled={saving}
                className="px-6 py-2 rounded-md text-white bg-blue-600 hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
            >
                {saving ? "Saving…" : "Save profile"}
            </button>
        </div>
    );
}
