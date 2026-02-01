"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ConsultantPublicRead } from "@/lib/types";

export default function ConsultantsPage() {
    const [consultants, setConsultants] = useState<ConsultantPublicRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");

    useEffect(() => {
        loadConsultants();
    }, []);

    async function loadConsultants() {
        try {
            const data = await apiFetch<ConsultantPublicRead[]>("/api/consultants");
            setConsultants(data);
        } catch (error) {
            console.error("Failed to load consultants:", error);
        } finally {
            setLoading(false);
        }
    }

    const filteredConsultants = consultants.filter((c) => {
        if (!search) return true;
        const query = search.toLowerCase();
        return (
            c.display_name.toLowerCase().includes(query) ||
            c.specialties?.toLowerCase().includes(query) ||
            c.consultant_type.toLowerCase().includes(query)
        );
    });

    return (
        <div className="max-w-6xl mx-auto p-6 space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Find a Consultant</h1>
                <p className="mt-2 text-sm text-gray-600">
                    Browse verified health and wellness consultants
                </p>
            </div>

            <div>
                <input
                    type="text"
                    placeholder="Search by name, specialty, or type..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
            </div>

            {loading ? (
                <div className="text-center py-12">
                    <p className="text-gray-600">Loading consultants...</p>
                </div>
            ) : filteredConsultants.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg shadow">
                    <p className="text-gray-500">
                        {search ? "No consultants found matching your search" : "No consultants available"}
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredConsultants.map((consultant) => (
                        <Link
                            key={consultant.id}
                            href={`/consultants/${consultant.id}`}
                            className="block bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6 space-y-3"
                        >
                            <div className="flex items-start justify-between">
                                <h3 className="text-lg font-semibold text-gray-900">
                                    {consultant.display_name}
                                </h3>
                                {consultant.is_verified && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                        Verified
                                    </span>
                                )}
                            </div>

                            <div className="space-y-2">
                                <p className="text-sm text-gray-600">
                                    <span className="font-medium">Type:</span>{" "}
                                    <span className="capitalize">{consultant.consultant_type.replace("_", " ")}</span>
                                </p>

                                <p className="text-sm text-gray-600">
                                    <span className="font-medium">Qualification:</span>{" "}
                                    {consultant.highest_qualification}
                                </p>

                                {consultant.graduation_institution && (
                                    <p className="text-sm text-gray-600">
                                        <span className="font-medium">Institution:</span>{" "}
                                        {consultant.graduation_institution}
                                    </p>
                                )}

                                {consultant.specialties && (
                                    <p className="text-sm text-gray-600 line-clamp-2">
                                        <span className="font-medium">Specialties:</span> {consultant.specialties}
                                    </p>
                                )}
                            </div>

                            {consultant.bio && (
                                <p className="text-sm text-gray-500 line-clamp-3">{consultant.bio}</p>
                            )}

                            <div className="pt-2">
                                <span className="text-sm font-medium text-blue-600 hover:text-blue-700">
                                    View Profile & Book →
                                </span>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
