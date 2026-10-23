import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis
} from "recharts";

type Summary = {
  scheduled_departures: number;
  planned_seats: number;
  origin_airports: number;
  active_routes: number;
  active_airlines: number;
};
type Series = { month: string; scheduled_departures: number; planned_seats: number };
type Rank = { code: string; scheduled_departures: number; planned_seats: number };
type Options = { airlines: string[]; origins: string[]; destinations: string[]; service_types: string[] };
type DelaySummary = {
  scheduled_flights: number; operated_flights: number; cancelled_flights: number;
  punctuality_percent: number | null; average_delay_minutes: number | null;
  median_delay_minutes: number | null; delayed_10_plus: number; delayed_30_plus: number;
  delayed_60_plus: number; delayed_90_plus: number; delayed_120_plus: number;
};
type DelayBucket = { bucket: string; flights: number };
type DelaySeries = {
  month: string; scheduled_flights: number; operated_flights: number;
  cancelled_flights: number; delayed_30_plus: number; average_delay_minutes: number | null;
};
type PassengerImpact = {
  impacted_flights: number; matched_flights: number; coverage_percent: number | null;
  estimated_paid_passengers: number | null; estimated_total_passengers: number | null;
  estimated: true; method: string; limitations: string;
};
type WeatherCorrelation = {
  airport_month_observations: number; airports: number; average_station_distance_km: number | null;
  delay_precipitation_correlation: number | null; delay_wind_gust_correlation: number | null;
  cancellation_precipitation_correlation: number | null; causal: false; interpretation: string;
};
type MachineLearningAnalysis = {
  status: "experimental";
  model: string;
  objective: string;
  generated_at_utc: string;
  library: string;
  scope: string;
  sampling: { train_rows: number; test_rows: number; train_years: number[]; test_years: number[] };
  target: { name: string; test_positive_rate: number };
  metrics: { roc_auc: number; average_precision: number; balanced_accuracy: number; precision: number; recall: number; f1: number; brier_score: number };
  top_features: { feature: string; importance: number }[];
  limitations: string[];
};

const initial = {
  start_month: "2025-01", end_month: "2025-12", market: "domestic",
  regularity: "all", airline: "", origin: "", destination: ""
};
const number = new Intl.NumberFormat("pt-BR");
const correlationPercent = new Intl.NumberFormat("pt-BR", {
  style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1
});

function params(filters: typeof initial) {
  const value = new URLSearchParams();
  Object.entries(filters).forEach(([key, item]) => item && value.set(key, item));
  return value.toString();
}

