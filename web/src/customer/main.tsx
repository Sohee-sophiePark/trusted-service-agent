import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Customer from "./Customer";
import "../index.css";

createRoot(document.getElementById("root")!).render(<StrictMode><Customer /></StrictMode>);
