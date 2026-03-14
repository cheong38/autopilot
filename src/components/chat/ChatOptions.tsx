import { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ChatOption } from "@/types";
import { cn } from "@/lib/utils";

interface ChatOptionsProps {
  options: ChatOption[];
  onSelect: (value: string, label: string) => void;
  onSendCustom: (text: string) => void;
}

export default function ChatOptions({
  options,
  onSelect,
  onSendCustom,
}: ChatOptionsProps) {
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customText, setCustomText] = useState("");

  const handleOptionClick = (option: ChatOption) => {
    if (option.value === "other") {
      setShowCustomInput(true);
      return;
    }
    onSelect(option.value, option.label);
  };

  const handleCustomSend = () => {
    if (!customText.trim()) return;
    onSendCustom(customText.trim());
    setCustomText("");
    setShowCustomInput(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleCustomSend();
    }
  };

  return (
    <div className="flex flex-col gap-2 border-t border-border bg-card px-4 py-3">
      {!showCustomInput ? (
        <div className="flex flex-col gap-1.5">
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => handleOptionClick(option)}
              className={cn(
                "rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:bg-accent",
                option.recommended
                  ? "border-primary/40 bg-primary/5 font-medium text-foreground hover:bg-primary/10"
                  : "border-border text-foreground/80"
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex items-end gap-2">
          <textarea
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your response..."
            className="flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            rows={2}
            autoFocus
          />
          <Button
            size="icon"
            onClick={handleCustomSend}
            disabled={!customText.trim()}
            className="shrink-0"
          >
            <Send className="size-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
