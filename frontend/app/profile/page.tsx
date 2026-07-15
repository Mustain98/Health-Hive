"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { UserRead, UserUpdate, UserDataRead, UserDataUpdate, ActivityLevel, Gender } from "@/lib/types";

const ACTIVITY_LABEL: Record<string, string> = {
    sedentary: "Sedentary",
    light: "Lightly active",
    moderate: "Moderately active",
    active: "Active",
    very_active: "Very active",
};

export default function ProfilePage() {
    const [user, setUser] = useState<UserRead | null>(null);
    const [userData, setUserData] = useState<UserDataUpdate>({});
    // Last-saved metrics, used to restore on Cancel.
    const [savedMetrics, setSavedMetrics] = useState<UserDataUpdate>({});
    const [editingMetrics, setEditingMetrics] = useState(false);
    const [savingMetrics, setSavingMetrics] = useState(false);
    const [userForm, setUserForm] = useState<UserUpdate>({});
    const [passwordForm, setPasswordForm] = useState({
        old_password: "",
        new_password: "",
        confirm_password: "",
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [savingPassword, setSavingPassword] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [passwordMessage, setPasswordMessage] = useState<string | null>(null);

    useEffect(() => {
        async function loadProfile() {
            try {
                const [userRes, dataRes] = await Promise.allSettled([
                    apiFetch<UserRead>("/api/auth/me"),
                    apiFetch<UserDataRead>("/api/user-data/me").catch(() => null),
                ]);

                if (userRes.status === "fulfilled") {
                    setUser(userRes.value);
                    setUserForm({
                        username: userRes.value.username,
                        email: userRes.value.email,
                        full_name: userRes.value.full_name || "",
                    });
                }

                if (dataRes.status === "fulfilled" && dataRes.value) {
                    const m = {
                        age: dataRes.value.age,
                        gender: dataRes.value.gender,
                        height_cm: dataRes.value.height_cm,
                        weight_kg: dataRes.value.weight_kg,
                        activity_level: dataRes.value.activity_level,
                    };
                    setUserData(m);
                    setSavedMetrics(m);
                }
            } catch (error) {
                console.error("Failed to load profile:", error);
            } finally {
                setLoading(false);
            }
        }
        loadProfile();
    }, []);

    async function saveAccount() {
        setSaving(true);
        setMessage(null);

        try {
            // Account details only — body metrics have their own edit/save below.
            await apiFetch("/api/auth/users/me", {
                method: "PUT",
                body: userForm,
            });

            setMessage("Account updated successfully!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

    async function saveMetrics() {
        setSavingMetrics(true);
        setMessage(null);
        try {
            await apiFetch("/api/user-data/me", { method: "PUT", body: userData });
            setSavedMetrics(userData);
            setEditingMetrics(false);
            setMessage("Body metrics updated!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSavingMetrics(false);
        }
    }

    function cancelMetrics() {
        setUserData(savedMetrics);
        setEditingMetrics(false);
    }

    const bmi =
        userData.weight_kg && userData.height_cm
            ? userData.weight_kg / (userData.height_cm / 100) ** 2
            : null;

    async function handlePasswordUpdate(e: FormEvent) {
        e.preventDefault();
        setPasswordMessage(null);

        if (passwordForm.new_password !== passwordForm.confirm_password) {
            setPasswordMessage("Error: Passwords do not match");
            return;
        }

        if (passwordForm.new_password.length < 6) {
            setPasswordMessage("Error: Password must be at least 6 characters");
            return;
        }

        setSavingPassword(true);

        try {
            if (user?.has_password) {
                // Change an existing password (old + new).
                await apiFetch("/api/auth/users/me/password", {
                    method: "PUT",
                    body: {
                        old_password: passwordForm.old_password,
                        new_password: passwordForm.new_password,
                    },
                });
                setPasswordMessage("Password updated successfully!");
            } else {
                // First password for a Google account (no old password).
                await apiFetch("/api/auth/users/me/set-password", {
                    method: "POST",
                    body: { new_password: passwordForm.new_password },
                });
                setPasswordMessage("Password set! You can now sign in with your email and password too.");
                setUser((u) => (u ? { ...u, has_password: true } : u));
            }
            setPasswordForm({ old_password: "", new_password: "", confirm_password: "" });
        } catch (error: any) {
            setPasswordMessage(`Error: ${error.message}`);
        } finally {
            setSavingPassword(false);
        }
    }

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Manage your account and health information
                </p>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            <div className="space-y-8">
                {/* Account Section */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Account Details</h2>
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Username</label>
                            <input
                                type="text"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                value={userForm.username || ""}
                                onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Email</label>
                            <input
                                type="email"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                value={userForm.email || ""}
                                onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                            />
                        </div>
                        <div className="sm:col-span-2">
                            <label className="block text-sm font-medium text-gray-700">Full Name</label>
                            <input
                                type="text"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                value={userForm.full_name || ""}
                                onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })}
                            />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">
                                User Type: <span className="font-medium capitalize">{user?.user_type}</span>
                            </p>
                        </div>
                    </div>
                    <div className="mt-6 flex justify-end">
                        <button
                            type="button"
                            onClick={saveAccount}
                            disabled={saving}
                            className="inline-flex justify-center py-2 px-4 text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50"
                        >
                            {saving ? "Saving..." : "Save Account"}
                        </button>
                    </div>
                </div>

                {/* Password Section */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-1">
                        {user?.has_password ? "Change Password" : "Set a Password"}
                    </h2>
                    {!user?.has_password && (
                        <p className="text-sm text-gray-500 mb-4">
                            You signed up with Google. Set a password to also sign in with your email.
                        </p>
                    )}

                    {passwordMessage && (
                        <div className={`rounded-md p-4 mb-4 ${passwordMessage.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                            <p className={`text-sm ${passwordMessage.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                                {passwordMessage}
                            </p>
                        </div>
                    )}

                    <form onSubmit={handlePasswordUpdate} className="space-y-4">
                        {user?.has_password && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Current Password</label>
                                <input
                                    type="password"
                                    required
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                    value={passwordForm.old_password}
                                    onChange={(e) => setPasswordForm({ ...passwordForm, old_password: e.target.value })}
                                />
                            </div>
                        )}
                        <div>
                            <label className="block text-sm font-medium text-gray-700">New Password</label>
                            <input
                                type="password"
                                required
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                value={passwordForm.new_password}
                                onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Confirm New Password</label>
                            <input
                                type="password"
                                required
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                value={passwordForm.confirm_password}
                                onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                            />
                        </div>
                        <div className="flex justify-end">
                            <button
                                type="submit"
                                disabled={savingPassword}
                                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50"
                            >
                                {savingPassword
                                    ? "Saving..."
                                    : user?.has_password
                                        ? "Update Password"
                                        : "Set Password"}
                            </button>
                        </div>
                    </form>
                </div>

                {/* Body Metrics Section — view-first, edit on demand */}
                <div className="bg-white shadow rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h2 className="text-lg font-medium text-gray-900">Body Metrics</h2>
                            <p className="text-sm text-gray-500">Used to personalize your nutrition plan</p>
                        </div>
                        {!editingMetrics ? (
                            <button
                                type="button"
                                onClick={() => setEditingMetrics(true)}
                                className="text-sm font-medium text-emerald-600 hover:text-emerald-700"
                            >
                                Edit
                            </button>
                        ) : (
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    onClick={cancelMetrics}
                                    disabled={savingMetrics}
                                    className="text-sm font-medium text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-md hover:bg-gray-100 disabled:opacity-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="button"
                                    onClick={saveMetrics}
                                    disabled={savingMetrics}
                                    className="text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 px-3 py-1.5 rounded-md disabled:opacity-50"
                                >
                                    {savingMetrics ? "Saving…" : "Save"}
                                </button>
                            </div>
                        )}
                    </div>

                    {!editingMetrics ? (
                        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                            {[
                                { label: "Age", value: userData.age != null ? `${userData.age}` : "—" },
                                { label: "Gender", value: userData.gender ? userData.gender[0].toUpperCase() + userData.gender.slice(1) : "—" },
                                { label: "Height", value: userData.height_cm != null ? `${userData.height_cm} cm` : "—" },
                                { label: "Weight", value: userData.weight_kg != null ? `${userData.weight_kg} kg` : "—" },
                                { label: "BMI", value: bmi != null ? bmi.toFixed(1) : "—" },
                                { label: "Activity", value: userData.activity_level ? ACTIVITY_LABEL[userData.activity_level] : "—" },
                            ].map((m) => (
                                <div key={m.label} className="rounded-xl bg-gray-50 p-3">
                                    <p className="text-[11px] uppercase tracking-wide text-gray-400">{m.label}</p>
                                    <p className="mt-0.5 font-semibold text-gray-900">{m.value}</p>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Age</label>
                                <input
                                    type="number"
                                    min="10"
                                    max="120"
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                    value={userData.age ?? ""}
                                    onChange={(e) => setUserData({ ...userData, age: e.target.value ? Number(e.target.value) : null })}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Gender</label>
                                <select
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                    value={userData.gender || ""}
                                    onChange={(e) => setUserData({ ...userData, gender: e.target.value as Gender })}
                                >
                                    <option value="">Select...</option>
                                    <option value="male">Male</option>
                                    <option value="female">Female</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Height (cm)</label>
                                <input
                                    type="number"
                                    min="50"
                                    max="260"
                                    step="0.1"
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                    value={userData.height_cm ?? ""}
                                    onChange={(e) => setUserData({ ...userData, height_cm: e.target.value ? Number(e.target.value) : null })}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Weight (kg)</label>
                                <input
                                    type="number"
                                    min="20"
                                    max="400"
                                    step="0.1"
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                    value={userData.weight_kg ?? ""}
                                    onChange={(e) => setUserData({ ...userData, weight_kg: e.target.value ? Number(e.target.value) : null })}
                                />
                            </div>
                            <div className="sm:col-span-2">
                                <label className="block text-sm font-medium text-gray-700">Activity Level</label>
                                <select
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm px-3 py-2 border"
                                    value={userData.activity_level || ""}
                                    onChange={(e) => setUserData({ ...userData, activity_level: e.target.value as ActivityLevel })}
                                >
                                    <option value="">Select...</option>
                                    <option value="sedentary">Sedentary</option>
                                    <option value="light">Lightly Active</option>
                                    <option value="moderate">Moderately Active</option>
                                    <option value="active">Active</option>
                                    <option value="very_active">Very Active</option>
                                </select>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
