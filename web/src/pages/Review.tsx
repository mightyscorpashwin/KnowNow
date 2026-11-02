import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useLoad } from "../hooks";
import { formatDateTime } from "../format";
import type { RunStatus, Topic } from "../types";

const DONE = new Set(["Completed", "Failed", "Terminated"]);

function GenerateForm({ onFinished }: { onFinished: () => void }) {
  const topics = useLoad(() => api.topics(), []);
  const [topicId, setTopicId] = useState("cloud");
  const [subtopicId, setSubtopicId] = useState("");
  const [detail, setDetail] = useState<Topic | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.topic(topicId).then(setDetail).catch(() => setDetail(null));
    setSubtopicId("");
  }, [topicId]);

  useEffect(() => {
    if (!runId) return;
    const timer = window.setInterval(async () => {
      try {
        const s = await api.runStatus(runId);
        setRun(s);
        if (DONE.has(s.status)) {
          window.clearInterval(timer);
          onFinished();
        }
      } catch (e) {
        setError((e as Error).message);
        window.clearInterval(timer);
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [runId, onFinished]);

  async function start(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setRun(null);
    try {
      const { instanceId } = await api.generate({ topicId, subtopicId: subtopicId || undefined });
      setRunId(instanceId);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const running = runId !== null && !(run && DONE.has(run.status));

  return (
    <form className="generate" onSubmit={start}>
      <h2>Draft new pages</h2>
      <p>Pulls current Microsoft Learn pages and drafts them for review. Drafting a sub-topic takes a few minutes.</p>
      <div className="generate-fields">
        <label>
          Topic
          <select value={topicId} onChange={(e) => setTopicId(e.target.value)}>
            {topics.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Sub-topic
          <select value={subtopicId} onChange={(e) => setSubtopicId(e.target.value)}>
            <option value="">All sub-topics marked for drafting</option>
            {detail?.subtopics.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="primary" disabled={running}>
          {running ? "Drafting…" : "Draft pages"}
        </button>
      </div>
      {run?.customStatus && !DONE.has(run.status) && (
        <p role="status">
          {run.customStatus.done} of {run.customStatus.total} pages drafted
        </p>
      )}
      {run && DONE.has(run.status) && run.output && (
        <p role="status">
          Finished: {run.output.drafted} of {run.output.total} drafted
          {run.output.errors.length > 0 && `, ${run.output.errors.length} failed`}.
        </p>
      )}
      {run?.status === "Failed" && <p className="error">The run failed. Check Application Insights for details.</p>}
      {error && <p className="error">{error}</p>}
    </form>
  );
}

export default function Review() {
  const drafts = useLoad(() => api.drafts(), []);
  const waiting = useMemo(() => drafts.data?.filter((d) => d.status === "draft") ?? [], [drafts.data]);
  const rejected = useMemo(() => drafts.data?.filter((d) => d.status === "rejected") ?? [], [drafts.data]);

  return (
    <>
      <header className="topic-head">
        <h1>Review</h1>
        <p className="lede">Nothing reaches readers until a reviewer approves it.</p>
      </header>

      <GenerateForm onFinished={drafts.reload} />

      <section className="draft-list">
        <h2>Waiting for review ({waiting.length})</h2>
        {drafts.loading && <p className="notice">Loading drafts…</p>}
        {drafts.error && <p className="notice error">{drafts.error}</p>}
        {!drafts.loading && waiting.length === 0 && <p className="notice">No drafts waiting. Draft pages above.</p>}
        <ul>
          {waiting.map((d) => (
            <li key={d.id}>
              <Link to={`/review/${d.topicId}/${d.pageId}`}>{d.title || d.pageId}</Link>
              <span className="meta">
                {d.subtopicId} / {d.areaName}
                {d.generatedAt && `, drafted ${formatDateTime(d.generatedAt)}`}
              </span>
              {!d.checks.passed && <span className="flag">Failed {d.checks.problems.length} checks</span>}
            </li>
          ))}
        </ul>
        {rejected.length > 0 && (
          <>
            <h2>Rejected ({rejected.length})</h2>
            <ul>
              {rejected.map((d) => (
                <li key={d.id}>
                  <Link to={`/review/${d.topicId}/${d.pageId}`}>{d.title || d.pageId}</Link>
                  <span className="meta">
                    {d.subtopicId} / {d.areaName}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}
