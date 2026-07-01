# Cities News Scrapper 🏙️📰

Coletor automatizado de notícias hiper-locais para 100+ cidades brasileiras, usando Google News RSS. Projetado para alimentar a IA interna da 99 com dados brutos estruturados sobre eventos que impactam a operação de mobilidade.

## Pré-requisitos

- Python 3.x
- pip

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

### 1. Lista de Cidades

Edite o arquivo `cidades.json` com suas cidades:

```json
[
  "São Paulo",
  "Rio de Janeiro",
  "Belo Horizonte",
  "Porto Alegre",
  "..."
]
```

### 2. Parâmetros (opcional)

Edite `config.py` para ajustar:

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `SEARCH_PERIOD_DAYS` | `7` | Janela temporal de busca (dias) |
| `BASE_DELAY` | `1.0` | Delay inicial entre requisições (segundos) |
| `MAX_DELAY` | `10.0` | Delay máximo em caso de bloqueio |
| `BACKOFF_FACTOR` | `2.0` | Multiplicador de backoff |
| `SEARCH_QUERIES` | *ver arquivo* | Matriz de palavras-chave por categoria |

## Execução

```bash
python scrapper.py
```

O relatório será salvo em: `output/relatorio_YYYY-MM-DD.csv`

## Formato de Saída (CSV)

O arquivo de saída é gerado com vírgula (`,`) como delimitador e codificação `UTF-8-SIG` para compatibilidade total com ferramentas de IA e análise de dados.

As colunas do arquivo CSV são:

1. `cidade`: Nome da cidade pesquisada.
2. `categoria`: Categoria operacional (Concorrência, Clima, Legislação, Eventos).
3. `query_termo`: Palavra-chave específica que deu match na notícia.
4. `titulo`: Título da matéria de notícias.
5. `link`: Link original da matéria.
6. `resumo_google`: Resumo gerado pelo Google News (limpo de tags HTML).
7. `data_publicacao`: Data e hora da publicação em formato ISO 8601.

Exemplo de linhas do CSV:
```csv
cidade,categoria,query_termo,titulo,link,resumo_google,data_publicacao
Porto Alegre,Eventos,greve transporte,Sindicato anuncia greve de ônibus,https://...,Motoristas ameaçam paralisar linhas...,2026-06-28T14:30:00+00:00
Porto Alegre,Concorrência,inDrive,InDrive lança nova categoria,https://...,Campanha agressiva da concorrente...,2026-06-27T09:15:00+00:00
```

## Categorias de Busca Ativas

- **Concorrência**: Uber, inDrive, aplicativo de transporte, aplicativo de corrida, motorista de aplicativo
- **Clima**: chuva, alagamento, temporal, enchente
- **Legislação**: regulamentação transporte aplicativo, lei motorista aplicativo, decreto transporte, tarifa aplicativo, regulamentação autônomo, locadora veículos regulamentação
- **Eventos**: show, festival, evento, vestibular, concurso público, jogo futebol, feriado municipal, greve transporte

