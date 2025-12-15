'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { PaymentVerificationCard } from './payment-verification-card';
import { cn } from '@/lib/utils';
import { SendIcon, Loader2, Globe, Mic } from 'lucide-react';

interface Message {
    id: string;
    role: 'user' | 'agent';
    content: string;
}

export function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([
        { id: '1', role: 'agent', content: '👋 Hi, Welcome to Evolution Restaurant! I am Smart-Waiter. Please select your preferred language (English, Hausa, Yoruba, Igbo, French) to continue.' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId] = useState(() => 'web-session-' + Math.random().toString(36).substring(7));
    const [isHITL, setIsHITL] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<BlobPart[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isHITL]);

    // Check for HITL Trigger in Agent messages
    useEffect(() => {
        const lastMsg = messages[messages.length - 1];
        if (lastMsg?.role === 'agent') {
            const content = lastMsg.content.toLowerCase();
            // Trigger phrases from payment_flow.py
            if (content.includes("verify your transfer") || content.includes("paused the transaction") || content.includes("waiting for verification")) {
                setIsHITL(true);
            } else {
                if (isHITL) setIsHITL(false); // Reset if moved past
            }
        }
    }, [messages]);

    const handleSend = async (text: string = input) => {
        if (!text.trim() || isLoading) return;

        const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || ''
                },
                body: JSON.stringify({ message: text, session_id: sessionId }),
            });

            if (!response.ok) throw new Error(response.statusText);
            if (!response.body) throw new Error("No response body");

            // Create placeholder for agent response
            const agentMsgId = (Date.now() + 1).toString();
            setMessages(prev => [...prev, { id: agentMsgId, role: 'agent', content: '' }]);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                accumulatedContent += chunk;

                setMessages(prev => prev.map(msg =>
                    msg.id === agentMsgId ? { ...msg, content: accumulatedContent } : msg
                ));
            }

        } catch (error) {
            console.error("Chat Error:", error);
            setMessages(prev => [...prev, { id: 'err', role: 'agent', content: '❌ Error: The Smart Waiter service is temporarily unavailable. Please try again later.' }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleVerifyTransfer = () => {
        setIsHITL(false);
        handleSend("verified");
    };

    const handleToggleRecording = async () => {
        if (isRecording) {
            // Stop Recording
            if (mediaRecorderRef.current) {
                mediaRecorderRef.current.stop();
                setIsRecording(false);
                mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
            }
        } else {
            // Start Recording
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const recorder = new MediaRecorder(stream);
                mediaRecorderRef.current = recorder;
                chunksRef.current = [];

                recorder.ondataavailable = (e) => {
                    if (e.data.size > 0) chunksRef.current.push(e.data);
                };

                recorder.onstop = async () => {
                    const blob = new Blob(chunksRef.current, { type: 'audio/m4a' });
                    const formData = new FormData();
                    formData.append('file', blob, 'recording.m4a');

                    setIsLoading(true);
                    try {
                        const res = await fetch('/api/voice', {
                            method: 'POST',
                            headers: {
                                'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || ''
                            },
                            body: formData
                        });

                        if (!res.ok) throw new Error("Voice request failed");
                        const data = await res.json();

                        // Append User Message (Transcription)
                        setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', content: data.transcription }]);

                        // Append Agent Message
                        setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'agent', content: data.response }]);

                        // Play Audio
                        if (data.audio) {
                            const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);
                            audio.play().catch(e => console.error("Audio play error", e));
                        }
                    } catch (error) {
                        console.error("Voice Error:", error);
                        setMessages(prev => [...prev, { id: 'err', role: 'agent', content: '❌ Voice processing error.' }]);
                    } finally {
                        setIsLoading(false);
                    }
                };

                recorder.start();
                setIsRecording(true);
            } catch (err) {
                console.error("Microphone access denied:", err);
                alert("Could not access microphone.");
            }
        }
    };

    return (
        <div className="flex flex-col h-screen max-w-2xl mx-auto bg-gray-50 border-x shadow-xl">
            {/* Header */}
            <div className="bg-white border-b p-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
                <div className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                        SW
                    </div>
                    <div>
                        <h1 className="font-bold text-gray-900">Smart Waiter</h1>
                        <div className="flex items-center gap-1 text-xs text-green-600">
                            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                            Online • Multilingual
                        </div>
                    </div>
                </div>
                <Button variant="ghost" size="icon" title="Change Language">
                    <Globe className="w-5 h-5 text-gray-500" />
                </Button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={cn(
                            "flex w-full mb-4",
                            msg.role === 'user' ? "justify-end" : "justify-start"
                        )}
                    >
                        <div
                            className={cn(
                                "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
                                msg.role === 'user'
                                    ? "bg-blue-600 text-white rounded-br-none"
                                    : "bg-white text-gray-800 border border-gray-100 rounded-bl-none"
                            )}
                        >
                            <div className="whitespace-pre-wrap font-sans">
                                {msg.content || <span className="animate-pulse">...</span>}
                            </div>
                        </div>
                    </div>
                ))}

                {/* Specific UI for HITL */}
                {isHITL && (
                    <div className="flex justify-start w-full animate-in fade-in slide-in-from-bottom-2">
                        <PaymentVerificationCard
                            onVerify={handleVerifyTransfer}
                            isLoading={isLoading}
                        />
                    </div>
                )}

                <div ref={scrollRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-white border-t">
                <div className="relative flex items-end gap-2">
                    <Textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder={isHITL ? "Verification required..." : "Type your order..."}
                        disabled={isLoading || isHITL}
                        className="min-h-[50px] max-h-[150px] resize-none pr-12 py-3 rounded-xl border-gray-300 focus:ring-blue-500"
                    />
                    <Button
                        onClick={handleToggleRecording}
                        disabled={isLoading || isHITL}
                        size="icon"
                        className={cn(
                            "mb-2 h-10 w-10 text-gray-500",
                            isRecording ? "bg-red-500 hover:bg-red-600 text-white animate-pulse" : "bg-gray-100 hover:bg-gray-200"
                        )}
                        variant="ghost"
                        title="Voice Input"
                    >
                        <Mic className="w-5 h-5" />
                    </Button>
                    <Button
                        onClick={() => handleSend()}
                        disabled={!input.trim() || isLoading || isHITL}
                        size="icon"
                        className="absolute right-2 bottom-2 h-8 w-8 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendIcon className="w-4 h-4" />}
                    </Button>
                </div>
                <div className="text-center mt-2 text-xs text-gray-400">
                    Powered by Meta Llama 3 • Groq • LangGraph
                </div>
            </div>
        </div>
    );
}
