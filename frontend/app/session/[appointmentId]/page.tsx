"use client";

import { useEffect, useState, useRef, FormEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/components/guards/AuthGuard";
import type {
  SessionRoomRead,
  ChatMessageRead,
  ChatMessageCreate,
  AppointmentRead,
  SessionNoteRead,
  AppointmentDetailsResponse,
} from "@/lib/types";
import VideoCall from "@/components/session/VideoCall";

export default function UserSessionPage() {
  const params = useParams();
  const appointmentId = params.appointmentId as string;
  const { user: currentUser } = useAuth();

  const [appointment, setAppointment] = useState<AppointmentRead | null>(null);
  const [room, setRoom] = useState<SessionRoomRead | null>(null);

  const [messages, setMessages] = useState<ChatMessageRead[]>([]);
  const [newMessage, setNewMessage] = useState("");

  const [note, setNote] = useState<SessionNoteRead | null>(null);

  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const [blockedNotStarted, setBlockedNotStarted] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Video Chat State
  const [videoCredentials, setVideoCredentials] = useState<{
    appId: string;
    channel: string;
    token: string;
    uid: number;
  } | null>(null);
  const [joiningVideo, setJoiningVideo] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const canSend = room?.status === "active";
  // Users can view chat history and notes when the session is ended (read-only)
  const canViewHistory = room?.status === "active" || room?.status === "ended";

  useEffect(() => {
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId]);

  useEffect(() => {
    if (!room) return;
    if (!blockedNotStarted) {
      loadMessagesByRoomId(room.id);
      // For ended sessions, no need to poll — load once
      if (room.status === "active") {
        const interval = setInterval(() => loadMessagesByRoomId(room.id), 3000);
        return () => clearInterval(interval);
      }
    }
  }, [room?.id, room?.status, blockedNotStarted]);

  // Disabled auto-scroll to prevent page jumping
  // useEffect(() => {
  //   // Only auto-scroll if user is near the bottom (within 100px)
  //   const chatContainer = messagesEndRef.current?.parentElement;
  //   if (chatContainer) {
  //     const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 100;
  //     if (isNearBottom) {
  //       messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  //     }
  //   }
  // }, [messages]);

  async function loadMessagesByRoomId(roomId: string) {
    try {
      const msgs = await apiFetch<ChatMessageRead[]>(
        `/api/sessions/rooms/${roomId}/messages?limit=200`
      );
      setMessages(msgs);
    } catch (error) {
      console.error("Failed to load messages:", error);
    }
  }

  async function loadSession() {
    setLoading(true);
    setErrorMsg(null);
    setBlockedNotStarted(false);

    try {
      const appointments = await apiFetch<AppointmentRead[]>("/api/appointments/me");
      const appt = appointments.find((a) => String(a.id) === appointmentId);
      setAppointment(appt || null);

      // This may 403 if not started (backend rule)
      const roomData = await apiFetch<SessionRoomRead>(
        `/api/appointments/${appointmentId}/room`
      );
      setRoom(roomData);

      // messages
      await loadMessagesByRoomId(roomData.id);

      // note (visible only)
      try {
        const noteData = await apiFetch<SessionNoteRead>(
          `/api/sessions/appointments/${appointmentId}/note`
        );
        setNote(noteData);
      } catch {
        // ok
      }
    } catch (error: any) {
      console.error("Failed to load session:", error);

      const msg = error?.message || "Failed to load session";
      setErrorMsg(msg);

      // if backend says not started, show waiting UI
      if (String(msg).toLowerCase().includes("not started")) {
        setBlockedNotStarted(true);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!room || !newMessage.trim() || !canSend) return;

    setSending(true);
    setErrorMsg(null);

    try {
      const msgData: ChatMessageCreate = { message: newMessage };

      await apiFetch(`/api/sessions/rooms/${room.id}/messages`, {
        method: "POST",
        body: msgData,
      });

      setNewMessage("");
      await loadMessagesByRoomId(room.id);
    } catch (error: any) {
      console.error("Failed to send message:", error);
      setErrorMsg(error?.message || "Failed to send message");
    } finally {
      setSending(false);
    }
  }

  async function handleJoinVideo() {
    if (!room) return;
    setJoiningVideo(true);
    setErrorMsg(null);
    try {
      const res = await apiFetch<{ appId: string; channel: string; token: string; uid: number }>(
        `/api/video/appointments/${appointmentId}/join`,
        { method: "POST" }
      );
      setVideoCredentials(res);
    } catch (error: any) {
      console.error("Failed to join video:", error);
      setErrorMsg(error?.message || "Failed to join video session");
    } finally {
      setJoiningVideo(false);
    }
  }

  if (loading) return <div className="text-gray-600">Loading session...</div>;

  if (!currentUser) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-gray-600">You must be logged in.</p>
        <Link href="/login" className="text-blue-600 hover:text-blue-500">
          Go to Login →
        </Link>
      </div>
    );
  }

  if (blockedNotStarted) {
    return (
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Session</h1>
            <p className="mt-2 text-sm text-gray-600">
              Appointment #{appointmentId}
              {appointment ? ` • Consultant #${appointment.consultant_user_id}` : ""}
            </p>
          </div>
          <Link
            href="/appointments"
            className="text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            ← Back to Appointments
          </Link>
        </div>

        <div className="bg-white rounded-lg shadow p-8">
          <h2 className="text-xl font-semibold text-gray-900">
            Session hasn’t started yet
          </h2>
          <p className="text-sm text-gray-600 mt-2">
            Please wait for the consultant to start the session.
          </p>
          {errorMsg && (
            <p className="text-xs text-gray-500 mt-2">
              ({errorMsg})
            </p>
          )}
          <button
            onClick={loadSession}
            className="mt-4 px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Session</h1>
          <p className="mt-2 text-sm text-gray-600">
            Appointment #{appointmentId}
            {appointment ? ` • Consultant #${appointment.consultant_user_id}` : ""}
          </p>
          {room && (
            <p className="mt-1 text-xs text-gray-500">
              Status: <span className="font-medium">{room.status}</span>
            </p>
          )}
        </div>
        <Link
          href="/appointments"
          className="text-sm font-medium text-blue-600 hover:text-blue-500"
        >
          ← Back to Appointments
        </Link>
      </div>

      {/* Video Call Area */}
      {
        videoCredentials ? (
          <div className="mb-6 w-full aspect-video max-h-[600px]">
            <VideoCall
              appId={videoCredentials.appId}
              channel={videoCredentials.channel}
              token={videoCredentials.token}
              uid={videoCredentials.uid}
              onLeave={() => {
                setVideoCredentials(null);
              }}
            />
          </div>
        ) : room?.status === "active" && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-blue-900">Video Session Available</h3>
              <p className="text-xs text-blue-700 mt-1">
                The consultant is online. You can join the video call now.
              </p>
            </div>
            <button
              onClick={handleJoinVideo}
              disabled={joiningVideo}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {joiningVideo ? "Joining..." : "Join Video Call"}
            </button>
          </div>
        )
      }

      {errorMsg && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
          {errorMsg}
        </div>
      )}

      {room?.status === "ended" && (
        <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-800">
          This session has ended. Chat history and notes are shown in read-only mode.
        </div>
      )}

      {
        !canSend && room?.status !== "ended" && (
          <div className="rounded-md bg-yellow-50 p-3 text-sm text-yellow-800">
            Session is not active. You can view history, but chat is disabled.
          </div>
        )
      }

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chat */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
            </div>

            <div className="h-[60vh] overflow-y-auto p-4 space-y-3">
              {messages.length === 0 ? (
                <p className="text-sm text-gray-500">No messages yet.</p>
              ) : (
                messages.map((m) => {
                  const mine = m.sender_user_id === currentUser.id;
                  return (
                    <div
                      key={m.id}
                      className={`flex ${mine ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${mine
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-900"
                          }`}
                      >
                        <div className="opacity-80 text-[11px] mb-1">
                          {new Date(m.sent_at).toLocaleString()}
                        </div>
                        {m.message}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSend} className="p-4 border-t flex gap-2">
              <input
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder={
                  canSend ? "Type a message..." : "Chat is disabled"
                }
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
                disabled={!room || sending || !canSend}
              />
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
                disabled={!room || sending || !canSend}
              >
                {sending ? "Sending..." : "Send"}
              </button>
            </form>
          </div>

          <PermissionGrantPanel appointmentId={appointmentId} active={room?.status === 'active'} />
          <SuggestedGoalTargetPanel appointmentId={appointmentId} />
        </div>

        {/* Note (read-only for user) */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">Session Note</h2>
          </div>
          <div className="p-4">
            {note ? (
              <p className="text-sm text-gray-700 whitespace-pre-wrap">
                {note.note}
              </p>
            ) : (
              <p className="text-sm text-gray-500">No visible note yet.</p>
            )}
          </div>
        </div>
      </div>
    </div >
  );
}


function PermissionGrantPanel({ appointmentId, active }: { appointmentId: string, active: boolean }) {
  const [granted, setGranted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    checkStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId, active]);

  async function checkStatus() {
    if (!active) return;
    try {
      const appointments = await apiFetch<AppointmentRead[]>("/api/appointments/me");
      const appt = appointments.find((a) => String(a.id) === appointmentId);
      if (appt) {
        setGranted(appt.consultant_access ?? true);
      }
    } catch {
      // ignore
    }
  }

  async function togglePermission() {
    setLoading(true);
    setMsg("");
    try {
      const newAccess = !granted;
      await apiFetch(`/api/appointments/${appointmentId}/permission?grant=${newAccess}`, {
        method: "PUT"
      });
      setGranted(newAccess);
      setMsg(newAccess ? "Access granted." : "Access revoked.");
    } catch (err: any) {
      setMsg("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!active) return null;

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">Consultant Data Access</h3>
          <p className="text-sm text-gray-500">
            {granted
              ? "Consultant has access to view your health data."
              : "Grant access to allow consultant to view your data."}
          </p>
        </div>
        <button
          onClick={togglePermission}
          disabled={loading}
          className={`px-4 py-2 text-sm font-medium rounded-md text-white transition-colors ${granted
            ? "bg-red-600 hover:bg-red-700"
            : "bg-blue-600 hover:bg-blue-700"
            } disabled:opacity-50`}
        >
          {loading ? "Updating..." : granted ? "Revoke Access" : "Grant Access"}
        </button>
      </div>
      {msg && <p className="text-xs text-blue-600 mt-2">{msg}</p>}
    </div>
  );
}

function SuggestedGoalTargetPanel({ appointmentId }: { appointmentId: string }) {
  const [details, setDetails] = useState<AppointmentDetailsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [adopting, setAdopting] = useState<string | null>(null);

  useEffect(() => {
    loadDetails();
  }, [appointmentId]);

  async function loadDetails() {
    setLoading(true);
    try {
      const res = await apiFetch<AppointmentDetailsResponse>(`/api/appointments/${appointmentId}/details`);
      setDetails(res);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function adoptGoal() {
    if (!details?.goal) return;
    setAdopting("goal");
    try {
      await apiFetch(`/api/goal/${details.goal.id}/activate`, { method: "PUT" });
      await loadDetails();
    } catch (error: any) {
      alert(`Failed to activate goal: ${error.message}`);
    } finally {
      setAdopting(null);
    }
  }

  async function adoptTarget() {
    if (!details?.nutrition_target) return;
    setAdopting("target");
    try {
      await apiFetch(`/api/nutrition-target/${details.nutrition_target.id}/activate`, { method: "PUT" });
      await loadDetails();
    } catch (error: any) {
      alert(`Failed to activate target: ${error.message}`);
    } finally {
      setAdopting(null);
    }
  }

  async function adoptMealPlan() {
    if (!details?.meal_plan_setting) return;
    setAdopting("mealplan");
    try {
      await apiFetch(`/api/meal-plan-settings/${details.meal_plan_setting.id}/activate`, { method: "PATCH" });
      await loadDetails();
    } catch (error: any) {
      alert(`Failed to activate meal plan: ${error.message}`);
    } finally {
      setAdopting(null);
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mt-6">
        <h3 className="font-semibold text-gray-900 mb-2">Suggested Goals & Targets</h3>
        <p className="text-sm text-gray-500">Checking suggestions...</p>
      </div>
    );
  }

  if (!details?.goal && !details?.nutrition_target && !details?.meal_plan_setting) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mt-6">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold text-gray-900">Suggested Goals & Targets</h3>
          <button onClick={loadDetails} className="text-xs text-blue-600 hover:underline">Refresh</button>
        </div>
        <p className="text-sm text-gray-500">No suggestions from the consultant yet.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 mt-6">
      <div className="flex justify-between items-center border-b pb-2 mb-4">
        <h3 className="font-semibold text-gray-900">Suggested Goals & Targets</h3>
        <button onClick={loadDetails} className="text-xs text-blue-600 hover:underline">Refresh</button>
      </div>

      <div className="space-y-4">
        {details.goal && (
          <div className="bg-blue-50 border border-blue-100 rounded p-3">
            <p className="text-sm font-medium text-blue-900 mb-1">
              Goal {details.goal.active ? "(Active)" : "(Suggested)"}
            </p>
            <p className="text-xs text-blue-800 capitalize">Type: {details.goal.goal_type}</p>
            {details.goal.target_weight && <p className="text-xs text-blue-800">Target Weight: {details.goal.target_weight}kg</p>}

            {!details.goal.active && (
              <button
                onClick={adoptGoal}
                disabled={adopting === "goal"}
                className="mt-2 w-full text-xs font-medium bg-blue-600 text-white rounded py-1 px-2 hover:bg-blue-700 disabled:opacity-50"
              >
                {adopting === "goal" ? "Adopting..." : "Adopt This Goal"}
              </button>
            )}
          </div>
        )}

        {details.nutrition_target && (
          <div className="bg-green-50 border border-green-100 rounded p-3">
            <p className="text-sm font-medium text-green-900 mb-1">
              Nutrition Target {details.nutrition_target.active ? "(Active)" : "(Suggested)"}
            </p>
            <p className="text-xs text-green-800">Cals: {details.nutrition_target.calories_kcal} | P: {details.nutrition_target.protein_g}g | C: {details.nutrition_target.carbs_g}g | F: {details.nutrition_target.fat_g}g</p>

            {!details.nutrition_target.active && (
              <button
                onClick={adoptTarget}
                disabled={adopting === "target"}
                className="mt-2 w-full text-xs font-medium bg-green-600 text-white rounded py-1 px-2 hover:bg-green-700 disabled:opacity-50"
              >
                {adopting === "target" ? "Adopting..." : "Adopt This Target"}
              </button>
            )}
          </div>
        )}

        {details.meal_plan_setting && (
          <div className="bg-purple-50 border border-purple-100 rounded p-3">
            <p className="text-sm font-medium text-purple-900 mb-1">
              Meal Plan {details.meal_plan_setting.active ? "(Active)" : "(Suggested)"}
            </p>
            <p className="text-xs text-purple-800 mb-2">
              {details.meal_plan_setting.name} ({details.meal_plan_setting.timed_meals_per_day} meals)
            </p>
            <div className="grid grid-cols-1 gap-2 text-xs text-purple-900 mb-3">
              {details.meal_plan_setting.timed_meals?.map((tm: any, i: number) => (
                <div key={i} className="bg-purple-100/50 rounded p-2 border border-purple-200/50">
                  <p className="font-semibold border-b border-purple-200/50 pb-1 mb-1">{tm.name} <span className="text-[10px] font-normal text-purple-700 capitalize">({tm.meal_time?.replace("_", " ")})</span></p>
                  <div className="flex justify-between text-[11px]">
                    <span>Calories: <span className="font-medium">{tm.calories_pct}%</span></span>
                    <span>Protein: <span className="font-medium">{tm.protein_g_pct}%</span></span>
                    <span>Carbs: <span className="font-medium">{tm.carbs_g_pct}%</span></span>
                    <span>Fat: <span className="font-medium">{tm.fat_g_pct}%</span></span>
                  </div>
                </div>
              ))}
            </div>

            {!details.meal_plan_setting.active && (
              <button
                onClick={adoptMealPlan}
                disabled={adopting === "mealplan"}
                className="mt-2 w-full text-xs font-medium bg-purple-600 text-white rounded py-1 px-2 hover:bg-purple-700 disabled:opacity-50"
              >
                {adopting === "mealplan" ? "Adopting..." : "Adopt This Plan"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

