function ReportPanel({ active, reportType, onReportTypeChange, onSendReport, reportMsg }) {
  return (
    <section className={`view ${active ? 'active' : ''}`} aria-hidden={!active} id="reports-card">
      <article className="card">
        <h2>Report Hazard / Incident</h2>
        <div className="body">
          <div className="controls">
            <select
              className="btn"
              style={{ padding: '.45rem .6rem' }}
              value={reportType}
              onChange={(e) => onReportTypeChange(e.target.value)}
            >
              <option value="accident">Accident</option>
              <option value="construction">Construction</option>
              <option value="hazard">Road hazard</option>
              <option value="blocked">Blocked parking</option>
            </select>
            <button className="btn" onClick={onSendReport}>Send report</button>
          </div>
          <div style={{ marginTop: '.6rem', color: 'var(--muted)' }}>{reportMsg}</div>
        </div>
      </article>
    </section>
  )
}

export default ReportPanel
