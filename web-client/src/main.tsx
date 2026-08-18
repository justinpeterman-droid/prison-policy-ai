import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { AuthProvider } from "./auth/AuthProvider";
import { WorkspaceMemoryProvider } from "./workspace/WorkspaceMemoryProvider";
import "./styles/global.css";

const root = document.getElementById("root");
if (!root) throw new Error("Application root element is missing");

createRoot(root).render(
  <StrictMode>
    <AuthProvider>
      <WorkspaceMemoryProvider>
        <App />
      </WorkspaceMemoryProvider>
    </AuthProvider>
  </StrictMode>,
);
