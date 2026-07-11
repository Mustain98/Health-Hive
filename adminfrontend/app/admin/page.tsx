"use client";

import { useState, useEffect, CSSProperties, ReactNode } from "react";
import { apiFetch, apiUpload } from "../../lib/api";

// ── Types ────────────────────────────────────────────────────────────────────
interface AdminStats {
  total_users: number;
  users_by_type?: Record<string, number>;
  total_consultants: number;
  verified_consultants?: number;
  pending_verifications: number;
  total_appointments: number;
  appointments_by_status?: Record<string, number>;
  upcoming_appointments?: number;
  consultation_requests_by_status?: Record<string, number>;
  total_meals?: number;
  meals_enriched?: number;
  meals_not_enriched?: number;
  total_food_items?: number;
  pending_applications?: number;
  unverified_documents?: number;
  consultants_needing_review?: number;
}

interface User {
  id: string;
  full_name?: string;
  email: string;
  role: string;
}

interface Consultant {
  id: string;
  user_id: string;
  full_name?: string;
  email: string;
  specialties?: string;
  consultant_type?: string;
  verification_status: "pending" | "verified" | "rejected";
  created_at?: string;
  highest_qualification?: string;
  bio?: string;
}

interface ConsultationOverview {
  totals: { pending: number; accepted: number; declined: number; total: number };
  open_chats: number;
  per_consultant: {
    consultant_user_id: string;
    display_name: string | null;
    is_verified: boolean;
    pending: number;
    accepted: number;
    declined: number;
    open_chats: number;
    total: number;
  }[];
}

interface ConsultantApplication {
  id: string;
  user_id: string;
  display_name: string;
  email?: string;
  consultant_type: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  documents?: { id: string; doc_type: string; file_path: string; url?: string; issuer?: string; issue_date?: string; file_name?: string }[];
  highest_qualification?: string;
  specialties?: string;
  graduation_institution?: string;
  registration_body?: string;
  registration_number?: string;
  bio?: string;
  other_info?: string;
}

interface NavItem {
  id: string;
  label: string;
  icon: string;
  badge?: number;
}

// ── Design Tokens ────────────────────────────────────────────────────────────
const C = {
  blue: "#2563eb",
  blueSoft: "#eff6ff",
  green: "#16a34a",
  greenSoft: "#f0fdf4",
  red: "#dc2626",
  redSoft: "#fef2f2",
  amber: "#d97706",
  amberSoft: "#fffbeb",
  gray50: "#f9fafb",
  gray100: "#f3f4f6",
  gray200: "#e5e7eb",
  gray400: "#9ca3af",
  gray500: "#6b7280",
  gray700: "#374151",
  gray900: "#111827",
  white: "#ffffff",
  modalOverlay: "rgba(0,0,0,0.5)",
} as const;

const NAV: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "users", label: "Users", icon: "👥" },
  { id: "consultants", label: "Consultants", icon: "🏥" },
  { id: "applications", label: "Applications", icon: "📝" },
  { id: "consultations", label: "Consultations", icon: "💬" },
  { id: "food_items", label: "Food Database", icon: "🍎" },
  { id: "meals", label: "Meals", icon: "🍽️" },
];

