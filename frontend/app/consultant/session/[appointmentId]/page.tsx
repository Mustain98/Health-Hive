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
  SessionNoteCreate,
  AppointmentDetailsResponse,
} from "@/lib/types";
import { GoalType } from "@/lib/types";
import VideoCall from "@/components/session/VideoCall";

export default function ConsultantSessionPage() {
  const params = useParams();
  const appointmentId = params.appointmentId as string;
  const { user: currentUser } = useAuth();

  const [appointment, setAppointment] = useState<AppointmentRead | null>(null);
  const [room, setRoom] = useState<SessionRoomRead | null>(null);

  const [messages, setMessages] = useState<ChatMessageRead[]>([]);
  const [newMessage, setNewMessage] = useState("");

  const [note, setNote] = useState<SessionNoteRead | null>(null);
  const [noteText, setNoteText] = useState("");
  const [noteVisible, setNoteVisible] = useState(false);

  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [starting, setStarting] = useState(false);
  const [ending, setEnding] = useState(false);

  // Video Chat State
  const [videoCredentials, setVideoCredentials] = useState<{
    appId: string;
    channel: string;
    token: string;
    uid: number;
  } | null>(null);
  const [joiningVideo, setJoiningVideo] = useState(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [startingFollowup, setStartingFollowup] = useState(false);
  const [followupStarted, setFollowupStarted] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const canSend = room?.status === "active";
  const canEditNote = room?.status === "active";
  // Consultant can view chat/notes in ended sessions (read-only)
  const canViewSession = room?.status === "active" || room?.status === "ended";

  useEffect(() => {
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId]);

  useEffect(() => {
    if (!room || !canViewSession) return;

    loadMessagesByRoomId(room.id);
    const interval = setInterval(() => loadMessagesByRoomId(room.id), 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [room?.id, canViewSession]);

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
    setErrorMsg(null);
    setLoading(true);

    try {
      const appointments = await apiFetch<AppointmentRead[]>(
        "/api/appointments/consultant/me"
      );
      const appt = appointments.find((a) => String(a.id) === appointmentId);
      setAppointment(appt || null);

      const roomData = await apiFetch<SessionRoomRead>(
        `/api/appointments/${appointmentId}/room`
      );
      setRoom(roomData);

      // Load messages for active or ended sessions
      if (roomData.status === "active" || roomData.status === "ended") {
        await loadMessagesByRoomId(roomData.id);
      }

      // Always try to load notes – consultant can read notes even after session ends
      try {
        const noteData = await apiFetch<SessionNoteRead>(
          `/api/sessions/appointments/${appointmentId}/note`
        );
        setNote(noteData);
        setNoteText(noteData.note);
        setNoteVisible(noteData.is_visible_to_user);
      } catch {
        // ok – no note yet
      }
    } catch (error: any) {
      console.error("Failed to load session:", error);
      setErrorMsg(error?.message || "Failed to load session");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartSession() {
    if (!appointmentId) return;
    setStarting(true);
    setErrorMsg(null);
    try {
      const updated = await apiFetch<SessionRoomRead>(
        `/api/sessions/appointments/${appointmentId}/start`,
        { method: "POST" }
      );
      setRoom(updated);
    } catch (error: any) {
      console.error("Failed to start session:", error);
      setErrorMsg(error?.message || "Failed to start session");
    } finally {
      setStarting(false);
    }
  }

  async function handleEndSession() {
    if (!appointmentId) return;
    setEnding(true);
    setErrorMsg(null);
    try {
      const updated = await apiFetch<SessionRoomRead>(
        `/api/sessions/appointments/${appointmentId}/end`,
        { method: "POST" }
      );
      setRoom(updated);
    } catch (error: any) {
      console.error("Failed to end session:", error);
      setErrorMsg(error?.message || "Failed to end session");
    } finally {
      setEnding(false);
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

  async function handleSaveNote(e: FormEvent) {
    e.preventDefault();
    if (!noteText.trim() || !canEditNote) return;

    setSavingNote(true);
    setErrorMsg(null);

    try {
      const noteData: SessionNoteCreate = {
        note: noteText,
        is_visible_to_user: noteVisible,
      };

      const saved = await apiFetch<SessionNoteRead>(
        `/api/sessions/appointments/${appointmentId}/note`,
        {
          method: "PUT",
          body: noteData,
        }
      );
      setNote(saved);
    } catch (error: any) {
      console.error("Failed to save note:", error);
      setErrorMsg(error?.message || "Failed to save note");
    } finally {
      setSavingNote(false);
    }
  }

  async function handleStartFollowup() {
    setStartingFollowup(true);
    setErrorMsg(null);
    try {
      await apiFetch(`/api/followup/from-session/${appointmentId}`, {
        method: "POST"
      });
      setFollowupStarted(true);
      // Let the banner show, then auto-hide or just leave it
      setTimeout(() => setFollowupStarted(false), 5000);

      // Refresh appointment to get the followup_room_id 
      await loadSession();
    } catch (error: any) {
      setErrorMsg(error?.message || "Failed to start follow-up");
    } finally {
      setStartingFollowup(false);
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

  // Patient display name and email
  const patientName = appointment?.user_name || `Client #${String(appointment?.user_id ?? "").substring(0, 8)}`;
  const patientEmail = appointment?.user_email;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Session</h1>
          <p className="mt-2 text-sm text-gray-600">
            Appointment #{appointmentId.substring(0, 8)}
            {appointment ? ` • ${patientName}` : ""}
          </p>
          {patientEmail && (
            <p className="text-xs text-gray-500 mt-0.5">✉ {patientEmail}</p>
          )}

          {room && (
            <p className="mt-1 text-xs text-gray-500">
              Status: <span className="font-medium capitalize">{room.status.replace("_", " ")}</span>
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {room?.status === "not_started" && (
            <>
              <button
                onClick={handleStartSession}
                disabled={starting}
                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-60"
              >
                {starting ? "Starting..." : "Start Session"}
              </button>
              <button
                onClick={handleEndSession}
                disabled={ending}
                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-60"
                title="Mark as ended without starting (e.g. no-show)"
              >
                {ending ? "Ending..." : "End Without Starting"}
              </button>
            </>
          )}

          {room?.status === "active" && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleStartFollowup}
                disabled={startingFollowup || !!appointment?.followup_room_id}
                className="px-4 py-2 text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 disabled:opacity-50"
              >
                {startingFollowup ? "Starting..." : !!appointment?.followup_room_id ? "Follow-up Active ✓" : "Start Follow-up"}
              </button>
              <button
                onClick={handleEndSession}
                disabled={ending}
                className="px-4 py-2 text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-60"
              >
                {ending ? "Ending..." : "End Session"}
              </button>
            </div>
          )}

          <Link
            href="/consultant/appointments"
            className="text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            ← Back to Appointments
          </Link>
        </div>
      </div>

      {followupStarted && (
        <div className="rounded-md bg-green-50 border border-green-200 p-3 flex items-center gap-3">
          <span className="text-green-600 font-bold text-lg">✓</span>
          <div>
            <p className="text-sm font-medium text-green-800">Follow-up started!</p>
            <p className="text-xs text-green-700">
              You can manage it from{" "}
              <a href="/consultant/followup" className="underline font-medium">Follow-up</a>.
            </p>
          </div>
        </div>
      )}

      {/* Video Call Area */}
      {videoCredentials ? (
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
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between mb-6">
          <div>
            <h3 className="text-sm font-medium text-blue-900">Video Session Available</h3>
            <p className="text-xs text-blue-700 mt-1">
              You can start/join the video call now.
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
      )}

      {errorMsg && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
          {errorMsg}
        </div>
      )}

      {!canSend && (
        <div className="rounded-md bg-yellow-50 p-3 text-sm text-yellow-800">
          {room?.status === "not_started"
            ? "Session not started yet. Click \"Start Session\" to enable chat and notes."
            : room?.status === "ended"
              ? "Session ended. Chat and notes are read-only."
              : null}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chat */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
            </div>

            <div className="h-[50vh] overflow-y-auto p-4 space-y-3">
              {!canViewSession ? (
                <p className="text-sm text-gray-500">Chat is available once the session starts.</p>
              ) : messages.length === 0 ? (
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
                  canSend ? "Type a message..." : "Chat is disabled (session not active)"
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

          {/* Client Health Data Panel */}
          <ClientHealthPanel appointmentId={appointmentId} active={room?.status === "active"} appointment={appointment} />

          {/* Consultant's own suggested goals & targets for this appointment */}
          <ConsultantSuggestedPanel appointmentId={appointmentId} />
        </div>

        {/* Notes */}
        <div className="bg-white rounded-lg shadow h-fit">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">Session Note</h2>
            <p className="text-xs text-gray-500 mt-1">
              {canEditNote
                ? "Notes can be hidden or visible to user."
                : room?.status === "ended"
                  ? "Session ended – notes are read-only."
                  : "Notes available once session starts."}
            </p>
          </div>

          <form onSubmit={handleSaveNote} className="p-4 space-y-3">
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              className="w-full min-h-[220px] rounded-md border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50"
              placeholder={
                canEditNote
                  ? "Write session note..."
                  : canViewSession
                    ? "(Read-only)"
                    : "Notes are read-only (session not active)"
              }
              disabled={!canEditNote}
            />
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={noteVisible}
                onChange={(e) => setNoteVisible(e.target.checked)}
                disabled={!canEditNote}
              />
              Visible to user
            </label>
            <button
              type="submit"
              className="w-full px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
              disabled={savingNote || !canEditNote}
            >
              {savingNote ? "Saving..." : note ? "Update Note" : "Save Note"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function ClientHealthPanel({
  appointmentId,
  active,
  appointment
}: {
  appointmentId: string,
  active: boolean,
  appointment: AppointmentRead | null
}) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Suggestion Flow
  const [showSuggestGoal, setShowSuggestGoal] = useState(false);
  const [showSuggestTarget, setShowSuggestTarget] = useState(false);

  const [goalForm, setGoalForm] = useState({
    goal_type: "lose" as GoalType,
    target_delta_kg: "",
    duration_days: "",
  });

  const [targetForm, setTargetForm] = useState({
    calories_kcal: "",
    protein_g: "",
    carbs_g: "",
    fat_g: "",
  });

  const [suggesting, setSuggesting] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);

  async function handleSuggestGoal(e: React.FormEvent) {
    e.preventDefault();
    setSuggesting(true);
    setSuggestError(null);
    try {
      const userId = data?.client?.id || appointment?.user_id || "";
      const payload: any = { goal_type: goalForm.goal_type };
      if (goalForm.target_delta_kg) payload.target_delta_kg = Number(goalForm.target_delta_kg);
      if (goalForm.duration_days) payload.duration_days = Number(goalForm.duration_days);

      await apiFetch(`/api/consultant/users/${userId}/goal?appointment_id=${appointmentId}`, {
        method: "POST",
        body: payload,
      });
      setShowSuggestGoal(false);
      loadHealth();
    } catch (err: any) {
      setSuggestError(err.message || "Failed to suggest goal");
    } finally {
      setSuggesting(false);
    }
  }

  async function handleSuggestTarget(e: React.FormEvent) {
    e.preventDefault();
    setSuggesting(true);
    setSuggestError(null);
    try {
      const userId = data?.client?.id || appointment?.user_id || "";
      const payload: any = {};
      if (targetForm.calories_kcal) payload.calories_kcal = Number(targetForm.calories_kcal);
      if (targetForm.protein_g) payload.protein_g = Number(targetForm.protein_g);
      if (targetForm.carbs_g) payload.carbs_g = Number(targetForm.carbs_g);
      if (targetForm.fat_g) payload.fat_g = Number(targetForm.fat_g);

      await apiFetch(`/api/consultant/users/${userId}/nutrition-target?appointment_id=${appointmentId}`, {
        method: "POST",
        body: payload,
      });
      setShowSuggestTarget(false);
      loadHealth();
    } catch (err: any) {
      setSuggestError(err.message || "Failed to suggest target");
    } finally {
      setSuggesting(false);
    }
  }

  async function loadHealth() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<any>(`/api/sessions/appointments/${appointmentId}/client-health`);
      setData(res);
    } catch (err: any) {
      if (err.status === 403) {
        setError("Permission to view health data not granted. Ask the client to grant access.");
      } else {
        setError(err.message || "Failed to load health data.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (!active) {
    return (
      <div className="bg-white rounded-lg shadow p-4 opacity-70">
        <h3 className="font-semibold text-gray-900 border-b pb-2 mb-2">Client Health Data</h3>
        <p className="text-sm text-gray-500">Available when session is active.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex justify-between items-center border-b pb-2 mb-4">
        <h3 className="font-semibold text-gray-900">Client Health Data</h3>
        <button
          onClick={loadHealth}
          className="text-xs text-blue-600 hover:underline"
          disabled={loading}
        >
          {data ? "Refresh" : "Load Data"}
        </button>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading...</p>}

      {error && (
        <div className="bg-yellow-50 p-3 rounded text-sm text-yellow-800 mb-2 border border-yellow-200">
          {error}
        </div>
      )}

      {suggestError && (
        <div className="bg-red-50 p-3 rounded text-sm text-red-800 mb-2">
          {suggestError}
        </div>
      )}

      {data && (
        <div className="space-y-4 text-sm">
          {data.client && (
            <div>
              <p className="font-medium text-gray-700">Client Info</p>
              <p className="text-gray-600">Name: {data.client.full_name}</p>
              <p className="text-gray-600">Email: {data.client.email}</p>
            </div>
          )}

          <div>
            <p className="font-medium text-gray-700">Health Metrics</p>
            {data.user_data ? (
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600">
                <p>Age: <span className="text-gray-900">{data.user_data.age ?? "-"}</span></p>
                <p>Gender: <span className="text-gray-900 capitalize">{data.user_data.gender ?? "-"}</span></p>
                <p>Height: <span className="text-gray-900">{data.user_data.height_cm ? `${data.user_data.height_cm}cm` : "-"}</span></p>
                <p>Weight: <span className="text-gray-900">{data.user_data.weight_kg ? `${data.user_data.weight_kg}kg` : "-"}</span></p>
                <p className="col-span-2">Activity: <span className="text-gray-900 capitalize">{data.user_data.activity_level?.replace("_", " ") ?? "-"}</span></p>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Not provided yet.</p>
            )}
          </div>

          {data.goal ? (
            <div>
              <p className="font-medium text-gray-700">Goal {data.goal.active ? "(Active)" : "(Suggested)"}</p>
              <p className="text-gray-600 capitalize">Type: {data.goal.goal_type}</p>
              {data.goal.target_delta_kg && <p className="text-gray-600">Target Delta: {data.goal.target_delta_kg}kg</p>}
            </div>
          ) : (
            <p className="text-gray-500">No goal set.</p>
          )}

          {!showSuggestGoal ? (
            <button
              onClick={() => setShowSuggestGoal(true)}
              className="text-xs text-blue-600 font-medium"
            >
              + Suggest New Goal
            </button>
          ) : (
            <form onSubmit={handleSuggestGoal} className="bg-gray-50 p-3 rounded border space-y-2">
              <p className="font-medium text-xs text-gray-700">Suggest Goal (Linked to this session)</p>
              <div>
                <label className="block text-xs text-gray-500">Goal Type</label>
                <select
                  value={goalForm.goal_type}
                  onChange={e => setGoalForm({ ...goalForm, goal_type: e.target.value as GoalType })}
                  className="w-full text-xs p-1 border rounded"
                >
                  <option value="lose">Lose Weight</option>
                  <option value="gain">Gain Weight</option>
                  <option value="maintain">Maintain</option>
                </select>
              </div>
              {goalForm.goal_type !== "maintain" && (
                <div>
                  <label className="block text-xs text-gray-500">Target Change (kg)</label>
                  <input
                    type="number" step="0.1"
                    value={goalForm.target_delta_kg}
                    onChange={e => setGoalForm({ ...goalForm, target_delta_kg: e.target.value })}
                    className="w-full text-xs p-1 border rounded"
                  />
                </div>
              )}
              <div>
                <label className="block text-xs text-gray-500">Duration (Days)</label>
                <input
                  type="number"
                  value={goalForm.duration_days}
                  onChange={e => setGoalForm({ ...goalForm, duration_days: e.target.value })}
                  className="w-full text-xs p-1 border rounded"
                />
              </div>
              <div className="flex justify-end gap-2 mt-2">
                <button type="button" onClick={() => setShowSuggestGoal(false)} className="text-xs text-gray-500">Cancel</button>
                <button type="submit" disabled={suggesting} className="bg-blue-600 text-white text-xs px-2 py-1 rounded">
                  {suggesting ? "Suggesting..." : "Suggest Goal"}
                </button>
              </div>
            </form>
          )}

          {data.nutrition_target ? (
            <div>
              <p className="font-medium text-gray-700">Nutrition Targets {data.nutrition_target.active ? "(Active)" : "(Suggested)"}</p>
              <div className="grid grid-cols-2 gap-2 mt-1">
                <div className="bg-gray-50 p-2 rounded">
                  <span className="block text-xs text-gray-500">Calories</span>
                  {data.nutrition_target.calories_kcal}
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <span className="block text-xs text-gray-500">Protein</span>
                  {data.nutrition_target.protein_g}g
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <span className="block text-xs text-gray-500">Carbs</span>
                  {data.nutrition_target.carbs_g}g
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <span className="block text-xs text-gray-500">Fat</span>
                  {data.nutrition_target.fat_g}g
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">No nutrition targets.</p>
          )}

          {!showSuggestTarget ? (
            <button
              onClick={() => setShowSuggestTarget(true)}
              className="text-xs text-blue-600 font-medium"
            >
              + Suggest New Targets
            </button>
          ) : (
            <form onSubmit={handleSuggestTarget} className="bg-gray-50 p-3 rounded border space-y-2">
              <p className="font-medium text-xs text-gray-700">Suggest Targets (Linked to this session)</p>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-500">Calories</label>
                  <input
                    type="number" min="800" max="10000"
                    value={targetForm.calories_kcal}
                    onChange={e => setTargetForm({ ...targetForm, calories_kcal: e.target.value })}
                    className="w-full text-xs p-1 border rounded"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Protein (g)</label>
                  <input
                    type="number"
                    value={targetForm.protein_g}
                    onChange={e => setTargetForm({ ...targetForm, protein_g: e.target.value })}
                    className="w-full text-xs p-1 border rounded"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Carbs (g)</label>
                  <input
                    type="number"
                    value={targetForm.carbs_g}
                    onChange={e => setTargetForm({ ...targetForm, carbs_g: e.target.value })}
                    className="w-full text-xs p-1 border rounded"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Fat (g)</label>
                  <input
                    type="number"
                    value={targetForm.fat_g}
                    onChange={e => setTargetForm({ ...targetForm, fat_g: e.target.value })}
                    className="w-full text-xs p-1 border rounded"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-2">
                <button type="button" onClick={() => setShowSuggestTarget(false)} className="text-xs text-gray-500">Cancel</button>
                <button type="submit" disabled={suggesting} className="bg-blue-600 text-white text-xs px-2 py-1 rounded">
                  {suggesting ? "..." : "Suggest Targets"}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Shows the consultant a read-only view of the goal and nutrition target
 * they have already suggested for this appointment.
 * Fetches /api/appointments/:id/details (now works for consultants via backend fix).
 */
function ConsultantSuggestedPanel({ appointmentId }: { appointmentId: string }) {
  const [details, setDetails] = useState<AppointmentDetailsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDetails();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId]);

  async function loadDetails() {
    setLoading(true);
    try {
      const res = await apiFetch<AppointmentDetailsResponse>(`/api/appointments/${appointmentId}/details`);
      setDetails(res);
    } catch {
      // ignore – consultant may not have suggested anything yet
    } finally {
      setLoading(false);
    }
  }

  const hasData = details?.goal || details?.nutrition_target;

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex justify-between items-center border-b pb-2 mb-3">
        <h3 className="font-semibold text-gray-900">Your Suggestions for This Session</h3>
        <button
          onClick={loadDetails}
          disabled={loading}
          className="text-xs text-blue-600 hover:underline disabled:opacity-50"
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {loading && !hasData && (
        <p className="text-sm text-gray-400">Loading suggestions...</p>
      )}

      {!hasData && !loading && (
        <p className="text-sm text-gray-500">
          No goal or nutrition target suggested yet for this appointment.
        </p>
      )}

      <div className="space-y-3">
        {details?.goal && (
          <div className="bg-blue-50 border border-blue-100 rounded p-3">
            <p className="text-sm font-medium text-blue-900 mb-1">
              🎯 Goal{" "}
              <span className="text-xs font-normal text-blue-700">
                {details.goal.active ? "(Active)" : "(Suggested — not yet adopted by client)"}
              </span>
            </p>
            <p className="text-xs text-blue-800 capitalize">Type: {details.goal.goal_type}</p>
            {details.goal.target_delta_kg != null && (
              <p className="text-xs text-blue-800">Target Change: {details.goal.target_delta_kg} kg</p>
            )}
            {details.goal.duration_days != null && (
              <p className="text-xs text-blue-800">Duration: {details.goal.duration_days} days</p>
            )}
          </div>
        )}

        {details?.nutrition_target && (
          <div className="bg-green-50 border border-green-100 rounded p-3">
            <p className="text-sm font-medium text-green-900 mb-1">
              🥗 Nutrition Target{" "}
              <span className="text-xs font-normal text-green-700">
                {details.nutrition_target.active ? "(Active)" : "(Suggested — not yet adopted by client)"}
              </span>
            </p>
            <div className="grid grid-cols-2 gap-2 mt-1">
              <div className="bg-white rounded p-1.5">
                <span className="block text-[10px] text-gray-500">Calories</span>
                <span className="text-xs font-medium text-gray-800">{details.nutrition_target.calories_kcal} kcal</span>
              </div>
              <div className="bg-white rounded p-1.5">
                <span className="block text-[10px] text-gray-500">Protein</span>
                <span className="text-xs font-medium text-gray-800">{details.nutrition_target.protein_g}g</span>
              </div>
              <div className="bg-white rounded p-1.5">
                <span className="block text-[10px] text-gray-500">Carbs</span>
                <span className="text-xs font-medium text-gray-800">{details.nutrition_target.carbs_g}g</span>
              </div>
              <div className="bg-white rounded p-1.5">
                <span className="block text-[10px] text-gray-500">Fat</span>
                <span className="text-xs font-medium text-gray-800">{details.nutrition_target.fat_g}g</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
