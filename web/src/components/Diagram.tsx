import { useEffect, useId, useState } from "react";

let initialised = false;

/** Renders Mermaid source to SVG. Falls back to showing the source. */
export default function Diagram({ source, caption }: { source: string; caption: string }) {
  const id = "d" + useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        if (!initialised) {
          mermaid.initialize({
            startOnLoad: false,
            securityLevel: "strict",
            theme: "base",
            fontFamily: "IBM Plex Sans, system-ui, sans-serif",
            themeVariables: {
              primaryColor: "#FFFFFF",
              primaryBorderColor: "#1B2A2F",
              primaryTextColor: "#1B2A2F",
              lineColor: "#56707A",
              fontSize: "14px",
            },
          });
          initialised = true;
        }
        const { svg } = await mermaid.render(id, source);
        if (alive) setSvg(svg);
      } catch {
        if (alive) setFailed(true);
      }
    })();
    return () => {
      alive = false;
    };
  }, [id, source]);

  return (
    <figure className="diagram">
      {svg && <div className="diagram-canvas" dangerouslySetInnerHTML={{ __html: svg }} />}
      {failed && <pre className="diagram-source">{source}</pre>}
      {!svg && !failed && <div className="diagram-canvas placeholder">Drawing diagram…</div>}
      <figcaption>{caption}</figcaption>
    </figure>
  );
}
