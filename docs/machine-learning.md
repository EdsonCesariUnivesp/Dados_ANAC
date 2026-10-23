# Machine learning aplicado à análise de atrasos

## Objetivo

O projeto utiliza machine learning como experimento analítico para verificar se
características da programação do voo, da rota e do contexto meteorológico ajudam a
distinguir voos com maior propensão a atrasos de partida.

O problema foi formulado como uma **classificação binária**:

- classe `0`: atraso de partida inferior a 30 minutos;
- classe `1`: atraso de partida igual ou superior a 30 minutos.

O experimento não altera a classificação oficial dos voos, não converte atrasos em
cancelamentos e não deve ser utilizado para decisões operacionais.

## Escopo dos dados

Foram considerados registros da camada analítica VRA que atendem simultaneamente aos
seguintes critérios:

- voos domésticos regulares de passageiros, identificados pelo tipo de linha `N`;
- situação oficial `REALIZADO`;
- horário previsto de partida disponível;
- atraso calculado entre -360 e 1.440 minutos;
- existência de meteorologia mensal associada ao aeroporto de origem.

Cancelamentos ficaram fora da variável-alvo, pois um voo cancelado não possui o mesmo
processo de geração do atraso de um voo realizado.

## Preparação e amostragem

O DuckDB lê diretamente os Parquets curados e faz a junção entre os voos e a
meteorologia por aeroporto de origem, ano e mês. Para manter o processamento leve e
reproduzível, foi usada amostragem *reservoir* com sementes fixas.

| Conjunto | Período | Registros | Finalidade |
|---|---:|---:|---|
| Treino | 2018, 2019, 2022 e 2023 | 120.000 | ajuste do modelo |
| Teste temporal | 2024 e 2025 | 50.000 | avaliação fora da amostra |

Os anos de 2020 e 2021 foram excluídos do treino por representarem uma ruptura
operacional excepcional causada pela pandemia. A divisão por tempo, em vez de uma
divisão aleatória de todos os anos, reduz o risco de uma avaliação artificialmente
otimista.

Durante a extração, o DuckDB é limitado a 2 GB de memória e dois *threads*. Esses
limites tornam a execução adequada a uma máquina com 4 CPUs e 8 GB de RAM.

## Variáveis utilizadas

### Categóricas

- código ICAO da companhia aérea;
- aeroporto ICAO de origem;
- aeroporto ICAO de destino.

Valores ausentes são preenchidos pela categoria mais frequente. Em seguida, as
categorias são transformadas com `OrdinalEncoder`. Categorias que aparecem somente no
teste recebem o código `-1`, permitindo avaliar rotas ou empresas não vistas no treino.

### Numéricas

- quantidade de assentos planejados;
- mês do ano;
- dia da semana;
- hora prevista de partida;
- precipitação mensal;
- horas com chuva;
- temperatura média;
- velocidade média do vento;
- rajada máxima;
- umidade média;
- pressão média.

Mês, dia da semana e hora são variáveis cíclicas. Por isso, cada uma é representada
por seno e cosseno. Essa transformação preserva relações como dezembro estar próximo
de janeiro e 23h estar próximo de 0h. Valores numéricos ausentes são preenchidos pela
mediana calculada no conjunto de treino.

Não são fornecidos ao modelo o horário realizado, o atraso final, a situação, a
justificativa ou a faixa de atraso. Esses campos revelariam direta ou indiretamente o
resultado que se deseja classificar.

## Algoritmo

Foi escolhido o `HistGradientBoostingClassifier`, da biblioteca scikit-learn. O
algoritmo constrói uma sequência de árvores de decisão, em que cada nova árvore busca
corrigir parte dos erros das anteriores. Sua implementação baseada em histogramas é
eficiente para conjuntos tabulares e possui consumo de memória compatível com a VPS do
projeto.

Configuração usada:

| Parâmetro | Valor |
|---|---:|
| `learning_rate` | 0,08 |
| `max_iter` | 150 |
| `max_leaf_nodes` | 31 |
| `max_depth` | 7 |
| `min_samples_leaf` | 100 |
| `l2_regularization` | 1,0 |
| `class_weight` | `balanced` |
| `early_stopping` | habilitado |
| `validation_fraction` | 0,10 |
| `random_state` | 42 |

