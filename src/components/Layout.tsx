import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import ChatPopover from "./chat/ChatPopover";

export default function Layout() {
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto" key={location.pathname}>
        <div className="animate-page-enter">
          <Outlet />
        </div>
      </main>
      <ChatPopover />
    </div>
  );
}
