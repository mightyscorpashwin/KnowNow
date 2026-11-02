import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import PageBody from "../components/PageBody";
import { useLoad } from "../hooks";
import { formatDateTime, plural } from "../format";
import { topicColor } from "../topicColors";

export default function ReviewDraft() {
  const { topicId = "", pageId = "" } = useParams();
  const navigate = useNavigate();
  const draft = useLoad(() => api.draft(topicId, pageId), [topicId, pageId]);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (draft.loading) return <p className="notice">Loading draft…</p>;
  if (draft.error || !draft.data) return <p className="notice error">{draft.error ?? "Draft not found."}</p>;
  const d = draft.data;

  async function act(kind: "approve" | "reject") {
    setBusy(true);
    setError(null);
    try {
      if (kind === "approve") await api.approve(topicId, pageId);
      else await api.reject(topicId, pageId, comment);
      navigate("/review");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div style={{ ["--topic" as string]: topicColor(topicId) }}>
      <header className="page-head">
        <p className="crumbs">
          <Link to="/review">Review</Link>
        </p>
        <h1>{d.content.title}</h1>
        <p className="lede">{d.content.summary}</p>
      </header>

      <aside className="review-panel" aria-label="Review this draft">
        <div className={d.checks.passed ? "checks ok" : "checks bad"}>
          {d.checks.passed ? (
            <p>All automated checks passed.</p>
          ) : (
            <>
              <p>Automated checks found {plural(d.checks.problems.length, "problem", "problems")}:</p>
              <ul>
                {d.checks.problems.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </>
          )}
        </div>
        <p className="meta">
          Drafted {formatDateTime(d.generation.generatedAt)} with deployment “{d.generation.model}”, prompt{" "}
          {d.generation.promptVersion}. Built from {plural(d.generation.fetchedSources.length, "Microsoft Learn page", "Microsoft Learn pages")}.
        </p>
        {d.status === "rejected" && d.review && (
          <p className="meta">
            Rejected by {d.review.by}
            {d.review.comment ? `: “${d.review.comment}”` : "."}
          </p>
        )}
        <label className="comment">
          Reason (needed to reject)
          <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} />
        </label>
        <div className="review-actions">
          <button type="button" className="primary" disabled={busy} onClick={() => act("approve")}>
            Approve and publish
          </button>
          <button type="button" disabled={busy || !comment.trim()} onClick={() => act("reject")}>
            Reject
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </aside>

      <PageBody page={d.content} />
    </div>
  );
}
