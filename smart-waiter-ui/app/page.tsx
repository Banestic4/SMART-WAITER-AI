import { ChatInterface } from "@/components/chat-interface";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-xl overflow-hidden h-[90vh]">
        {/* Render the chat interface */}
        <ChatInterface />
      </div>
    </main>
  );
}
