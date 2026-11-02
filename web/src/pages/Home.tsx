import { Link } from "react-router-dom";
import { api } from "../api";
import { useLoad } from "../hooks";
import { topicColor } from "../topicColors";

export default function Home() {
  const topics = useLoad(() => api.topics(), []);

  return (
    <>
      <section className="intro">
        <h1>Refresh a topic before your next project, call or interview.</h1>
        <p>
          Short, reviewed pages in one format: overview, diagram, key concepts, a comparison, pitfalls and a quick
          quiz. Pick an area to start.
        </p>
      </section>

      {topics.loading && <p className="notice">Loading topics…</p>}
      {topics.error && <p className="notice error">Topics couldn’t load: {topics.error}</p>}

      {topics.data && (
        <ul className="topic-index">
          {topics.data.map((t) => (
            <li key={t.id} style={{ ["--topic" as string]: topicColor(t.id) }}>
              <Link to={`/t/${t.id}`} className="topic-row">
                <span className="topic-name">{t.name}</span>
                <span className="topic-desc">{t.description}</span>
                <span className="topic-count">
                  {t.subtopicCount} {t.subtopicCount === 1 ? "sub-topic" : "sub-topics"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
