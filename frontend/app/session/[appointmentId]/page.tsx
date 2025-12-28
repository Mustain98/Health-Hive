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

export default function UserSessionPage() {
  const params = useParams();
  const appointmentId = Number(params.appointmentId);
  const currentUser = useAuth();

  const [appointment, setAppointment] = useState<AppointmentRead | null>(null);
  const [room, setRoom] = useState<SessionRoomRead | null>(null);

  const [messages, setMessages] = useState<ChatMessageRead[]>([]);
  const [newMessage, setNewMessage] = useState("");

  const [note, setNote] = useState<SessionNoteRead | null>(null);

  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId]);

  // ✅ Poll messages when room exists
  useEffect(() => {
    if (!room) return;

    loadMessagesByRoomId(room.id);
    const interval = setInterval(() => loadMessagesByRoomId(room.id), 3000);
    return () => clearInterval(interval);
  }, [room?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
    try {
      // Load appointment (user list)
      const appointments = await apiFetch<AppointmentRead[]>(
        "/api/appointments/me"
      );
      const appt = appointments.find((a) => a.id === appointmentId);
      setAppointment(appt || null);

      // Load room
      const roomData = await apiFetch<SessionRoomRead>(
        `/api/appointments/${appointmentId}/room`
      );
      setRoom(roomData);

      // Load messages immediately
      await loadMessagesByRoomId(roomData.id);

      // Load note (user sees only if visible)
      try {
        const noteData = await apiFetch<SessionNoteRead>(
          `/api/sessions/appointments/${appointmentId}/note`
        );
        setNote(noteData);
      } catch {
        // Note doesn't exist or not visible
      }
    } catch (error) {
      console.error("Failed to load session:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!room || !newMessage.trim()) return;

    setSending(true);

    try {
      const msgData: ChatMessageCreate = {
        message: newMessage,
      };

      await apiFetch(`/api/sessions/rooms/${room.id}/messages`, {
        method: "POST",
        body: msgData,
      });

      setNewMessage("");
      await loadMessagesByRoomId(room.id);
    } catch (error) {
      console.error("Failed to send message:", error);
    } finally {
      setSending(false);
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

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chat */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow">
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
                      className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                        mine
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
              placeholder="Type a message..."
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
              disabled={!room || sending}
            />
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
              disabled={!room || sending}
            >
              {sending ? "Sending..." : "Send"}
            </button>
          </form>
        </div>

        {/* Note (read only for user) */}
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
              <p className="text-sm text-gray-500">
                No visible note yet.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
