import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useLoad } from "../hooks";
import { topicColor } from "../topicColors";

export default function TopicPage() {
  const { topicId = "" } = useParams();
  const topic = useLoad(() => api.topic(topicId), [topicId]);

  if (topic.loading) return <p className="notice">Loading…</p>;
  if (topic.error || !topic.data) return <p className="notice error">{topic.error ?? "Topic not found."}</p>;
  const t = topic.data;

  return (
    <div style={{ ["--topic" as string]: topicColor(t.id) }}>
      <header className="topic-head">
        <p className="crumbs">
          <Link to="/">Topics</Link>
        </p>
        <h1>{t.name}</h1>
        <p className="lede">{t.description}</p>
      </header>

      <div className="subtopics">
        {t.subtopics.map((s) => {
          const ready = s.areas.filter((a) => a.published).length;
          return (
            <section key={s.id} className="subtopic" aria-labelledby={`st-${s.id}`}>
              <div className="subtopic-head">
                <h2 id={`st-${s.id}`}>{s.name}</h2>
                <p>{s.description}</p>
                <p className="subtopic-progress">
                  {ready === 0 ? "Pages coming soon" : `${ready} of ${s.areas.length} pages ready`}
                </p>
              </div>
              <ul className="areas">
                {s.areas.map((a) =>
                  a.published ? (
                    <li key={a.id}>
                      <Link to={`/t/${t.id}/${s.id}--${a.id}`}>{a.name}</Link>
                    </li>
                  ) : (
                    <li key={a.id} className="pending">
                      <span>{a.name}</span>
                    </li>
                  ),
                )}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}
