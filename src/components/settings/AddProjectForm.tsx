import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AddProjectForm() {
  const [name, setName] = useState("");
  const [remoteUrl, setRemoteUrl] = useState("");

  function handleAdd(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    console.log("Add project:", { name, remoteUrl });
    setName("");
    setRemoteUrl("");
  }

  return (
    <form onSubmit={handleAdd} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="project-name">Project Name</Label>
          <Input
            id="project-name"
            placeholder="my-project"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="remote-url">Remote URL</Label>
          <Input
            id="remote-url"
            placeholder="https://github.com/org/repo"
            value={remoteUrl}
            onChange={(e) => setRemoteUrl(e.target.value)}
            required
          />
        </div>
      </div>
      <Button type="submit" size="sm">
        <Plus className="size-4" />
        Add Project
      </Button>
    </form>
  );
}
