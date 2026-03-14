import type { Project } from "@/types";

export type { Project };

export const mockProjects: Project[] = [
  {
    id: "proj-1",
    name: "autopilot",
    remoteUrl: "https://github.com/cheong38/autopilot",
    provider: "github",
  },
  {
    id: "proj-2",
    name: "e-commerce-api",
    remoteUrl: "https://github.com/cheong38/e-commerce-api",
    provider: "github",
  },
  {
    id: "proj-3",
    name: "ml-pipeline",
    remoteUrl: "https://gitlab.com/cheong38/ml-pipeline",
    provider: "gitlab",
  },
];