export function App() {
  const [draft, setDraft] = useState(initial);
  const [filters, setFilters] = useState(initial);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [series, setSeries] = useState<Series[]>([]);
  const [airports, setAirports] = useState<Rank[]>([]);
  const [options, setOptions] = useState<Options>({ airlines: [], origins: [], destinations: [], service_types: [] });
  const [delaySummary, setDelaySummary] = useState<DelaySummary | null>(null);
  const [delayBuckets, setDelayBuckets] = useState<DelayBucket[]>([]);
  const [delaySeries, setDelaySeries] = useState<DelaySeries[]>([]);
  const [delayAvailable, setDelayAvailable] = useState(true);
  const [passengerImpact, setPassengerImpact] = useState<PassengerImpact | null>(null);
  const [weatherCorrelation, setWeatherCorrelation] = useState<WeatherCorrelation | null>(null);
  const [machineLearning, setMachineLearning] = useState<MachineLearningAnalysis | null>(null);
  const [status, setStatus] = useState("Carregando dados...");
  const query = useMemo(() => params(filters), [filters]);
  const operationalQuery = useMemo(() => params({ ...filters, market: "domestic", regularity: "regular" }), [filters]);
  const operationalScopeAvailable = filters.regularity !== "non_regular";

  useEffect(() => {
    fetch("/api/v1/filters").then(r => r.json()).then(setOptions).catch(() => undefined);
    fetch("/api/v1/ml/delay-analysis").then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setMachineLearning).catch(() => setMachineLearning(null));
  }, []);

  useEffect(() => {
    setStatus("Atualizando análise...");
    Promise.all([
      fetch(`/api/v1/summary?${query}`).then(r => { if (!r.ok) throw new Error(); return r.json(); }),
      fetch(`/api/v1/timeseries?${query}`).then(r => r.json()),
      fetch(`/api/v1/airports?${query}&limit=12`).then(r => r.json())
    ]).then(([nextSummary, nextSeries, nextAirports]) => {
      setSummary(nextSummary); setSeries(nextSeries); setAirports(nextAirports); setStatus("");
    }).catch(() => setStatus("Não foi possível carregar a análise. Verifique a API e tente novamente."));

    if (!operationalScopeAvailable) {
      setDelaySummary(null); setDelayBuckets([]); setDelaySeries([]); setDelayAvailable(false);
      setPassengerImpact(null); setWeatherCorrelation(null);
    } else {
      Promise.all([
        fetch(`/api/v1/delays/summary?${operationalQuery}`).then(r => { if (!r.ok) throw new Error(); return r.json(); }),
        fetch(`/api/v1/delays/buckets?${operationalQuery}`).then(r => { if (!r.ok) throw new Error(); return r.json(); }),
        fetch(`/api/v1/delays/timeseries?${operationalQuery}`).then(r => { if (!r.ok) throw new Error(); return r.json(); })
      ]).then(([nextSummary, nextBuckets, nextSeries]) => {
        setDelaySummary(nextSummary); setDelayBuckets(nextBuckets); setDelaySeries(nextSeries); setDelayAvailable(true);
      }).catch(() => {
        setDelaySummary(null); setDelayBuckets([]); setDelaySeries([]); setDelayAvailable(false);
      });
      fetch(`/api/v1/passengers/impacted?${operationalQuery}`)
        .then(r => { if (!r.ok) throw new Error(); return r.json(); })
        .then(setPassengerImpact).catch(() => setPassengerImpact(null));
      fetch(`/api/v1/weather/correlation?${operationalQuery}`)
        .then(r => { if (!r.ok) throw new Error(); return r.json(); })
        .then(setWeatherCorrelation).catch(() => setWeatherCorrelation(null));
    }
  }, [query, operationalQuery, operationalScopeAvailable]);

  function submit(event: FormEvent) { event.preventDefault(); setFilters(draft); }
  function update(name: string, value: string) { setDraft(current => ({ ...current, [name]: value })); }

  return <div className="page">
    <header className="hero">
      <div><span className="eyebrow">ANAC · SIROS</span><h1>Malha Aérea Brasileira</h1><p>Uma leitura da oferta programada de voos e assentos no Brasil.</p></div>
      <div className="source-pill"><span>Base atual</span><strong>mar/2018 — dez/2025</strong></div>
    </header>

    <form className="filters" onSubmit={submit}>
      <label>Mês inicial<input type="month" min="2018-03" max="2025-12" value={draft.start_month} onChange={e => update("start_month", e.target.value)} /></label>
      <label>Mês final<input type="month" min="2018-03" max="2025-12" value={draft.end_month} onChange={e => update("end_month", e.target.value)} /></label>
      <label>Mercado<select value={draft.market} onChange={e => update("market", e.target.value)}><option value="all">Todos</option><option value="domestic">Doméstico</option><option value="international">Internacional</option></select></label>
      <label>Origem<select value={draft.origin} onChange={e => update("origin", e.target.value)}><option value="">Todos</option>{options.origins.map(x => <option key={x}>{x}</option>)}</select></label>
      <label>Destino<select value={draft.destination} onChange={e => update("destination", e.target.value)}><option value="">Todos</option>{options.destinations.map(x => <option key={x}>{x}</option>)}</select></label>
      <label>Regularidade do serviço<select value={draft.regularity} onChange={e => update("regularity", e.target.value)}><option value="all">Todos</option><option value="regular">Regular — operação programada</option><option value="non_regular">Não regular</option></select></label>
      <label>Companhia<select value={draft.airline} onChange={e => update("airline", e.target.value)}><option value="">Todas</option>{options.airlines.map(x => <option key={x}>{x}</option>)}</select></label>
      <button type="submit">Aplicar filtros</button>
    </form>

    {status && <div className="status" role="status">{status}</div>}
    <main>
      <section className="cards" aria-label="Indicadores principais">
        {[
          ["Decolagens programadas", summary?.scheduled_departures], ["Assentos previstos", summary?.planned_seats],
          ["Aeroportos de origem", summary?.origin_airports], ["Rotas ativas", summary?.active_routes],
          ["Companhias", summary?.active_airlines]
        ].map(([label, value]) => <article className="card" key={String(label)}><span>{label}</span><strong>{value == null ? "—" : number.format(Number(value))}</strong></article>)}
      </section>

      <section className="chart-grid">
        <article className="panel wide"><div className="panel-title"><div><span>Evolução mensal</span><h2>Oferta programada</h2></div><small>Decolagens e assentos previstos</small></div>
          <div className="chart"><ResponsiveContainer><LineChart data={series}><CartesianGrid strokeDasharray="3 3" stroke="#dce3e8"/><XAxis dataKey="month"/><YAxis yAxisId="left"/><YAxis yAxisId="right" orientation="right"/><Tooltip formatter={(value) => number.format(Number(value ?? 0))}/><Legend/><Line yAxisId="left" type="monotone" dataKey="scheduled_departures" name="Decolagens" stroke="#085c6b" strokeWidth={3} dot={false}/><Line yAxisId="right" type="monotone" dataKey="planned_seats" name="Assentos" stroke="#e56b2f" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></div>
        </article>
        <article className="panel"><div className="panel-title"><div><span>Ranking</span><h2>Aeroportos de origem</h2></div></div>
          <div className="chart"><ResponsiveContainer><BarChart data={airports} layout="vertical" margin={{left: 8}}><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number"/><YAxis dataKey="code" type="category" width={50}/><Tooltip formatter={(value) => number.format(Number(value ?? 0))}/><Bar dataKey="scheduled_departures" name="Decolagens" fill="#085c6b" radius={[0,4,4,0]}/></BarChart></ResponsiveContainer></div>
        </article>
      </section>
      <section className="section-heading">
        <span>ANAC · VRA · ESCOPO DOMÉSTICO</span><h2>Pontualidade e cancelamentos</h2>
        <p>Cancelamentos refletem a situação oficial do VRA. Atrasos de duas horas ou mais permanecem classificados como atrasos críticos.</p>
      </section>
      {!delayAvailable ? <div className="status">{filters.regularity === "non_regular" ? "Indicadores VRA indisponíveis para serviços não regulares no escopo atual." : "A base VRA ainda não foi processada para este ambiente."}</div> : <>
        <section className="cards delay-cards" aria-label="Indicadores de pontualidade">
          {[
            ["Voos realizados", delaySummary?.operated_flights == null ? null : number.format(delaySummary.operated_flights)],
            ["Pontualidade", delaySummary?.punctuality_percent == null ? null : `${number.format(delaySummary.punctuality_percent)}%`],
            ["Cancelamentos", delaySummary?.cancelled_flights == null ? null : number.format(delaySummary.cancelled_flights)],
            ["Atrasos 30+ min", delaySummary?.delayed_30_plus == null ? null : number.format(delaySummary.delayed_30_plus)],
            ["Atrasos 120+ min", delaySummary?.delayed_120_plus == null ? null : number.format(delaySummary.delayed_120_plus)]
          ].map(([label, value]) => <article className="card" key={String(label)}><span>{label}</span><strong>{value ?? "—"}</strong></article>)}
        </section>
        <section className="chart-grid">
          <article className="panel"><div className="panel-title"><div><span>Distribuição</span><h2>Faixas de atraso</h2></div></div>
            <div className="chart"><ResponsiveContainer><BarChart data={delayBuckets}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="bucket" angle={-30} textAnchor="end" height={90}/><YAxis/><Tooltip formatter={(value) => number.format(Number(value ?? 0))}/><Bar dataKey="flights" name="Voos" fill="#e56b2f" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div>
          </article>
          <article className="panel"><div className="panel-title"><div><span>Evolução</span><h2>Atrasos e cancelamentos</h2></div></div>
            <div className="chart"><ResponsiveContainer><LineChart data={delaySeries}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="month"/><YAxis/><Tooltip formatter={(value) => number.format(Number(value ?? 0))}/><Legend/><Line type="monotone" dataKey="delayed_30_plus" name="Atrasos 30+" stroke="#e56b2f" strokeWidth={3}/><Line type="monotone" dataKey="cancelled_flights" name="Cancelados" stroke="#8b3149" strokeWidth={2}/></LineChart></ResponsiveContainer></div>
          </article>
        </section>
      </>}
      {operationalScopeAvailable && <section className="insight-grid">
        <article className="panel insight-panel">
          <div className="panel-title"><div><span>Estimativa</span><h2>Passageiros impactados</h2></div></div>
          {passengerImpact ? <>
            <strong className="insight-value">{passengerImpact.estimated_paid_passengers == null ? "—" : number.format(passengerImpact.estimated_paid_passengers)}</strong>
            <p>Passageiros pagos estimados · cobertura de {passengerImpact.coverage_percent == null ? "—" : `${number.format(passengerImpact.coverage_percent)}%`} dos voos impactados.</p>
            <small>{passengerImpact.limitations}</small>
          </> : <p className="muted">Aguardando a importação dos Dados Estatísticos oficiais da ANAC.</p>}
        </article>
        <article className="panel insight-panel">
          <div className="panel-title"><div><span>Associação</span><h2>Meteorologia e atrasos</h2></div></div>
          {weatherCorrelation ? <>
            <strong className="insight-value">{weatherCorrelation.delay_precipitation_correlation == null ? "—" : correlationPercent.format(weatherCorrelation.delay_precipitation_correlation)}</strong>
            <p>Associação linear entre precipitação mensal e percentual de voos com atraso de 30 minutos ou mais.</p>
            <small>Coeficiente de correlação × 100. Não representa percentual de atrasos nem impacto causal. {weatherCorrelation.interpretation}</small>
          </> : <p className="muted">Aguardando o processamento dos históricos oficiais do INMET.</p>}
        </article>
      </section>}
      <section className="panel ml-panel" aria-labelledby="ml-title">
        <div className="panel-title">
          <div><span>Experimento de machine learning</span><h2 id="ml-title">Análise de atrasos com HistGradientBoosting Scikit-Learn</h2></div>
          <small>Modelo demonstrativo · não operacional</small>
        </div>
        {machineLearning ? <>
          <p className="ml-objective">{machineLearning.objective} {machineLearning.scope}</p>
          <div className="ml-metrics">
            <div><span>ROC-AUC</span><strong>{correlationPercent.format(machineLearning.metrics.roc_auc)}</strong><small>Capacidade de ordenar voos com e sem atraso.</small></div>
            <div><span>Precisão média</span><strong>{correlationPercent.format(machineLearning.metrics.average_precision)}</strong><small>Linha de base: {correlationPercent.format(machineLearning.target.test_positive_rate)}.</small></div>
            <div><span>Recall</span><strong>{correlationPercent.format(machineLearning.metrics.recall)}</strong><small>Parcela dos atrasos 30+ identificada no corte de 50%.</small></div>
            <div><span>Amostra</span><strong>{number.format(machineLearning.sampling.train_rows)}</strong><small>Treino; {number.format(machineLearning.sampling.test_rows)} registros no teste temporal.</small></div>
          </div>
          <div className="ml-details">
            <div>
              <h3>Variáveis com maior contribuição preditiva</h3>
              <ol className="feature-list">{machineLearning.top_features.slice(0, 6).map(item =>
                <li key={item.feature}><span>{item.feature}</span><small>{item.importance.toLocaleString("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</small></li>
              )}</ol>
            </div>
            <div className="ml-caveat">
              <h3>Como interpretar</h3>
              <p>Treino em {machineLearning.sampling.train_years.join(", ")} e teste fora da amostra em {machineLearning.sampling.test_years.join("–")}. A importância por permutação mede contribuição ao modelo, não causa do atraso.</p>
              <p><strong>Limite:</strong> {machineLearning.limitations[0]}</p>
              <a href="/metodologia#machine-learning">Ver metodologia do modelo</a>
            </div>
          </div>
        </> : <p className="muted">O experimento de machine learning ainda não foi processado neste ambiente.</p>}
      </section>
      <aside className="method methodology">
        <div className="method-title"><span>Metodologia</span><strong>Critérios e nomenclaturas adotados</strong></div>
        <dl>
          <div><dt>Serviço regular</dt><dd>Operação ofertada conforme programação previamente publicada ou como série sistemática de voos.</dd></div>
          <div><dt>Serviço não regular</dt><dd>Serviço de transporte aéreo público que não se caracteriza como regular.</dd></div>
          <div><dt>Operação doméstica</dt><dd>Etapa realizada entre aeroportos situados no território nacional.</dd></div>
          <div><dt>Etapa e decolagem programada</dt><dd>Trecho entre origem e destino registrado no SIROS; o registro não comprova que o voo ocorreu.</dd></div>
          <div><dt>Realizado e cancelado</dt><dd>Situações oficiais informadas no VRA. Atraso de 120+ minutos permanece atraso crítico, não cancelamento.</dd></div>
          <div><dt>Pontualidade e atraso</dt><dd>Critério analítico: pontual de 0 a 9 minutos; atrasos em faixas de 10–19, 20–29, 30–39, 40–49, 50–59, 60–89, 90–119 e 120+ minutos.</dd></div>
          <div><dt>Assentos e passageiros</dt><dd>Assentos previstos representam capacidade programada. Passageiros impactados, quando disponíveis, são estimativas mensais.</dd></div>
          <div><dt>Meteorologia</dt><dd>Associação estatística por aeroporto/mês; não demonstra que o clima causou o atraso.</dd></div>
          <div><dt>Horários</dt><dd>O SIROS usa UTC. Os horários VRA são preservados conforme informados pela fonte, sem conversão implícita.</dd></div>
        </dl>
        <a href="/metodologia">Ver metodologia completa</a>
      </aside>
    </main>
    <footer>Fonte: Agência Nacional de Aviação Civil · Dados de programação SIROS-VAR, PI-IV Univesp 2026.</footer>
  </div>;
}
