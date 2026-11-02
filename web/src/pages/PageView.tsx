import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import PageBody from "../components/PageBody";
import { useLoad } from "../hooks";
import { topicColor } from "../topicColors";

export default function PageView() {
  const { topicId = "", pageId = "" } = useParams();
  const page = useLoad(() => api.page(topicId, pageId), [topicId, pageId]);

  if (page.loading) return <p className="notice">Loading…</p>;
  if (page.error || !page.data) return <p className="notice error">{page.error ?? "Page not found."}</p>;
  const p = page.data;
  const reviewed = p.review?.at ? new Date(p.review.at).toLocaleDateString() : null;

  return (
    <div style={{ ["--topic" as string]: topicColor(topicId) }}>
      <header className="page-head">
        <p className="crumbs">
          <Link to="/">Topics</Link> / <Link to={`/t/${topicId}`}>Back to topic</Link>
        </p>
        <h1>{p.content.title}</h1>
        <p className="lede">{p.content.summary}</p>
        {reviewed && (
          <p className="provenance">
            Drafted with Azure OpenAI from Microsoft Learn, reviewed by {p.review?.by} on {reviewed}.
          </p>
        )}
      </header>
      <PageBody page={p.content} />
    </div>
  );
}
