export interface Project {
  id: string;
  name: string;
  remoteUrl: string;
  provider: "github" | "gitlab";
}

export const mockProjects: Project[] = [
  {
    id: "proj-1",
    name: "autopilot",
    remoteUrl: "https://github.com/cheong38/autopilot",
    provider: "github" as const,
  },
  {
    id: "proj-2",
    name: "e-commerce-api",
    remoteUrl: "https://github.com/cheong38/e-commerce-api",
    provider: "github" as const,
  },
  {
    id: "proj-3",
    name: "ml-pipeline",
    remoteUrl: "https://gitlab.com/cheong38/ml-pipeline",
    provider: "gitlab" as const,
  },
];
