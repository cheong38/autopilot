import { NavLink } from "react-router-dom";
import { House, GitBranch, Settings, MessageCircle, ChevronsUpDown, Check, Bot, Moon, Sun } from "lucide-react";
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
  { to: "/agents", label: "Agents", icon: Bot },
  { to: "/dag", label: "DAG", icon: GitBranch },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export default function Sidebar() {
  const { currentProject, setCurrentProject, openChatDefault, isDark, toggleTheme } = useApp();

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      {/* Project switcher */}
      <div className="p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className="w-full justify-between font-medium shadow-sm transition-all duration-150 hover:shadow-md"
              size="lg"
            >
              <div className="flex items-center gap-2 truncate">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[10px] font-bold text-primary">
                  {currentProject.name.charAt(0).toUpperCase()}
                </span>
                <span className="truncate">{currentProject.name}</span>
              </div>
              <ChevronsUpDown className="ml-1 size-4 shrink-0 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[calc(var(--radix-dropdown-menu-trigger-width))]" align="start">
            {mockProjects.map((project) => (
              <DropdownMenuItem
                key={project.id}
                onSelect={() => setCurrentProject(project)}
                className="flex items-center justify-between transition-colors"
              >
                <span className="flex items-center gap-2 truncate">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[10px] font-bold text-primary">
                    {project.name.charAt(0).toUpperCase()}
                  </span>
                  <span className="truncate">{project.name}</span>
                </span>
                {project.id === currentProject.id && (
                  <Check className="ml-2 size-4 shrink-0 text-primary" />
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Separator />

      {/* Navigation links */}
      <nav className="flex-1 px-2 py-3">
        <ul className="flex flex-col gap-0.5">
          {navItems.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150",
                    isActive
                      ? "nav-active-bar bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground hover:translate-x-0.5"
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

      {/* Bottom actions */}
      <div className="flex flex-col gap-2 p-3">
        {/* Dark mode toggle */}
        <div className="flex items-center justify-between px-1">
          <span className="text-xs text-muted-foreground">Theme</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-7 transition-transform duration-200 hover:rotate-12"
                onClick={toggleTheme}
              >
                {isDark ? (
                  <Sun className="size-4 text-amber-400" />
                ) : (
                  <Moon className="size-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              <p>Switch to {isDark ? "light" : "dark"} mode</p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Chat with OP button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="lg"
              className="w-full gap-2 shadow-sm transition-all duration-150 hover:shadow-md"
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
