from datetime import datetime, timedelta, timezone
from typing import Optional
from core.supabase_client import supabase


def _now():
    return datetime.now(timezone.utc).isoformat()


def _log(admin_id: str, action: str, target: str, note: Optional[str] = None):
    supabase.table("moderation_log").insert({
        "admin_id": admin_id,
        "action": action,
        "target": target,
        "note": note,
        "created_at": _now(),
    }).execute()


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats():
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    total_users         = supabase.table("users").select("id", count="exact").execute()
    active_today        = supabase.table("users").select("id", count="exact").eq("status", "active").execute()
    total_consultants   = supabase.table("consultant_profiles").select("id", count="exact").execute()
    pending_verif       = supabase.table("consultant_profiles").select("id", count="exact").eq("verification_status", "pending").execute()
    reported_content    = supabase.table("reports").select("id", count="exact").eq("status", "pending").execute()
    total_appointments  = supabase.table("appointments").select("id", count="exact").execute()

    return {
        "total_users":            total_users.count or 0,
        "active_today":           active_today.count or 0,
        "total_consultants":      total_consultants.count or 0,
        "pending_verifications":  pending_verif.count or 0,
        "reported_content":       reported_content.count or 0,
        "total_appointments":     total_appointments.count or 0,
    }


# ── Users ─────────────────────────────────────────────────────────────────────

def get_all_users(search: Optional[str] = None):
    query = supabase.table("users").select("id, full_name, email, role, status, created_at")
    if search:
        query = query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%")
    query = query.order("created_at", desc=True)
    result = query.execute()
    return result.data or []


def set_user_status(admin_id: str, user_id: str, status: str, note: Optional[str] = None):
    supabase.table("users").update({"status": status}).eq("id", user_id).execute()
    action = "Banned user" if status == "banned" else "Unbanned user"
    _log(admin_id, action, user_id, note)
    return {"success": True}


# ── Consultants ───────────────────────────────────────────────────────────────

def get_consultants(status: Optional[str] = None):
    query = supabase.table("consultant_profiles").select("*, users(full_name, email)")
    if status and status != "all":
        query = query.eq("verification_status", status)
    query = query.order("created_at", desc=True)
    result = query.execute()

    rows = []
    for row in (result.data or []):
        user = row.pop("users", {}) or {}
        rows.append({**row, "full_name": user.get("full_name"), "email": user.get("email")})
    return rows


def verify_consultant(admin_id: str, consultant_id: str, decision: str, note: Optional[str] = None):
    new_status = "verified" if decision == "approve" else "rejected"
    supabase.table("consultant_profiles").update({
        "verification_status": new_status,
        "verification_note": note,
        "verified_at": _now() if new_status == "verified" else None,
        "verified_by": admin_id,
    }).eq("id", consultant_id).execute()

    action = "Approved consultant" if new_status == "verified" else "Rejected consultant"
    _log(admin_id, action, consultant_id, note)
    return {"success": True, "status": new_status}


# ── Reports ───────────────────────────────────────────────────────────────────

def get_reports(status: Optional[str] = None):
    query = supabase.table("reports").select(
        "*, reporter:users!reporter_id(full_name), reported:users!reported_user_id(full_name)"
    )
    if status:
        query = query.eq("status", status)
    query = query.order("created_at", desc=True)
    result = query.execute()

    rows = []
    for row in (result.data or []):
        rows.append({
            **row,
            "reporter_name": (row.pop("reporter", None) or {}).get("full_name"),
            "reported_name": (row.pop("reported", None) or {}).get("full_name"),
        })
    return rows


def action_report(admin_id: str, report_id: str, action: str, note: Optional[str] = None):
    report = supabase.table("reports").select("*").eq("id", report_id).single().execute()
    if not report.data:
        raise ValueError("Report not found")

    new_status = "dismissed" if action == "dismiss" else "actioned"

    supabase.table("reports").update({
        "status": new_status,
        "actioned_by": admin_id,
        "actioned_at": _now(),
        "action_taken": action,
        "action_note": note,
    }).eq("id", report_id).execute()

    if action == "ban":
        supabase.table("users").update({"status": "banned"}).eq("id", report.data["reported_user_id"]).execute()

    action_labels = {
        "remove":  "Removed content",
        "resolve": "Resolved report",
        "ban":     "Banned user via report",
        "dismiss": "Dismissed report",
    }
    _log(admin_id, action_labels.get(action, action), f"Report #{report_id}", note)
    return {"success": True}


# ── Audit Log ─────────────────────────────────────────────────────────────────

def get_audit_log(limit: int = 50):
    result = (
        supabase.table("moderation_log")
        .select("*, users(full_name)")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = []
    for row in (result.data or []):
        rows.append({
            **row,
            "admin_name": (row.pop("users", None) or {}).get("full_name", "Admin"),
        })
    return rows