import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import ChatPopover from "./chat/ChatPopover";

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
      <ChatPopover />
    </div>
  );
}
