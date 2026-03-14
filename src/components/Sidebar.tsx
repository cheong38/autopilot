import { NavLink } from "react-router-dom";
import { House, GitBranch, Settings, MessageCircle, ChevronsUpDown, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { mockProjects } from "@/data/mock-projects";
import { useApp } from "@/context/AppContext";

const navItems = [
  { to: "/", label: "Home", icon: House },
  { to: "/dag", label: "DAG", icon: GitBranch },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export default function Sidebar() {
  const { currentProject, setCurrentProject, openChatDefault } = useApp();

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      {/* Project switcher */}
      <div className="p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className="w-full justify-between font-medium"
              size="lg"
            >
              <span className="truncate">{currentProject.name}</span>
              <ChevronsUpDown className="ml-1 size-4 shrink-0 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[calc(var(--radix-dropdown-menu-trigger-width))]" align="start">
            {mockProjects.map((project) => (
              <DropdownMenuItem
                key={project.id}
                onSelect={() => setCurrentProject(project)}
                className="flex items-center justify-between"
              >
                <span className="truncate">{project.name}</span>
                {project.id === currentProject.id && (
                  <Check className="ml-2 size-4 shrink-0" />
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Separator />

      {/* Navigation links */}
      <nav className="flex-1 p-3">
        <ul className="flex flex-col gap-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                  )
                }
              >
                <Icon className="size-4 shrink-0" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <Separator />

      {/* Chat with OP button */}
      <div className="p-3">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="lg"
              className="w-full gap-2"
              onClick={() => openChatDefault()}
            >
              <MessageCircle className="size-4" />
              Chat with OP
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p>Chat with OP (오피)</p>
          </TooltipContent>
        </Tooltip>
      </div>
    </aside>
  );
}
