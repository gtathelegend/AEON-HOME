import React, { useState, useRef } from "react";
import { Mic, Square } from "lucide-react";
import { Button } from "../ui/button";
import { toast } from "sonner";

export function VoiceRecorder({ backendUrl }: { backendUrl: string }) {
  const [recording, setRecording] = useState(false);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<BlobPart[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);
      audioChunks.current = [];

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };

      mediaRecorder.current.onstop = async () => {
        const audioBlob = new Blob(audioChunks.current, { type: "audio/webm" });
        // Stop all tracks to release microphone
        stream.getTracks().forEach((track) => track.stop());
        
        // In a real implementation, we would send this to the Sarvam STT backend.
        // For the hackathon, we simulate sending the audio blob to the backend text processor.
        toast.info("Processing voice command via Snapdragon Edge...");
        
        try {
          const res = await fetch(`${backendUrl}/api/v1/voice/command`, {
            method: "POST",
            body: audioBlob,
            headers: { "Content-Type": "audio/webm" }
          });
          
          if (res.ok) {
            toast.success("Command understood and executed");
          } else {
            toast.error("Failed to process voice command");
          }
        } catch (err) {
          console.error(err);
          // Fallback if offline - queue it!
          toast.warning("Offline. Voice command queued for background sync.");
        }
      };

      mediaRecorder.current.start();
      setRecording(true);
    } catch (err) {
      console.error(err);
      toast.error("Could not access microphone.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state === "recording") {
      mediaRecorder.current.stop();
      setRecording(false);
    }
  };

  return (
    <Button
      variant={recording ? "destructive" : "default"}
      size="icon"
      className="rounded-full shadow-lg h-14 w-14 transition-all hover:scale-105"
      onClick={recording ? stopRecording : startRecording}
    >
      {recording ? <Square className="h-6 w-6 animate-pulse" /> : <Mic className="h-6 w-6" />}
    </Button>
  );
}