O balanceamento de classes recebe atenção porque atrasos de 30 minutos ou mais são
minoritários. O `class_weight="balanced"` aumenta a relevância dos exemplos positivos
durante o ajuste. O *early stopping* interrompe o crescimento quando a validação
interna deixa de melhorar, reduzindo custo e sobreajuste.

## Avaliação obtida

A execução atual produziu os seguintes resultados no teste temporal de 50 mil voos:

| Métrica | Resultado | Leitura |
|---|---:|---|
| Frequência real de atrasos 30+ | 8,13% | linha de base positiva |
| ROC-AUC | 62,56% | capacidade modesta de ordenação entre as classes |
| Precisão média | 12,77% | superior à linha de base de 8,13% |
| Acurácia balanceada | 58,59% | média do desempenho nas duas classes |
| Precisão no corte 0,5 | 11,53% | proporção de alertas que eram atrasos 30+ |
| Recall no corte 0,5 | 53,54% | parcela dos atrasos 30+ identificada |
| F1 | 18,97% | equilíbrio entre precisão e recall |
| Brier score | 0,2287 | erro quadrático das probabilidades |

A ROC-AUC acima de 50% e a precisão média acima da frequência positiva mostram que há
sinal preditivo nos dados. Entretanto, o desempenho é modesto e insuficiente para uso
operacional. O resultado atende ao objetivo de demonstrar uma aplicação real de
machine learning com avaliação transparente.

## Interpretação das variáveis

A contribuição das variáveis é calculada por importância de permutação em até 5 mil
registros do teste. Cada variável é embaralhada e mede-se a perda na precisão média.
As maiores contribuições observadas foram:

1. hora prevista de partida;
2. mês do ano;
3. aeroporto de origem;
4. assentos planejados;
5. aeroporto de destino;
6. precipitação mensal.

Importância preditiva não significa causalidade. Por exemplo, um aeroporto pode ser
relevante por concentrar rotas, horários, companhias ou condições operacionais que não
estão representadas individualmente no conjunto de dados.

## Limitações

- A amostragem foi intencionalmente reduzida para demonstração.
- O modelo foi avaliado para atrasos de 30 minutos ou mais, não para cada faixa de atraso.
- Cancelamentos não fazem parte da variável-alvo.
- A meteorologia é um agregado observado do mês completo. Parte dessas observações não
  estaria disponível antes da partida de cada voo; portanto, o experimento é
  retrospectivo e não uma previsão em tempo real.
- Não há calibração específica das probabilidades nem seleção de limiar orientada a um
  custo operacional.
- Mudanças na malha, nas empresas e nos procedimentos aeroportuários podem degradar o
  desempenho ao longo do tempo.

## Execução reproduzível

Crie o ambiente Python, instale as dependências específicas e execute:

```bash
pip install -r requirements-ml.txt
python -m ml.train_delay_model --train-rows 120000 --test-rows 50000
```

Entradas padrão:

```text
data/curated/flight_delay_analysis.parquet
data/curated/airport_weather.parquet
```

Saídas locais:

```text
data/models/delay_hgb.joblib
data/curated/delay_ml_metrics.json
```

Os dois artefatos ficam fora do Git. O arquivo Joblib contém o pipeline treinado. O
JSON contém somente métricas, períodos, tamanho das amostras, matriz de confusão,
variáveis relevantes e limitações.

## Integração com o dashboard

O treinamento não ocorre durante uma requisição HTTP. A API FastAPI lê o JSON de
métricas já produzido e o publica em:

```text
GET /api/v1/ml/delay-analysis
```

O frontend apresenta o resultado em um painel identificado como “Experimento de
machine learning”. A imagem de produção permanece leve porque não instala
scikit-learn; ela apenas consome o JSON montado no diretório de dados.

Fluxo resumido:

```text
ANAC/VRA + INMET
        ↓
Parquets curados
        ↓
amostragem e divisão temporal
        ↓
pré-processamento + HistGradientBoostingClassifier
        ↓
avaliação no período 2024–2025
        ↓
JSON de métricas → FastAPI → dashboard
```
