import { Link, NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { useLoad } from "./hooks";
import Home from "./pages/Home";
import TopicPage from "./pages/TopicPage";
import PageView from "./pages/PageView";
import Review from "./pages/Review";
import ReviewDraft from "./pages/ReviewDraft";

export default function App() {
  const me = useLoad(() => api.me(), []);

  return (
    <div className="shell">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="masthead">
        <Link to="/" className="wordmark" aria-label="KnowNow home">
          <span className="wordmark-bars" aria-hidden="true">
            <i style={{ background: "#2F5DDB" }} />
            <i style={{ background: "#7A4FD1" }} />
            <i style={{ background: "#1F8A5B" }} />
            <i style={{ background: "#B7791F" }} />
            <i style={{ background: "#A33A3A" }} />
          </span>
          KnowNow
        </Link>
        <nav className="masthead-nav">
          <NavLink to="/" end>
            Topics
          </NavLink>
          {me.data?.isReviewer && <NavLink to="/review">Review</NavLink>}
          {me.data && (
            <span className="who" title={me.data.name}>
              {me.data.name}
            </span>
          )}
          <a href="/.auth/logout">Sign out</a>
        </nav>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/t/:topicId" element={<TopicPage />} />
          <Route path="/t/:topicId/:pageId" element={<PageView />} />
          <Route path="/review" element={<Review />} />
          <Route path="/review/:topicId/:pageId" element={<ReviewDraft />} />
          <Route path="*" element={<p className="notice">That page doesn’t exist. Go back to the topics.</p>} />
        </Routes>
      </main>
    </div>
  );
}
