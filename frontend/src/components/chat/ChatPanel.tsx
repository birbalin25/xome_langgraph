import { useCallback, useEffect, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";
import type { ChatMessage as ChatMessageType, GeneratedEmail } from "../../types";
import { sendChatMessage } from "../../api/chat";
import ChatMessage from "./ChatMessage";
import EmailPreview from "../email/EmailPreview";

let nextId = 1;
function makeId(): string {
  return `msg-${nextId++}`;
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [latestEmail, setLatestEmail] = useState<GeneratedEmail | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessageType = {
      id: makeId(),
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendChatMessage(text);
      const assistantMsg: ChatMessageType = {
        id: makeId(),
        role: "assistant",
        content: response.reply,
        email: response.email,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (response.email) {
        setLatestEmail(response.email);
      }
    } catch (err) {
      const errorMsg: ChatMessageType = {
        id: makeId(),
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Something went wrong."}`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [input, loading]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* Chat conversation */}
      <div className="flex flex-1 flex-col">
        {/* Messages area */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.length === 0 && (
              <div className="flex h-full items-center justify-center pt-24 text-center text-gray-400">
                <div>
                  <p className="text-lg font-medium">Xome Campaign Chat</p>
                  <p className="mt-2 text-sm">
                    Try: "Generate a campaign email for USER_001" or
                    "Generate email for USER_042 in Austin"
                  </p>
                </div>
              </div>
            )}
            {messages.map((msg) => (
              <div key={msg.id}>
                <ChatMessage message={msg} />
                {msg.email && (
                  <div className="mt-3 ml-0">
                    <EmailPreview
                      email={msg.email}
                      properties={[]}
                      onPropertyClick={() => {}}
                    />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Input bar */}
        <div className="border-t border-gray-200 bg-white px-6 py-4">
          <div className="mx-auto flex max-w-3xl items-center gap-3">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              disabled={loading}
              className="flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm
                         focus:border-xome-500 focus:outline-none focus:ring-1 focus:ring-xome-500
                         disabled:bg-gray-50 disabled:text-gray-400"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-xome-600
                         text-white transition hover:bg-xome-700
                         disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Email preview sidebar (shows latest email) */}
      {latestEmail && (
        <div className="w-[480px] border-l border-gray-200 overflow-y-auto bg-gray-50 p-4">
          <h3 className="mb-3 text-sm font-semibold text-gray-700">Latest Email Preview</h3>
          <EmailPreview
            email={latestEmail}
            properties={[]}
            onPropertyClick={() => {}}
          />
        </div>
      )}
    </div>
  );
}
