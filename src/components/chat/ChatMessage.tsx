import { Sparkles } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * Renders very basic markdown-like formatting:
 * **bold**, `code`, and newlines as <br>.
 */
function renderContent(text: string) {
  const parts: (string | React.ReactElement)[] = [];
  // Split by **bold** and `code`
  const regex = /(\*\*(.+?)\*\*|`(.+?)`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let keyIdx = 0;

  while ((match = regex.exec(text)) !== null) {
    // Push text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[2]) {
      // Bold
      parts.push(
        <strong key={keyIdx++} className="font-semibold">
          {match[2]}
        </strong>
      );
    } else if (match[3]) {
      // Code
      parts.push(
        <code
          key={keyIdx++}
          className="rounded bg-muted px-1 py-0.5 text-xs font-mono"
        >
          {match[3]}
        </code>
      );
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  // Handle newlines
  const result: (string | React.ReactElement)[] = [];
  for (const part of parts) {
    if (typeof part === "string") {
      const lines = part.split("\n");
      lines.forEach((line, i) => {
        result.push(line);
        if (i < lines.length - 1) {
          result.push(<br key={`br-${keyIdx++}`} />);
        }
      });
    } else {
      result.push(part);
    }
  }

  return result;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isOp = message.role === "op";

  return (
    <div className={cn("flex gap-2", isOp ? "justify-start" : "justify-end")}>
      {isOp && (
        <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="size-3.5 text-primary" />
        </div>
      )}
      <div className="flex max-w-[85%] flex-col gap-1">
        {/* UL violation warning */}
        {message.ulViolation && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-600 dark:bg-amber-950/40 dark:text-amber-200">
            <span className="mt-0.5 shrink-0 text-base">&#9888;</span>
            <span>
              Unknown UL term detected:{" "}
              <strong className="font-semibold">
                &ldquo;{message.ulViolation.unknownTerm}&rdquo;
              </strong>
              {message.ulViolation.suggestedTerm && (
                <>
                  {" "}
                  &mdash; did you mean{" "}
                  <strong className="font-semibold">
                    &ldquo;{message.ulViolation.suggestedTerm}&rdquo;
                  </strong>
                  ?
                </>
              )}
            </span>
          </div>
        )}

        {/* Message bubble */}
        <div
          className={cn(
            "rounded-2xl px-3.5 py-2 text-sm leading-relaxed",
            isOp
              ? "rounded-tl-sm bg-muted text-foreground"
              : "rounded-tr-sm bg-primary text-primary-foreground"
          )}
        >
          {renderContent(message.content)}
        </div>
      </div>
    </div>
  );
}
