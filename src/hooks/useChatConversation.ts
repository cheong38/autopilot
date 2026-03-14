import { useState, useCallback, useRef } from "react";
import type { ChatMessage } from "@/types";
import {
  mockConversations,
  conversationScripts,
} from "@/data/mock-conversations";

interface UseChatConversationReturn {
  messages: ChatMessage[];
  isTyping: boolean;
  sendMessage: (text: string) => void;
  selectOption: (value: string, label: string) => void;
  hasOptions: boolean;
  currentOptions: ChatMessage["options"] | undefined;
  isFreeinput: boolean;
}

export function useChatConversation(
  conversationId: string | null
): UseChatConversationReturn {
  // Find the initial messages for this conversation
  const initialConv = conversationId
    ? mockConversations.find((c) => c.id === conversationId)
    : null;

  const [messages, setMessages] = useState<ChatMessage[]>(
    initialConv ? [...initialConv.messages] : []
  );
  const [isTyping, setIsTyping] = useState(false);
  const stepRef = useRef(0);
  const prevConvIdRef = useRef(conversationId);

  // Reset state when conversation changes
  if (conversationId !== prevConvIdRef.current) {
    prevConvIdRef.current = conversationId;
    const conv = conversationId
      ? mockConversations.find((c) => c.id === conversationId)
      : null;
    setMessages(conv ? [...conv.messages] : []);
    stepRef.current = 0;
    setIsTyping(false);
  }

  const appendOpResponse = useCallback(
    (_userMsg: ChatMessage) => {
      if (!conversationId) return;
      const script = conversationScripts[conversationId];
      if (!script) return;

      const nextStep = stepRef.current + 1;
      const scriptEntry = script[nextStep];
      if (!scriptEntry) return;

      setIsTyping(true);

      setTimeout(() => {
        const opMsg: ChatMessage = {
          ...scriptEntry.response,
          id: `msg-live-${Date.now()}-op`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, opMsg]);
        setIsTyping(false);
        stepRef.current = nextStep;
      }, 700);
    },
    [conversationId]
  );

  const sendMessage = useCallback(
    (text: string) => {
      const userMsg: ChatMessage = {
        id: `msg-live-${Date.now()}-user`,
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      appendOpResponse(userMsg);
    },
    [appendOpResponse]
  );

  const selectOption = useCallback(
    (_value: string, label: string) => {
      const userMsg: ChatMessage = {
        id: `msg-live-${Date.now()}-user`,
        role: "user",
        content: label,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      appendOpResponse(userMsg);
    },
    [appendOpResponse]
  );

  // Determine current state
  const lastMessage = messages[messages.length - 1];
  const hasOptions = !!(lastMessage?.role === "op" && lastMessage.options?.length);
  const currentOptions = hasOptions ? lastMessage.options : undefined;

  // Free input mode: last OP message has no options, or there's no OP message at all (conv-3 initial)
  const isFreeinput =
    !hasOptions &&
    !isTyping &&
    messages.length > 0 &&
    lastMessage?.role === "op" &&
    !lastMessage.options?.length;

  return {
    messages,
    isTyping,
    sendMessage,
    selectOption,
    hasOptions,
    currentOptions,
    isFreeinput,
  };
}
