import type { GeneratedEmail } from "../types";

const BASE = "/api/chat";

interface ChatApiResponse {
  reply: string;
  email: GeneratedEmail | null;
}

export async function sendChatMessage(
  message: string
): Promise<ChatApiResponse> {
  const res = await fetch(`${BASE}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}
