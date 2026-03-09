"use client";

import { useEffect, useRef, useState } from "react";
import AgoraRTC, {
  IAgoraRTCClient,
  ILocalAudioTrack,
  ILocalVideoTrack,
} from "agora-rtc-sdk-ng";

interface VideoCallProps {
  appId: string;
  channel: string;
  token: string;
  uid: number;
  onLeave: () => void;
}

export default function VideoCall({
  appId,
  channel,
  token,
  uid,
  onLeave,
}: VideoCallProps) {
  const clientRef = useRef<IAgoraRTCClient | null>(null);
  const localAudioRef = useRef<ILocalAudioTrack | null>(null);
  const localVideoRef = useRef<ILocalVideoTrack | null>(null);
  const screenTrackRef = useRef<ILocalVideoTrack | null>(null);

  const localElRef = useRef<HTMLDivElement | null>(null);
  const remoteElRef = useRef<HTMLDivElement | null>(null);

  // Control states
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [isSharingScreen, setIsSharingScreen] = useState(false);
  const [remoteUserCount, setRemoteUserCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  // init once
  useEffect(() => {
    const client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
    clientRef.current = client;

    const onUserPublished = async (user: any, mediaType: "audio" | "video") => {
      await client.subscribe(user, mediaType);

      if (mediaType === "video" && remoteElRef.current) {
        remoteElRef.current.innerHTML = "";
        user.videoTrack?.play(remoteElRef.current);
      }

      if (mediaType === "audio") {
        user.audioTrack?.play();
      }
    };

    const onUserUnpublished = () => {
      if (remoteElRef.current) remoteElRef.current.innerHTML = "";
    };

    const onUserJoined = () => {
      setRemoteUserCount((prev) => prev + 1);
    };

    const onUserLeft = () => {
      setRemoteUserCount((prev) => Math.max(0, prev - 1));
      if (remoteElRef.current) remoteElRef.current.innerHTML = "";
    };

    client.on("user-published", onUserPublished);
    client.on("user-unpublished", onUserUnpublished);
    client.on("user-joined", onUserJoined);
    client.on("user-left", onUserLeft);

    return () => {
      client.removeAllListeners();
      clientRef.current = null;
    };
  }, []);

  // join/publish when credentials arrive/change
  useEffect(() => {
    const client = clientRef.current;
    if (!client) return;
    if (!appId || !channel || !token || !uid) return;

    let cancelled = false;

    (async () => {
      try {
        try {
          if (client.connectionState !== "DISCONNECTED") {
            await client.leave();
          }
        } catch { }

        await client.join(appId, channel, token, uid);
        setIsConnected(true);

        const [mic, cam] = await AgoraRTC.createMicrophoneAndCameraTracks();

        if (cancelled) {
          mic.close();
          cam.close();
          return;
        }

        localAudioRef.current = mic;
        localVideoRef.current = cam;

        if (localElRef.current) {
          cam.play(localElRef.current);
        }

        await client.publish([mic, cam]);
      } catch (err) {
        setIsConnected(false);
        try {
          await client.leave();
        } catch { }
        console.error("Agora join/publish failed:", err);
      }
    })();

    return () => {
      cancelled = true;

      (async () => {
        try {
          localAudioRef.current?.stop();
          localAudioRef.current?.close();
          localAudioRef.current = null;

          localVideoRef.current?.stop();
          localVideoRef.current?.close();
          localVideoRef.current = null;

          screenTrackRef.current?.stop();
          screenTrackRef.current?.close();
          screenTrackRef.current = null;

          if (localElRef.current) localElRef.current.innerHTML = "";
          if (remoteElRef.current) remoteElRef.current.innerHTML = "";

          if (client.connectionState !== "DISCONNECTED") {
            await client.leave();
          }
          setIsConnected(false);
        } catch { }
      })();
    };
  }, [appId, channel, token, uid]);

  const toggleAudio = async () => {
    if (!localAudioRef.current) return;

    if (isAudioMuted) {
      await localAudioRef.current.setEnabled(true);
      setIsAudioMuted(false);
    } else {
      await localAudioRef.current.setEnabled(false);
      setIsAudioMuted(true);
    }
  };

  const toggleVideo = async () => {
    if (!localVideoRef.current) return;

    if (isVideoOff) {
      await localVideoRef.current.setEnabled(true);
      setIsVideoOff(false);
    } else {
      await localVideoRef.current.setEnabled(false);
      setIsVideoOff(true);
    }
  };

  const toggleScreenShare = async () => {
    const client = clientRef.current;
    if (!client) return;

    try {
      if (isSharingScreen) {
        // Stop screen sharing
        if (screenTrackRef.current) {
          await client.unpublish(screenTrackRef.current);
          screenTrackRef.current.stop();
          screenTrackRef.current.close();
          screenTrackRef.current = null;
        }

        // Re-publish camera
        if (localVideoRef.current) {
          await client.publish(localVideoRef.current);
        }

        setIsSharingScreen(false);
      } else {
        // Start screen sharing
        const screenTrack = await AgoraRTC.createScreenVideoTrack({});

        // Unpublish camera
        if (localVideoRef.current) {
          await client.unpublish(localVideoRef.current);
        }

        // Publish screen
        screenTrackRef.current = Array.isArray(screenTrack) ? screenTrack[0] : screenTrack;
        await client.publish(screenTrackRef.current);

        setIsSharingScreen(true);

        // Handle screen share stop (user clicks browser "Stop sharing")
        screenTrackRef.current.on("track-ended", () => {
          toggleScreenShare();
        });
      }
    } catch (err) {
      console.error("Screen share error:", err);
    }
  };

  const handleLeave = async () => {
    const client = clientRef.current;
    try {
      localAudioRef.current?.stop();
      localAudioRef.current?.close();
      localAudioRef.current = null;

      localVideoRef.current?.stop();
      localVideoRef.current?.close();
      localVideoRef.current = null;

      screenTrackRef.current?.stop();
      screenTrackRef.current?.close();
      screenTrackRef.current = null;

      if (client && client.connectionState !== "DISCONNECTED") {
        await client.leave();
      }
    } catch { }
    onLeave();
  };

  return (
    <div className="w-full h-full aspect-video bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl overflow-hidden relative shadow-2xl">
      {/* Remote video - full background */}
      <div ref={remoteElRef} className="w-full h-full absolute inset-0 bg-gray-800">
        {remoteUserCount === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <p className="text-gray-400 text-sm">Waiting for others to join...</p>
            </div>
          </div>
        )}
      </div>

      {/* Local video - Picture-in-Picture */}
      <div className="absolute bottom-24 right-4 w-48 h-36 bg-black/60 backdrop-blur-sm rounded-xl overflow-hidden border-2 border-white/20 shadow-xl transition-all hover:scale-105">
        <div ref={localElRef} className="w-full h-full">
          {isVideoOff && (
            <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-gray-700 to-gray-800">
              <div className="w-16 h-16 rounded-full bg-blue-500 flex items-center justify-center">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
            </div>
          )}
        </div>
        <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/50 backdrop-blur-sm rounded text-xs text-white font-medium">
          You
        </div>
      </div>

      {/* Top bar - Status */}
      <div className="absolute top-0 left-0 right-0 p-4 bg-gradient-to-b from-black/50 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
              <span className="text-white text-sm font-medium">{isConnected ? 'Connected' : 'Connecting...'}</span>
            </div>
            <div className="h-4 w-px bg-white/30"></div>
            <div className="flex items-center gap-2 text-white/80 text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <span>{remoteUserCount + 1} participant{remoteUserCount !== 0 ? 's' : ''}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Control bar - Bottom */}
      <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/60 via-black/40 to-transparent backdrop-blur-sm">
        <div className="flex items-center justify-center gap-3">
          {/* Mute/Unmute Audio */}
          <button
            onClick={toggleAudio}
            className={`group relative w-14 h-14 rounded-full transition-all transform hover:scale-110 ${isAudioMuted
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-white/20 hover:bg-white/30 backdrop-blur-md'
              } flex items-center justify-center shadow-lg`}
            title={isAudioMuted ? 'Unmute' : 'Mute'}
          >
            {isAudioMuted ? (
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
              </svg>
            ) : (
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            )}
          </button>

          {/* Video On/Off */}
          <button
            onClick={toggleVideo}
            className={`group relative w-14 h-14 rounded-full transition-all transform hover:scale-110 ${isVideoOff
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-white/20 hover:bg-white/30 backdrop-blur-md'
              } flex items-center justify-center shadow-lg`}
            title={isVideoOff ? 'Turn on camera' : 'Turn off camera'}
          >
            {isVideoOff ? (
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3l18 18" />
              </svg>
            ) : (
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            )}
          </button>

          {/* Screen Share */}
          <button
            onClick={toggleScreenShare}
            className={`group relative w-14 h-14 rounded-full transition-all transform hover:scale-110 ${isSharingScreen
              ? 'bg-blue-500 hover:bg-blue-600'
              : 'bg-white/20 hover:bg-white/30 backdrop-blur-md'
              } flex items-center justify-center shadow-lg`}
            title={isSharingScreen ? 'Stop sharing' : 'Share screen'}
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </button>

          {/* Leave Call */}
          <button
            onClick={handleLeave}
            className="group relative w-14 h-14 rounded-full bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 transition-all transform hover:scale-110 flex items-center justify-center shadow-lg"
            title="Leave call"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
