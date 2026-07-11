"use client";

import { useEffect, useState, FormEvent, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import Fuse from "fuse.js";

type MealIngredient = {
    food_item_name: string;
    quantity: number;
    unit: string;
};

type Meal = {
    id: string;
    name: string;
    description: string | null;
    instructions: string | null;
    image_url: string | null;
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    sodium_mg?: number;
    fiber_g?: number;
    sugar_g?: number;
    servings: number;
    total_weight_g: number | null;
    labels: string[];
    ingredients: MealIngredient[];
};

export default function MealsBrowser() {
    const [q, setQ] = useState("");
    const [labelFilters, setLabelFilters] = useState<string[]>([]);
    const [meals, setMeals] = useState<Meal[]>([]);
    const [likedMealIds, setLikedMealIds] = useState<Set<string>>(new Set());
    const [viewMode, setViewMode] = useState<"all" | "liked">("all");
    const [expandedMeal, setExpandedMeal] = useState<Meal | null>(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fuse = useMemo(() => new Fuse(meals, { keys: ['name', 'description'], threshold: 0.4 }), [meals]);

    // Filtered data memo
    const filteredMeals = useMemo(() => {
        let result = q ? fuse.search(q).map(res => res.item) : meals;

        if (labelFilters.length > 0) {
            result = result.filter(meal =>
                meal.labels && labelFilters.every(lf => meal.labels.includes(lf))
            );
        }

        return result;
    }, [meals, q, labelFilters, fuse]);

    const availableLabels = [
        "breakfast", "lunch", "dinner", "snack",
        "high_protein", "low_carb", "vegetarian", "vegan", "halal", "gym_friendly"
    ];

    useEffect(() => {
        if (viewMode === "all") {
            fetchMeals();
        } else {
            fetchLikedMeals();
        }
        fetchLikedMealIds();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [viewMode]);

    const fetchMeals = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await apiFetch(`/api/meals?limit=1000`);
            setMeals(data);
        } catch (err: any) {
            setError(err.message || "Failed to fetch meals.");
        } finally {
            setLoading(false);
        }
    };

    const fetchLikedMeals = async () => {
        try {
            setLoading(true);
            setError(null);
            // We use the liked endpoint which currently returns full Meal objects
            const data = await apiFetch(`/api/meals/liked?limit=1000`);
            setMeals(data);
        } catch (err: any) {
            setError(err.message || "Failed to fetch liked meals.");
        } finally {
            setLoading(false);
        }
    };

    const fetchLikedMealIds = async () => {
        try {
            const data = await apiFetch(`/api/meals/liked?limit=1000`);
            const ids = new Set<string>(data.map((m: any) => m.id));
            setLikedMealIds(ids);
        } catch (err: any) {
            console.error("Failed to load liked meal IDs", err);
        }
    };

    const handleSearch = (e: FormEvent) => {
        e.preventDefault();
        // Search is purely client-side via filteredMeals memo.
    };

    const toggleLike = async (mealId: string) => {
        const isLiked = likedMealIds.has(mealId);

        // Optimistic UI update
        const newLikedIds = new Set(likedMealIds);
        if (isLiked) {
            newLikedIds.delete(mealId);
        } else {
            newLikedIds.add(mealId);
        }
        setLikedMealIds(newLikedIds);

        // If we are in "liked" view and we unlike something, optimistically remove it from the list
        if (viewMode === "liked" && isLiked) {
            setMeals(meals.filter(m => m.id !== mealId));
        }

        try {
            if (isLiked) {
                await apiFetch(`/api/meals/${mealId}/like`, { method: "DELETE" });
            } else {
                await apiFetch(`/api/meals/${mealId}/like`, { method: "POST" });
            }
        } catch (error) {
            console.error("Failed to toggle like status", error);
            // Revert optimistic update on failure
            fetchLikedMealIds();
            if (viewMode === "liked" && isLiked) {
                fetchLikedMeals();
            }
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-6 space-y-8 animate-in fade-in duration-500">
            <div className="bg-gradient-to-r from-orange-400 to-rose-500 rounded-2xl p-8 text-white shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                    <h1 className="text-4xl font-extrabold mb-2 tracking-tight">Meals Catalogue</h1>
                    <p className="text-orange-50 text-lg opacity-90 max-w-2xl">
                        Explore delicious verified meals, check their macros, and save your favorites to perfectly align with your health goals.
                    </p>
                </div>

                <div className="flex bg-white/20 p-1 rounded-xl backdrop-blur-md self-stretch md:self-auto">
                    <button
                        onClick={() => setViewMode("all")}
                        className={`px-6 py-2 rounded-lg font-medium transition-all flex-1 ${viewMode === 'all' ? 'bg-white text-orange-600 shadow-sm' : 'text-white hover:bg-white/10'}`}
                    >
                        Browse All
                    </button>
                    <button
                        onClick={() => setViewMode("liked")}
                        className={`px-6 py-2 rounded-lg font-medium transition-all flex items-center justify-center flex-1 gap-2 ${viewMode === 'liked' ? 'bg-white text-orange-600 shadow-sm' : 'text-white hover:bg-white/10'}`}
                    >
                        <span>❤️</span> My Favorites
                    </button>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-md border border-gray-100 p-6">
                <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4 items-end">
                    <div className="flex-1 w-full relative">
                        <label className="block text-sm font-semibold text-gray-700 mb-2">Search Meals</label>
                        <div className="relative">
                            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400">
                                🔍
                            </span>
                            <input
                                type="text"
                                className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all outline-none"
                                placeholder="E.g., Grilled Chicken Salad..."
                                value={q}
                                onChange={(e) => setQ(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="w-full md:w-80">
                        <label className="block text-sm font-semibold text-gray-700 mb-2">Filter Category</label>
                        <div className="relative border border-gray-200 rounded-lg bg-gray-50 min-h-[50px] flex items-center p-2 focus-within:ring-2 focus-within:ring-orange-500 focus-within:border-orange-500 transition-all">
                            <div className="flex flex-wrap gap-2 items-center flex-1">
                                {labelFilters.length === 0 && <span className="text-gray-400 pl-2">All Categories</span>}
                                {labelFilters.map(l => (
                                    <span
                                        key={l}
                                        onClick={() => setLabelFilters(prev => prev.filter(x => x !== l))}
                                        className="bg-orange-100 text-orange-600 px-3 py-1 rounded-full text-xs font-bold shadow-sm hover:bg-orange-200 transition-colors cursor-pointer flex items-center gap-1 z-10"
                                    >
                                        {l.replace('_', ' ').charAt(0).toUpperCase() + l.replace('_', ' ').slice(1)}
                                        <span className="text-[10px] bg-orange-200 rounded-full w-4 h-4 flex items-center justify-center">✕</span>
                                    </span>
                                ))}
                                <select
                                    className="bg-transparent border-none outline-none appearance-none cursor-pointer flex-1 min-w-[120px] text-gray-700 py-1"
                                    value=""
                                    onChange={(e) => {
                                        if (e.target.value && !labelFilters.includes(e.target.value)) {
                                            setLabelFilters(p => [...p, e.target.value]);
                                        }
                                    }}
                                >
                                    <option value="">+ Add filter...</option>
                                    {availableLabels.filter(l => !labelFilters.includes(l)).map(l => (
                                        <option key={l} value={l}>{l.replace('_', ' ').charAt(0).toUpperCase() + l.replace('_', ' ').slice(1)}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>
                    {/* The search button isn't strictly necessary since it filters instantly but we'll leave it in place or just rely on Reset */}
                    {(q || labelFilters.length > 0) && (
                        <button
                            type="button"
                            onClick={() => { setQ(""); setLabelFilters([]); }}
                            className="w-full md:w-auto px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg transition-all"
                        >
                            Reset Options
                        </button>
                    )}
                </form>
            </div>

            {loading ? (
                <div className="flex justify-center items-center py-24">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
                </div>
            ) : error ? (
                <div className="bg-red-50 border-l-4 border-red-500 p-6 rounded-r-lg shadow-sm">
                    <div className="flex items-center">
                        <span className="text-red-500 text-xl mr-3">⚠️</span>
                        <p className="text-red-700 font-medium">{error}</p>
                    </div>
                </div>
            ) : filteredMeals.length === 0 ? (
                <div className="text-center py-20 bg-gray-50 rounded-xl border border-dashed border-gray-300">
                    <span className="text-4xl block mb-4">🍽️</span>
                    <p className="text-gray-500 text-lg">
                        {viewMode === 'liked' ? "You haven't saved any favorite meals yet." : "No meals found matching your criteria."}
                    </p>
                    <p className="text-gray-400 text-sm mt-2">
                        {viewMode === 'liked' ? "Explore 'Browse All' and click the heart icon on meals you love!" : "Try adjusting your search terms or filters."}
                    </p>
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredMeals.map(meal => {
                            const isLiked = likedMealIds.has(meal.id);
                            return (
                                <div
                                    key={meal.id}
                                    onClick={() => setExpandedMeal(meal)}
                                    className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col cursor-pointer"
                                >
                                    {meal.image_url ? (
                                        <div className="relative h-48 overflow-hidden bg-gray-100">
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img src={meal.image_url} alt={meal.name} className="w-full h-full object-cover transition-transform duration-700 hover:scale-105" />
                                            <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); e.preventDefault(); toggleLike(meal.id); }}
                                                className="absolute top-4 right-4 p-2.5 bg-white/30 backdrop-blur-md rounded-full hover:bg-white/80 transition-all flex items-center justify-center group/btn"
                                            >
                                                <span className={`text-xl transition-all duration-300 ${isLiked ? 'scale-110 drop-shadow-md' : 'grayscale opacity-60 group-hover/btn:grayscale-0 group-hover/btn:opacity-100'}`}>
                                                    {isLiked ? '❤️' : '🤍'}
                                                </span>
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="h-32 bg-gradient-to-br from-gray-100 to-gray-200 relative flex items-center justify-center border-b border-gray-100">
                                            <span className="text-4xl opacity-20">🍽️</span>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); e.preventDefault(); toggleLike(meal.id); }}
                                                className="absolute top-4 right-4 p-2.5 bg-white shadow-sm border border-gray-100 rounded-full hover:bg-gray-50 transition-all flex items-center justify-center group/btn"
                                            >
                                                <span className={`text-xl transition-all duration-300 ${isLiked ? 'scale-110' : 'grayscale opacity-60 group-hover/btn:grayscale-0 group-hover/btn:opacity-100'}`}>
                                                    {isLiked ? '❤️' : '🤍'}
                                                </span>
                                            </button>
                                        </div>
                                    )}

                                    <div className="p-6 flex-1 flex flex-col">
                                        <h3 className="text-xl font-bold text-gray-800 mb-2 leading-tight">{meal.name}</h3>

                                        <div className="flex items-center text-sm text-gray-500 mb-4 font-medium">
                                            <span className="flex items-center">
                                                📊 {meal.calories} kcal
                                            </span>
                                            <span className="mx-2 text-gray-300">•</span>
                                            <span className="flex items-center">
                                                ⚖️ {meal.servings} serving{meal.servings > 1 ? 's' : ''}
                                            </span>
                                        </div>

                                        <div className="grid grid-cols-3 gap-2 py-3 border-y border-gray-100 mb-4 bg-gray-50/50 -mx-6 px-6">
                                            <div className="text-center">
                                                <div className="text-blue-600 font-bold">{meal.protein_g}g</div>
                                                <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Protein</div>
                                            </div>
                                            <div className="text-center border-x border-gray-200">
                                                <div className="text-green-600 font-bold">{meal.carbs_g}g</div>
                                                <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Carbs</div>
                                            </div>
                                            <div className="text-center">
                                                <div className="text-red-500 font-bold">{meal.fat_g}g</div>
                                                <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Fat</div>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-3 gap-2 pb-3 mb-4 text-center">
                                            <div>
                                                <div className="text-gray-700 font-semibold text-sm">{Math.round(meal.sodium_mg || 0)}<span className="text-[10px] text-gray-400"> mg</span></div>
                                                <div className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Sodium</div>
                                            </div>
                                            <div className="border-x border-gray-100">
                                                <div className="text-emerald-600 font-semibold text-sm">{Math.round(meal.fiber_g || 0)}<span className="text-[10px] text-gray-400"> g</span></div>
                                                <div className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Fiber</div>
                                            </div>
                                            <div>
                                                <div className="text-pink-600 font-semibold text-sm">{Math.round(meal.sugar_g || 0)}<span className="text-[10px] text-gray-400"> g</span></div>
                                                <div className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Sugar</div>
                                            </div>
                                        </div>

                                        <div className="mb-4 text-sm text-gray-600 flex-1">
                                            <p className="line-clamp-2">{meal.description || "No description provided."}</p>
                                        </div>

                                        <div className="mt-auto">
                                            {meal.labels && meal.labels.length > 0 && (
                                                <div className="flex flex-wrap gap-1.5 pt-2">
                                                    {meal.labels.slice(0, 3).map(l => (
                                                        <span key={l} className="px-2 py-1 bg-gray-100 text-gray-600 text-[10px] font-bold uppercase tracking-wide rounded border border-gray-200">
                                                            {l.replace('_', ' ')}
                                                        </span>
                                                    ))}
                                                    {meal.labels.length > 3 && (
                                                        <span className="px-2 py-1 bg-gray-50 text-gray-400 text-[10px] font-bold uppercase tracking-wide rounded border border-gray-100">
                                                            +{meal.labels.length - 3}
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    {/* Expanded Meal Modal */}
                    {expandedMeal && (
                        <div
                            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300"
                            onClick={() => setExpandedMeal(null)}
                        >
                            <div
                                className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto"
                                onClick={e => e.stopPropagation()}
                            >
                                {/* Header Image */}
                                <div className="relative h-64 sm:h-80 bg-gray-100 flex-shrink-0">
                                    {expandedMeal.image_url ? (
                                        /* eslint-disable-next-line @next/next/no-img-element */
                                        <img src={expandedMeal.image_url} alt={expandedMeal.name} className="w-full h-full object-cover" />
                                    ) : (
                                        <div className="absolute inset-0 flex items-center justify-center text-6xl opacity-20">🍽️</div>
                                    )}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>

                                    <button
                                        onClick={() => setExpandedMeal(null)}
                                        className="absolute top-4 left-4 p-2 bg-black/40 text-white rounded-full hover:bg-black/60 transition-all backdrop-blur-md"
                                    >
                                        ✕
                                    </button>

                                    <button
                                        onClick={() => toggleLike(expandedMeal.id)}
                                        className="absolute top-4 right-4 p-3 bg-white/30 backdrop-blur-md rounded-full hover:bg-white/80 transition-all flex items-center justify-center"
                                    >
                                        <span className={`text-2xl transition-all duration-300 ${likedMealIds.has(expandedMeal.id) ? 'scale-110 drop-shadow-md' : 'grayscale opacity-60'}`}>
                                            {likedMealIds.has(expandedMeal.id) ? '❤️' : '🤍'}
                                        </span>
                                    </button>

                                    <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-8 text-white">
                                        {expandedMeal.labels && expandedMeal.labels.length > 0 && (
                                            <div className="flex flex-wrap gap-2 mb-3">
                                                {expandedMeal.labels.map(l => (
                                                    <span key={l} className="px-3 py-1 bg-white/20 backdrop-blur-sm text-white text-xs font-bold uppercase tracking-wider rounded-full shadow-sm border border-white/30">
                                                        {l.replace('_', ' ')}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                        <h2 className="text-3xl sm:text-4xl font-extrabold leading-tight text-shadow-sm">{expandedMeal.name}</h2>
                                        <p className="text-gray-200 mt-2 font-medium">{expandedMeal.servings} serving{expandedMeal.servings > 1 ? 's' : ''}</p>
                                    </div>
                                </div>

                                {/* Modal Body */}
                                <div className="p-6 sm:p-8">
                                    <div className="flex flex-col md:flex-row gap-8">
                                        {/* Left Col: Details & Macros */}
                                        <div className="flex-1 space-y-6">
                                            {expandedMeal.description && (
                                                <div>
                                                    <h3 className="text-lg font-bold text-gray-800 mb-2">About this meal</h3>
                                                    <p className="text-gray-600 leading-relaxed">{expandedMeal.description}</p>
                                                </div>
                                            )}

                                            <div className="bg-orange-50/50 border border-orange-100 rounded-xl p-5">
                                                <h3 className="text-sm font-bold text-orange-800 uppercase tracking-wider mb-4 flex items-center gap-2">
                                                    <span>📊</span> Nutrition per serving
                                                </h3>
                                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                                    <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-orange-100">
                                                        <div className="text-2xl font-black text-gray-800">{expandedMeal.calories}</div>
                                                        <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Calories</div>
                                                    </div>
                                                    <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-indigo-50">
                                                        <div className="text-2xl font-black text-indigo-600">{expandedMeal.protein_g}g</div>
                                                        <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Protein</div>
                                                    </div>
                                                    <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-emerald-50">
                                                        <div className="text-2xl font-black text-emerald-600">{expandedMeal.carbs_g}g</div>
                                                        <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Carbs</div>
                                                    </div>
                                                    <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-rose-50">
                                                        <div className="text-2xl font-black text-rose-500">{expandedMeal.fat_g}g</div>
                                                        <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Fat</div>
                                                    </div>
                                                </div>
                                                <div className="grid grid-cols-3 gap-4 mt-4">
                                                    <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-gray-100">
                                                        <div className="text-xl font-black text-gray-700">{Math.round(expandedMeal.sodium_mg || 0)}<span className="text-xs text-gray-400"> mg</span></div>
                                                        <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Sodium</div>
                                                    </div>
                                                    <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-emerald-50">
                                                        <div className="text-xl font-black text-emerald-700">{Math.round(expandedMeal.fiber_g || 0)}<span className="text-xs text-gray-400"> g</span></div>
                                                        <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Fiber</div>
                                                    </div>
                                                    <div className="bg-white p-3 rounded-lg shadow-sm text-center border border-pink-50">
                                                        <div className="text-xl font-black text-pink-600">{Math.round(expandedMeal.sugar_g || 0)}<span className="text-xs text-gray-400"> g</span></div>
                                                        <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">Sugar</div>
                                                    </div>
                                                </div>
                                            </div>

                                            {expandedMeal.instructions && (
                                                <div>
                                                    <h3 className="text-lg font-bold text-gray-800 mb-3 flex items-center gap-2">
                                                        <span>👨‍🍳</span> Preparation
                                                    </h3>
                                                    <div className="bg-gray-50 rounded-xl p-5 text-gray-700 whitespace-pre-wrap leading-relaxed text-sm">
                                                        {expandedMeal.instructions}
                                                    </div>
                                                </div>
                                            )}
                                        </div>

                                        {/* Right Col: Ingredients */}
                                        <div className="w-full md:w-72 flex-shrink-0">
                                            <div className="bg-gray-50 rounded-xl p-5 border border-gray-100 h-full">
                                                <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                                                    <span>🧺</span> Ingredients
                                                </h3>
                                                {(!expandedMeal.ingredients || expandedMeal.ingredients.length === 0) ? (
                                                    <p className="text-gray-400 text-sm italic">No ingredients listed.</p>
                                                ) : (
                                                    <ul className="space-y-3">
                                                        {expandedMeal.ingredients.map((ing, idx) => (
                                                            <li key={idx} className="flex justify-between items-start text-sm pb-3 border-b border-gray-200/60 last:border-0 last:pb-0">
                                                                <span className="font-semibold text-gray-700 pr-4">{ing.food_item_name}</span>
                                                                <span className="text-gray-500 whitespace-nowrap bg-white px-2 py-0.5 rounded shadow-sm border border-gray-100">
                                                                    {ing.quantity} {ing.unit}
                                                                </span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div >
    );
}
