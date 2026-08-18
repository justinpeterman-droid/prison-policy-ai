import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import "./styles.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Guided Operations root element is missing.");
}

createRoot(root).render(
  <StrictMode>
    <BrowserRouter basename="/workspace">
      <App />
    </BrowserRouter>
  </StrictMode>,
);
