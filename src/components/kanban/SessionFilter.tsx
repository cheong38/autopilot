import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Session } from "@/types";

interface SessionFilterProps {
  sessions: Session[];
  value: string; // session id or "all"
  onChange: (value: string) => void;
}

export default function SessionFilter({
  sessions,
  value,
  onChange,
}: SessionFilterProps) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-[200px]">
        <SelectValue placeholder="Filter by session" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">
          <span className="flex items-center gap-2">
            <span className="size-2.5 shrink-0 rounded-full bg-muted-foreground/40" />
            All Sessions
          </span>
        </SelectItem>
        {sessions.map((session) => (
          <SelectItem key={session.id} value={session.id}>
            <span className="flex items-center gap-2">
              <span
                className="size-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: session.color }}
              />
              {session.name}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
