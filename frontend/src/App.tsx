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

const initial = { start_month: "2025-01", end_month: "2025-12", market: "domestic", airline: "", origin: "", destination: "" };
const number = new Intl.NumberFormat("pt-BR");

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
  const [status, setStatus] = useState("Carregando dados...");
  const query = useMemo(() => params(filters), [filters]);

  useEffect(() => {
    fetch("/api/v1/filters").then(r => r.json()).then(setOptions).catch(() => undefined);
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
  }, [query]);

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
      <aside className="method"><strong>Como ler estes números</strong><p>Os dados representam serviços programados. Assentos previstos não são passageiros transportados, e a presença de uma etapa não comprova que o voo ocorreu.</p></aside>
    </main>
    <footer>Fonte: Agência Nacional de Aviação Civil · Dados de programação SIROS</footer>
  </div>;
}
