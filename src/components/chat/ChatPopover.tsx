import { useEffect, useRef, useState } from "react";
import { X, Sparkles, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useApp } from "@/context/AppContext";
import { useChatConversation } from "@/hooks/useChatConversation";
import { mockConversations } from "@/data/mock-conversations";
import { mockProjects } from "@/data/mock-projects";
import ChatMessageComponent from "./ChatMessage";
import ChatOptions from "./ChatOptions";
import { cn } from "@/lib/utils";

export default function ChatPopover() {
  const { chatOpen, setChatOpen, activeChatConversationId } = useApp();
  const {
    messages,
    isTyping,
    sendMessage,
    selectOption,
    hasOptions,
    currentOptions,
    isFreeinput,
  } = useChatConversation(activeChatConversationId);

  const [freeText, setFreeText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      // Find the viewport element inside the ScrollArea
      const viewport = scrollRef.current.querySelector(
        '[data-slot="scroll-area-viewport"]'
      );
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    }
  }, [messages, isTyping]);

  // Get project name for header context
  const conversation = activeChatConversationId
    ? mockConversations.find((c) => c.id === activeChatConversationId)
    : null;
  const project = conversation
    ? mockProjects.find((p) => p.id === conversation.projectId)
    : null;

  const handleFreeTextSend = () => {
    if (!freeText.trim()) return;
    sendMessage(freeText.trim());
    setFreeText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleFreeTextSend();
    }
  };

  if (!chatOpen) return null;

  return (
    <>
      {/* Backdrop — subtle, allows click to close */}
      <div
        className="fixed inset-0 z-40"
        onClick={() => setChatOpen(false)}
      />

      {/* Popover panel */}
      <div
        className={cn(
          "fixed bottom-4 right-4 z-50 flex w-[400px] flex-col rounded-2xl border border-border bg-popover shadow-2xl",
          "animate-in slide-in-from-bottom-4 fade-in-0 duration-200",
          "max-h-[min(600px,calc(100vh-2rem))]"
        )}
        style={{ height: 520 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-full bg-primary/10">
              <Sparkles className="size-3.5 text-primary" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold">Chat with OP (오피)</span>
              {project && (
                <span className="text-xs text-muted-foreground">
                  {project.name}
                </span>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            onClick={() => setChatOpen(false)}
          >
            <X className="size-4" />
          </Button>
        </div>

        {/* Messages area */}
        <div ref={scrollRef} className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="flex flex-col gap-3 p-4">
              {messages.map((msg) => (
                <ChatMessageComponent key={msg.id} message={msg} />
              ))}

              {/* Typing indicator */}
              {isTyping && (
                <div className="flex items-center gap-2">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <Sparkles className="size-3.5 text-primary" />
                  </div>
                  <div className="rounded-2xl rounded-tl-sm bg-muted px-3.5 py-2">
                    <div className="flex items-center gap-1">
                      <span className="inline-block size-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
                      <span className="inline-block size-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                      <span className="inline-block size-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Bottom area: options or free input */}
        {hasOptions && currentOptions && (
          <ChatOptions
            options={currentOptions}
            onSelect={selectOption}
            onSendCustom={sendMessage}
          />
        )}

        {isFreeinput && (
          <div className="flex items-end gap-2 border-t border-border px-4 py-3">
            <textarea
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              className="flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              rows={1}
            />
            <Button
              size="icon"
              onClick={handleFreeTextSend}
              disabled={!freeText.trim()}
              className="shrink-0"
            >
              <Send className="size-4" />
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
