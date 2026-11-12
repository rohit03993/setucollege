import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Shell from "./Shell.jsx";
import Browse from "./Browse.jsx";
import College from "./College.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/browse" element={<Browse />} />
          <Route path="/college/:slug" element={<College />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  </StrictMode>
);
