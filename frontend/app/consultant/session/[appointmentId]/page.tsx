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
} from "@/lib/types";
import VideoCall from "@/components/session/VideoCall";

export default function ConsultantSessionPage() {
  const params = useParams();
  const appointmentId = Number(params.appointmentId);
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

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const canSend = room?.status === "active";
  const canEditNote = room?.status === "active";

  useEffect(() => {
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId]);

  useEffect(() => {
    if (!room) return;

    loadMessagesByRoomId(room.id);
    const interval = setInterval(() => loadMessagesByRoomId(room.id), 3000);
    return () => clearInterval(interval);
  }, [room?.id]);

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

  async function loadMessagesByRoomId(roomId: number) {
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
      const appt = appointments.find((a) => a.id === appointmentId);
      setAppointment(appt || null);

      const roomData = await apiFetch<SessionRoomRead>(
        `/api/appointments/${appointmentId}/room`
      );
      setRoom(roomData);

      await loadMessagesByRoomId(roomData.id);

      try {
        const noteData = await apiFetch<SessionNoteRead>(
          `/api/sessions/appointments/${appointmentId}/note`
        );
        setNote(noteData);
        setNoteText(noteData.note);
        setNoteVisible(noteData.is_visible_to_user);
      } catch {
        // ok
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

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Session</h1>
          <p className="mt-2 text-sm text-gray-600">
            Appointment #{appointmentId}
            {appointment ? ` • Client #${appointment.user_id}` : ""}
          </p>

          {room && (
            <p className="mt-1 text-xs text-gray-500">
              Status: <span className="font-medium">{room.status}</span>
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {room?.status === "not_started" && (
            <button
              onClick={handleStartSession}
              disabled={starting}
              className="px-4 py-2 text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-60"
            >
              {starting ? "Starting..." : "Start Session"}
            </button>
          )}

          {room?.status === "active" && (
            <button
              onClick={handleEndSession}
              disabled={ending}
              className="px-4 py-2 text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-60"
            >
              {ending ? "Ending..." : "End Session"}
            </button>
          )}

          <Link
            href="/consultant/appointments"
            className="text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            ← Back to Appointments
          </Link>
        </div>
      </div>

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
            ? "Session not started yet. Click “Start Session” to enable chat and notes."
            : "Session ended. Chat and notes are read-only."}
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
          <ClientHealthPanel appointmentId={appointmentId} active={room?.status === 'active'} />
        </div>

        {/* Notes */}
        <div className="bg-white rounded-lg shadow h-fit">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold text-gray-900">Session Note</h2>
            <p className="text-xs text-gray-500 mt-1">
              Notes can be hidden or visible to user. Locked after session ends.
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

function ClientHealthPanel({ appointmentId, active }: { appointmentId: number, active: boolean }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadHealth() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<any>(`/api/sessions/appointments/${appointmentId}/client-health`);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load health data. Permission required.");
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
        <div className="bg-red-50 p-3 rounded text-sm text-red-800 mb-2">
          {error} <br />
          <span className="text-xs opacity-75">Ask the client to grant permission in their session view.</span>
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

          {data.user_data && (
            <div>
              <p className="font-medium text-gray-700">Health Metrics</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600">
                <p>Age: <span className="text-gray-900">{data.user_data.age ?? '-'}</span></p>
                <p>Gender: <span className="text-gray-900 capitalize">{data.user_data.gender ?? '-'}</span></p>
                <p>Height: <span className="text-gray-900">{data.user_data.height_cm ? `${data.user_data.height_cm}cm` : '-'}</span></p>
                <p>Weight: <span className="text-gray-900">{data.user_data.weight_kg ? `${data.user_data.weight_kg}kg` : '-'}</span></p>
                <p className="col-span-2">Activity: <span className="text-gray-900 capitalize">{data.user_data.activity_level?.replace('_', ' ') ?? '-'}</span></p>
              </div>
            </div>
          )}

          {data.goal ? (
            <div>
              <p className="font-medium text-gray-700">Goal</p>
              <p className="text-gray-600 capitalize">Type: {data.goal.goal_type}</p>
              {data.goal.target_delta_kg && <p className="text-gray-600">Target Delta: {data.goal.target_delta_kg}kg</p>}
            </div>
          ) : (
            <p className="text-gray-500">No goal set.</p>
          )}

          {data.nutrition_target ? (
            <div>
              <p className="font-medium text-gray-700">Nutrition Targets</p>
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
        </div>
      )}
    </div>
  );
}
