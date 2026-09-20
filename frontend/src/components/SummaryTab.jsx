import { Disclaimer, Empty, ResourceView } from "./Status";

export default function SummaryTab({ resource, load }) {
  return (
    <ResourceView
      resource={resource}
      load={load}
      loadingText="Reading your document and writing a plain-English summary. This can take up to 30 seconds."
    >
      {(data) => (
        <div>
          <h2>Simple Language Summary</h2>
          <p className="lead">{data.overview}</p>

          <h3>Key Sections</h3>
          <div>
            {data.sections.map((s, i) => (
              <details key={i} className="acc-item" open={i === 0}>
                <summary>{s.title}</summary>
                <p>{s.explanation}</p>
              </details>
            ))}
          </div>

          <h3>Important Obligations</h3>
          {data.key_obligations.length ? (
            <ul className="bullets">
              {data.key_obligations.map((o, i) => (
                <li key={i}>{o}</li>
              ))}
            </ul>
          ) : (
            <Empty text="No specific obligations were identified." />
          )}

          <h3>Important Dates</h3>
          {data.key_dates.length ? (
            <ul className="date-list">
              {data.key_dates.map((d, i) => (
                <li key={i}>
                  <strong>{d.date}</strong> - {d.description}
                </li>
              ))}
            </ul>
          ) : (
            <Empty text="No dates were found in this document." />
          )}

          <Disclaimer text={data.disclaimer} />
        </div>
      )}
    </ResourceView>
  );
}