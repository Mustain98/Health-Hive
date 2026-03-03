"use client";

import { useEffect, useState, FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { UserRead, UserUpdate, UserDataRead, UserDataUpdate, ActivityLevel, Gender } from "@/lib/types";

export default function ProfilePage() {
    const [user, setUser] = useState<UserRead | null>(null);
    const [userData, setUserData] = useState<UserDataUpdate>({});
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
                    setUserData({
                        age: dataRes.value.age,
                        gender: dataRes.value.gender,
                        height_cm: dataRes.value.height_cm,
                        weight_kg: dataRes.value.weight_kg,
                        activity_level: dataRes.value.activity_level,
                    });
                }
            } catch (error) {
                console.error("Failed to load profile:", error);
            } finally {
                setLoading(false);
            }
        }
        loadProfile();
    }, []);

    async function handleSave(e: FormEvent) {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            // Update account info
            await apiFetch("/api/auth/users/me", {
                method: "PUT",
                body: userForm,
            });

            // Update health data
            await apiFetch("/api/user-data/me", {
                method: "PUT",
                body: userData,
            });

            setMessage("Profile updated successfully!");
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setSaving(false);
        }
    }

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
            await apiFetch("/api/auth/password", {
                method: "PUT",
                body: {
                    old_password: passwordForm.old_password,
                    new_password: passwordForm.new_password,
                },
            });

            setPasswordMessage("Password updated successfully!");
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

            <form onSubmit={handleSave} className="space-y-8">
                {/* Account Section */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Account Details</h2>
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Username</label>
                            <input
                                type="text"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={userForm.username || ""}
                                onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Email</label>
                            <input
                                type="email"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={userForm.email || ""}
                                onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                            />
                        </div>
                        <div className="sm:col-span-2">
                            <label className="block text-sm font-medium text-gray-700">Full Name</label>
                            <input
                                type="text"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
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
                </div>

                {/* Password Section */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Change Password</h2>

                    {passwordMessage && (
                        <div className={`rounded-md p-4 mb-4 ${passwordMessage.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                            <p className={`text-sm ${passwordMessage.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                                {passwordMessage}
                            </p>
                        </div>
                    )}

                    <form onSubmit={handlePasswordUpdate} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Current Password</label>
                            <input
                                type="password"
                                required
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={passwordForm.old_password}
                                onChange={(e) => setPasswordForm({ ...passwordForm, old_password: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">New Password</label>
                            <input
                                type="password"
                                required
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={passwordForm.new_password}
                                onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Confirm New Password</label>
                            <input
                                type="password"
                                required
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={passwordForm.confirm_password}
                                onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                            />
                        </div>
                        <div className="flex justify-end">
                            <button
                                type="submit"
                                disabled={savingPassword}
                                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                            >
                                {savingPassword ? "Updating..." : "Update Password"}
                            </button>
                        </div>
                    </form>
                </div>

                {/* Health Data Section */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Health Information</h2>
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Age</label>
                            <input
                                type="number"
                                min="10"
                                max="120"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={userData.age ?? ""}
                                onChange={(e) => setUserData({ ...userData, age: e.target.value ? Number(e.target.value) : null })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Gender</label>
                            <select
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
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
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
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
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                value={userData.weight_kg ?? ""}
                                onChange={(e) => setUserData({ ...userData, weight_kg: e.target.value ? Number(e.target.value) : null })}
                            />
                        </div>
                        <div className="sm:col-span-2">
                            <label className="block text-sm font-medium text-gray-700">Activity Level</label>
                            <select
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
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
                </div>

                <div className="flex justify-end">
                    <button
                        type="submit"
                        disabled={saving}
                        className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                    >
                        {saving ? "Saving..." : "Save Profile"}
                    </button>
                </div>
            </form>
        </div>
    );
}
