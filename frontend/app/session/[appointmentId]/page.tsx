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
} from "@/lib/types";
import VideoCall from "@/components/session/VideoCall";

export default function UserSessionPage() {
  const params = useParams();
  const appointmentId = Number(params.appointmentId);
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

  useEffect(() => {
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId]);

  useEffect(() => {
    if (!room) return;
    if (!blockedNotStarted) {
      loadMessagesByRoomId(room.id);
      const interval = setInterval(() => loadMessagesByRoomId(room.id), 3000);
      return () => clearInterval(interval);
    }
  }, [room?.id, blockedNotStarted]);

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
    setLoading(true);
    setErrorMsg(null);
    setBlockedNotStarted(false);

    try {
      const appointments = await apiFetch<AppointmentRead[]>("/api/appointments/me");
      const appt = appointments.find((a) => a.id === appointmentId);
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

      {
        errorMsg && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
            {errorMsg}
          </div>
        )
      }

      {
        !canSend && (
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

function PermissionGrantPanel({ appointmentId, active }: { appointmentId: number, active: boolean }) {
  const [granted, setGranted] = useState(false);
  const [scope, setScope] = useState<"read" | "read_write">("read");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  async function togglePermission() {
    setLoading(true);
    setMsg("");
    try {
      if (!granted) {
        await apiFetch(`/api/sessions/appointments/${appointmentId}/permissions`, {
          method: "PUT",
          body: {
            scope: scope,
            resources: ["user_data", "user_goals", "nutrition_targets"]
          }
        });
        setGranted(true);
        setMsg("Access granted.");
      } else {
        await apiFetch(`/api/sessions/appointments/${appointmentId}/permissions`, {
          method: "PUT",
          body: {
            scope: "read",
            resources: []
          }
        });
        setGranted(false);
        setMsg("Access revoked.");
      }
    } catch (err: any) {
      setMsg("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  // Allow updating scope even if already granted
  async function updateScope(newScope: "read" | "read_write") {
    setScope(newScope);
    if (granted) {
      setLoading(true);
      try {
        await apiFetch(`/api/sessions/appointments/${appointmentId}/permissions`, {
          method: "PUT",
          body: {
            scope: newScope,
            resources: ["user_data", "user_goals", "nutrition_targets"]
          }
        });
        setMsg("Scope updated.");
      } catch (err: any) {
        setMsg("Error updating scope: " + err.message);
      } finally {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    checkStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId, active]);

  async function checkStatus() {
    if (!active) return;
    try {
      const perms = await apiFetch<any[]>(`/api/sessions/appointments/${appointmentId}/permissions`);
      const p = perms.find(p => p.status === 'active' && p.resources.length > 0);
      if (p) {
        setGranted(true);
        setScope(p.scope);
      } else {
        setGranted(false);
      }
    } catch {
      // ignore
    }
  }

  if (!active) return null;

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">Consultant Data Access</h3>
          <p className="text-sm text-gray-500">
            {granted
              ? "Consultant has access to your health data."
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

      <div className="flex gap-4 items-center pl-1">
        <label className="flex items-center space-x-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="radio"
            name="scope"
            checked={scope === 'read'}
            onChange={() => updateScope('read')}
            className="text-blue-600 focus:ring-blue-500"
          />
          <span>View Only</span>
        </label>
        <label className="flex items-center space-x-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="radio"
            name="scope"
            checked={scope === 'read_write'}
            onChange={() => updateScope('read_write')}
            className="text-blue-600 focus:ring-blue-500"
          />
          <span>Allow Updates (User Goals)</span>
        </label>
      </div>
      {msg && <p className="text-xs text-blue-600 mt-2">{msg}</p>}
    </div>
  );
}
