# Pipeline de dados

## Fontes e escopo

| Fonte | Uso | Cobertura alvo |
|---|---|---|
| ANAC/SIROS | oferta programada e assentos previstos | mar/2018–dez/2025 |
| ANAC/VRA | horários previstos/reais e situação do voo | jan/2018–dez/2025 |
| ANAC/Dados Estatísticos | passageiros agregados por mês, empresa e rota | importação manual oficial |
| INMET | observações meteorológicas horárias | jan/2018–dez/2025 |

A fase operacional inicial inclui somente voos domésticos regulares de passageiros,
identificados pelo tipo de linha `N`. Voos de carga, militares, não regulares e
internacionais não entram nessa camada.

## Execução reproduzível

```bash
python -m coletores.collect_vra --start-month 2018-01 --end-month 2025-12 --workers 2
python -m coletores.build_vra
python -m coletores.collect_inmet --start-year 2018 --end-year 2025
python -m coletores.build_weather
```

Para passageiros, faça o download interativo no portal oficial e execute:

```bash
python -m coletores.import_anac_statistics --source-file CAMINHO_DO_CSV_OFICIAL
python -m coletores.build_passenger_impact
```

O projeto não tenta contornar bloqueios, autenticação ou controles do portal.

## Camadas locais

```text
data/raw/       arquivos originais e manifestos SHA-256
data/staging/   normalizações intermediárias
data/curated/   Parquets consumidos pela API
```

Esses diretórios são ignorados pelo Git. Downloads são gravados em arquivo temporário
e promovidos atomicamente somente após conclusão. Reexecuções aproveitam arquivos já
validados.

## Regras operacionais

- `antecipado`: diferença menor que zero;
- `pontual`: de 0 a 9 minutos;
- `atraso_10_19`, `atraso_20_29`, `atraso_30_39`, `atraso_40_49`, `atraso_50_59`;
- `atraso_60_89`, `atraso_90_119` e `atraso_critico_120_mais`;
- `cancelado`: somente situação oficial cancelada;
- `nao_informado`: situação ou horários insuficientes.

As faixas são mutuamente exclusivas. Os contadores 10+, 30+, 60+, 90+ e 120+ são
indicadores cumulativos derivados de `departure_delay_minutes`.

## Meteorologia

Cada aeroporto é associado à estação INMET mais próxima dentro de 50 km. As leituras
horárias são agregadas por aeroporto e mês. A API calcula associações descritivas com
atrasos e cancelamentos; nenhum resultado deve ser apresentado como causa comprovada.

## Experimento de machine learning

O classificador experimental usa apenas voos realizados, domésticos e regulares,
com alvo `departure_delay_minutes >= 30`. O treino e a avaliação são separados no
tempo para evitar que observações futuras sejam usadas na validação:

```bash
pip install -r requirements-ml.txt
python -m ml.train_delay_model --train-rows 120000 --test-rows 50000
```

- treino: 2018, 2019, 2022 e 2023;
- teste: 2024 e 2025;
- fora das entradas: horário realizado, atraso calculado, situação, justificativa e faixa final;
- avaliação: ROC-AUC, precisão média, acurácia balanceada, precisão, recall, F1 e Brier score;
- interpretação de variáveis: importância por permutação no conjunto de teste.

A meteorologia é agregada com observações do mês completo. Portanto, o experimento
é retrospectivo e não pode ser apresentado como inferência disponível antes do voo.

Os anos pandêmicos de 2020 e 2021 não entram no treino. O processamento limita o
DuckDB a 2 GB e dois threads, e a importância usa no máximo 5 mil linhas. O modelo
e as métricas ficam sob `data/` e não são versionados.

O processo completo, os hiperparâmetros e a interpretação das métricas estão em
[Machine learning aplicado à análise de atrasos](machine-learning.md).

## Validação antes de publicar

```bash
pytest
cd frontend
npm run build
```

Também verifique `/api/v1/data-quality`, cobertura mensal, tipos de linha presentes,
duplicidades operacionais e ausência de segredos no conteúdo versionado.
