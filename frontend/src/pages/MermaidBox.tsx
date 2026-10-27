import React, { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

let mid = 0;
mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  flowchart: { curve: "basis", useMaxWidth: true },
  themeVariables: {
    fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif',
    fontSize: "12px",
  },
});

/** Mermaid渲染盒: 代码 → SVG */
const MermaidBox: React.FC<{ code: string }> = ({ code }) => {
  const [svg, setSvg] = useState<string>("");
  const [err, setErr] = useState<string>("");
  const idRef = useRef(`mm-${++mid}`);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { svg } = await mermaid.render(idRef.current, code);
        if (alive) { setSvg(svg); setErr(""); }
      } catch (e) {
        if (alive) setErr(String(e));
      }
    })();
    return () => { alive = false; };
  }, [code]);

  if (err) {
    return (
      <div style={{ fontSize: 11.5, color: "#94a3b8", background: "#f8fafc",
                    border: "1px dashed #e2e8f0", borderRadius: 10, padding: 12 }}>
        Mermaid渲染失败: {err.slice(0, 120)}
      </div>
    );
  }
  if (!svg) {
    return <div style={{ fontSize: 12, color: "#94a3b8", padding: 12 }}>Mermaid渲染中…</div>;
  }
  return (
    <div className="mermaid-box"
         style={{ border: "1px solid #eef2f7", borderRadius: 10, padding: 8,
                  background: "#fff", overflow: "auto", maxHeight: 420 }}
         dangerouslySetInnerHTML={{ __html: svg }} />
  );
};

export default MermaidBox;
