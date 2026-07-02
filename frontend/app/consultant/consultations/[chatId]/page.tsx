"use client";

import { useParams } from "next/navigation";
import { ConsultationChat } from "@/components/consultation/ConsultationChat";

export default function ConsultantConsultationChatPage() {
    const { chatId } = useParams<{ chatId: string }>();
    return (
        <div className="max-w-5xl mx-auto p-6">
            <ConsultationChat chatId={chatId} backHref="/consultant/requests" />
        </div>
    );
}
