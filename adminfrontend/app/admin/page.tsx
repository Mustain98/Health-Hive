"use client";

import { useState, CSSProperties, ReactNode } from "react";

// ── Types ────────────────────────────────────────────────────────────────────
interface AdminStats {
  total_users: number;
  total_consultants: number;
  pending_verifications: number;
  total_appointments: number;
  reported_content: number;
  active_today: number;
}

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  status: "active" | "banned";
  joined: string;
  goal: string;
}

interface Consultant {
  id: number;
  name: string;
  email: string;
  specialty: string;
  status: "pending" | "verified" | "rejected";
  submitted: string;
  cert: string;
}

interface Report {
  id: number;
  type: string;
  reporter: string;
  against: string;
  reason: string;
  date: string;
  status: "open" | "resolved";
}

interface AuditLog {
  id: number;
  admin: string;
  action: string;
  target: string;
  time: string;
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
} as const;

// ── Mock Data ────────────────────────────────────────────────────────────────
const MOCK_STATS: AdminStats = {
  total_users: 1284,
  total_consultants: 47,
  pending_verifications: 6,
  total_appointments: 392,
  reported_content: 3,
  active_today: 218,
};

const MOCK_USERS: User[] = [
  { id: 1, name: "Ayesha Rahman", email: "ayesha@email.com", role: "user", status: "active", joined: "2026-01-12", goal: "Weight Loss" },
  { id: 2, name: "Tariq Hossain", email: "tariq@email.com", role: "user", status: "active", joined: "2026-02-03", goal: "Muscle Gain" },
  { id: 3, name: "Nadia Islam", email: "nadia@email.com", role: "user", status: "banned", joined: "2025-11-20", goal: "Maintenance" },
  { id: 4, name: "Rafiq Ahmed", email: "rafiq@email.com", role: "user", status: "active", joined: "2026-03-01", goal: "Weight Loss" },
  { id: 5, name: "Sumaiya Khan", email: "sumaiya@email.com", role: "user", status: "active", joined: "2026-02-18", goal: "Muscle Gain" },
];

const MOCK_CONSULTANTS: Consultant[] = [
  { id: 1, name: "Dr. Farhan Kabir", email: "farhan@health.com", specialty: "Dietitian", status: "pending", submitted: "2026-03-05", cert: "MSc Nutrition, DU" },
  { id: 2, name: "Dr. Mitu Akter", email: "mitu@health.com", specialty: "Nutritionist", status: "verified", submitted: "2026-02-10", cert: "BSc Food & Nutrition, BUET" },
  { id: 3, name: "Shafiq Uddin", email: "shafiq@fitness.com", specialty: "Fitness Trainer", status: "pending", submitted: "2026-03-06", cert: "ACSM Certified Trainer" },
  { id: 4, name: "Dr. Rina Begum", email: "rina@diet.com", specialty: "Dietitian", status: "rejected", submitted: "2026-01-28", cert: "Certificate unclear" },
  { id: 5, name: "Karim Hasan", email: "karim@health.com", specialty: "Nutritionist", status: "verified", submitted: "2026-01-15", cert: "MSc Clinical Nutrition" },
  { id: 6, name: "Priya Sharma", email: "priya@wellness.com", specialty: "Wellness Coach", status: "pending", submitted: "2026-03-07", cert: "IIN Health Coach" },
];

const MOCK_REPORTS: Report[] = [
  { id: 1, type: "Meal Plan", reporter: "Tariq Hossain", against: "Unknown User", reason: "Harmful diet advice", date: "2026-03-06", status: "open" },
  { id: 2, type: "Message", reporter: "Ayesha Rahman", against: "Karim Hasan", reason: "Inappropriate content", date: "2026-03-05", status: "open" },
  { id: 3, type: "Profile", reporter: "Sumaiya Khan", against: "Nadia Islam", reason: "Spam / fake profile", date: "2026-03-04", status: "resolved" },
];

