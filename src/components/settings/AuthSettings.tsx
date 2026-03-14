import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AuthSettings() {
  const [claudeToken, setClaudeToken] = useState("");
  const [githubPat, setGithubPat] = useState("");
  const [showClaude, setShowClaude] = useState(false);
  const [showGithub, setShowGithub] = useState(false);

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    console.log("Save auth settings:", {
      claudeToken: claudeToken ? "***" : "(empty)",
      githubPat: githubPat ? "***" : "(empty)",
    });
  }

  return (
    <form onSubmit={handleSave} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="claude-token">Claude Code Auth Token</Label>
        <div className="relative">
          <Input
            id="claude-token"
            type={showClaude ? "text" : "password"}
            placeholder="sk-ant-..."
            value={claudeToken}
            onChange={(e) => setClaudeToken(e.target.value)}
            className="pr-10"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            className="absolute right-1 top-1/2 -translate-y-1/2"
            onClick={() => setShowClaude((v) => !v)}
            aria-label={showClaude ? "Hide token" : "Show token"}
          >
            {showClaude ? (
              <EyeOff className="size-4" />
            ) : (
              <Eye className="size-4" />
            )}
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="github-pat">GitHub PAT</Label>
        <div className="relative">
          <Input
            id="github-pat"
            type={showGithub ? "text" : "password"}
            placeholder="ghp_..."
            value={githubPat}
            onChange={(e) => setGithubPat(e.target.value)}
            className="pr-10"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            className="absolute right-1 top-1/2 -translate-y-1/2"
            onClick={() => setShowGithub((v) => !v)}
            aria-label={showGithub ? "Hide token" : "Show token"}
          >
            {showGithub ? (
              <EyeOff className="size-4" />
            ) : (
              <Eye className="size-4" />
            )}
          </Button>
        </div>
      </div>

      <Button type="submit" size="sm">
        Save
      </Button>
    </form>
  );
}
