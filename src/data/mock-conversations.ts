import type { Conversation, ChatMessage } from "@/types";

/**
 * Scripted conversation flows. Each conversation has a sequence of
 * scripted steps: each user action (pick option or send message) triggers
 * the next OP response in the script.
 */

// Helper to generate IDs
let msgIdCounter = 0;
function msgId(): string {
  return `msg-${++msgIdCounter}`;
}

// ─── Conversation 1: Requirement Clarification (linked to HI item hi-1) ─────
const conv1InitialMessages: ChatMessage[] = [
  {
    id: msgId(),
    role: "op",
    content:
      "The Kanban board layout needs 7 columns. Should I use horizontal scroll or compress columns to fit the viewport?",
    timestamp: "2026-03-14T09:15:00Z",
    options: [
      {
        label: "Horizontal scroll (Recommended)",
        value: "use_horizontal_scroll",
        recommended: true,
      },
      { label: "Compress columns", value: "compress_columns" },
      { label: "Let me decide later", value: "defer" },
      { label: "Other", value: "other" },
    ],
  },
];

// Scripted follow-ups keyed by step number
export const conv1Script: Record<
  number,
  { triggerValues?: string[]; response: ChatMessage }
> = {
  1: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "Got it. For the horizontal scroll behavior, should the board auto-scroll to the first column with a pending issue, or always start at the leftmost column?",
      timestamp: "2026-03-14T09:15:30Z",
      options: [
        {
          label: "Auto-scroll to first pending (Recommended)",
          value: "auto_scroll_pending",
          recommended: true,
        },
        { label: "Always start at leftmost", value: "start_leftmost" },
        { label: "Other", value: "other" },
      ],
    },
  },
  2: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "Perfect. One more thing — should collapsed empty columns be hidden or shown as thin placeholders?",
      timestamp: "2026-03-14T09:16:00Z",
      options: [
        {
          label: "Show as thin placeholders (Recommended)",
          value: "thin_placeholders",
          recommended: true,
        },
        { label: "Hide empty columns", value: "hide_empty" },
        { label: "Other", value: "other" },
      ],
    },
  },
  3: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "All clarified! I'll proceed with implementing the Kanban layout based on your choices. I'll update the issue when it's ready for review.",
      timestamp: "2026-03-14T09:16:30Z",
    },
  },
};

// ─── Conversation 2: UL Violation Demo (linked to HI item hi-5) ─────────────
const conv2InitialMessages: ChatMessage[] = [
  {
    id: msgId(),
    role: "op",
    content:
      "For the session color-coding feature, where should the color indicator appear on each Kanban card?",
    timestamp: "2026-03-14T10:05:00Z",
    options: [
      {
        label: "Left border stripe (Recommended)",
        value: "left_border",
        recommended: true,
      },
      { label: "Top bar", value: "top_bar" },
      { label: "Background tint", value: "bg_tint" },
      { label: "Other", value: "other" },
    ],
  },
];

export const conv2Script: Record<
  number,
  { triggerValues?: string[]; response: ChatMessage }
> = {
  1: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "Good choice. Should the colors also appear in the sprint backlog view or only on the Kanban board?",
      timestamp: "2026-03-14T10:05:30Z",
      options: [
        { label: "Both views", value: "both_views" },
        { label: "Kanban only", value: "kanban_only" },
        { label: "Other", value: "other" },
      ],
    },
  },
  // Step 2 is the UL violation detection — triggers after user mentions "sprint backlog"
  2: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "I noticed you used the term **\"sprint backlog\"**. This term is not defined in the project's Ubiquitous Language. Did you mean one of these?",
      timestamp: "2026-03-14T10:06:00Z",
      ulViolation: {
        unknownTerm: "sprint backlog",
        suggestedTerm: "backlog",
      },
      options: [
        {
          label: "'backlog' — existing UL term for issue status (Recommended)",
          value: "use_backlog",
          recommended: true,
        },
        {
          label: "Define 'sprint backlog' as a new UL term",
          value: "define_new_term",
        },
        { label: "Skip — not a domain term", value: "skip_term" },
        { label: "Other", value: "other" },
      ],
    },
  },
  3: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "Understood. I'll use **\"backlog\"** consistently. The color-coding will be applied to the Kanban board cards with a left border stripe. Proceeding with implementation.",
      timestamp: "2026-03-14T10:06:30Z",
    },
  },
};

// ─── Conversation 3: New Requirements Input ─────────────────────────────────
const conv3InitialMessages: ChatMessage[] = [
  {
    id: msgId(),
    role: "op",
    content:
      "Hi! I'm OP (오피), your project autopilot. How can I help you today?",
    timestamp: "2026-03-14T11:00:00Z",
  },
];

export const conv3Script: Record<
  number,
  { triggerValues?: string[]; response: ChatMessage }
> = {
  1: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "Interesting! A notification system. Let me ask a few clarifying questions one at a time.\n\nFirst: what types of events should trigger notifications?",
      timestamp: "2026-03-14T11:00:30Z",
      options: [
        {
          label: "Issue status changes (Recommended)",
          value: "status_changes",
          recommended: true,
        },
        { label: "HI queue items", value: "hi_items" },
        { label: "PR reviews", value: "pr_reviews" },
        { label: "All of the above", value: "all_events" },
        { label: "Other", value: "other" },
      ],
    },
  },
  2: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "Got it. Next question: how should notifications be delivered?",
      timestamp: "2026-03-14T11:01:00Z",
      options: [
        {
          label: "In-app toast notifications (Recommended)",
          value: "in_app_toast",
          recommended: true,
        },
        { label: "System notifications (OS-level)", value: "system_notif" },
        { label: "Both", value: "both" },
        { label: "Other", value: "other" },
      ],
    },
  },
  3: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "Last question: should users be able to configure which notifications they receive, or keep it simple with an on/off toggle?",
      timestamp: "2026-03-14T11:01:30Z",
      options: [
        {
          label: "Granular per-event settings (Recommended)",
          value: "granular",
          recommended: true,
        },
        { label: "Simple on/off toggle", value: "simple_toggle" },
        { label: "Other", value: "other" },
      ],
    },
  },
  4: {
    response: {
      id: msgId(),
      role: "op",
      content:
        "Great, I have everything I need! I'll create the following issues for the notification system:\n\n1. **Define notification event types** (story)\n2. **Implement in-app toast component** (task)\n3. **Add notification preferences to settings** (task)\n\nI'll add these to the backlog and link them as dependencies. You'll see them on the Kanban board shortly.",
      timestamp: "2026-03-14T11:02:00Z",
    },
  },
};

// ─── Export conversations ────────────────────────────────────────────────────

export const mockConversations: Conversation[] = [
  {
    id: "conv-1",
    projectId: "proj-1",
    hiItemId: "hi-1",
    messages: [...conv1InitialMessages],
    status: "active",
  },
  {
    id: "conv-2",
    projectId: "proj-1",
    hiItemId: "hi-5",
    messages: [...conv2InitialMessages],
    status: "active",
  },
  {
    id: "conv-3",
    projectId: "proj-1",
    messages: [...conv3InitialMessages],
    status: "active",
  },
];

export type ConversationScript = Record<
  number,
  { triggerValues?: string[]; response: ChatMessage }
>;

export const conversationScripts: Record<string, ConversationScript> = {
  "conv-1": conv1Script,
  "conv-2": conv2Script,
  "conv-3": conv3Script,
};
