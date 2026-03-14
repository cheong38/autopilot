import { BrowserRouter, Routes, Route } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppProvider } from "@/context/AppContext";
import Layout from "@/components/Layout";
import HomePage from "@/pages/HomePage";
import DagPage from "@/pages/DagPage";
import SettingsPage from "@/pages/SettingsPage";

function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <TooltipProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/dag" element={<DagPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </TooltipProvider>
      </AppProvider>
    </BrowserRouter>
  );
}

export default App;
