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
    target_weight: "",
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
      if (goalForm.target_weight) payload.target_weight = Number(goalForm.target_weight);
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
      // Also fetch the user's active Meal Plan Setting
      let activeSetting = null;
      try {
        const settingRes = await apiFetch<any>(`/api/consultant/users/${res.client?.id || appointment?.user_id}/meal-plan-setting`);
        activeSetting = settingRes;
      } catch (e) {
        // Ignore 404
      }
      setData({ ...res, active_meal_plan_setting: activeSetting });
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
              {data.goal.target_weight && <p className="text-gray-600">Target Weight: {data.goal.target_weight}kg</p>}
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
                  <label className="block text-xs text-gray-500">Target Weight (kg)</label>
                  <input
                    type="number" step="0.1"
                    value={goalForm.target_weight}
                    onChange={e => setGoalForm({ ...goalForm, target_weight: e.target.value })}
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

          {/* MEAL PLAN SETTING */}
          {data.active_meal_plan_setting ? (
            <div className="mt-4 border-t pt-4">
              <p className="font-medium text-gray-700">Active Meal Setting</p>
              <p className="text-gray-600 mb-1">{data.active_meal_plan_setting.name} ({data.active_meal_plan_setting.timed_meals_per_day} meals)</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {data.active_meal_plan_setting.timed_meals?.slice(0, 4).map((tm: any, i: number) => (
                  <div key={i} className="bg-gray-50 rounded p-1.5 border border-gray-100">
                    <p className="font-medium text-gray-700 border-b pb-0.5 mb-0.5">{tm.name}</p>
                    <p className="text-gray-500">Kcal: {tm.calories_pct}%</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-4 border-t pt-2">
              <p className="text-gray-500">No active meal plan setting.</p>
            </div>
          )}

          <MealPlanSettingForm
            appointmentId={appointmentId}
            userId={data?.client?.id || appointment?.user_id || ""}
            onSuccess={loadHealth}
          />
        </div>
      )}
    </div>
  );
}

