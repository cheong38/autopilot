import { Trash2 } from "lucide-react";
import type { Project } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ProjectListProps {
  projects: Project[];
}

const providerVariant: Record<string, "default" | "secondary" | "outline"> = {
  github: "default",
  gitlab: "secondary",
  jira: "outline",
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
    <ul className="space-y-3">
      {projects.map((project) => (
        <li
          key={project.id}
          className="flex items-center justify-between rounded-lg border px-4 py-3"
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{project.name}</span>
              <Badge variant={providerVariant[project.provider] ?? "outline"}>
                {project.provider}
              </Badge>
            </div>
            <span className="text-xs text-muted-foreground">
              {project.remoteUrl}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => handleRemove(project)}
            aria-label={`Remove ${project.name}`}
          >
            <Trash2 className="size-4 text-muted-foreground" />
          </Button>
        </li>
      ))}
    </ul>
  );
}
