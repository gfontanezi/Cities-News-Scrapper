# ============================================================
# config.py — Configurações centralizadas do Cities News Scrapper
# ============================================================

# --- Filtro Temporal ---
# Quantidade de dias para buscar notícias (7 = última semana)
SEARCH_PERIOD_DAYS = 7

# --- Rate Limiting / Delay Adaptativo ---
# Delay inicial entre requisições (em segundos)
BASE_DELAY = 1.0

# Delay máximo (teto do backoff)
MAX_DELAY = 10.0

# Fator de multiplicação quando ocorre falha/bloqueio
BACKOFF_FACTOR = 2.0

# Fator de redução quando volta a ter sucesso (diminui o delay gradualmente)
RECOVERY_FACTOR = 0.8

# --- Caminhos ---
# Arquivo com a lista de cidades
CITIES_FILE = "cidades.json"

# Diretório e extensão de saída dos relatórios (formato CSV para a IA corporativa)
OUTPUT_DIR = "output"

# --- Google News RSS ---
# Template da URL do Google News RSS
# {query} = termo de busca URL-encoded
# {when} = filtro temporal (ex: "7d" para 7 dias)
# hl=pt-BR e gl=BR garantem resultados em português do Brasil
GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?"
    "q={query}+when:{when}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
)

# --- Matriz de Palavras-Chave ---
# Cada categoria contém uma lista de termos de busca.
# O script irá agrupar os termos de cada categoria em uma única busca usando
# o operador OR, reduzindo o número total de requisições ao Google News.
# Para cada cidade e categoria, a query será: "NomeCidade" (Termo1 OR Termo2 OR ...)
#
# Categorias focadas no que realmente impacta a operação de mobilidade:
#   - Concorrência: apps grandes + termos genéricos que capturam apps locais/regionais
#   - Clima: eventos climáticos que travam a cidade
#   - Legislação: apenas regulação de transporte/mobilidade/aplicativos (não crime)
#   - Eventos: shows, provas, jogos e qualquer evento que gere pico de demanda
SEARCH_QUERIES = {
    "Concorrência": [
        "Uber",
        "inDrive",
        "aplicativo de transporte",
        "aplicativo de corrida",
        "motorista de aplicativo",
    ],
    "Clima": [
        "chuva",
        "alagamento",
        "temporal",
        "enchente",
    ],
    "Legislação": [
        "regulamentação transporte aplicativo",
        "lei motorista aplicativo",
        "decreto transporte",
        "tarifa aplicativo",
        "regulamentação autônomo",
        "locadora veículos regulamentação",
    ],
    "Eventos": [
        "show",
        "festival",
        "evento",
        "vestibular",
        "concurso público",
        "jogo futebol",
        "feriado municipal",
        "greve transporte",
    ],
}

# --- Filtro de Relevância ---
# Após coletar uma notícia, o título e resumo devem conter ao menos
# UMA dessas palavras para ser considerada relevante.
# Isso elimina notícias genéricas que o Google News retorna por
# proximidade geográfica mas sem relação com mobilidade/operação.
# (A busca é case-insensitive)
RELEVANCE_KEYWORDS = {
    "Concorrência": [
        "uber", "indrive", "in drive", "99", "99app",
        "aplicativo", "app", "corrida", "motorista",
        "passageiro", "viagem", "tarifa", "desconto",
        "promoção", "concorrente", "concorrência",
        "plataforma", "mobilidade",
    ],
    "Clima": [
        "chuva", "alagamento", "temporal", "enchente",
        "inundação", "tempestade", "vendaval", "granizo",
        "ciclone", "tromba", "dilúvio", "nível do rio",
        "deslizamento", "alerta", "defesa civil",
    ],
    "Legislação": [
        "regulamentação", "regulação", "lei", "decreto",
        "tarifa", "legislação", "autônomo", "locadora",
        "aplicativo", "transporte", "motorista", "plataforma",
        "vereador", "câmara", "prefeitura", "projeto de lei",
        "sanção", "veículo", "cnh", "alvará", "licença",
    ],
    "Eventos": [
        "show", "festival", "evento", "vestibular", "enem",
        "concurso", "prova", "jogo", "futebol", "partida",
        "feriado", "greve", "paralisação", "manifestação",
        "carnaval", "réveillon", "festa", "congresso", "feira",
        "exposição", "arena", "estádio", "ingresso", "público",
        "milhares", "multidão",
    ],
}

