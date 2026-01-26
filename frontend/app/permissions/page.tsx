"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { PermissionRead, PermissionGrant, PermissionRevoke, ConsultantPublicRead } from "@/lib/types";

export default function PermissionsPage() {
    const [permissions, setPermissions] = useState<PermissionRead[]>([]);
    const [consultants, setConsultants] = useState<ConsultantPublicRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [showGrantModal, setShowGrantModal] = useState(false);
    const [selectedConsultantId, setSelectedConsultantId] = useState<number | null>(null);
    const [selectedResources, setSelectedResources] = useState<string[]>(["nutrition_targets", "user_goals"]);
    const [granting, setGranting] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        try {
            const [perms, cons] = await Promise.all([
                apiFetch<PermissionRead[]>("/api/permissions/me"),
                apiFetch<ConsultantPublicRead[]>("/api/consultants?verified_only=true&limit=100"),
            ]);

            setPermissions(perms);
            setConsultants(cons);
        } catch (error) {
            console.error("Failed to load permissions:", error);
        } finally {
            setLoading(false);
        }
    }

    async function handleGrant() {
        if (!selectedConsultantId) return;

        setGranting(true);
        setMessage(null);

        try {
            const grant: PermissionGrant = {
                consultant_user_id: selectedConsultantId,
                scope: "read_write",
                resources: selectedResources,
            };

            await apiFetch("/api/permissions/me/grant", {
                method: "POST",
                body: grant,
            });

            setMessage("Permission granted successfully!");
            setShowGrantModal(false);
            setSelectedConsultantId(null);
            await loadData(); // Reload permissions
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setGranting(false);
        }
    }

    async function handleRevoke(consultantUserId: number) {
        if (!confirm("Are you sure you want to revoke this permission?")) return;

        setMessage(null);

        try {
            const revoke: PermissionRevoke = {
                consultant_user_id: consultantUserId,
            };

            await apiFetch("/api/permissions/me/revoke", {
                method: "POST",
                body: revoke,
            });

            setMessage("Permission revoked successfully");
            await loadData(); // Reload permissions
        } catch (error: any) {
            setMessage(`Error: ${error.message}`);
        }
    }

    function toggleResource(resource: string) {
        setSelectedResources((prev) =>
            prev.includes(resource)
                ? prev.filter((r) => r !== resource)
                : [...prev, resource]
        );
    }

    if (loading) {
        return <div className="text-center py-12">Loading...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Permissions</h1>
                    <p className="mt-2 text-sm text-gray-600">
                        Manage which consultants can access and update your health data
                    </p>
                </div>
                <button
                    onClick={() => setShowGrantModal(true)}
                    className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                    Grant Permission
                </button>
            </div>

            {message && (
                <div className={`rounded-md p-4 ${message.includes("Error") ? "bg-red-50" : "bg-green-50"}`}>
                    <p className={`text-sm ${message.includes("Error") ? "text-red-800" : "text-green-800"}`}>
                        {message}
                    </p>
                </div>
            )}

            {/* Active Permissions */}
            <div className="space-y-4">
                {permissions.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-lg shadow">
                        <p className="text-gray-500">No active permissions</p>
                        <button
                            onClick={() => setShowGrantModal(true)}
                            className="text-blue-600 hover:text-blue-500 mt-2 inline-block"
                        >
                            Grant permission to a consultant →
                        </button>
                    </div>
                ) : (
                    permissions.map((perm) => (
                        <div key={perm.id} className="bg-white shadow rounded-lg p-6">
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center space-x-2">
                                        <h3 className="text-lg font-medium text-gray-900">
                                            Consultant ID: {perm.consultant_user_id}
                                        </h3>
                                        <span
                                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${perm.status === "active"
                                                    ? "bg-green-100 text-green-800"
                                                    : "bg-gray-100 text-gray-800"
                                                }`}
                                        >
                                            {perm.status}
                                        </span>
                                    </div>
                                    <div className="mt-2 space-y-1">
                                        <p className="text-sm text-gray-600">
                                            <span className="font-medium">Scope:</span>{" "}
                                            <span className="capitalize">{perm.scope.replace("_", " ")}</span>
                                        </p>
                                        <p className="text-sm text-gray-600">
                                            <span className="font-medium">Resources:</span>{" "}
                                            {perm.resources.join(", ")}
                                        </p>
                                        <p className="text-sm text-gray-600">
                                            <span className="font-medium">Granted:</span>{" "}
                                            {new Date(perm.granted_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                </div>
                                {perm.status === "active" && (
                                    <button
                                        onClick={() => handleRevoke(perm.consultant_user_id)}
                                        className="inline-flex items-center px-4 py-2 border border-red-300 shadow-sm text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                                    >
                                        Revoke
                                    </button>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Grant Modal */}
            {showGrantModal && (
                <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">
                            Grant Permission to Consultant
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Select Consultant
                                </label>
                                <select
                                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                                    value={selectedConsultantId || ""}
                                    onChange={(e) => setSelectedConsultantId(Number(e.target.value))}
                                >
                                    <option value="">Choose...</option>
                                    {consultants.map((consultant) => (
                                        <option key={consultant.id} value={consultant.user_id}>
                                            {consultant.display_name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Allow access to:
                                </label>
                                <div className="space-y-2">
                                    <label className="flex items-center">
                                        <input
                                            type="checkbox"
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                            checked={selectedResources.includes("nutrition_targets")}
                                            onChange={() => toggleResource("nutrition_targets")}
                                        />
                                        <span className="ml-2 text-sm text-gray-700">Nutrition Targets</span>
                                    </label>
                                    <label className="flex items-center">
                                        <input
                                            type="checkbox"
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                            checked={selectedResources.includes("user_goals")}
                                            onChange={() => toggleResource("user_goals")}
                                        />
                                        <span className="ml-2 text-sm text-gray-700">Goals</span>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 flex justify-end space-x-3">
                            <button
                                onClick={() => setShowGrantModal(false)}
                                disabled={granting}
                                className="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleGrant}
                                disabled={granting || !selectedConsultantId || selectedResources.length === 0}
                                className="px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                            >
                                {granting ? "Granting..." : "Grant Permission"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
