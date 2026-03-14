import { mockProjects } from "@/data/mock-projects";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import ProjectList from "@/components/settings/ProjectList";
import AddProjectForm from "@/components/settings/AddProjectForm";
import AuthSettings from "@/components/settings/AuthSettings";
import ConfigSettings from "@/components/settings/ConfigSettings";

export default function SettingsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage projects, authentication, and configuration.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Projects</CardTitle>
          <CardDescription>
            Registered projects and their remote repositories.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <ProjectList projects={mockProjects} />
          <div className="border-t pt-4">
            <h3 className="mb-3 text-sm font-medium">Add a project</h3>
            <AddProjectForm />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Authentication</CardTitle>
          <CardDescription>
            API tokens for Claude Code and source-control providers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AuthSettings />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>
            Autopilot runtime parameters.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ConfigSettings />
        </CardContent>
      </Card>
    </div>
  );
}
