import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { Project } from "@/types";
import { mockProjects } from "@/data/mock-projects";
import { mockConversations } from "@/data/mock-conversations";

interface AppContextValue {
  currentProject: Project;
  setCurrentProject: (project: Project) => void;
  // Chat state
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
  activeChatConversationId: string | null;
  setActiveChatConversationId: (id: string | null) => void;
  openChatForHiItem: (hiItemId: string) => void;
  openChatDefault: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [currentProject, setCurrentProject] = useState<Project>(mockProjects[0]);
  const [chatOpen, setChatOpen] = useState(false);
  const [activeChatConversationId, setActiveChatConversationId] = useState<string | null>(null);

  const openChatForHiItem = useCallback((hiItemId: string) => {
    // Find conversation linked to this HI item
    const conv = mockConversations.find((c) => c.hiItemId === hiItemId);
    if (conv) {
      setActiveChatConversationId(conv.id);
    } else {
      // Fallback to most recent conversation
      setActiveChatConversationId(mockConversations[0]?.id ?? null);
    }
    setChatOpen(true);
  }, []);

  const openChatDefault = useCallback(() => {
    // Open the most recent conversation or the free-form one (conv-3)
    const freeConv = mockConversations.find((c) => !c.hiItemId);
    setActiveChatConversationId(freeConv?.id ?? mockConversations[0]?.id ?? null);
    setChatOpen(true);
  }, []);

  return (
    <AppContext.Provider
      value={{
        currentProject,
        setCurrentProject,
        chatOpen,
        setChatOpen,
        activeChatConversationId,
        setActiveChatConversationId,
        openChatForHiItem,
        openChatDefault,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
