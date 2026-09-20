import { Disclaimer, Empty, ResourceView } from "./Status";

export default function RiskTab({ resource, load }) {
  return (
    <ResourceView
      resource={resource}
      load={load}
      loadingText="Scanning the document for important clauses. This can take up to 30 seconds."
    >
      {(data) => {
        const counts = { high: 0, medium: 0, low: 0 };
        data.risks.forEach((r) => {
          counts[r.risk_level] += 1;
        });
        return (
          <div>
            <h2>Potential Risks &amp; Important Clauses</h2>
            {data.risks.length === 0 ? (
              <Empty text="No clauses were flagged as especially important." />
            ) : (
              <>
                <p className="hint">
                  {counts.high} high · {counts.medium} medium · {counts.low} low.
                  These are AI-generated and may miss clauses, so read the full document too.
                </p>
                {data.risks.map((r, i) => (
                  <article key={i} className={`risk-card ${r.risk_level}`}>
                    <div className="risk-head">
                      <span className={`badge ${r.risk_level}`}>{r.risk_level.toUpperCase()}</span>
                      <span className="risk-section">{r.section_reference}</span>
                    </div>
                    <blockquote className="excerpt">{r.clause_excerpt}</blockquote>
                    <p><strong>Why it matters:</strong> {r.why_it_matters}</p>
                  </article>
                ))}
              </>
            )}
            <Disclaimer text={data.disclaimer} />
          </div>
        );
      }}
    </ResourceView>
  );
}