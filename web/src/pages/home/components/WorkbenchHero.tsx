type WorkbenchHeroProps = {
  powerBalance: number | string;
  logsTotal: number | string;
  modelTotal: number | string;
};

export function WorkbenchHero({
  powerBalance,
  logsTotal,
  modelTotal,
}: WorkbenchHeroProps) {
  return (
    <section className="home-panel workbench-hero">
      <div className="workbench-hero-copy">
        {/* <span className="workbench-kicker">Workbench</span> */}
        <h1>控制台</h1>
      </div>

      <div className="workbench-summary-grid">
        <article className="workbench-summary-card">
          <span>算力</span>
          <strong>{powerBalance}</strong>
        </article>
        <article className="workbench-summary-card">
          <span>模型</span>
          <strong>{modelTotal}</strong>
        </article>
        <article className="workbench-summary-card">
          <span>请求</span>
          <strong>{logsTotal}</strong>
        </article>
      </div>
    </section>
  );
}
