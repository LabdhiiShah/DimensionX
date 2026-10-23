// Collapsed by default - handy when Unity rejects something.
export default function ActivityLog({ log }) {
  return (
    <details className="activity">
      <summary>Activity log ({log.length})</summary>
      {log.length === 0
        ? <div className="activity-empty">Nothing yet.</div>
        : log.map(entry => (
          <div key={entry.id} className={'activity-entry ' + entry.kind}>
            <span className="t">{entry.time}</span><span>{entry.text}</span>
          </div>
        ))}
    </details>
  );
}
