"use client";

import { useMemo } from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
    ReferenceDot,
    ReferenceLine,
} from "recharts";
import type { GoalLogRead } from "@/lib/types";

export function GoalTrackerChart({ logs, targetWeight, initialWeight, goalType }: { logs: GoalLogRead[], targetWeight?: number | null, initialWeight?: number | null, goalType: string }) {
    // Format logs for Recharts
    const data = useMemo(() => {
        return logs.map((log) => ({
            date: new Date(log.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
            weight: log.weight,
            // We assume due_terget is an absolute value relative to the starting weight. 
            // If the backend stores due_target as a delta (e.g., 0.5, 1.0, 1.5) we need the starting weight to chart it.
            // Let's check if due_target is the expected *weight* or the expected *difference*.
            // For now, let's just chart the actual weight. We'll add a reference line for final target if known.
            target: log.due_terget,
            fullDate: new Date(log.date).toLocaleString(),
        }));
    }, [logs]);

    if (!logs || logs.length === 0) {
        return (
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-100">
                <p className="text-gray-400 font-medium">No tracking logs yet.</p>
            </div>
        );
    }

    // Find min and max for nicely scaled Y axis
    const allWeights = logs.map(l => l.weight);
    if (targetWeight) allWeights.push(targetWeight);

    const minWeight = Math.min(...allWeights);
    const maxWeight = Math.max(...allWeights);
    const yDomain = [Math.floor(minWeight - 2), Math.ceil(maxWeight + 2)];

    return (
        <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis
                        dataKey="date"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#6b7280', fontSize: 12 }}
                        dy={10}
                    />
                    <YAxis
                        domain={yDomain}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#6b7280', fontSize: 12 }}
                        dx={-10}
                        unit="kg"
                    />
                    <Tooltip
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        labelStyle={{ fontWeight: 'bold', color: '#374151', marginBottom: '4px' }}
                    />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />

                    <Line
                        type="monotone"
                        name="Actual Weight"
                        dataKey="weight"
                        stroke="#2563eb"
                        strokeWidth={3}
                        dot={{ r: 4, strokeWidth: 2 }}
                        activeDot={{ r: 6, strokeWidth: 0 }}
                        animationDuration={1500}
                    />

                    {/* If we have a target weight, draw a dotted line to show the goal line */}
                    {targetWeight && (
                        <Line
                            type="monotone"
                            name="Target Weight"
                            dataKey={() => targetWeight}
                            stroke="#10b981"
                            strokeWidth={2}
                            strokeDasharray="5 5"
                            dot={false}
                        />
                    )}

                    {/* Draw the initial weight as a horizontal static reference line */}
                    {initialWeight && (
                        <ReferenceLine
                            y={initialWeight}
                            stroke="#9ca3af"
                            strokeDasharray="3 3"
                            label={{ position: 'insideTopLeft', value: 'Initial Weight', fill: '#6b7280', fontSize: 12 }}
                        />
                    )}
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