function MealPlanSettingForm({ appointmentId, userId, onSuccess }: { appointmentId: string, userId: string, onSuccess: () => void }) {
  const [show, setShow] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestedName, setSuggestedName] = useState("Consultant Suggested Plan");
  const [timedMeals, setTimedMeals] = useState<any[]>([
    { name: "Breakfast", meal_time: "breakfast", calories_pct: 35, protein_g_pct: 35, carbs_g_pct: 35, fat_g_pct: 35 },
    { name: "Lunch", meal_time: "lunch", calories_pct: 40, protein_g_pct: 40, carbs_g_pct: 40, fat_g_pct: 40 },
    { name: "Dinner", meal_time: "dinner", calories_pct: 25, protein_g_pct: 25, carbs_g_pct: 25, fat_g_pct: 25 },
  ]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSuggesting(true);
    setError(null);

    const totalCalories = timedMeals.reduce((acc, tm) => acc + tm.calories_pct, 0);
    const totalProtein = timedMeals.reduce((acc, tm) => acc + tm.protein_g_pct, 0);
    const totalCarbs = timedMeals.reduce((acc, tm) => acc + tm.carbs_g_pct, 0);
    const totalFat = timedMeals.reduce((acc, tm) => acc + tm.fat_g_pct, 0);

    if (totalCalories !== 100 || totalProtein !== 100 || totalCarbs !== 100 || totalFat !== 100) {
      setError("Error: All percentages must add up to exactly 100%.");
      setSuggesting(false);
      return;
    }

    try {
      await apiFetch(`/api/consultant/users/${userId}/meal-plan-setting?appointment_id=${appointmentId}`, {
        method: "POST",
        body: {
          name: suggestedName,
          timed_meals_per_day: timedMeals.length,
          timed_meals: timedMeals
        }
      });
      setShow(false);
      onSuccess();
    } catch (err: any) {
      setError(err.message || "Failed to suggest meal setting");
    } finally {
      setSuggesting(false);
    }
  }

  if (!show) {
    return (
      <button
        onClick={() => setShow(true)}
        className="text-xs text-blue-600 font-medium mt-2"
      >
        + Suggest Meal Plan Setting
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="bg-gray-50 p-3 rounded border mt-2">
      <div className="flex justify-between items-center mb-2">
        <p className="font-medium text-xs text-gray-700">Suggest Meal Setting</p>
        <button
          type="button"
          onClick={() => {
            if (timedMeals.length < 8) {
              setTimedMeals([...timedMeals, { name: `Meal ${timedMeals.length + 1}`, meal_time: "snack", calories_pct: 0, protein_g_pct: 0, carbs_g_pct: 0, fat_g_pct: 0 }]);
            }
          }}
          className="text-[10px] bg-blue-100 text-blue-700 px-2 py-1 rounded font-medium"
        >
          + Add Meal
        </button>
      </div>

      {error && <p className="text-[10px] text-red-600 mb-2">{error}</p>}

      <div className="mb-2">
        <label className="block text-[10px] text-gray-500 mb-1">Plan Name</label>
        <input
          type="text" value={suggestedName} onChange={(e) => setSuggestedName(e.target.value)}
          className="w-full text-xs p-1 border rounded" required
        />
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {timedMeals.map((tm, index) => (
          <div key={index} className="p-2 border border-gray-200 rounded bg-white relative">
            {timedMeals.length > 1 && (
              <button
                type="button"
                onClick={() => setTimedMeals(timedMeals.filter((_, i) => i !== index))}
                className="absolute top-1 right-1 text-gray-400 hover:text-red-500 text-[10px] w-4 h-4 rounded-full bg-gray-100 flex items-center justify-center font-bold"
              >
                ✕
              </button>
            )}
            <div className="flex gap-2 mb-2 pr-4">
              <div className="flex-1">
                <input
                  type="text" value={tm.name} placeholder="Name"
                  onChange={e => { const a = [...timedMeals]; a[index].name = e.target.value; setTimedMeals(a); }}
                  className="w-full text-[10px] p-1 border rounded" required
                />
              </div>
              <div className="flex-1">
                <select
                  value={tm.meal_time}
                  onChange={e => { const a = [...timedMeals]; a[index].meal_time = e.target.value; setTimedMeals(a); }}
                  className="w-full text-[10px] p-1 border rounded"
                >
                  <option value="breakfast">Breakfast</option>
                  <option value="lunch">Lunch</option>
                  <option value="dinner">Dinner</option>
                  <option value="snack">Snack</option>
                  <option value="pre_workout">Pre Workout</option>
                  <option value="post_workout">Post Workout</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-1 mb-2">
              <div><span className="block text-[8px] text-gray-500 text-center">%Kcal</span><input type="number" min="0" max="100" value={tm.calories_pct} onChange={e => { const a = [...timedMeals]; a[index].calories_pct = parseInt(e.target.value) || 0; setTimedMeals(a); }} className="w-full text-center text-[10px] border rounded" required /></div>
              <div><span className="block text-[8px] text-gray-500 text-center">%Prot</span><input type="number" min="0" max="100" value={tm.protein_g_pct} onChange={e => { const a = [...timedMeals]; a[index].protein_g_pct = parseInt(e.target.value) || 0; setTimedMeals(a); }} className="w-full text-center text-[10px] border rounded" required /></div>
              <div><span className="block text-[8px] text-gray-500 text-center">%Carb</span><input type="number" min="0" max="100" value={tm.carbs_g_pct} onChange={e => { const a = [...timedMeals]; a[index].carbs_g_pct = parseInt(e.target.value) || 0; setTimedMeals(a); }} className="w-full text-center text-[10px] border rounded" required /></div>
              <div><span className="block text-[8px] text-gray-500 text-center">%Fat</span><input type="number" min="0" max="100" value={tm.fat_g_pct} onChange={e => { const a = [...timedMeals]; a[index].fat_g_pct = parseInt(e.target.value) || 0; setTimedMeals(a); }} className="w-full text-center text-[10px] border rounded" required /></div>
            </div>
            <div>
              <span className="block text-[8px] text-gray-500 mb-1">Labels</span>
              <div className="flex flex-wrap gap-1">
                {["breakfast", "lunch", "dinner", "snack", "main_meal", "side_meal", "drink", "dessert", "halal", "vegetarian", "vegan", "high_protein", "low_carb", "gym_friendly", "other"].map((label) => {
                  const selected = (tm.meal_labels || []).includes(label);
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => {
                        const a = [...timedMeals];
                        const current = a[index].meal_labels || [];
                        a[index].meal_labels = selected
                          ? current.filter((l: string) => l !== label)
                          : [...current, label];
                        setTimedMeals(a);
                      }}
                      className={`text-[9px] px-1.5 py-0.5 rounded-full border transition-colors ${selected
                          ? "bg-indigo-600 text-white border-indigo-600"
                          : "bg-white text-gray-600 border-gray-300 hover:border-indigo-400"
                        }`}
                    >
                      {label.replace(/_/g, " ")}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center text-[10px] font-medium pt-2 border-t mt-2 text-gray-500">
        <span>Totals:</span>
        <span>
          <span className={timedMeals.reduce((a, b) => a + b.calories_pct, 0) !== 100 ? "text-red-500 mx-1" : "text-green-600 mx-1"}>{timedMeals.reduce((a, b) => a + b.calories_pct, 0)}%Kc</span>
          <span className={timedMeals.reduce((a, b) => a + b.protein_g_pct, 0) !== 100 ? "text-red-500 mx-1" : "text-green-600 mx-1"}>{timedMeals.reduce((a, b) => a + b.protein_g_pct, 0)}%P</span>
          <span className={timedMeals.reduce((a, b) => a + b.carbs_g_pct, 0) !== 100 ? "text-red-500 mx-1" : "text-green-600 mx-1"}>{timedMeals.reduce((a, b) => a + b.carbs_g_pct, 0)}%C</span>
          <span className={timedMeals.reduce((a, b) => a + b.fat_g_pct, 0) !== 100 ? "text-red-500 mx-1" : "text-green-600 mx-1"}>{timedMeals.reduce((a, b) => a + b.fat_g_pct, 0)}%F</span>
        </span>
      </div>

      <div className="flex justify-end gap-2 mt-3">
        <button type="button" onClick={() => setShow(false)} className="text-xs text-gray-500">Cancel</button>
        <button type="submit" disabled={suggesting} className="bg-blue-600 text-white text-xs px-2 py-1 rounded">
          {suggesting ? "..." : "Suggest Setting"}
        </button>
      </div>
    </form>
  )
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

  const hasData = details?.goal || details?.nutrition_target || details?.meal_plan_setting;

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
            {details.goal.target_weight != null && (
              <p className="text-xs text-blue-800">Target Weight: {details.goal.target_weight} kg</p>
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

        {details?.meal_plan_setting && (
          <div className="bg-purple-50 border border-purple-100 rounded p-3">
            <p className="text-sm font-medium text-purple-900 mb-1">
              🍽️ Meal Plan Setting{" "}
              <span className="text-xs font-normal text-purple-700">
                {details.meal_plan_setting.active ? "(Active)" : "(Suggested — not yet adopted by client)"}
              </span>
            </p>
            <p className="text-xs text-purple-800 mb-2">{details.meal_plan_setting.name} ({details.meal_plan_setting.timed_meals_per_day} meals)</p>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
              {details.meal_plan_setting.timed_meals?.map((tm: any, idx: number) => (
                <div key={idx} className="bg-white rounded p-1.5 shadow-sm">
                  <span className="block text-[10px] font-semibold text-gray-700 capitalize border-b pb-0.5 mb-1">{tm.name}</span>
                  <div className="text-[10px] text-gray-600 space-y-0.5">
                    <div className="flex justify-between"><span>Kcal:</span> <span className="font-medium text-gray-800">{tm.calories_pct}%</span></div>
                    <div className="flex justify-between"><span>Protein:</span> <span className="font-medium text-gray-800">{tm.protein_g_pct}%</span></div>
                    <div className="flex justify-between"><span>Carbs:</span> <span className="font-medium text-gray-800">{tm.carbs_g_pct}%</span></div>
                    <div className="flex justify-between"><span>Fat:</span> <span className="font-medium text-gray-800">{tm.fat_g_pct}%</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
