"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/components/guards/AuthGuard";
import type { GoalRead, NutritionTargetRead, AppointmentRead } from "@/lib/types";

export default function DashboardPage() {
    const user = useAuth();
    const [goal, setGoal] = useState<GoalRead | null>(null);
    const [nutrition, setNutrition] = useState<NutritionTargetRead | null>(null);
    const [appointments, setAppointments] = useState<AppointmentRead[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            try {
                const [goalRes, nutritionRes, appointmentsRes] = await Promise.allSettled([
                    apiFetch<GoalRead>("/api/goal/me").catch(() => null),
                    apiFetch<NutritionTargetRead>("/api/nutrition-target/me").catch(() => null),
                    apiFetch<AppointmentRead[]>("/api/appointments/me").catch(() => []),
                ]);

                if (goalRes.status === "fulfilled") setGoal(goalRes.value);
                if (nutritionRes.status === "fulfilled") setNutrition(nutritionRes.value);
                if (appointmentsRes.status === "fulfilled") setAppointments(appointmentsRes.value);
            } catch (error) {
                console.error("Failed to load dashboard data:", error);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Welcome back! Here's an overview of your health journey.
                </p>
            </div>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {/* Goal Card */}
                <div className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="p-5">
                        <div className="flex items-center">
                            <div className="flex-1">
                                <h3 className="text-lg font-medium text-gray-900">Goal</h3>
                                {goal ? (
                                    <div className="mt-2">
                                        <p className="text-sm text-gray-600 capitalize">
                                            {goal.goal_type.replace("_", " ")}
                                        </p>
                                        {goal.target_delta_kg && (
                                            <p className="text-sm text-gray-600">
                                                Target: {goal.target_delta_kg} kg
                                            </p>
                                        )}
                                    </div>
                                ) : (
                                    <p className="mt-2 text-sm text-gray-500">No goal set</p>
                                )}
                            </div>
                        </div>
                        <div className="mt-4">
                            <Link
                                href="/goal"
                                className="text-sm font-medium text-blue-600 hover:text-blue-500"
                            >
                                {goal ? "Edit goal" : "Set a goal"} →
                            </Link>
                        </div>
                    </div>
                </div>

                {/* Nutrition Card */}
                <div className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="p-5">
                        <div className="flex items-center">
                            <div className="flex-1">
                                <h3 className="text-lg font-medium text-gray-900">Nutrition</h3>
                                {nutrition ? (
                                    <div className="mt-2 space-y-1">
                                        <p className="text-sm text-gray-600">
                                            Calories: {nutrition.calories_kcal} kcal
                                        </p>
                                        <p className="text-sm text-gray-600">
                                            Protein: {nutrition.protein_g}g
                                        </p>
                                    </div>
                                ) : (
                                    <p className="mt-2 text-sm text-gray-500">No targets set</p>
                                )}
                            </div>
                        </div>
                        <div className="mt-4">
                            <Link
                                href="/nutrition"
                                className="text-sm font-medium text-blue-600 hover:text-blue-500"
                            >
                                {nutrition ? "Edit targets" : "Set targets"} →
                            </Link>
                        </div>
                    </div>
                </div>

                {/* Appointments Card */}
                <div className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="p-5">
                        <div className="flex items-center">
                            <div className="flex-1">
                                <h3 className="text-lg font-medium text-gray-900">Appointments</h3>
                                <p className="mt-2 text-sm text-gray-600">
                                    {appointments.length} scheduled
                                </p>
                            </div>
                        </div>
                        <div className="mt-4">
                            <Link
                                href="/appointments"
                                className="text-sm font-medium text-blue-600 hover:text-blue-500"
                            >
                                View all →
                            </Link>
                        </div>
                    </div>
                </div>
            </div>

            {/* Consultant Portal Access */}
            {user?.user_type === "consultant" && (
                <div className="bg-gradient-to-r from-blue-500 to-blue-600 shadow rounded-lg p-6 text-white">
                    <h2 className="text-xl font-bold mb-2">Consultant Portal</h2>
                    <p className="text-blue-100 mb-4">
                        Manage your clients, appointments, and applications
                    </p>
                    <Link
                        href="/consultant/profile"
                        className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-blue-600 bg-white hover:bg-blue-50 transition-colors"
                    >
                        Go to Consultant Dashboard →
                    </Link>
                </div>
            )}

            {/* Apply as Consultant */}
            {user?.user_type !== "consultant" && (
                <div className="bg-gradient-to-r from-green-500 to-green-600 shadow rounded-lg p-6 text-white">
                    <h2 className="text-xl font-bold mb-2">Become a Consultant</h2>
                    <p className="text-green-100 mb-4">
                        Share your expertise and help others achieve their health goals
                    </p>
                    <Link
                        href="/apply-consultant"
                        className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-green-600 bg-white hover:bg-green-50 transition-colors"
                    >
                        Apply Now →
                    </Link>
                </div>
            )}

            {/* Quick Actions */}
            <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <Link
                        href="/consultants"
                        className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                    >
                        Find Consultants
                    </Link>
                    <Link
                        href="/profile"
                        className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                    >
                        Update Profile
                    </Link>
                    <Link
                        href="/permissions"
                        className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                    >
                        Manage Permissions
                    </Link>
                    <Link
                        href="/appointments"
                        className="inline-flex items-center justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                    >
                        Book Appointment
                    </Link>
                </div>
            </div>
        </div>
    );
}
