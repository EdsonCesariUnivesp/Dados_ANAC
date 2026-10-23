const delayRanges = [
  ["Antecipado", "Partida realizada antes do horário previsto."],
  ["Pontual", "Partida realizada entre 0 e 9 minutos após o horário previsto."],
  ["Atraso", "Faixas exclusivas de 10–19, 20–29, 30–39, 40–49, 50–59, 60–89 e 90–119 minutos."],
  ["Atraso crítico", "Partida realizada com 120 minutos ou mais de atraso; não é convertida em cancelamento."],
  ["Cancelado", "Somente quando a situação oficial do VRA é CANCELADO."],
  ["Não informado", "Situação ou horários insuficientes para classificação."],
];

export function MethodologyPage() {
  return <div className="methodology-page">
    <header className="methodology-hero">
      <a className="back-link" href="/">← Voltar ao dashboard</a>
      <span className="eyebrow">ANAC · METODOLOGIA</span>
      <h1>Como os indicadores são calculados</h1>
      <p>Critérios, nomenclaturas, fontes e limitações usados na análise da malha aérea brasileira.</p>
    </header>

    <main className="methodology-content">
      <section className="methodology-section">
        <span className="section-kicker">Escopo</span>
        <h2>O que está sendo analisado</h2>
        <div className="definition-grid">
          <article><h3>Oferta programada</h3><p>Registros do SIROS entre março de 2018 e dezembro de 2025. Representam operações planejadas e assentos previstos, não a confirmação de que o voo ocorreu.</p></article>
          <article><h3>Operação realizada</h3><p>A camada VRA cobre inicialmente voos domésticos regulares de passageiros, tipo de linha <code>N</code>, entre janeiro de 2018 e dezembro de 2025.</p></article>
          <article><h3>Meteorologia</h3><p>Observações do INMET associadas ao aeroporto pela estação elegível mais próxima, dentro do limite metodológico de 50 km, e agregadas por mês.</p></article>
        </div>
      </section>

      <section className="methodology-section" id="machine-learning">
        <span className="section-kicker">Machine learning</span>
        <h2>Experimento de classificação de atrasos</h2>
        <p className="section-intro">O <code>HistGradientBoostingClassifier</code>, do scikit-learn, é usado em uma prova de conceito para estimar a probabilidade de atraso de partida de 30 minutos ou mais. O resultado é analítico e demonstrativo, não uma recomendação operacional.</p>
        <dl className="full-definitions">
          <div><dt>Treino</dt><dd>Amostra determinística de 120 mil voos de 2018, 2019, 2022 e 2023. Os anos de 2020 e 2021 foram excluídos do treino devido à ruptura operacional da pandemia.</dd></div>
          <div><dt>Teste temporal</dt><dd>50 mil voos de 2024 e 2025, não usados no ajuste, para reduzir uma avaliação excessivamente otimista.</dd></div>
          <div><dt>Variável-alvo</dt><dd>Voo realizado com atraso de partida igual ou superior a 30 minutos. Cancelamentos não integram o alvo.</dd></div>
          <div><dt>Variáveis explicativas</dt><dd>Empresa, origem, destino, assentos planejados, mês, dia da semana, hora prevista e meteorologia mensal observada.</dd></div>
          <div><dt>Prevenção de vazamento</dt><dd>Horário realizado, atraso final, situação e justificativa do voo não são fornecidos ao modelo. Como a meteorologia agrega o mês inteiro, o experimento é retrospectivo e não uma previsão em tempo real.</dd></div>
          <div><dt>Importância</dt><dd>Calculada por permutação no teste. Indica contribuição preditiva, não relação causal.</dd></div>
        </dl>
        <p>As métricas e o artefato são gerados fora da API. O ambiente publicado lê somente um JSON compacto, mantendo o container de produção sem scikit-learn.</p>
      </section>

      <section className="methodology-section">
        <span className="section-kicker">Nomenclaturas ANAC</span>
        <h2>Serviços e etapas</h2>
        <dl className="full-definitions">
          <div><dt>Serviço regular</dt><dd>Operação ofertada ao público conforme programação previamente publicada ou com regularidade que constitua uma série sistemática de voos identificável.</dd></div>
          <div><dt>Serviço não regular</dt><dd>Serviço de transporte aéreo público que não se caracteriza como serviço aéreo regular.</dd></div>
          <div><dt>Operação doméstica</dt><dd>Operação realizada exclusivamente entre aeroportos situados no território nacional.</dd></div>
          <div><dt>Operação internacional</dt><dd>Operação que envolve ao menos um aeroporto situado fora do território nacional.</dd></div>
          <div><dt>Etapa</dt><dd>Trecho direcional de um voo entre um aeroporto de origem e um aeroporto de destino.</dd></div>
          <div><dt>Decolagem programada</dt><dd>Etapa com origem e partida prevista válidas no SIROS. O registro não comprova realização.</dd></div>
        </dl>
      </section>

      <section className="methodology-section">
        <span className="section-kicker">Pontualidade</span>
        <h2>Classificação de atrasos e cancelamentos</h2>
        <p className="section-intro">O atraso de partida é a diferença, em minutos, entre a partida realizada e a partida prevista. As faixas abaixo são critérios analíticos do projeto.</p>
        <div className="criteria-table" role="table" aria-label="Faixas de atraso">
          {delayRanges.map(([name, description]) => <div role="row" key={name}><strong role="cell">{name}</strong><span role="cell">{description}</span></div>)}
        </div>
      </section>

      <section className="methodology-section">
        <span className="section-kicker">Indicadores</span>
        <h2>Como interpretar os valores</h2>
        <dl className="full-definitions">
          <div><dt>Assentos previstos</dt><dd>Capacidade programada da aeronave. Não representa passageiros efetivamente transportados.</dd></div>
          <div><dt>Passageiros impactados</dt><dd>Estimativa baseada na média mensal de passageiros por decolagem para a mesma empresa e rota. Não identifica ocupantes de um voo específico.</dd></div>
          <div><dt>Pontualidade</dt><dd>Percentual de voos realizados classificados como antecipados ou pontuais pelo critério do projeto.</dd></div>
          <div><dt>Correlação meteorológica</dt><dd>Coeficiente de correlação apresentado como percentual, calculado por aeroporto/mês. Não é percentual de atrasos e não demonstra causalidade.</dd></div>
          <div><dt>Rotas ativas</dt><dd>Pares direcionais distintos de origem e destino presentes no período filtrado.</dd></div>
          <div><dt>Horários</dt><dd>O SIROS utiliza UTC. Os horários VRA são preservados conforme informados pela fonte, sem conversão implícita.</dd></div>
        </dl>
      </section>

      <section className="methodology-section sources-section">
        <span className="section-kicker">Fontes</span>
        <h2>Dados e referências</h2>
        <ul>
          <li>ANAC/SIROS — registro de operações planejadas.</li>
          <li>ANAC/VRA — horários previstos, realizados e situação oficial dos voos.</li>
          <li>ANAC/Dados Estatísticos — passageiros e decolagens agregados, quando disponíveis.</li>
          <li>INMET — observações meteorológicas horárias.</li>
        </ul>
        <p>As fontes podem revisar dados históricos. Os resultados refletem os arquivos coletados e processados pelo projeto.</p>
      </section>

      <a className="return-button" href="/">Voltar ao dashboard</a>
    </main>
  </div>;
}
