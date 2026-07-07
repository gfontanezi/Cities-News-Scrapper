# Cities News Scrapper v2.0 🏙️📰

Coletor profissional de notícias hiper-locais para 100+ cidades brasileiras, usando Google News RSS.
Projetado para alimentar a IA interna da **99** com dados limpos e operacionalmente relevantes sobre eventos que impactam a mobilidade urbana.

## Pré-requisitos

- Python 3.10+
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
  "..."
]
```

### 2. Parâmetros (opcional)

Edite `config.py` para ajustar:

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `SEARCH_PERIOD_DAYS` | `7` | Janela temporal de busca (dias) |
| `BASE_DELAY` | `1.5` | Delay entre requisições (segundos) |
| `MAX_DELAY` | `10.0` | Delay máximo em caso de bloqueio |
| `ENABLE_GLOBAL_DEDUP` | `True` | Deduplicação global por título |
| `SEARCH_QUERIES` | *ver arquivo* | Termos de busca por categoria |

## Execução

```bash
python scrapper.py
```

O relatório será salvo em: `output/relatorio_YYYY-MM-DD.csv`

## Pipeline de Filtros (4 Camadas)

Cada notícia coletada passa por **4 filtros em sequência**. Se falhar em qualquer um, é descartada:

```
Notícia bruta do Google News
    │
    ▼
┌─────────────────────────┐
│ 1. BLACKLIST             │  Crime, fofoca, celebridade, política partidária?
│    → Descartada           │  
└─────────────────────────┘
    │ Passou
    ▼
┌─────────────────────────┐
│ 2. LOCALIDADE            │  Notícia de outro país (Portugal, Nigéria, etc.)?
│    → Descartada           │
└─────────────────────────┘
    │ Passou
    ▼
┌─────────────────────────┐
│ 3. RELEVÂNCIA            │  Contém keywords operacionais da categoria?
│    → Descartada           │
└─────────────────────────┘
    │ Passou
    ▼
┌─────────────────────────┐
│ 4. DEDUPLICAÇÃO GLOBAL   │  Mesmo título já apareceu em outra cidade?
│    → Descartada           │
└─────────────────────────┘
    │ Passou
    ▼
  ✅ ACEITA no CSV final
```

## Formato de Saída (CSV)

Arquivo com vírgula (`,`) como delimitador e codificação `UTF-8-SIG`.

| Coluna | Descrição |
|--------|-----------|
| `cidade` | Cidade pesquisada |
| `categoria` | Categoria operacional |
| `query_termo` | Palavra-chave que deu match |
| `titulo` | Título limpo (sem nome do portal) |
| `fonte` | Nome do portal/veículo |
| `link` | Link original |
| `resumo_google` | Resumo do Google News |
| `data_publicacao` | Data ISO 8601 |

## Categorias de Busca

| Categoria | Foco | Fonte |
|-----------|------|-------|
| **Concorrência** | Uber, inDrive, apps locais | Google News |
| **Legislação & Regulação** | Leis de transporte por app, locadoras | Google News |
| **Clima Severo** | Alagamentos, enchentes, deslizamentos | Google News |
| **Eventos de Grande Porte** | Shows lotados, vestibulares, greves | Google News |
| **Governo (fonte oficial)** | Decretos e regulamentações | `site:gov.br` / `site:leg.br` |

## Exemplo de Log de Execução

```
🏙️  [1/100] São Paulo
    📰 Concorrência: 3 aceita(s) | 5 filtrada(s)
    📰 Legislação & Regulação: 1 aceita(s)
    📰 Clima Severo: 2 aceita(s) | 1 filtrada(s)
    ✅ Total: 6 notícia(s) relevante(s)

📊 RESUMO DA COLETA v2.0
  🏙️  Cidades processadas:    100
  ✅ Cidades com notícias:    67
  📰 Notícias ACEITAS:        234
  🚫 Total filtradas:         1847
      ├─ Blacklist (crime):   312
      ├─ Estrangeiras:        89
      ├─ Irrelevantes:        1204
      └─ Duplicadas (global): 242
```
