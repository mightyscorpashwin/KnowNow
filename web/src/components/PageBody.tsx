import Markdown from "react-markdown";
import type { PageContent } from "../types";
import Diagram from "./Diagram";
import Quiz from "./Quiz";

const SECTIONS = [
  ["overview", "Overview"],
  ["diagram", "Diagram"],
  ["concepts", "Key concepts"],
  ["compare", "Compared"],
  ["when", "When to use what"],
  ["pitfalls", "Common pitfalls"],
  ["quiz", "Check yourself"],
  ["sources", "Sources"],
] as const;

/** The fixed KnowNow page layout, shared by readers and reviewers. */
export default function PageBody({ page }: { page: PageContent }) {
  return (
    <div className="page-layout">
      <nav className="page-toc" aria-label="On this page">
        <ol>
          {SECTIONS.map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`}>{label}</a>
            </li>
          ))}
        </ol>
      </nav>

      <article className="page-body">
        <section id="overview">
          <h2>Overview</h2>
          <div className="prose">
            <Markdown>{page.overview}</Markdown>
          </div>
        </section>

        <section id="diagram">
          <h2>Diagram</h2>
          <Diagram source={page.diagram.mermaid} caption={page.diagram.caption} />
        </section>

        <section id="concepts">
          <h2>Key concepts</h2>
          <dl className="concepts">
            {page.keyConcepts.map((c) => (
              <div key={c.term}>
                <dt>{c.term}</dt>
                <dd>{c.explanation}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section id="compare">
          <h2>Compared</h2>
          <div className="table-wrap" tabIndex={0} role="region" aria-label={page.comparison.caption}>
            <table>
              <caption>{page.comparison.caption}</caption>
              <thead>
                <tr>
                  {page.comparison.columns.map((c) => (
                    <th key={c} scope="col">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {page.comparison.rows.map((row, i) => (
                  <tr key={i}>
                    {row.map((cell, j) =>
                      j === 0 ? (
                        <th key={j} scope="row">
                          {cell}
                        </th>
                      ) : (
                        <td key={j}>{cell}</td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section id="when">
          <h2>When to use what</h2>
          <ul className="when">
            {page.whenToUse.map((w) => (
              <li key={w.option}>
                <strong>{w.option}</strong>
                <span>{w.useWhen}</span>
              </li>
            ))}
          </ul>
        </section>

        <section id="pitfalls">
          <h2>Common pitfalls</h2>
          <ul className="pitfalls">
            {page.pitfalls.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </section>

        <section id="quiz">
          <h2>Check yourself</h2>
          <Quiz questions={page.quiz} />
        </section>

        <section id="sources">
          <h2>Sources</h2>
          <ul className="sources">
            {page.sources.map((s) => (
              <li key={s.url}>
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.title}
                </a>
              </li>
            ))}
          </ul>
        </section>
      </article>
    </div>
  );
}
