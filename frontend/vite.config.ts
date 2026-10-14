import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server on :5173. The app calls the backend directly at http://localhost:8000
// (override with VITE_API_URL); the backend allows this origin via CORS.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
