// The draft-plan picker: the clickable slots the chat shows instead of asking
// "which plan? (ID cf6c0f02…)" in prose.
//
// Rendered in the message flow when the backend emits a `choice` frame, which happens
// when a write is blocked until the user points the chat at a plan. Styled as a sibling
// of the amber approval card so both read as the same family of in-flow interrupts.

import type { PlanRead } from "@/lib/types";
import { formatRelativeDate } from "@/lib/format";
import { PlanSummary, planSignature, planIsEmpty } from "./PlanSummary";

export type DraftChoice = {
    kind: "choose_draft_plan";
    reason: "unpinned_with_drafts" | "empty_draft_exists";
    plans: PlanRead[];
    allowNew: boolean;
    /** Approval-mode only: the decisions to replay verbatim once a plan is pinned.
     * Echoed back by the backend rather than held here, because sendDecisions() has
     * already cleared its own copy by the time the picker appears. */
    resume: { decisions: { decision: "approve" | "edit" | "reject"; message?: string }[] } | null;
};

/** Sentinel for the "create new" tile, so `busy` can distinguish it from a plan id. */
export const NEW_PLAN = "__new__";

/** Titles for cards that are otherwise indistinguishable.
 *
 * Every AI draft is literally named "AI plan", so the title is the plan's CONTENTS.
 * When two plans have identical contents AND the same day, a #n suffix is the only
 * thing left — derived from list position at render time, never persisted (there is no
 * slot/ordinal concept in the backend, and this does not invent one). */
export function cardTitles(plans: PlanRead[]): string[] {
    const raw = plans.map((p) => ({
        sig: planIsEmpty(p) ? "" : planSignature(p),
        day: (p.created_at || "").slice(0, 10),
    }));
    const seen = new Map<string, number>();
    return raw.map(({ sig, day }) => {
        if (!sig) return "Empty draft";
        const dupes = raw.filter((r) => r.sig === sig && r.day === day).length;
        if (dupes < 2) return sig;
        const key = `${sig}|${day}`;
        const n = (seen.get(key) ?? 0) + 1;
        seen.set(key, n);
        return `${sig}  #${n}`;
    });
}

export function DraftPlanPicker({
    choice, busy, error, onPick,
}: {
    choice: DraftChoice;
    busy: string | null;
    error: string | null;
    onPick: (planId: string | null) => void;
}) {
    const titles = cardTitles(choice.plans);
    const heading = choice.reason === "empty_draft_exists"
        ? "You already have an empty draft — reuse it, or start another?"
        : "Which plan should this go into?";

    return (
        <div className="rounded-2xl border-2 border-indigo-300 bg-indigo-50 p-4 space-y-3">
            <div>
                <p className="text-sm font-semibold text-indigo-900">{heading}</p>
                <p className="text-xs text-indigo-800 mt-0.5">
                    Pick one to carry on with it — or just tell me which one.
                </p>
            </div>

            {error && (
                <p className="text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                    {error}
                </p>
            )}

            <div className="space-y-2">
                {choice.plans.map((p, i) => (
                    <button
                        key={p.id}
                        onClick={() => onPick(p.id)}
                        disabled={!!busy}
                        className="w-full text-left rounded-lg bg-white border border-indigo-200 p-3 space-y-2 hover:border-indigo-400 hover:shadow-sm disabled:opacity-50 disabled:cursor-wait transition"
                    >
                        <div className="flex items-baseline justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-sm font-semibold text-gray-900 truncate">{titles[i]}</p>
                                <p className="text-xs text-gray-400">{p.name}</p>
                            </div>
                            <span className="text-xs text-gray-500 shrink-0">
                                {busy === p.id ? "Opening…" : formatRelativeDate(p.created_at)}
                            </span>
                        </div>
                        <PlanSummary plan={p} compact />
                    </button>
                ))}

                {choice.allowNew && (
                    <button
                        onClick={() => onPick(null)}
                        disabled={!!busy}
                        className="w-full rounded-lg border-2 border-dashed border-indigo-300 bg-white/60 px-3 py-3 text-sm font-semibold text-indigo-700 hover:bg-white hover:border-indigo-400 disabled:opacity-50 disabled:cursor-wait transition"
                    >
                        {busy === NEW_PLAN ? "Creating…" : "➕ Create a new plan"}
                    </button>
                )}
            </div>
        </div>
    );
}