const MOCK_AUDIT: AuditLog[] = [
  { id: 1, admin: "Admin", action: "Approved consultant", target: "Dr. Mitu Akter", time: "2026-03-05 14:32" },
  { id: 2, admin: "Admin", action: "Banned user", target: "Nadia Islam", time: "2026-03-04 09:15" },
  { id: 3, admin: "Admin", action: "Rejected consultant", target: "Dr. Rina Begum", time: "2026-03-03 11:00" },
  { id: 4, admin: "Moderator", action: "Removed meal plan", target: "Reported content #1", time: "2026-03-02 16:45" },
];

const NAV: NavItem[] = [
  { id: "users", label: "Users", icon: "👥" },
  { id: "consultants", label: "Consultants", icon: "🏥" },
  { id: "content", label: "Content Reports", icon: "🚩" },
  { id: "audit", label: "Audit Log", icon: "📋" },
];

// ── Utility Components ───────────────────────────────────────────────────────
type BadgeStatus = "active" | "banned" | "verified" | "pending" | "rejected" | "open" | "resolved" | "flagged";

function Badge({ status }: { status: BadgeStatus | string }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    active:   { bg: C.greenSoft, color: C.green, label: "Active" },
    banned:   { bg: C.redSoft,   color: C.red,   label: "Banned" },
    verified: { bg: C.greenSoft, color: C.green, label: "Verified" },
    pending:  { bg: C.amberSoft, color: C.amber, label: "Pending" },
    rejected: { bg: C.redSoft,   color: C.red,   label: "Rejected" },
    open:     { bg: C.amberSoft, color: C.amber, label: "Open" },
    resolved: { bg: C.greenSoft, color: C.green, label: "Resolved" },
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

function Table({ headers, children }: { headers: string[]; children: ReactNode }) {
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
        <tbody>{children}</tbody>
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

// ── Sidebar ──────────────────────────────────────────────────────────────────
function Sidebar({ active, onNav, pendingVerif, reports }: {
  active: string;
  onNav: (id: string) => void;
  pendingVerif: number;
  reports: number;
}) {
  return (
    <aside style={{
      width: "220px", minHeight: "100vh", flexShrink: 0,
      backgroundColor: C.white,
      borderRight: `1px solid ${C.gray200}`,
      display: "flex", flexDirection: "column",
      position: "sticky", top: 0,
    }}>
      {/* Nav */}
      <nav style={{ padding: "70px 10px 12px", flex: 1 }}>
        {NAV.map(item => {
          const isActive = active === item.id;
          const badgeCount =
            item.id === "consultants" ? pendingVerif :
            item.id === "content" ? reports : 0;
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

      {/* Admin info */}
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
function DashboardPage({ stats }: { stats: AdminStats }) {
  const quickActions = [
    { icon: "🚩", bg: C.redSoft,   label: "Moderate Reported Content",  desc: `${stats.reported_content} reports need attention` },
    { icon: "👥", bg: C.blueSoft,  label: "Manage Users",               desc: "View, search and manage all users" },
    { icon: "📋", bg: C.gray100,   label: "View Audit Log",             desc: "Track all admin actions" },
  ];

  return (
    <div>
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Dashboard</h1>
        <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>
          Welcome back — here&apos;s what&apos;s happening on HealthHive today.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px", marginBottom: "28px" }}>
        <StatCard label="Total Users"                   value={stats.total_users}            icon="👥" sub="Registered accounts" />
        <StatCard label="Consultants"                   value={stats.total_consultants}       icon="🏥" sub="Across all specialties" />
        <StatCard label="Review Pending Verifications"  value={stats.pending_verifications}  icon="⏳" accent sub="Awaiting certificate review" />
        <StatCard label="Total Appointments"            value={stats.total_appointments}     icon="📅" sub="All-time sessions" />
        <StatCard label="Reported Content"              value={stats.reported_content}       icon="🚩" accent sub="Needs moderation" />
        <StatCard label="Active Today"                  value={stats.active_today}           icon="🟢" sub="Users online today" />
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

      <SectionTitle>Recent Activity</SectionTitle>
      <Card>
        <Table headers={["Admin", "Action", "Target", "Time"]}>
          {MOCK_AUDIT.map(a => (
            <Tr key={a.id}>
              <Td bold>{a.admin}</Td>
              <Td>{a.action}</Td>
              <Td>{a.target}</Td>
              <Td>{a.time}</Td>
            </Tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function UsersPage() {
  const [search, setSearch] = useState("");
  const [users, setUsers] = useState<User[]>(MOCK_USERS);

  const filtered = users.filter(u =>
    u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase())
  );

  const toggleBan = (id: number) => {
    setUsers(prev => prev.map(u =>
      u.id === id ? { ...u, status: u.status === "banned" ? "active" : "banned" } : u
    ));
  };

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
        <Table headers={["Name", "Email", "Goal", "Joined", "Status", "Actions"]}>
          {filtered.map(u => (
            <Tr key={u.id}>
              <Td bold>{u.name}</Td>
              <Td>{u.email}</Td>
              <Td>{u.goal}</Td>
              <Td>{u.joined}</Td>
              <Td><Badge status={u.status} /></Td>
              <Td>
                <ActionBtn
                  color={u.status === "banned" ? C.green : C.red}
                  bg={u.status === "banned" ? C.greenSoft : C.redSoft}
                  onClick={() => toggleBan(u.id)}
                >{u.status === "banned" ? "Unban" : "Ban"}</ActionBtn>
                <ActionBtn color={C.blue} bg={C.blueSoft} onClick={() => {}}>View</ActionBtn>
              </Td>
            </Tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function ConsultantsPage() {
  const [filter, setFilter] = useState<"all" | Consultant["status"]>("all");
  const [consultants, setConsultants] = useState<Consultant[]>(MOCK_CONSULTANTS);

  const filtered = consultants.filter(c => filter === "all" || c.status === filter);

  const updateStatus = (id: number, newStatus: Consultant["status"]) => {
    setConsultants(prev => prev.map(c => c.id === id ? { ...c, status: newStatus } : c));
  };

  const tabs: Array<"all" | Consultant["status"]> = ["all", "pending", "verified", "rejected"];

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Consultant Verification</h1>
        <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>Review certificates and manage consultant access.</p>
      </div>

      <div style={{ display: "flex", gap: "6px", marginBottom: "20px" }}>
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            style={{
              padding: "7px 16px", borderRadius: "8px",
              border: `1px solid ${filter === t ? C.blue : C.gray200}`,
              backgroundColor: filter === t ? C.blue : C.white,
              color: filter === t ? C.white : C.gray700,
              fontSize: "12px", fontWeight: 600, cursor: "pointer",
              textTransform: "capitalize", transition: "all 0.15s",
            }}
          >{t.charAt(0).toUpperCase() + t.slice(1)}</button>
        ))}
      </div>

      <Card>
        <Table headers={["Name", "Email", "Specialty", "Certificate", "Submitted", "Status", "Actions"]}>
          {filtered.map(c => (
            <Tr key={c.id}>
              <Td bold>{c.name}</Td>
              <Td>{c.email}</Td>
              <Td>{c.specialty}</Td>
              <Td>
                <span style={{
                  backgroundColor: C.blueSoft, color: C.blue,
                  fontSize: "11px", padding: "2px 8px", borderRadius: "4px",
                  cursor: "pointer", fontWeight: 500,
                }}>📄 View Doc</span>
              </Td>
              <Td>{c.submitted}</Td>
              <Td><Badge status={c.status} /></Td>
              <Td>
                {c.status === "pending" && (
                  <>
                    <ActionBtn color={C.green} bg={C.greenSoft} onClick={() => updateStatus(c.id, "verified")}>Approve</ActionBtn>
                    <ActionBtn color={C.red}   bg={C.redSoft}   onClick={() => updateStatus(c.id, "rejected")}>Reject</ActionBtn>
                  </>
                )}
                {c.status === "verified" && (
                  <ActionBtn color={C.red} bg={C.redSoft} onClick={() => updateStatus(c.id, "rejected")}>Revoke</ActionBtn>
                )}
                {c.status === "rejected" && (
                  <ActionBtn color={C.green} bg={C.greenSoft} onClick={() => updateStatus(c.id, "verified")}>Re-approve</ActionBtn>
                )}
              </Td>
            </Tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function ContentPage() {
  const [reports, setReports] = useState<Report[]>(MOCK_REPORTS);

  const resolve = (id: number) =>
    setReports(prev => prev.map(r => r.id === id ? { ...r, status: "resolved" as const } : r));
  const remove = (id: number) =>
    setReports(prev => prev.filter(r => r.id !== id));

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Content Moderation</h1>
        <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>Review reported meal plans, messages, and profiles.</p>
      </div>
      <Card>
        <Table headers={["Type", "Reported By", "Against", "Reason", "Date", "Status", "Actions"]}>
          {reports.map(r => (
            <Tr key={r.id}>
              <Td>
                <span style={{
                  backgroundColor: C.gray100, color: C.gray700,
                  fontSize: "11px", padding: "2px 8px", borderRadius: "4px", fontWeight: 500,
                }}>{r.type}</span>
              </Td>
              <Td bold>{r.reporter}</Td>
              <Td>{r.against}</Td>
              <Td>{r.reason}</Td>
              <Td>{r.date}</Td>
              <Td><Badge status={r.status} /></Td>
              <Td>
                {r.status === "open" ? (
                  <>
                    <ActionBtn color={C.green} bg={C.greenSoft} onClick={() => resolve(r.id)}>Resolve</ActionBtn>
                    <ActionBtn color={C.red}   bg={C.redSoft}   onClick={() => remove(r.id)}>Remove</ActionBtn>
                  </>
                ) : (
                  <span style={{ fontSize: "12px", color: C.gray400 }}>No action needed</span>
                )}
              </Td>
            </Tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}



function AuditPage() {
  const logs: AuditLog[] = [
    ...MOCK_AUDIT,
    { id: 5, admin: "Moderator", action: "Resolved report",        target: "Report #3",    time: "2026-03-01 10:20" },
    { id: 6, admin: "Admin",     action: "Added meal to library",  target: "Vegetable Dal", time: "2026-02-28 13:55" },
    { id: 7, admin: "Admin",     action: "Approved consultant",    target: "Karim Hasan",  time: "2026-01-15 09:30" },
  ];

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: 0, fontSize: "22px", fontWeight: 700, color: C.gray900 }}>Audit Log</h1>
        <p style={{ margin: "4px 0 0", fontSize: "13px", color: C.gray500 }}>
          Track all admin and moderator actions across the platform.
        </p>
      </div>
      <Card>
        <Table headers={["Admin / Moderator", "Action Taken", "Target", "Timestamp"]}>
          {logs.map(a => (
            <Tr key={a.id}>
              <Td>
                <span style={{
                  backgroundColor: a.admin === "Admin" ? C.blueSoft : C.amberSoft,
                  color: a.admin === "Admin" ? C.blue : C.amber,
                  fontSize: "11px", padding: "2px 8px", borderRadius: "4px", fontWeight: 600,
                }}>{a.admin}</span>
              </Td>
              <Td bold>{a.action}</Td>
              <Td>{a.target}</Td>
              <Td>{a.time}</Td>
            </Tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}

// ── Root ─────────────────────────────────────────────────────────────────────
export default function AdminDashboard() {
  const [page, setPage] = useState("dashboard");
  const stats = MOCK_STATS;
  const pendingVerif = MOCK_CONSULTANTS.filter(c => c.status === "pending").length;
  const openReports  = MOCK_REPORTS.filter(r => r.status === "open").length;

  const pageMap: Record<string, ReactNode> = {
    dashboard:   <DashboardPage stats={stats} />,
    users:       <UsersPage />,
    consultants: <ConsultantsPage />,
    content:     <ContentPage />,
    audit:       <AuditPage />,
  };

  return (
    <div style={{
      display: "flex", minHeight: "100vh",
      fontFamily: "'Geist', 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
      backgroundColor: C.gray50,
    }}>
      <Sidebar active={page} onNav={setPage} pendingVerif={pendingVerif} reports={openReports} />
      <main style={{ flex: 1, padding: "32px 36px", overflowY: "auto" }}>
        {pageMap[page]}
      </main>
    </div>
  );
}