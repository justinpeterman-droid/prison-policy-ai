import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Root } from "./Root";
import "./styles.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Guided Operations root element is missing.");
}

createRoot(root).render(
  <StrictMode>
    <BrowserRouter basename="/workspace">
      <Root />
    </BrowserRouter>
  </StrictMode>,
);
