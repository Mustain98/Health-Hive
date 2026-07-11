"use client";

import { useEffect, useState, FormEvent, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import Fuse from "fuse.js";

type MeasureUnit = "g" | "ml" | "piece" | "tbsp";

type FoodItem = {
    id: string;
    name: string;
    description: string | null;
    nutrition_unit: MeasureUnit;
    weight_per_unit_g: number | null;
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    labels?: string[];
};

export default function FoodItemsBrowser() {
    const [q, setQ] = useState("");
    const [labelFilter, setLabelFilter] = useState("");
    const [viewMode, setViewMode] = useState<"all" | "allergens" | "preferences">("all");
    const [items, setItems] = useState<FoodItem[]>([]);
    const [allergenIds, setAllergenIds] = useState<Set<string>>(new Set());
    const [preferenceIds, setPreferenceIds] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fuse = useMemo(() => new Fuse(items, { keys: ['name', 'description'], threshold: 0.4 }), [items]);

    // Filtered data memo
    const filteredItems = useMemo(() => {
        let result = q ? fuse.search(q).map(res => res.item) : items;

        if (labelFilter) {
            result = result.filter(item =>
                item.labels && item.labels.includes(labelFilter)
            );
        }
        return result;
    }, [items, q, labelFilter, fuse]);

    const availableLabels = [
        "grain", "meat", "fish", "dairy", "vegetable", "fruit", "legume",
        "nut_seed", "oil_fat", "beverage", "spice", "sweetener",
        "halal", "vegetarian", "vegan",
        "high_protein", "high_fiber", "low_carb", "low_fat"
    ];

    useEffect(() => {
        if (viewMode === "all") {
            fetchItems();
        } else if (viewMode === "allergens") {
            fetchAllergens();
        } else {
            fetchPreferences();
        }
        fetchAllergenIds();
        fetchPreferenceIds();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [viewMode]);

    const fetchItems = async () => {
        try {
            setLoading(true);
            setError(null);
            // Fetch everything and filter client side for a smoother experience
            const data = await apiFetch(`/api/food-items?limit=1000`);
            setItems(data);
        } catch (err: any) {
            setError(err.message || "Failed to fetch food items.");
        } finally {
            setLoading(false);
        }
    };

    const fetchAllergens = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await apiFetch(`/api/food-items/allergens?limit=1000`);
            setItems(data);
        } catch (err: any) {
            setError(err.message || "Failed to fetch allergens.");
        } finally {
            setLoading(false);
        }
    };

    const fetchAllergenIds = async () => {
        try {
            const data = await apiFetch(`/api/food-items/allergens?limit=1000`);
            const ids = new Set<string>(data.map((i: any) => i.id));
            setAllergenIds(ids);
        } catch (err: any) {
            console.error("Failed to load allergen IDs", err);
        }
    };

    const fetchPreferences = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await apiFetch(`/api/food-items/preferences?limit=1000`);
            setItems(data);
        } catch (err: any) {
            setError(err.message || "Failed to fetch preferences.");
        } finally {
            setLoading(false);
        }
    };

    const fetchPreferenceIds = async () => {
        try {
            const data = await apiFetch(`/api/food-items/preferences?limit=1000`);
            const ids = new Set<string>(data.map((i: any) => i.id));
            setPreferenceIds(ids);
        } catch (err: any) {
            console.error("Failed to load preference IDs", err);
        }
    };

    const toggleAllergen = async (itemId: string) => {
        const isAllergen = allergenIds.has(itemId);

        // Optimistic UI update
        const newIds = new Set(allergenIds);
        if (isAllergen) newIds.delete(itemId);
        else newIds.add(itemId);
        setAllergenIds(newIds);

        if (viewMode === "allergens" && isAllergen) {
            setItems(items.filter(i => i.id !== itemId));
        }

        try {
            if (isAllergen) {
                await apiFetch(`/api/food-items/${itemId}/allergen`, { method: "DELETE" });
            } else {
                await apiFetch(`/api/food-items/${itemId}/allergen`, { method: "POST" });
            }
        } catch (error) {
            console.error("Failed to toggle allergen status", error);
            // Revert optimistic update on failure
            fetchAllergenIds();
            if (viewMode === "allergens" && isAllergen) {
                fetchAllergens();
            }
        }
    };

    const togglePreference = async (itemId: string) => {
        const isPref = preferenceIds.has(itemId);

        // Optimistic UI update
        const newIds = new Set(preferenceIds);
        if (isPref) newIds.delete(itemId);
        else newIds.add(itemId);
        setPreferenceIds(newIds);

        if (viewMode === "preferences" && isPref) {
            setItems(items.filter(i => i.id !== itemId));
        }

        try {
            if (isPref) {
                await apiFetch(`/api/food-items/${itemId}/preference`, { method: "DELETE" });
            } else {
                await apiFetch(`/api/food-items/${itemId}/preference`, { method: "POST" });
            }
        } catch (error) {
            console.error("Failed to toggle preference status", error);
            fetchPreferenceIds();
            if (viewMode === "preferences" && isPref) {
                fetchPreferences();
            }
        }
    };

    const handleSearch = (e: FormEvent) => {
        e.preventDefault();
        // Search is now purely client-side via the filteredItems memo,
        // no need to re-fetch on form submit.
    };

    return (
        <div className="max-w-6xl mx-auto p-6 space-y-8 animate-in fade-in duration-500">
            <div className="bg-gradient-to-r from-teal-500 to-green-600 rounded-2xl p-8 text-white shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                    <h1 className="text-4xl font-extrabold mb-4 tracking-tight">Food Items Browser</h1>
                    <p className="text-teal-50 text-lg opacity-90 max-w-2xl">
                        Discover ingredients, check nutrition, and mark any food allergies to personalize your experience.
                    </p>
                </div>

                <div className="flex bg-white/20 p-1 rounded-xl backdrop-blur-md self-stretch md:self-auto">
                    <button
                        onClick={() => setViewMode("all")}
                        className={`px-6 py-2 rounded-lg font-medium transition-all flex-1 ${viewMode === 'all' ? 'bg-white text-teal-700 shadow-sm' : 'text-white hover:bg-white/10'}`}
                    >
                        Browse All
                    </button>
                    <button
                        onClick={() => setViewMode("allergens")}
                        className={`px-6 py-2 rounded-lg font-medium transition-all flex items-center justify-center flex-1 gap-2 ${viewMode === 'allergens' ? 'bg-white text-red-600 shadow-sm' : 'text-white hover:bg-white/10'}`}
                    >
                        <span>⚠️</span> My Allergens
                    </button>
                    <button
                        onClick={() => setViewMode("preferences")}
                        className={`px-6 py-2 rounded-lg font-medium transition-all flex items-center justify-center flex-1 gap-2 ${viewMode === 'preferences' ? 'bg-white text-green-600 shadow-sm' : 'text-white hover:bg-white/10'}`}
                    >
                        <span>⭐</span> My Preferences
                    </button>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-md border border-gray-100 p-6">
                <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4 items-end">
                    <div className="flex-1 w-full relative">
                        <label className="block text-sm font-semibold text-gray-700 mb-2">Search Items</label>
                        <div className="relative">
                            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400">
                                🔍
                            </span>
                            <input
                                type="text"
                                className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all outline-none"
                                placeholder="E.g., Chicken Breast, Apple..."
                                value={q}
                                onChange={(e) => setQ(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="w-full md:w-64">
                        <label className="block text-sm font-semibold text-gray-700 mb-2">Filter by Label</label>
                        <div className="relative">
                            <select
                                className="w-full pl-3 pr-10 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 appearance-none transition-all outline-none text-gray-700"
                                value={labelFilter}
                                onChange={(e) => setLabelFilter(e.target.value)}
                            >
                                <option value="">All Categories</option>
                                {availableLabels.map(l => (
                                    <option key={l} value={l}>{l.replace('_', ' ').charAt(0).toUpperCase() + l.replace('_', ' ').slice(1)}</option>
                                ))}
                            </select>
                            <span className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-gray-400">
                                ▼
                            </span>
                        </div>
                    </div>
                    <button
                        type="submit"
                        className="w-full md:w-auto px-8 py-3 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all active:scale-95 flex items-center justify-center"
                    >
                        Search
                    </button>
                    {(q || labelFilter) && (
                        <button
                            type="button"
                            onClick={() => { setQ(""); setLabelFilter(""); }}
                            className="w-full md:w-auto px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg transition-all"
                        >
                            Reset
                        </button>
                    )}
                </form>
            </div>

            {loading ? (
                <div className="flex justify-center items-center py-24">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
                </div>
            ) : error ? (
                <div className="bg-red-50 border-l-4 border-red-500 p-6 rounded-r-lg shadow-sm">
                    <div className="flex items-center">
                        <span className="text-red-500 text-xl mr-3">⚠️</span>
                        <p className="text-red-700 font-medium">{error}</p>
                    </div>
                </div>
            ) : filteredItems.length === 0 ? (
                <div className="text-center py-20 bg-gray-50 rounded-xl border border-dashed border-gray-300">
                    <span className="text-4xl block mb-4">🥗</span>
                    <p className="text-gray-500 text-lg">
                        {viewMode === 'allergens' ? "You haven't marked any food items as allergens." : viewMode === 'preferences' ? "You haven't marked any food items as preferences." : "No food items found matching your criteria."}
                    </p>
                    <p className="text-gray-400 text-sm mt-2">
                        {viewMode === 'allergens' ? "Browse all items and click the warning icon to mark your allergies." : viewMode === 'preferences' ? "Browse all items and click the star icon to mark your preferences." : "Try adjusting your search terms or filters."}
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredItems.map(item => {
                        const isAllergen = allergenIds.has(item.id);
                        const isPref = preferenceIds.has(item.id);
                        let borderClass = 'border-gray-100';
                        if (isAllergen) borderClass = 'border-red-200 bg-red-50/10';
                        else if (isPref) borderClass = 'border-green-200 bg-green-50/10';

                        return (
                            <div key={item.id} className={`bg-white rounded-xl shadow-sm border ${borderClass} overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group`}>
                                <div className="p-6">
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-xl font-bold text-gray-800 line-clamp-1 group-hover:text-teal-600 transition-colors">{item.name}</h3>

                                            <div className="flex gap-1 ml-2">
                                                <button
                                                    onClick={() => togglePreference(item.id)}
                                                    className={`p-1.5 rounded-full transition-all flex border items-center justify-center ${isPref ? 'bg-green-100 text-green-600 border-green-200 shadow-sm' : 'bg-gray-50 text-gray-400 border-gray-200 hover:bg-green-50 hover:text-green-500 hover:border-green-200'}`}
                                                    title={isPref ? "Remove Preference" : "Mark as Preference"}
                                                >
                                                    ⭐
                                                </button>
                                                <button
                                                    onClick={() => toggleAllergen(item.id)}
                                                    className={`p-1.5 rounded-full transition-all flex border items-center justify-center ${isAllergen ? 'bg-red-100 text-red-600 border-red-200 shadow-sm' : 'bg-gray-50 text-gray-400 border-gray-200 hover:bg-red-50 hover:text-red-500 hover:border-red-200'}`}
                                                    title={isAllergen ? "Remove Allergen" : "Mark as Allergen"}
                                                >
                                                    ⚠️
                                                </button>
                                            </div>
                                        </div>
                                        {item.weight_per_unit_g && (
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                                                ~{item.weight_per_unit_g}g / {item.nutrition_unit}
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-gray-500 text-sm mb-4 line-clamp-2 min-h-[40px]">
                                        {item.description || "No description provided."}
                                    </p>

                                    <div className="bg-gray-50 p-4 rounded-lg">
                                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-2">Nutrition per {item.nutrition_unit === 'g' || item.nutrition_unit === 'ml' ? '100' + item.nutrition_unit : '1 ' + item.nutrition_unit}</span>
                                        <div className="grid grid-cols-2 gap-y-3 gap-x-4">
                                            <div>
                                                <span className="text-xs text-gray-500 block">Calories</span>
                                                <span className="font-bold text-orange-600">{item.calories} kcal</span>
                                            </div>
                                            <div>
                                                <span className="text-xs text-gray-500 block">Protein</span>
                                                <span className="font-bold text-blue-600">{item.protein_g}g</span>
                                            </div>
                                            <div>
                                                <span className="text-xs text-gray-500 block">Carbs</span>
                                                <span className="font-bold text-green-600">{item.carbs_g}g</span>
                                            </div>
                                            <div>
                                                <span className="text-xs text-gray-500 block">Fat</span>
                                                <span className="font-bold text-red-600">{item.fat_g}g</span>
                                            </div>
                                        </div>
                                    </div>

                                    {item.labels && item.labels.length > 0 && (
                                        <div className="mt-4 flex flex-wrap gap-2">
                                            {item.labels.map(l => (
                                                <span key={l} className="px-2 py-1 bg-teal-50 text-teal-700 text-xs font-medium rounded-md border border-teal-100">
                                                    {l}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
