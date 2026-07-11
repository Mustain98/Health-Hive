"use client";

import type { DailyLogHistoryDay } from "@/lib/types";

export function LogHistoryTable({ history }: { history: DailyLogHistoryDay[] }) {
    if (history.length === 0) return <p className="text-sm text-gray-400">No logs yet.</p>;
    return (
        <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
                <thead>
                    <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                        <th className="py-2 pr-4 font-medium">Date</th>
                        <th className="py-2 pr-4 font-medium">Goals</th>
                        <th className="py-2 pr-4 font-medium">Cal in</th>
                        <th className="py-2 pr-4 font-medium">Cal out</th>
                        <th className="py-2 font-medium">Deficit</th>
                    </tr>
                </thead>
                <tbody>
                    {history.map((day) => (
                        <tr key={day.date} className="border-b border-gray-50 align-top">
                            <td className="py-2 pr-4 whitespace-nowrap text-gray-700">{day.date}</td>
                            <td className="py-2 pr-4">
                                {day.goals.length === 0 ? <span className="text-gray-300">—</span> : (
                                    <div className="space-y-0.5">
                                        {day.goals.map((g) => (
                                            <p key={g.daily_goal_id + day.date} className="text-gray-700">
                                                <span className={g.completed ? "text-emerald-600" : "text-gray-300"}>{g.completed ? "✓" : "✗"}</span>{" "}
                                                {g.name}
                                                {g.value != null ? <span className="text-gray-400"> · {g.value}{g.unit ? ` ${g.unit}` : ""}</span> : ""}
                                                {g.target_value != null ? <span className="text-gray-300"> / {g.target_value}</span> : ""}
                                            </p>
                                        ))}
                                    </div>
                                )}
                            </td>
                            <td className="py-2 pr-4 text-gray-700">{day.calories_in ?? "—"}</td>
                            <td className="py-2 pr-4 text-gray-700">{day.calories_out ?? "—"}</td>
                            <td className={`py-2 font-medium ${day.deficit_surplus == null ? "text-gray-300" : day.deficit_surplus < 0 ? "text-emerald-600" : "text-red-600"}`}>
                                {day.deficit_surplus == null ? "—" : `${day.deficit_surplus > 0 ? "+" : ""}${day.deficit_surplus}`}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
