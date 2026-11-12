import { Link, Route, Routes } from "react-router-dom";
import { PageMessage } from "./components/ui";
import { AdminPage } from "./pages/admin/AdminPage";
import { HomePage } from "./pages/HomePage";
import { LandingPage } from "./pages/LandingPage";
import { OAuthCallbackPage } from "./pages/OAuthCallbackPage";
import { ScratchPage } from "./pages/ScratchPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/c/:slug" element={<LandingPage />} />
      <Route path="/s/:token" element={<ScratchPage />} />
      <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route
        path="*"
        element={
          <PageMessage icon="🧭" title="Page not found">
            <Link to="/" className="btn-primary">See current campaigns</Link>
          </PageMessage>
        }
      />
    </Routes>
  );
}
