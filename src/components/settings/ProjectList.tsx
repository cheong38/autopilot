import { Trash2 } from "lucide-react";
import type { Project } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ProjectListProps {
  projects: Project[];
}

const providerStyles: Record<string, string> = {
  github: "bg-gray-900 text-white dark:bg-gray-700",
  gitlab: "bg-orange-600 text-white",
  jira: "bg-blue-600 text-white",
};

export default function ProjectList({ projects }: ProjectListProps) {
  function handleRemove(project: Project) {
    console.log("Remove project:", project.name, project.id);
  }

  if (projects.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No projects configured.</p>
    );
  }

  return (
    <ul className="space-y-2">
      {projects.map((project) => (
        <li
          key={project.id}
          className="flex items-center justify-between rounded-lg border border-border bg-background px-4 py-3 transition-colors hover:bg-accent/30"
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{project.name}</span>
              <Badge
                className={`border-none text-[10px] font-medium uppercase tracking-wider ${
                  providerStyles[project.provider] ?? "bg-muted text-muted-foreground"
                }`}
              >
                {project.provider}
              </Badge>
            </div>
            <span className="font-technical text-xs text-muted-foreground">
              {project.remoteUrl}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => handleRemove(project)}
            aria-label={`Remove ${project.name}`}
            className="text-muted-foreground hover:text-destructive transition-colors"
          >
            <Trash2 className="size-4" />
          </Button>
        </li>
      ))}
    </ul>
  );
}