// ── Small helpers ────────────────────────────────────────────────────────────
function statBreakdown(counts?: Record<string, number>): string {
  if (!counts || Object.keys(counts).length === 0) return "—";
  return Object.entries(counts)
    .map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`)
    .join(" · ");
}

function sumValues(counts?: Record<string, number>): number {
  return Object.values(counts || {}).reduce((a, b) => a + b, 0);
}

// ── Utility Components ───────────────────────────────────────────────────────
type BadgeStatus = "active" | "banned" | "verified" | "pending" | "rejected" | "open" | "resolved" | "flagged" | "dismissed" | "actioned";

function Badge({ status }: { status: BadgeStatus | string }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    active: { bg: C.greenSoft, color: C.green, label: "Active" },
    banned: { bg: C.redSoft, color: C.red, label: "Banned" },
    verified: { bg: C.greenSoft, color: C.green, label: "Verified" },
    pending: { bg: C.amberSoft, color: C.amber, label: "Pending" },
    rejected: { bg: C.redSoft, color: C.red, label: "Rejected" },
    open: { bg: C.amberSoft, color: C.amber, label: "Open" },
    resolved: { bg: C.greenSoft, color: C.green, label: "Resolved" },
    dismissed: { bg: C.gray100, color: C.gray500, label: "Dismissed" },
    actioned: { bg: C.blueSoft, color: C.blue, label: "Actioned" },
  };
  const s = map[status] ?? { bg: C.gray100, color: C.gray500, label: status };
  return (
    <span style={{
      backgroundColor: s.bg, color: s.color,
      fontSize: "11px", fontWeight: 600,
      padding: "3px 10px", borderRadius: "20px",
      letterSpacing: "0.03em", textTransform: "uppercase",
    }}>{s.label}</span>
  );
}

function StatCard({ label, value, icon, accent, sub }: {
  label: string; value: number; icon: string; accent?: boolean; sub?: string;
}) {
  return (
    <div style={{
      backgroundColor: C.white, border: `1px solid ${C.gray200}`,
      borderRadius: "14px", padding: "22px 24px",
      display: "flex", flexDirection: "column", gap: "8px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <p style={{ fontSize: "13px", color: C.gray500, fontWeight: 500, margin: 0 }}>{label}</p>
        <span style={{ fontSize: "20px" }}>{icon}</span>
      </div>
      <p style={{ fontSize: "34px", fontWeight: 700, margin: 0, color: accent ? C.blue : C.gray900 }}>
        {value ?? 0}
      </p>
      {sub && <p style={{ fontSize: "12px", color: C.gray400, margin: 0 }}>{sub}</p>}
    </div>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2 style={{ fontSize: "16px", fontWeight: 700, color: C.gray900, margin: "0 0 16px 0", letterSpacing: "-0.01em" }}>
      {children}
    </h2>
  );
}

function Table({ headers, children, loading }: { headers: string[]; children: ReactNode; loading?: boolean }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
        <thead>
          <tr style={{ borderBottom: `2px solid ${C.gray100}` }}>
            {headers.map(h => (
              <th key={h} style={{
                textAlign: "left", padding: "10px 14px",
                color: C.gray500, fontWeight: 600,
                fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em",
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan={headers.length} style={{ textAlign: "center", padding: "20px", color: C.gray500 }}>Loading...</td></tr>
          ) : children}
        </tbody>
      </table>
    </div>
  );
}

function Tr({ children }: { children: ReactNode }) {
  const [hov, setHov] = useState(false);
  return (
    <tr
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        borderBottom: `1px solid ${C.gray100}`,
        backgroundColor: hov ? C.gray50 : C.white,
        transition: "background 0.15s",
      }}
    >{children}</tr>
  );
}

function Td({ children, bold }: { children: ReactNode; bold?: boolean }) {
  return (
    <td style={{ padding: "12px 14px", color: bold ? C.gray900 : C.gray700, fontWeight: bold ? 600 : 400 }}>
      {children}
    </td>
  );
}

function ActionBtn({ color, bg, onClick, children }: {
  color: string; bg: string; onClick: () => void; children: ReactNode;
}) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        fontSize: "11px", fontWeight: 600, padding: "4px 12px", borderRadius: "6px",
        border: `1px solid ${color}`,
        backgroundColor: hov ? color : bg,
        color: hov ? C.white : color,
        cursor: "pointer", transition: "all 0.15s", marginRight: "6px",
      }}
    >{children}</button>
  );
}

function Card({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div style={{
      backgroundColor: C.white, border: `1px solid ${C.gray200}`,
      borderRadius: "14px", padding: "24px", ...style,
    }}>{children}</div>
  );
}

function formatDate(isoStr?: string) {
  if (!isoStr) return "-";
  return new Date(isoStr).toLocaleDateString();
}

// ── Sidebar ──────────────────────────────────────────────────────────────────
function Sidebar({ active, onNav, pendingApps, consultantsNeedingReview, pendingConsultations }: {
  active: string;
  onNav: (id: string) => void;
  pendingApps: number;
  consultantsNeedingReview: number;
  pendingConsultations: number;
}) {
  return (
    <aside style={{
      width: "220px", minHeight: "100vh", flexShrink: 0,
      backgroundColor: C.white,
      borderRight: `1px solid ${C.gray200}`,
      display: "flex", flexDirection: "column",
      position: "sticky", top: 0,
    }}>
      <nav style={{ padding: "70px 10px 12px", flex: 1 }}>
        {NAV.map(item => {
          const isActive = active === item.id;
          const badgeCount =
            item.id === "consultants" ? consultantsNeedingReview :
              item.id === "applications" ? pendingApps :
                item.id === "consultations" ? pendingConsultations : 0;
          return (
            <button
              key={item.id}
              onClick={() => onNav(item.id)}
              style={{
                width: "100%", display: "flex", alignItems: "center", gap: "10px",
                padding: "10px 12px", borderRadius: "8px",
                backgroundColor: isActive ? C.blueSoft : "transparent",
                border: isActive ? `1px solid ${C.gray200}` : "1px solid transparent",
                color: isActive ? C.blue : C.gray500,
                cursor: "pointer", fontSize: "13px", fontWeight: isActive ? 600 : 400,
                marginBottom: "2px", textAlign: "left", transition: "all 0.15s",
              }}
            >
              <span style={{ fontSize: "14px", width: "18px", textAlign: "center" }}>{item.icon}</span>
              <span style={{ flex: 1 }}>{item.label}</span>
              {badgeCount > 0 && (
                <span style={{
                  backgroundColor: C.blue, color: C.white,
                  fontSize: "10px", fontWeight: 700,
                  padding: "1px 7px", borderRadius: "20px",
                }}>{badgeCount}</span>
              )}
            </button>
          );
        })}
      </nav>
      <div style={{
        padding: "14px 20px", borderTop: `1px solid ${C.gray200}`,
        display: "flex", alignItems: "center", gap: "10px",
      }}>
        <div style={{
          width: "30px", height: "30px", backgroundColor: C.blue,
          borderRadius: "50%", display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: "12px", fontWeight: 700,
          color: C.white, flexShrink: 0,
        }}>A</div>
        <div>
          <p style={{ margin: 0, fontSize: "12px", fontWeight: 600, color: C.gray900 }}>Admin</p>
          <p style={{ margin: 0, fontSize: "10px", color: C.gray400 }}>admin@healthhive.com</p>
        </div>
      </div>
    </aside>
  );
}

// ── Pages ────────────────────────────────────────────────────────────────────
function DashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);

  useEffect(() => {
    apiFetch("/api/admin/stats").then(setStats).catch(console.error);
  }, []);

  const quickActions = [
    { icon: "👥", bg: C.blueSoft, label: "Manage Users", desc: "View, search and manage all users" },
  ];

  if (!stats) return <div style={{ padding: "40px" }}>Loading stats...</div>;

  return (
    <div>
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Dashboard</h1>
        <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>
          Welcome back — here&apos;s what&apos;s happening on HealthHive today.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px", marginBottom: "28px" }}>
        <StatCard
          label="Total Users" value={stats.total_users} icon="👥"
          sub={statBreakdown(stats.users_by_type)}
        />
        <StatCard
          label="Consultants" value={stats.total_consultants} icon="🏥"
          sub={`${stats.verified_consultants ?? 0} verified · ${stats.pending_verifications} pending`}
        />
        <StatCard
          label="Pending Applications" value={stats.pending_applications ?? 0} icon="📝" accent
          sub="Awaiting review"
        />
        <StatCard
          label="Unverified Documents" value={stats.unverified_documents ?? 0} icon="⏳"
          sub={`${stats.consultants_needing_review ?? 0} consultant(s) need review`}
        />
        <StatCard
          label="Appointments" value={stats.total_appointments} icon="📅"
          sub={`${stats.upcoming_appointments ?? 0} upcoming · ${statBreakdown(stats.appointments_by_status)}`}
        />
        <StatCard
          label="Consultation Requests"
          value={sumValues(stats.consultation_requests_by_status)} icon="💬"
          sub={statBreakdown(stats.consultation_requests_by_status)}
        />
        <StatCard
          label="Meals" value={stats.total_meals ?? 0} icon="🍽️"
          sub={`${stats.meals_enriched ?? 0} AI-enriched · ${stats.meals_not_enriched ?? 0} pending`}
        />
        <StatCard label="Food Items" value={stats.total_food_items ?? 0} icon="🍎" sub="In the food database" />
      </div>

      <SectionTitle>Quick Actions</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "14px", marginBottom: "28px" }}>
        {quickActions.map(q => (
          <Card key={q.label} style={{ display: "flex", alignItems: "center", gap: "14px", cursor: "pointer" }}>
            <div style={{
              width: "44px", height: "44px", backgroundColor: q.bg,
              borderRadius: "10px", display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: "20px", flexShrink: 0,
            }}>{q.icon}</div>
            <div>
              <p style={{ margin: 0, fontWeight: 600, fontSize: "14px", color: C.gray900 }}>{q.label}</p>
              <p style={{ margin: "2px 0 0", fontSize: "12px", color: C.gray500 }}>{q.desc}</p>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function UsersPage() {
  const [search, setSearch] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchUsers = () => {
    setLoading(true);
    let url = "/api/admin/users";
    if (search) url += `?search=${encodeURIComponent(search)}`;
    apiFetch(url).then(setUsers).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => {
    const timer = setTimeout(fetchUsers, 300);
    return () => clearTimeout(timer);
  }, [search]);

  return (
    <div>
      <div style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>User Management</h1>
          <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>View and manage all registered users.</p>
        </div>
        <input
          placeholder="Search by name or email…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            padding: "8px 14px", borderRadius: "8px",
            border: `1px solid ${C.gray200}`, fontSize: "13px",
            outline: "none", width: "220px", color: C.gray900,
          }}
        />
      </div>
      <Card>
        <Table headers={["Name", "Email", "Role"]} loading={loading}>
          {users.map(u => (
            <Tr key={u.id}>
              <Td bold>{u.full_name || "-"}</Td>
              <Td>{u.email}</Td>
              <Td>{u.role}</Td>
            </Tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function ConsultantsPage() {
  const [filter, setFilter] = useState<"pending" | "verified">("pending");
  const [consultants, setConsultants] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any | null>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [actioning, setActioning] = useState(false);
  const [docActioning, setDocActioning] = useState<string | null>(null);

  const fetchConsultants = () => {
    setLoading(true);
    const url = `/api/admin/consultants?status=${filter}`;
    apiFetch(url).then(setConsultants).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { fetchConsultants(); }, [filter]);

  const openDetail = async (c: any) => {
    setSelected(c);
    setLoadingDocs(true);
    setDocs([]);
    try {
      const result = await apiFetch(`/api/admin/consultants/${c.user_id || c.id}/documents`);
      setDocs(result);
    } catch { /* ignore */ } finally { setLoadingDocs(false); }
  };

  const decide = async (id: string, decision: "approve" | "reject") => {
    const note = decision === "reject" ? prompt("Reason for rejection (required):") : "Approved by admin";
    if (decision === "reject" && !note) return;
    setActioning(true);
    try {
      await apiFetch(`/api/admin/consultants/${id}/verify`, { method: "PATCH", body: { decision, note } });
      setSelected(null);
      fetchConsultants();
    } catch { alert("Failed to update consultant status"); }
    finally { setActioning(false); }
  };

  const reviewDoc = async (consultantId: string, docId: string, decision: "approve" | "reject") => {
    const note = decision === "reject" ? prompt("Reason for rejection (required):") : "Verified by admin";
    if (decision === "reject" && !note) return;
    setDocActioning(docId);
    try {
      await apiFetch(`/api/admin/consultants/${consultantId}/documents/${docId}/review`, {
        method: "POST",
        body: { decision, note },
      });
      // Refresh docs
      const result = await apiFetch(`/api/admin/consultants/${consultantId}/documents`);
      setDocs(result);
    } catch { alert("Failed to review document"); }
    finally { setDocActioning(null); }
  };

  const tabs: Array<"pending" | "verified"> = ["pending", "verified"];
  const typeColor: Record<string, { bg: string; color: string }> = {
    clinical: { bg: "#ede9fe", color: "#7c3aed" },
    non_clinical: { bg: "#fef3c7", color: "#b45309" },
    wellness: { bg: "#d1fae5", color: "#065f46" },
  };

  const Field = ({ label, value }: { label: string; value?: string | null }) => (
    <div>
      <p style={{ margin: "0 0 3px 0", fontSize: "11px", fontWeight: 700, color: C.gray400, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</p>
      <p style={{ margin: 0, fontSize: "13px", color: value ? C.gray900 : C.gray400, fontWeight: value ? 500 : 400, fontStyle: value ? "normal" : "italic" }}>
        {value || "Not provided"}
      </p>
    </div>
  );

  const Section = ({ title, icon, children }: { title: string; icon: string; children: ReactNode }) => (
    <div style={{ backgroundColor: C.gray50, borderRadius: "12px", padding: "18px 20px", border: `1px solid ${C.gray200}` }}>
      <p style={{ margin: "0 0 14px 0", fontSize: "13px", fontWeight: 700, color: C.gray700, display: "flex", alignItems: "center", gap: "7px" }}>
        <span>{icon}</span>{title}
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
        {children}
      </div>
    </div>
  );

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Consultant Verification</h1>
        <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>
          Review applications, credentials, and manage consultant access.
        </p>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "6px", marginBottom: "20px" }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setFilter(t)} style={{
            padding: "7px 18px", borderRadius: "8px",
            border: `1px solid ${filter === t ? C.blue : C.gray200}`,
            backgroundColor: filter === t ? C.blue : C.white,
            color: filter === t ? C.white : C.gray700,
            fontSize: "12px", fontWeight: 600, cursor: "pointer", transition: "all 0.15s",
          }}>
            {t === "pending" ? "Pending Review" : "Verified"}
          </button>
        ))}
      </div>

      {/* Table */}
      <Card>
        <Table headers={["Name / Email", "Type", "Qualification", "Specialties", "Registration #", "Applied", "Status", "Action"]} loading={loading}>
          {consultants.map(c => {
            const tc = typeColor[c.consultant_type] || { bg: C.gray100, color: C.gray500 };
            const status = c.verification_status || (c.is_verified ? "verified" : "pending");
            return (
              <Tr key={c.user_id || c.id}>
                <Td bold>
                  <div>{c.full_name || c.display_name || "—"}</div>
                  <div style={{ fontSize: "11px", color: C.gray400, marginTop: "2px", fontWeight: 400 }}>{c.email}</div>
                </Td>
                <Td>
                  <span style={{ backgroundColor: tc.bg, color: tc.color, padding: "3px 9px", borderRadius: "10px", fontSize: "11px", fontWeight: 700, textTransform: "capitalize", whiteSpace: "nowrap" }}>
                    {(c.consultant_type || "—").replace(/_/g, " ")}
                  </span>
                </Td>
                <Td>{c.highest_qualification || "—"}</Td>
                <Td><span style={{ color: C.gray500, fontSize: "12px" }}>{c.specialties || "—"}</span></Td>
                <Td><span style={{ fontFamily: "monospace", fontSize: "12px", color: C.gray500 }}>{c.registration_number || "—"}</span></Td>
                <Td>{formatDate(c.created_at)}</Td>
                <Td><Badge status={status} /></Td>
                <Td>
                  <ActionBtn color={C.blue} bg={C.blueSoft} onClick={() => openDetail(c)}>View Profile</ActionBtn>
                </Td>
              </Tr>
            );
          })}
          {!loading && consultants.length === 0 && (
            <tr><td colSpan={8} style={{ textAlign: "center", padding: "30px", color: C.gray500 }}>No consultants found.</td></tr>
          )}
        </Table>
      </Card>

      {/* Detail / Verify Modal */}
      {selected && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", backgroundColor: C.modalOverlay, display: "flex", justifyContent: "center", alignItems: "flex-start", zIndex: 1000, overflowY: "auto", padding: "30px 0" }}>
          <div style={{ backgroundColor: C.white, borderRadius: "16px", width: "740px", maxWidth: "95%", padding: "0", boxShadow: "0 24px 64px rgba(0,0,0,0.22)", marginTop: "10px", overflow: "hidden" }}>

            {/* Modal Header Bar */}
            <div style={{ padding: "24px 28px 20px", borderBottom: `1px solid ${C.gray200}`, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                <div style={{ width: "48px", height: "48px", borderRadius: "50%", backgroundColor: C.blueSoft, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "20px" }}>🏥</div>
                <div>
                  <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 700, color: C.gray900 }}>
                    {selected.full_name || selected.display_name || "Unnamed Consultant"}
                  </h2>
                  <p style={{ margin: "3px 0 0", fontSize: "13px", color: C.gray500 }}>{selected.email}</p>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Badge status={selected.verification_status || (selected.is_verified ? "verified" : "pending")} />
                <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: C.gray400, padding: "0 4px" }}>✕</button>
              </div>
            </div>

            <div style={{ padding: "24px 28px", display: "flex", flexDirection: "column", gap: "18px" }}>

              {/* Identity Section */}
              <Section title="Identity & Contact" icon="👤">
                <Field label="Display Name" value={selected.display_name} />
                <Field label="Email" value={selected.email} />
                <div style={{ gridColumn: "1 / -1" }}>
                  <Field label="Bio" value={selected.bio} />
                </div>
              </Section>

              {/* Professional Section */}
              <Section title="Professional Details" icon="🎓">
                <Field label="Consultant Type" value={(selected.consultant_type || "").replace(/_/g, " ")} />
                <Field label="Specialties" value={selected.specialties} />
                <Field label="Highest Qualification" value={selected.highest_qualification} />
                <Field label="Graduation Institution" value={selected.graduation_institution} />
                <Field label="Registration Body" value={selected.registration_body} />
                <Field label="Registration Number" value={selected.registration_number} />
                {selected.other_info && (
                  <div style={{ gridColumn: "1 / -1" }}>
                    <Field label="Additional Info" value={selected.other_info} />
                  </div>
                )}
              </Section>

              {/* Timeline Section */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
                {[
                  { label: "Applied", value: formatDate(selected.created_at) },
                  { label: "Verified At", value: selected.verified_at ? formatDate(selected.verified_at) : null },
                  { label: "Status", value: selected.verification_status || (selected.is_verified ? "Verified" : "Pending") },
                ].map(({ label, value }) => (
                  <div key={label} style={{ backgroundColor: C.gray50, borderRadius: "10px", padding: "14px 16px", border: `1px solid ${C.gray200}`, textAlign: "center" }}>
                    <p style={{ margin: "0 0 4px 0", fontSize: "11px", fontWeight: 700, color: C.gray400, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</p>
                    <p style={{ margin: 0, fontSize: "13px", fontWeight: 600, color: C.gray900 }}>{value || "—"}</p>
                  </div>
                ))}
              </div>

              {/* Documents */}
              <div>
                <p style={{ margin: "0 0 12px 0", fontSize: "13px", fontWeight: 700, color: C.gray700, display: "flex", alignItems: "center", gap: "7px" }}>
                  📄 Submitted Documents
                </p>
                {loadingDocs ? (
                  <div style={{ padding: "24px", textAlign: "center", backgroundColor: C.gray50, borderRadius: "10px", border: `1px dashed ${C.gray200}` }}>
                    <p style={{ color: C.gray500, fontSize: "13px", margin: 0 }}>Generating secure document links…</p>
                  </div>
                ) : docs.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {docs.map((doc: any, i: number) => {
                      const consultantId = selected.user_id || selected.id;
                      const isUnverified = !doc.is_verified;
                      return (
                        <div key={i} style={{ border: `1px solid ${isUnverified ? C.amber : C.gray200}`, padding: "14px 16px", borderRadius: "10px", display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: isUnverified ? C.amberSoft : C.white }}>
                          <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", flex: 1, minWidth: 0 }}>
                            <div style={{ width: "36px", height: "36px", backgroundColor: C.blueSoft, borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", flexShrink: 0 }}>📃</div>
                            <div style={{ minWidth: 0 }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "3px" }}>
                                <p style={{ margin: 0, fontWeight: 700, fontSize: "13px", color: C.gray900, textTransform: "capitalize" }}>
                                  {(doc.doc_type || "document").replace(/_/g, " ")}
                                </p>
                                <Badge status={doc.is_verified ? "verified" : "pending"} />
                              </div>
                              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                                {doc.issuer && <span style={{ fontSize: "11px", color: C.gray500 }}>🏛 {doc.issuer}</span>}
                                {doc.issue_date && <span style={{ fontSize: "11px", color: C.gray500 }}>📅 Issued: {doc.issue_date}</span>}
                              </div>
                            </div>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
                            {doc.url && (
                              <a href={doc.url} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: "5px", backgroundColor: C.blueSoft, color: C.blue, textDecoration: "none", fontSize: "12px", fontWeight: 700, padding: "8px 14px", borderRadius: "8px", whiteSpace: "nowrap" }}>
                                View ↗
                              </a>
                            )}
                            {isUnverified && (
                              <>
                                <button disabled={docActioning === doc.id} onClick={() => reviewDoc(consultantId, doc.id, "approve")} style={{ padding: "6px 12px", borderRadius: "6px", border: "none", backgroundColor: C.green, color: C.white, fontWeight: 700, cursor: "pointer", fontSize: "11px" }}>
                                  ✓
                                </button>
                                <button disabled={docActioning === doc.id} onClick={() => reviewDoc(consultantId, doc.id, "reject")} style={{ padding: "6px 12px", borderRadius: "6px", border: "none", backgroundColor: C.red, color: C.white, fontWeight: 700, cursor: "pointer", fontSize: "11px" }}>
                                  ✕
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ padding: "24px", textAlign: "center", backgroundColor: C.gray50, borderRadius: "10px", border: `1px dashed ${C.gray200}` }}>
                    <p style={{ color: C.gray500, fontSize: "13px", margin: 0 }}>No documents uploaded by this consultant.</p>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              {(() => {
                const status = selected.verification_status || (selected.is_verified ? "verified" : "pending");
                const id = selected.user_id || selected.id;
                return (
                  <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", paddingTop: "4px", borderTop: `1px solid ${C.gray200}`, marginTop: "4px" }}>
                    <button onClick={() => setSelected(null)} style={{ padding: "10px 20px", borderRadius: "8px", border: `1px solid ${C.gray200}`, background: C.white, cursor: "pointer", color: C.gray700, fontWeight: 600, fontSize: "13px" }}>
                      Close
                    </button>
                    {status !== "verified" && (
                      <button onClick={() => decide(id, "approve")} disabled={actioning} style={{ padding: "10px 22px", borderRadius: "8px", border: "none", backgroundColor: C.green, color: C.white, fontWeight: 700, cursor: "pointer", fontSize: "13px" }}>
                        ✓ Approve
                      </button>
                    )}
                    {status !== "rejected" && (
                      <button onClick={() => decide(id, "reject")} disabled={actioning} style={{ padding: "10px 22px", borderRadius: "8px", border: "none", backgroundColor: C.red, color: C.white, fontWeight: 700, cursor: "pointer", fontSize: "13px" }}>
                        ✕ Reject
                      </button>
                    )}
                  </div>
                );
              })()}

            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Food Items Page ────────────────────────────────────────────────────────────
function FoodItemsPage() {
  const [search, setSearch] = useState("");
  const [labelFilter, setLabelFilter] = useState("");
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Labels for multi-select (plain strings — served from the backend enum)
  const [availableLabels, setAvailableLabels] = useState<string[]>([]);

  // Create Modal State
  const [showAdd, setShowAdd] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newFood, setNewFood] = useState({
    name: "",
    nutrition_unit: "gram",
    calories: 0,
    protein_g: 0,
    carbs_g: 0,
    fat_g: 0,
    weight_per_unit_g: 0,
    description: "",
    labels: [] as string[],
  });

  const fetchItems = () => {
    setLoading(true);
    let url = "/api/admin/food-items";
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (labelFilter) params.append("label", labelFilter);
    const qs = params.toString();
    if (qs) url += `?${qs}`;
    apiFetch(url).then(setItems).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => {
    // Fetch master label definitions once on mount
    apiFetch("/api/admin/food-labels").then(setAvailableLabels).catch(console.error);
  }, []);

  useEffect(() => {
    const timer = setTimeout(fetchItems, 300);
    return () => clearTimeout(timer);
  }, [search, labelFilter]);

  const toggleLabel = (labelName: string) => {
    setNewFood(prev => {
      const isSelected = prev.labels.includes(labelName);
      if (isSelected) {
        return { ...prev, labels: prev.labels.filter(l => l !== labelName) };
      } else {
        return { ...prev, labels: [...prev.labels, labelName] };
      }
    });
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}" from the global database?`)) return;
    try {
      await apiFetch(`/api/admin/food-items/${id}`, { method: "DELETE" });
      fetchItems();
    } catch (e: any) {
      console.error(e);
      // 409 = still referenced by meals — surface the backend message
      alert(e?.message || "Failed to delete food item");
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFood.name.trim()) return alert("Name is required");

    setIsSubmitting(true);
    try {
      // Send raw payload; backend will coerce types
      await apiFetch("/api/admin/food-items", {
        method: "POST",
        body: newFood,
      });
      setShowAdd(false);
      setNewFood({ name: "", nutrition_unit: "gram", calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0, weight_per_unit_g: 0, description: "", labels: [] });
      fetchItems();
    } catch (err) {
      console.error(err);
      alert("Failed to create food item.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Food Database</h1>
          <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>Global repository of master food items and macronutrients.</p>
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <select
            value={labelFilter}
            onChange={e => setLabelFilter(e.target.value)}
            style={{ padding: "8px 12px", borderRadius: "8px", border: `1px solid ${C.gray200}`, fontSize: "14px", outline: "none", backgroundColor: C.white, color: C.gray900 }}
          >
            <option value="">All Labels</option>
            {availableLabels.map(l => (
              <option key={l} value={l}>{l.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <input
            placeholder="Search food by name..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              padding: "8px 14px", borderRadius: "8px",
              border: `1px solid ${C.gray200}`, fontSize: "13px",
              outline: "none", width: "220px", color: C.gray900,
            }}
          />
          <button
            onClick={() => setShowAdd(true)}
            style={{
              backgroundColor: C.blue, color: C.white, border: "none",
              padding: "9px 16px", borderRadius: "8px", fontSize: "13px",
              fontWeight: 600, cursor: "pointer", transition: "all 0.15s"
            }}
          >+ Add Food Config</button>
        </div>
      </div>

      <Card>
        <Table headers={["Name", "Unit", "Labels", "Cals", "Protein", "Carbs", "Fat", "Avg Weight", "Actions"]} loading={loading}>
          {items.map(item => (
            <Tr key={item.id}>
              <Td bold>
                {item.name}
                {item.description && <div style={{ fontSize: "11px", color: C.gray500, marginTop: "2px", fontWeight: "normal" }}>{item.description}</div>}
              </Td>
              <Td><Badge status={item.nutrition_unit} /></Td>
              <Td>
                {item.labels?.length > 0 ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                    {item.labels.map((l: string) => (
                      <span key={l} style={{ backgroundColor: C.gray100, color: C.gray700, padding: "2px 6px", borderRadius: "10px", fontSize: "10px", fontWeight: 600 }}>{l}</span>
                    ))}
                  </div>
                ) : (
                  <span style={{ color: C.gray400, fontSize: "11px" }}>-</span>
                )}
              </Td>
              <Td>{item.calories} <span style={{ fontSize: "10px", color: C.gray400 }}>kcal</span></Td>
              <Td>{item.protein_g} <span style={{ fontSize: "10px", color: C.gray400 }}>g</span></Td>
              <Td>{item.carbs_g} <span style={{ fontSize: "10px", color: C.gray400 }}>g</span></Td>
              <Td>{item.fat_g} <span style={{ fontSize: "10px", color: C.gray400 }}>g</span></Td>
              <Td>{item.weight_per_unit_g ? `${item.weight_per_unit_g}g` : "-"}</Td>
              <Td>
                <ActionBtn color={C.red} bg={C.redSoft} onClick={() => handleDelete(item.id, item.name)}>Delete</ActionBtn>
              </Td>
            </Tr>
          ))}
          {items.length === 0 && !loading && (
            <tr><td colSpan={9} style={{ textAlign: "center", padding: "30px", color: C.gray500 }}>No matching food items found.</td></tr>
          )}
        </Table>
      </Card>

      {/* Create Food Modal */}
      {showAdd && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", backgroundColor: C.modalOverlay, display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: C.white, borderRadius: "14px", width: "500px", maxWidth: "90%", padding: "28px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "24px" }}>
              <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 700 }}>Add New Food Item</h2>
              <button
                onClick={() => setShowAdd(false)}
                style={{ background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: C.gray400 }}
              >✕</button>
            </div>

            <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: C.gray700, marginBottom: "6px" }}>Food Name *</label>
                <input required value={newFood.name} onChange={e => setNewFood({ ...newFood, name: e.target.value })} style={{ width: "100%", padding: "10px", borderRadius: "8px", border: `1px solid ${C.gray200}`, fontSize: "14px", outline: "none", color: C.gray900 }} placeholder="e.g. Medium Banana" />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: C.gray700, marginBottom: "6px" }}>Base Unit *</label>
                  <select required value={newFood.nutrition_unit} onChange={e => setNewFood({ ...newFood, nutrition_unit: e.target.value })} style={{ width: "100%", padding: "10px", borderRadius: "8px", border: `1px solid ${C.gray200}`, fontSize: "14px", outline: "none", backgroundColor: C.white, color: C.gray900 }}>
                    <option value="gram">Gram (per 100g)</option>
                    <option value="milliliter">Milliliter (per 100ml)</option>
                    <option value="piece">Piece (per 1 piece)</option>
                    <option value="tbsp">Tablespoon (per 1 tbsp)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: C.gray700, marginBottom: "6px" }}>Est. Weight Per Unit (g)</label>
                  <input type="number" min="0" step="0.1" value={newFood.weight_per_unit_g || ""} onChange={e => setNewFood({ ...newFood, weight_per_unit_g: parseFloat(e.target.value) || 0 })} style={{ width: "100%", padding: "10px", borderRadius: "8px", border: `1px solid ${C.gray200}`, fontSize: "14px", outline: "none", color: C.gray900 }} placeholder="Optional setup" />
                </div>
              </div>

              <div style={{ backgroundColor: C.gray50, padding: "16px", borderRadius: "10px", border: `1px solid ${C.gray200}` }}>
                <p style={{ margin: "0 0 12px 0", fontSize: "13px", fontWeight: 600, color: C.gray900 }}>Macronutrients (per {newFood.nutrition_unit === "gram" || newFood.nutrition_unit === "milliliter" ? `100 ${newFood.nutrition_unit}s` : `1 ${newFood.nutrition_unit}`})</p>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "11px", color: C.gray500, marginBottom: "4px" }}>Calories (kcal)</label>
                    <input type="number" min="0" required value={newFood.calories === 0 ? "" : newFood.calories} onChange={e => setNewFood({ ...newFood, calories: parseFloat(e.target.value) || 0 })} style={{ width: "100%", padding: "8px", borderRadius: "6px", border: `1px solid ${C.gray200}`, fontSize: "13px", outline: "none", color: C.gray900 }} />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "11px", color: C.gray500, marginBottom: "4px" }}>Protein (g)</label>
                    <input type="number" min="0" step="0.1" required value={newFood.protein_g === 0 ? "" : newFood.protein_g} onChange={e => setNewFood({ ...newFood, protein_g: parseFloat(e.target.value) || 0 })} style={{ width: "100%", padding: "8px", borderRadius: "6px", border: `1px solid ${C.gray200}`, fontSize: "13px", outline: "none", color: C.gray900 }} />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "11px", color: C.gray500, marginBottom: "4px" }}>Carbs (g)</label>
                    <input type="number" min="0" step="0.1" required value={newFood.carbs_g === 0 ? "" : newFood.carbs_g} onChange={e => setNewFood({ ...newFood, carbs_g: parseFloat(e.target.value) || 0 })} style={{ width: "100%", padding: "8px", borderRadius: "6px", border: `1px solid ${C.gray200}`, fontSize: "13px", outline: "none", color: C.gray900 }} />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "11px", color: C.gray500, marginBottom: "4px" }}>Fat (g)</label>
                    <input type="number" min="0" step="0.1" required value={newFood.fat_g === 0 ? "" : newFood.fat_g} onChange={e => setNewFood({ ...newFood, fat_g: parseFloat(e.target.value) || 0 })} style={{ width: "100%", padding: "8px", borderRadius: "6px", border: `1px solid ${C.gray200}`, fontSize: "13px", outline: "none", color: C.gray900 }} />
                  </div>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: C.gray700, marginBottom: "8px" }}>Assign Classification Labels</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {availableLabels.map(lbl => {
                    const isSelected = newFood.labels.includes(lbl);
                    return (
                      <button
                        key={lbl}
                        type="button"
                        onClick={() => toggleLabel(lbl)}
                        style={{
                          backgroundColor: isSelected ? C.blueSoft : C.white,
                          color: isSelected ? C.blue : C.gray500,
                          border: `1px solid ${isSelected ? C.blue : C.gray200}`,
                          padding: "6px 12px", borderRadius: "20px", fontSize: "11px", fontWeight: 600,
                          cursor: "pointer", transition: "all 0.15s"
                        }}
                      >
                        {lbl.replace(/_/g, ' ')}
                      </button>
                    );
                  })}
                  {availableLabels.length === 0 && <span style={{ fontSize: "12px", color: C.gray400 }}>No labels available.</span>}
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: C.gray700, marginBottom: "6px" }}>Short Description (Optional)</label>
                <input value={newFood.description} onChange={e => setNewFood({ ...newFood, description: e.target.value })} style={{ width: "100%", padding: "10px", borderRadius: "8px", border: `1px solid ${C.gray200}`, fontSize: "14px", outline: "none" }} placeholder="e.g. Contains high potassium" />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button type="button" onClick={() => setShowAdd(false)} style={{ padding: "10px 16px", borderRadius: "8px", border: `1px solid ${C.gray200}`, backgroundColor: C.white, fontWeight: 600, fontSize: "13px", cursor: "pointer" }}>Cancel</button>
                <button type="submit" disabled={isSubmitting} style={{ padding: "10px 16px", borderRadius: "8px", border: "none", backgroundColor: C.blue, color: C.white, fontWeight: 600, fontSize: "13px", cursor: isSubmitting ? "not-allowed" : "pointer", opacity: isSubmitting ? 0.7 : 1 }}>{isSubmitting ? "Saving..." : "Save Food Item"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Meals Page ────────────────────────────────────────────────────────────────
type EnrichState = "enriched" | "pending" | "not_enriched";

function enrichmentState(m: any): EnrichState {
  if (!m.enriched_at) return "not_enriched";
  // Admin edits bump updated_at; the main system's enrichment sets enriched_at only.
  // updated_at > enriched_at ⇒ source text may have changed since last enrichment.
  // (Image-only uploads also bump updated_at, so "pending" can be a false positive.)
  if (m.updated_at && new Date(m.updated_at) > new Date(m.enriched_at)) return "pending";
  return "enriched";
}

function EnrichmentBadge({ meal }: { meal: any }) {
  const state = enrichmentState(meal);
  const cfg = {
    enriched: { bg: C.greenSoft, color: C.green, label: "✨ AI-enriched" },
    pending: { bg: C.amberSoft, color: C.amber, label: "Re-enrichment pending" },
    not_enriched: { bg: C.gray100, color: C.gray500, label: "Not enriched" },
  }[state];
  return (
    <span
      title={meal.ai_health_context || "Enrichment runs automatically in the main system during meal-plan generation."}
      style={{ backgroundColor: cfg.bg, color: cfg.color, padding: "2px 7px", borderRadius: "10px", fontSize: "10px", fontWeight: 600 }}
    >
      {cfg.label}
    </span>
  );
}

function MealsPage() {
  const [search, setSearch] = useState("");
  const [labelFilters, setLabelFilters] = useState<string[]>([]);
  const [meals, setMeals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [mealLabels, setMealLabels] = useState<string[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const emptyMeal = { name: "", description: "", instructions: "", servings: 1, labels: [] as string[], ingredients: [] as any[] };
  const [form, setForm] = useState({ ...emptyMeal });
  const [editingMealId, setEditingMealId] = useState<string | null>(null);
  const [editingMeal, setEditingMeal] = useState<any | null>(null); // raw row, for read-only enrichment info
  const [ingSearch, setIngSearch] = useState("");
  const [ingResults, setIngResults] = useState<any[]>([]);
  const [ingLoading, setIngLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const liveTotal = form.ingredients.reduce((acc: any, ing: any) => {
    const fi = ing.food_item || ing.food_item_name; // handling both new format and fetched format
    if (!fi) return acc;
    // Attempt to resolve macros
    const c = fi.calories ?? (ing.food_item?.calories || 0);
    const p = fi.protein_g ?? (ing.food_item?.protein_g || 0);
    const cb = fi.carbs_g ?? (ing.food_item?.carbs_g || 0);
    const f = fi.fat_g ?? (ing.food_item?.fat_g || 0);

    const nut = fi.nutrition_unit || ing.unit || "gram";
    const qty = parseFloat(ing.quantity) || 0;
    let scale = ["gram", "milliliter", "g", "ml"].includes(nut) ? qty / 100 : qty;
    return { calories: acc.calories + c * scale, protein_g: acc.protein_g + p * scale, carbs_g: acc.carbs_g + cb * scale, fat_g: acc.fat_g + f * scale };
  }, { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 });
  const perServing = (v: number) => Math.round((form.servings > 0 ? v / form.servings : v) * 10) / 10;

  const fetchMeals = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (labelFilters.length > 0) {
      labelFilters.forEach(lf => params.append("label", lf));
    }
    const qs = params.toString();
    apiFetch(`/api/admin/meals${qs ? "?" + qs : ""}`).then(setMeals).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { apiFetch("/api/admin/meal-labels").then(setMealLabels).catch(console.error); }, []);
  useEffect(() => { const t = setTimeout(fetchMeals, 300); return () => clearTimeout(t); }, [search, labelFilters]);

  useEffect(() => {
    if (!ingSearch.trim()) { setIngResults([]); return; }
    const t = setTimeout(() => {
      setIngLoading(true);
      apiFetch(`/api/admin/food-items?search=${encodeURIComponent(ingSearch)}`).then(setIngResults).catch(console.error).finally(() => setIngLoading(false));
    }, 350);
    return () => clearTimeout(t);
  }, [ingSearch]);

  const addIngredient = (fi: any) => {
    setForm(prev => ({ ...prev, ingredients: [...prev.ingredients, { food_item_id: fi.id, food_item: fi, quantity: ["piece", "tbsp"].includes(fi.nutrition_unit) ? 1 : 100, unit: fi.nutrition_unit || "gram" }] }));
    setIngSearch(""); setIngResults([]);
  };
  const generateViaAI = async () => {
    if (!ingSearch.trim()) return;
    setAiLoading(true);
    try { const r = await apiFetch("/api/admin/food-items/generate", { method: "POST", body: { query: ingSearch } }); addIngredient(r); }
    catch (e: any) { alert("AI generation failed: " + (e?.message || String(e))); }
    finally { setAiLoading(false); }
  };
  const removeIngredient = (idx: number) => setForm(prev => ({ ...prev, ingredients: prev.ingredients.filter((_, i) => i !== idx) }));
  const updateIngQty = (idx: number, v: string) => setForm(prev => { const u = [...prev.ingredients]; u[idx] = { ...u[idx], quantity: parseFloat(v) || 0 }; return { ...prev, ingredients: u }; });
  const updateIngUnit = (idx: number, v: string) => setForm(prev => { const u = [...prev.ingredients]; u[idx] = { ...u[idx], unit: v }; return { ...prev, ingredients: u }; });
  const toggleLabel = (l: string) => setForm(prev => ({ ...prev, labels: prev.labels.includes(l) ? prev.labels.filter(x => x !== l) : [...prev.labels, l] }));

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return alert("Meal name required");
    if (form.ingredients.length === 0) return alert("Add at least one ingredient");
    setIsSubmitting(true);
    try {
      const payload = {
        name: form.name, description: form.description || null, instructions: form.instructions || null, servings: form.servings, labels: form.labels,
        ingredients: form.ingredients.map(ing => ({ food_item_id: ing.food_item_id || ing.id, quantity: ing.quantity, unit: ing.unit }))
      };

      let createdOrUpdated;
      if (editingMealId) {
        createdOrUpdated = await apiFetch(`/api/admin/meals/${editingMealId}`, { method: "PATCH", body: payload });
      } else {
        createdOrUpdated = await apiFetch("/api/admin/meals", { method: "POST", body: payload });
      }

      // Upload image if selected
      const targetId = editingMealId || createdOrUpdated?.id;
      if (imageFile && targetId) {
        const fd = new FormData();
        fd.append("file", imageFile);
        await apiUpload(`/api/admin/meals/${targetId}/upload-image`, fd);
      }
      closeModal();
      fetchMeals();
    } catch (err: any) { alert("Failed: " + (err?.message || String(err))); }
    finally { setIsSubmitting(false); }
  };

  const openEditModal = (m: any) => {
    setEditingMealId(m.id);
    setEditingMeal(m);
    setForm({
      name: m.name,
      description: m.description || "",
      instructions: m.instructions || "",
      servings: m.servings || 1,
      labels: m.labels || [],
      ingredients: m.ingredients || []
    });
    setImagePreview(m.image_url || null);
    setImageFile(null);
    setShowAdd(true);
  };

  const closeModal = () => {
    setShowAdd(false); setEditingMealId(null); setEditingMeal(null); setForm({ ...emptyMeal }); setImageFile(null); setImagePreview(null);
  };
  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete meal "${name}"?`)) return;
    try { await apiFetch(`/api/admin/meals/${id}`, { method: "DELETE" }); fetchMeals(); }
    catch (e: any) { alert(e?.message || "Failed to delete meal"); }
  };

  const IS: CSSProperties = { width: "100%", padding: "9px 12px", borderRadius: "8px", border: `1px solid ${C.gray200}`, fontSize: "14px", outline: "none", color: C.gray900, boxSizing: "border-box" };
  const LS: CSSProperties = { display: "block", fontSize: "12px", fontWeight: 600, color: C.gray700, marginBottom: "5px" };

  return (
    <div>
      <div style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Meals</h1>
          <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>Create and manage master meals. Macros are auto-calculated from ingredients.</p>
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <div style={{ position: "relative" }}>
            <div style={{ padding: "8px 12px", borderRadius: "8px", border: `1px solid ${C.gray200}`, fontSize: "14px", color: C.gray900, background: C.white, display: "flex", gap: "6px", alignItems: "center", minWidth: "150px", flexWrap: "wrap" }}>
              {labelFilters.length === 0 && <span style={{ color: C.gray500 }}>All Labels</span>}
              {labelFilters.map(l => (
                <span key={l} onClick={() => setLabelFilters(prev => prev.filter(x => x !== l))} style={{ backgroundColor: C.blueSoft, color: C.blue, padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", zIndex: 10 }}>{l.replace(/_/g, " ")} <span>✕</span></span>
              ))}
              <select value="" onChange={e => { if (e.target.value && !labelFilters.includes(e.target.value)) setLabelFilters(p => [...p, e.target.value]); }} style={{ outline: "none", border: "none", background: "transparent", cursor: "pointer", flex: 1, minWidth: "100px", color: C.gray700 }}>
                <option value="">+ Add filter...</option>
                {mealLabels.filter(l => !labelFilters.includes(l)).map(l => <option key={l} value={l}>{l.replace(/_/g, " ")}</option>)}
              </select>
            </div>
          </div>
          <input placeholder="Search meals..." value={search} onChange={e => setSearch(e.target.value)} style={{ padding: "9px 14px", borderRadius: "8px", border: `1px solid ${C.gray200}`, fontSize: "14px", width: "210px", color: C.gray900 }} />
          <ActionBtn color={C.blue} bg={C.blueSoft} onClick={() => setShowAdd(true)}>+ New Meal</ActionBtn>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "20px" }}>
        {loading && <p style={{ color: C.gray500, gridColumn: "1/-1", textAlign: "center", padding: "40px" }}>Loading meals...</p>}
        {!loading && meals.length === 0 && <p style={{ color: C.gray500, gridColumn: "1/-1", textAlign: "center", padding: "40px" }}>No meals found.</p>}
        {!loading && meals.map(m => (
          <div key={m.id} style={{ backgroundColor: C.white, borderRadius: "12px", border: `1px solid ${C.gray200}`, overflow: "hidden", display: "flex", flexDirection: "column" }}>
            {m.image_url ? (
              <img src={m.image_url} alt={m.name} style={{ width: "100%", height: "160px", objectFit: "cover" }} />
            ) : (
              <div style={{ width: "100%", height: "160px", backgroundColor: C.gray100, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "32px", opacity: 0.3 }}>🍽️</div>
            )}
            <div style={{ padding: "16px", flex: 1, display: "flex", flexDirection: "column" }}>
              <h3 style={{ margin: "0 0 4px", fontSize: "16px", fontWeight: 700, color: C.gray900 }}>{m.name}</h3>
              <p style={{ margin: "0 0 12px", fontSize: "12px", color: C.gray500, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{m.description || "No description."}</p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "6px", marginBottom: "14px", backgroundColor: C.gray50, padding: "10px", borderRadius: "8px" }}>
                <div style={{ textAlign: "center" }}><div style={{ fontSize: "12px", fontWeight: 700, color: C.gray900 }}>{m.calories}</div><div style={{ fontSize: "10px", color: C.gray500 }}>kcal</div></div>
                <div style={{ textAlign: "center" }}><div style={{ fontSize: "12px", fontWeight: 700, color: C.blue }}>{m.protein_g}</div><div style={{ fontSize: "10px", color: C.gray500 }}>Pro (g)</div></div>
                <div style={{ textAlign: "center" }}><div style={{ fontSize: "12px", fontWeight: 700, color: C.green }}>{m.carbs_g}</div><div style={{ fontSize: "10px", color: C.gray500 }}>Carb (g)</div></div>
                <div style={{ textAlign: "center" }}><div style={{ fontSize: "12px", fontWeight: 700, color: C.red }}>{m.fat_g}</div><div style={{ fontSize: "10px", color: C.gray500 }}>Fat (g)</div></div>
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "14px" }}>
                <EnrichmentBadge meal={m} />
                {(m.labels || []).slice(0, 3).map((l: string) => <span key={l} style={{ backgroundColor: C.blueSoft, color: C.blue, padding: "2px 7px", borderRadius: "10px", fontSize: "10px", fontWeight: 600 }}>{l.replace(/_/g, " ")}</span>)}
                {(m.labels || []).length > 3 && <span style={{ backgroundColor: C.gray100, color: C.gray500, padding: "2px 7px", borderRadius: "10px", fontSize: "10px", fontWeight: 600 }}>+{(m.labels.length - 3)}</span>}
              </div>

              <div style={{ marginTop: "auto", display: "flex", gap: "8px" }}>
                <button onClick={() => openEditModal(m)} style={{ flex: 1, padding: "8px", borderRadius: "6px", border: `1px solid ${C.blue}`, backgroundColor: C.white, color: C.blue, fontWeight: 600, fontSize: "12px", cursor: "pointer" }}>Edit / View Details</button>
                <button onClick={() => handleDelete(m.id, m.name)} style={{ padding: "8px 12px", borderRadius: "6px", border: "none", backgroundColor: C.redSoft, color: C.red, fontWeight: 600, fontSize: "12px", cursor: "pointer" }}>Delete</button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showAdd && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", backgroundColor: C.modalOverlay, display: "flex", justifyContent: "center", alignItems: "flex-start", zIndex: 1000, overflowY: "auto", padding: "30px 0" }}>
          <div style={{ backgroundColor: C.white, borderRadius: "16px", width: "660px", maxWidth: "95%", padding: "32px", boxShadow: "0 20px 60px rgba(0,0,0,0.2)", marginTop: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "24px" }}>
              <div><h2 style={{ margin: 0, fontSize: "18px", fontWeight: 700 }}>{editingMealId ? "Edit Meal" : "Create New Meal"}</h2><p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>Macros are auto-calculated from your ingredients.</p></div>
              <button onClick={closeModal} style={{ background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: C.gray400 }}>✕</button>
            </div>
            <form onSubmit={handleCreateOrUpdate} style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                <div><label style={LS}>Meal Name *</label><input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={IS} placeholder="e.g. Grilled Chicken Salad" /></div>
                <div><label style={LS}>Servings</label><input type="number" min="0.5" step="0.5" value={form.servings} onChange={e => setForm({ ...form, servings: parseFloat(e.target.value) || 1 })} style={IS} /></div>
              </div>
              <div><label style={LS}>Description</label><input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} style={IS} placeholder="Short description..." /></div>
              <div><label style={LS}>Instructions</label><textarea value={form.instructions} onChange={e => setForm({ ...form, instructions: e.target.value })} style={{ ...IS, height: "70px", resize: "vertical" } as CSSProperties} placeholder="Cooking steps..." /></div>

              {/* Image Upload */}
              <div>
                <label style={LS}>Meal Image (optional)</label>
                <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
                  <label htmlFor="meal-img-upload" style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "9px 16px", borderRadius: "8px", border: `2px dashed ${C.gray200}`, cursor: "pointer", fontSize: "13px", color: C.gray500, backgroundColor: C.gray50, flexShrink: 0 }}>
                    📷 {imageFile ? imageFile.name : "Choose image…"}
                    <input id="meal-img-upload" type="file" accept="image/*" style={{ display: "none" }} onChange={e => {
                      const f = e.target.files?.[0] || null;
                      setImageFile(f);
                      setImagePreview(f ? URL.createObjectURL(f) : null);
                    }} />
                  </label>
                  {imagePreview && (
                    <div style={{ position: "relative" }}>
                      <img src={imagePreview} alt="preview" style={{ width: "72px", height: "72px", objectFit: "cover", borderRadius: "10px", border: `1px solid ${C.gray200}` }} />
                      <button type="button" onClick={() => { setImageFile(null); setImagePreview(null); }} style={{ position: "absolute", top: "-6px", right: "-6px", background: C.red, border: "none", borderRadius: "50%", width: "20px", height: "20px", color: C.white, cursor: "pointer", fontSize: "12px", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>✕</button>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label style={LS}>Labels</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "7px" }}>
                  {mealLabels.map(l => {
                    const sel = form.labels.includes(l); return (
                      <button type="button" key={l} onClick={() => toggleLabel(l)} style={{ padding: "4px 12px", borderRadius: "20px", fontSize: "12px", fontWeight: 600, cursor: "pointer", border: sel ? `2px solid ${C.blue}` : `2px solid ${C.gray200}`, backgroundColor: sel ? C.blueSoft : C.white, color: sel ? C.blue : C.gray500 }}>{l.replace(/_/g, " ")}</button>
                    );
                  })}
                </div>
              </div>

              {editingMeal && (
                <div style={{ backgroundColor: C.gray50, padding: "14px 16px", borderRadius: "12px", border: `1px solid ${C.gray200}` }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                    <label style={{ ...LS, marginBottom: 0 }}>AI Enrichment (read-only)</label>
                    <EnrichmentBadge meal={editingMeal} />
                  </div>
                  {editingMeal.enriched_at ? (
                    <>
                      <div style={{ display: "flex", gap: "16px", fontSize: "12px", color: C.gray700, marginBottom: "6px" }}>
                        <span>Sodium ~{Math.round(editingMeal.sodium_mg || 0)}mg</span>
                        <span>Fiber ~{Math.round(editingMeal.fiber_g || 0)}g</span>
                        <span>Sugar ~{Math.round(editingMeal.sugar_g || 0)}g</span>
                        <span style={{ color: C.gray500 }}>enriched {formatDate(editingMeal.enriched_at)}</span>
                      </div>
                      {editingMeal.ai_health_context && (
                        <p style={{ margin: 0, fontSize: "12px", color: C.gray500, fontStyle: "italic" }}>{editingMeal.ai_health_context}</p>
                      )}
                    </>
                  ) : (
                    <p style={{ margin: 0, fontSize: "12px", color: C.gray500 }}>
                      Not yet enriched — enrichment runs automatically in the main system during meal-plan generation.
                    </p>
                  )}
                </div>
              )}

              <div style={{ backgroundColor: C.gray50, padding: "16px", borderRadius: "12px", border: `1px solid ${C.gray200}` }}>
                <label style={LS}>Add Ingredients</label>
                <div style={{ display: "flex", gap: "8px", marginBottom: "12px", position: "relative" }}>
                  <div style={{ flex: 1, position: "relative" }}>
                    <input value={ingSearch} onChange={e => setIngSearch(e.target.value)} style={IS} placeholder="Search food database..." />
                    {(ingResults.length > 0 || (ingLoading && ingSearch)) && (
                      <div style={{ position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, backgroundColor: C.white, border: `1px solid ${C.gray200}`, borderRadius: "8px", boxShadow: "0 8px 24px rgba(0,0,0,0.12)", zIndex: 20, maxHeight: "200px", overflowY: "auto" }}>
                        {ingLoading && <div style={{ padding: "12px", color: C.gray500, fontSize: "13px" }}>Searching…</div>}
                        {ingResults.map(fi => (
                          <button type="button" key={fi.id} onClick={() => addIngredient(fi)} style={{ display: "block", width: "100%", textAlign: "left", padding: "10px 14px", border: "none", background: "none", cursor: "pointer", fontSize: "13px", color: C.gray900 }} onMouseEnter={e => (e.currentTarget.style.background = C.gray50)} onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                            <strong>{fi.name}</strong> <span style={{ color: C.gray400, fontSize: "11px" }}>— {fi.calories} kcal per {["gram", "milliliter"].includes(fi.nutrition_unit) ? "100" : "1"} {fi.nutrition_unit}</span>
                          </button>
                        ))}
                        {!ingLoading && ingResults.length === 0 && ingSearch && <div style={{ padding: "12px", color: C.gray400, fontSize: "12px" }}>Not in database. Click "✨ Ask AI" →</div>}
                      </div>
                    )}
                  </div>
                  <button type="button" onClick={generateViaAI} disabled={aiLoading || !ingSearch.trim()} style={{ padding: "9px 16px", borderRadius: "8px", border: "none", backgroundColor: aiLoading ? C.gray200 : "#7c3aed", color: C.white, fontWeight: 700, fontSize: "13px", cursor: aiLoading ? "not-allowed" : "pointer", whiteSpace: "nowrap", flexShrink: 0 }}>
                    {aiLoading ? "Generating…" : "✨ Ask AI"}
                  </button>
                </div>
                {form.ingredients.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {form.ingredients.map((ing: any, idx: number) => (
                      <div key={idx} style={{ display: "flex", alignItems: "center", gap: "8px", backgroundColor: C.white, padding: "9px 12px", borderRadius: "8px", border: `1px solid ${C.gray200}` }}>
                        <span style={{ flex: 1, fontSize: "13px", fontWeight: 600, color: C.gray900 }}>{ing.food_item?.name || ing.food_item_name}</span>
                        <input type="number" min="0.1" step="0.1" value={ing.quantity} onChange={e => updateIngQty(idx, e.target.value)} style={{ width: "75px", padding: "5px 8px", borderRadius: "6px", border: `1px solid ${C.gray200}`, fontSize: "13px", color: C.gray900 }} />
                        <select value={ing.unit} onChange={e => updateIngUnit(idx, e.target.value)} style={{ padding: "5px 8px", borderRadius: "6px", border: `1px solid ${C.gray200}`, fontSize: "13px", color: C.gray900 }}>
                          <option value="gram">g</option><option value="milliliter">ml</option><option value="piece">piece</option><option value="tbsp">tbsp</option>
                        </select>
                        <button type="button" onClick={() => removeIngredient(idx)} style={{ background: C.redSoft, border: "none", borderRadius: "6px", padding: "5px 9px", cursor: "pointer", color: C.red, fontWeight: 700 }}>✕</button>
                      </div>
                    ))}
                  </div>
                )}
                {form.ingredients.length === 0 && <p style={{ color: C.gray400, fontSize: "12px", margin: 0 }}>Search for a food item above, or ask AI to generate one automatically.</p>}
              </div>

              {form.ingredients.length > 0 && (
                <div style={{ backgroundColor: "#f0fdf4", border: "1px solid #86efac", borderRadius: "10px", padding: "14px 16px" }}>
                  <p style={{ margin: "0 0 10px 0", fontSize: "13px", fontWeight: 700, color: C.green }}>📊 Estimated Macros (per serving)</p>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "10px" }}>
                    {[{ label: "Calories", value: perServing(liveTotal.calories), unit: "kcal" }, { label: "Protein", value: perServing(liveTotal.protein_g), unit: "g" }, { label: "Carbs", value: perServing(liveTotal.carbs_g), unit: "g" }, { label: "Fat", value: perServing(liveTotal.fat_g), unit: "g" }].map(m => (
                      <div key={m.label} style={{ backgroundColor: C.white, padding: "10px", borderRadius: "8px", textAlign: "center" }}>
                        <div style={{ fontSize: "11px", color: C.gray500, marginBottom: "2px" }}>{m.label}</div>
                        <div style={{ fontSize: "18px", fontWeight: 700, color: C.green }}>{m.value}</div>
                        <div style={{ fontSize: "10px", color: C.gray400 }}>{m.unit}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", paddingTop: "4px" }}>
                <button type="button" onClick={closeModal} style={{ padding: "10px 22px", borderRadius: "8px", border: `1px solid ${C.gray200}`, background: C.white, cursor: "pointer", color: C.gray700, fontWeight: 600 }}>Cancel</button>
                <button type="submit" disabled={isSubmitting} style={{ padding: "10px 26px", borderRadius: "8px", border: "none", backgroundColor: C.green, color: C.white, fontWeight: 700, cursor: isSubmitting ? "not-allowed" : "pointer" }}>{isSubmitting ? "Saving…" : "✅ Save Meal"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Applications Page ────────────────────────────────────────────────────────
function ApplicationsPage() {
  const [filter, setFilter] = useState<"all" | "pending" | "approved" | "rejected">("pending");
  const [apps, setApps] = useState<ConsultantApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ConsultantApplication | null>(null);
  const [actioning, setActioning] = useState(false);

  const fetchApps = () => {
    setLoading(true);
    const url = filter === "all" ? "/api/admin/applications" : `/api/admin/applications?status=${filter}`;
    apiFetch(url).then(setApps).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { fetchApps(); }, [filter]);

  const openDetail = (app: ConsultantApplication) => {
    setSelected(app);
  };

  const decide = async (id: string, decision: "approve" | "reject") => {
    const note = decision === "reject" ? prompt("Reason for rejection (required):") : "Approved by admin";
    if (decision === "reject" && !note) return;
    setActioning(true);
    try {
      await apiFetch(`/api/admin/applications/${id}/review`, { method: "POST", body: { decision, note } });
      setSelected(null);
      fetchApps();
    } catch { alert("Failed to update application status"); }
    finally { setActioning(false); }
  };

  const tabs: Array<"all" | "pending" | "approved" | "rejected"> = ["all", "pending", "approved", "rejected"];
  const typeColor: Record<string, { bg: string; color: string }> = {
    clinical: { bg: "#ede9fe", color: "#7c3aed" },
    non_clinical: { bg: "#fef3c7", color: "#b45309" },
    wellness: { bg: "#d1fae5", color: "#065f46" },
  };

  const Field = ({ label, value }: { label: string; value?: string | null }) => (
    <div>
      <p style={{ margin: "0 0 3px 0", fontSize: "11px", fontWeight: 700, color: C.gray400, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</p>
      <p style={{ margin: 0, fontSize: "13px", color: value ? C.gray900 : C.gray400, fontWeight: value ? 500 : 400, fontStyle: value ? "normal" : "italic" }}>
        {value || "Not provided"}
      </p>
    </div>
  );

  const Section = ({ title, icon, children }: { title: string; icon: string; children: ReactNode }) => (
    <div style={{ backgroundColor: C.gray50, borderRadius: "12px", padding: "18px 20px", border: `1px solid ${C.gray200}` }}>
      <p style={{ margin: "0 0 14px 0", fontSize: "13px", fontWeight: 700, color: C.gray700, display: "flex", alignItems: "center", gap: "7px" }}>
        <span>{icon}</span>{title}
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
        {children}
      </div>
    </div>
  );

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Consultant Applications</h1>
        <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>
          Review and approve or reject new consultant applications.
        </p>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "6px", marginBottom: "20px" }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setFilter(t)} style={{
            padding: "7px 18px", borderRadius: "8px",
            border: `1px solid ${filter === t ? C.blue : C.gray200}`,
            backgroundColor: filter === t ? C.blue : C.white,
            color: filter === t ? C.white : C.gray700,
            fontSize: "12px", fontWeight: 600, cursor: "pointer", transition: "all 0.15s",
          }}>
            {t === "all" ? "All" : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Table */}
      <Card>
        <Table headers={["Name / Email", "Type", "Qualification", "Applied", "Status", "Action"]} loading={loading}>
          {apps.map(a => {
            const tc = typeColor[a.consultant_type] || { bg: C.gray100, color: C.gray500 };
            return (
              <Tr key={a.id}>
                <Td bold>
                  <div>{a.display_name || "—"}</div>
                  <div style={{ fontSize: "11px", color: C.gray400, marginTop: "2px", fontWeight: 400 }}>{a.email}</div>
                </Td>
                <Td>
                  <span style={{ backgroundColor: tc.bg, color: tc.color, padding: "3px 9px", borderRadius: "10px", fontSize: "11px", fontWeight: 700, textTransform: "capitalize", whiteSpace: "nowrap" }}>
                    {(a.consultant_type || "—").replace(/_/g, " ")}
                  </span>
                </Td>
                <Td>{a.highest_qualification || "—"}</Td>
                <Td>{formatDate(a.created_at)}</Td>
                <Td><Badge status={a.status} /></Td>
                <Td>
                  <ActionBtn color={C.blue} bg={C.blueSoft} onClick={() => openDetail(a)}>Review App</ActionBtn>
                </Td>
              </Tr>
            );
          })}
          {!loading && apps.length === 0 && (
            <tr><td colSpan={6} style={{ textAlign: "center", padding: "30px", color: C.gray500 }}>No applications found.</td></tr>
          )}
        </Table>
      </Card>

      {/* Detail / Review Modal */}
      {selected && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", backgroundColor: C.modalOverlay, display: "flex", justifyContent: "center", alignItems: "flex-start", zIndex: 1000, overflowY: "auto", padding: "30px 0" }}>
          <div style={{ backgroundColor: C.white, borderRadius: "16px", width: "740px", maxWidth: "95%", padding: "0", boxShadow: "0 24px 64px rgba(0,0,0,0.22)", marginTop: "10px", overflow: "hidden" }}>

            {/* Modal Header */}
            <div style={{ padding: "24px 28px 20px", borderBottom: `1px solid ${C.gray200}`, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                <div style={{ width: "48px", height: "48px", borderRadius: "50%", backgroundColor: C.blueSoft, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "20px" }}>📝</div>
                <div>
                  <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 700, color: C.gray900 }}>
                    {selected.display_name}
                  </h2>
                  <p style={{ margin: "3px 0 0", fontSize: "13px", color: C.gray500 }}>{selected.email}</p>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Badge status={selected.status} />
                <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: C.gray400, padding: "0 4px" }}>✕</button>
              </div>
            </div>

            <div style={{ padding: "24px 28px", display: "flex", flexDirection: "column", gap: "18px" }}>
              <Section title="Professional Details" icon="🎓">
                <Field label="Consultant Type" value={(selected.consultant_type || "").replace(/_/g, " ")} />
                <Field label="Specialties" value={selected.specialties} />
                <Field label="Highest Qualification" value={selected.highest_qualification} />
                <Field label="Graduation Institution" value={selected.graduation_institution} />
                <Field label="Registration Body" value={selected.registration_body} />
                <Field label="Registration Number" value={selected.registration_number} />
              </Section>

              <Section title="Identity & Bio" icon="👤">
                <div style={{ gridColumn: "1 / -1" }}>
                  <Field label="Bio" value={selected.bio} />
                </div>
                {selected.other_info && (
                  <div style={{ gridColumn: "1 / -1", marginTop: "10px" }}>
                    <Field label="Additional Info" value={selected.other_info} />
                  </div>
                )}
              </Section>

              {/* Documents */}
              <div>
                <p style={{ margin: "0 0 12px 0", fontSize: "13px", fontWeight: 700, color: C.gray700, display: "flex", alignItems: "center", gap: "7px" }}>
                  📄 Attached Documents
                </p>
                {selected.documents && selected.documents.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {selected.documents.map((doc, i) => (
                      <div key={i} style={{ border: `1px solid ${C.gray200}`, padding: "14px 16px", borderRadius: "10px", display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: C.white }}>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                          <div style={{ width: "36px", height: "36px", backgroundColor: C.blueSoft, borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", flexShrink: 0 }}>📃</div>
                          <div>
                            <p style={{ margin: "0 0 3px 0", fontWeight: 700, fontSize: "13px", color: C.gray900, textTransform: "capitalize" }}>
                              {(doc.doc_type || "document").replace(/_/g, " ")}
                            </p>
                            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                              {doc.file_path && <span style={{ fontSize: "11px", color: C.gray500 }}>📎 {doc.file_path.split("/").pop()}</span>}
                              {doc.issuer && <span style={{ fontSize: "11px", color: C.gray500 }}>🏛 {doc.issuer}</span>}
                              {doc.issue_date && <span style={{ fontSize: "11px", color: C.gray500 }}>📅 Issued: {doc.issue_date}</span>}
                            </div>
                          </div>
                        </div>
                        {doc.url ? (
                          <a href={doc.url} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: "5px", backgroundColor: C.blueSoft, color: C.blue, textDecoration: "none", fontSize: "12px", fontWeight: 700, padding: "8px 14px", borderRadius: "8px", whiteSpace: "nowrap", flexShrink: 0 }}>
                            View ↗
                          </a>
                        ) : (
                          <span style={{ color: C.red, fontSize: "12px", backgroundColor: C.redSoft, padding: "4px 10px", borderRadius: "6px", fontWeight: 600 }}>No link</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: "24px", textAlign: "center", backgroundColor: C.gray50, borderRadius: "10px", border: `1px dashed ${C.gray200}` }}>
                    <p style={{ color: C.gray500, fontSize: "13px", margin: 0 }}>No documents provided.</p>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              {selected.status === "pending" && (
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", paddingTop: "4px", borderTop: `1px solid ${C.gray200}`, marginTop: "4px" }}>
                  <button onClick={() => setSelected(null)} style={{ padding: "10px 20px", borderRadius: "8px", border: `1px solid ${C.gray200}`, background: C.white, cursor: "pointer", color: C.gray700, fontWeight: 600, fontSize: "13px" }}>
                    Close
                  </button>
                  <button onClick={() => decide(selected.id, "approve")} disabled={actioning} style={{ padding: "10px 22px", borderRadius: "8px", border: "none", backgroundColor: C.green, color: C.white, fontWeight: 700, cursor: "pointer", fontSize: "13px" }}>
                    ✓ Approve Application
                  </button>
                  <button onClick={() => decide(selected.id, "reject")} disabled={actioning} style={{ padding: "10px 22px", borderRadius: "8px", border: "none", backgroundColor: C.red, color: C.white, fontWeight: 700, cursor: "pointer", fontSize: "13px" }}>
                    ✕ Reject Application
                  </button>
                </div>
              )}
              {selected.status !== "pending" && (
                <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "4px", borderTop: `1px solid ${C.gray200}`, marginTop: "4px" }}>
                  <button onClick={() => setSelected(null)} style={{ padding: "10px 20px", borderRadius: "8px", border: `1px solid ${C.gray200}`, background: C.white, cursor: "pointer", color: C.gray700, fontWeight: 600, fontSize: "13px" }}>
                    Close
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Consultations (privacy-safe aggregates) ──────────────────────────────────
function ConsultationsPage() {
  const [data, setData] = useState<ConsultationOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/admin/consultations")
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Consultations</h1>
        <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>
          Booking-funnel overview. Aggregate request counts only — no consultation content is shown.
        </p>
      </div>

      {loading && <div style={{ padding: "40px" }}>Loading…</div>}
      {!loading && data && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px", marginBottom: "28px" }}>
            <StatCard label="Pending Requests" value={data.totals.pending} icon="⏳" accent sub="Awaiting consultant reply" />
            <StatCard label="Accepted" value={data.totals.accepted} icon="✅" sub="Chat opened" />
            <StatCard label="Declined" value={data.totals.declined} icon="🚫" sub="Rejected by consultant" />
            <StatCard label="Open Chats" value={data.open_chats} icon="💬" sub={`${data.totals.total} requests total`} />
          </div>

          <Card>
            <Table headers={["Consultant", "Status", "Pending", "Accepted", "Declined", "Open Chats", "Total"]}>
              {data.per_consultant.map(c => (
                <Tr key={c.consultant_user_id}>
                  <Td bold>{c.display_name || "Unknown consultant"}</Td>
                  <Td><Badge status={c.is_verified ? "verified" : "pending"} /></Td>
                  <Td>{c.pending}</Td>
                  <Td>{c.accepted}</Td>
                  <Td>{c.declined}</Td>
                  <Td>{c.open_chats}</Td>
                  <Td bold>{c.total}</Td>
                </Tr>
              ))}
            </Table>
            {data.per_consultant.length === 0 && (
              <p style={{ color: C.gray500, fontSize: "13px", textAlign: "center", padding: "24px" }}>No consultation requests yet.</p>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

// ── Root ─────────────────────────────────────────────────────────────────────
export default function AdminDashboard() {
  const [page, setPage] = useState("dashboard");
  const [stats, setStats] = useState<AdminStats | null>(null);

  useEffect(() => {
    // Poll stats occasionally to get badge numbers
    apiFetch("/api/admin/stats").then(setStats).catch(console.error);
  }, [page]);

  const pageMap: Record<string, ReactNode> = {
    dashboard: <DashboardPage />,
    users: <UsersPage />,
    consultants: <ConsultantsPage />,
    applications: <ApplicationsPage />,
    consultations: <ConsultationsPage />,
    food_items: <FoodItemsPage />,
    meals: <MealsPage />,
  };

  return (
    <div style={{
      display: "flex", minHeight: "100vh",
      fontFamily: "'Geist', 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
      backgroundColor: C.gray50,
    }}>
      <Sidebar
        active={page}
        onNav={setPage}
        pendingApps={stats?.pending_applications || 0}
        consultantsNeedingReview={stats?.consultants_needing_review || 0}
        pendingConsultations={stats?.consultation_requests_by_status?.pending || 0}
      />
      <main style={{ flex: 1, padding: "32px 36px", overflowY: "auto" }}>
        {pageMap[page]}
      </main>
    </div>
  );
}
