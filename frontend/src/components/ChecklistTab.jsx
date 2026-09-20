import { Disclaimer, Empty, ResourceView } from "./Status";

export default function ChecklistTab({ resource, load, checked, setChecked }) {
  const toggle = (key) => setChecked((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <ResourceView
      resource={resource}
      load={load}
      loadingText="Building your checklist from the document. This can take up to 30 seconds."
    >
      {(data) => (
        <div>
          <h2>Your Checklist</h2>

          <section className="check-group green">
            <h3>Action Items <span className="count">{data.action_items.length}</span></h3>
            {data.action_items.length ? (
              <ul className="check-list">
                {data.action_items.map((a, i) => {
                  const key = `a${i}`;
                  return (
                    <li key={key}>
                      <label className={checked[key] ? "done" : ""}>
                        <input
                          type="checkbox"
                          checked={!!checked[key]}
                          onChange={() => toggle(key)}
                        />
                        <span>
                          {a.item} <span className="tag">{a.source_clause}</span>
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <Empty text="No action items were found." />
            )}
          </section>

          <section className="check-group purple">
            <h3>Key Dates <span className="count">{data.key_dates.length}</span></h3>
            {data.key_dates.length ? (
              <ul className="plain-list">
                {data.key_dates.map((d, i) => (
                  <li key={i}>
                    <span aria-hidden="true">📅</span>
                    <span>
                      <strong>{d.date}</strong> - {d.description}{" "}
                      <span className="tag">{d.source_clause}</span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty text="No dates were found in this document." />
            )}
          </section>

          <section className="check-group blue">
            <h3>
              Questions to Consider Asking a Lawyer{" "}
              <span className="count">{data.questions_for_lawyer.length}</span>
            </h3>
            {data.questions_for_lawyer.length ? (
              <ul className="plain-list">
                {data.questions_for_lawyer.map((q, i) => (
                  <li key={i}>
                    <span aria-hidden="true">❓</span>
                    <span>
                      {q.question} <span className="tag">{q.source_clause}</span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty text="No questions were suggested." />
            )}
          </section>

          <Disclaimer text={data.disclaimer} />
        </div>
      )}
    </ResourceView>
  );
}