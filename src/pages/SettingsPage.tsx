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
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Settings</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Manage projects, authentication, and configuration.
        </p>
      </div>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Projects</CardTitle>
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

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Authentication</CardTitle>
          <CardDescription>
            API tokens for Claude Code and source-control providers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AuthSettings />
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Configuration</CardTitle>
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
