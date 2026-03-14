import { createContext, useContext, useState, type ReactNode } from "react";
import type { Project } from "@/types";
import { mockProjects } from "@/data/mock-projects";

interface AppContextValue {
  currentProject: Project;
  setCurrentProject: (project: Project) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [currentProject, setCurrentProject] = useState<Project>(mockProjects[0]);

  return (
    <AppContext.Provider value={{ currentProject, setCurrentProject }}>
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
