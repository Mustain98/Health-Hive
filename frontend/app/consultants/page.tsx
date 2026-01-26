"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ConsultantPublicRead } from "@/lib/types";

export default function ConsultantsPage() {
    const [consultants, setConsultants] = useState<ConsultantPublicRead[]>([]);
    const [searchQuery, setSearchQuery] = useState("");
    const [verifiedOnly, setVerifiedOnly] = useState(true);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => {
            searchConsultants();
        }, 300); // Debounce search

        return () => clearTimeout(timer);
    }, [searchQuery, verifiedOnly]);

    async function searchConsultants() {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (searchQuery) params.append("q", searchQuery);
            params.append("verified_only", verifiedOnly.toString());
            params.append("limit", "50");

            const data = await apiFetch<ConsultantPublicRead[]>(
                `/api/consultants?${params.toString()}`
            );
            setConsultants(data);
        } catch (error) {
            console.error("Failed to search consultants:", error);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Find Consultants</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Search for verified health consultants
                </p>
            </div>

            {/* Search & Filters */}
            <div className="bg-white shadow rounded-lg p-6 space-y-4">
                <div>
                    <label htmlFor="search" className="block text-sm font-medium text-gray-700">
                        Search by name or specialty
                    </label>
                    <input
                        type="text"
                        id="search"
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                        placeholder="e.g., nutrition, weight loss..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <div className="flex items-center">
                    <input
                        id="verified-only"
                        type="checkbox"
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        checked={verifiedOnly}
                        onChange={(e) => setVerifiedOnly(e.target.checked)}
                    />
                    <label htmlFor="verified-only" className="ml-2 block text-sm text-gray-700">
                        Show verified consultants only
                    </label>
                </div>
            </div>

            {/* Results */}
            <div>
                {loading ? (
                    <div className="text-center py-12">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                ) : consultants.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-lg shadow">
                        <p className="text-gray-500">No consultants found</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                        {consultants.map((consultant) => (
                            <Link
                                key={consultant.id}
                                href={`/consultants/${consultant.id}`}
                                className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow"
                            >
                                <div className="p-6">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <h3 className="text-lg font-medium text-gray-900">
                                                {consultant.display_name}
                                            </h3>
                                            {consultant.is_verified && (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 mt-1">
                                                    ✓ Verified
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {consultant.specialties && (
                                        <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                                            <span className="font-medium">Specialties:</span> {consultant.specialties}
                                        </p>
                                    )}

                                    {consultant.bio && (
                                        <p className="mt-2 text-sm text-gray-500 line-clamp-3">
                                            {consultant.bio}
                                        </p>
                                    )}

                                    <div className="mt-4">
                                        <span className="text-sm font-medium text-blue-600 hover:text-blue-500">
                                            View Profile →
                                        </span>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>

            <div className="text-center text-sm text-gray-500">
                Found {consultants.length} consultant{consultants.length !== 1 ? "s" : ""}
            </div>
        </div>
    );
}
