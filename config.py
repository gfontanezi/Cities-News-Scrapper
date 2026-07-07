# ============================================================
# config.py — Configurações centralizadas do Cities News Scrapper
# Versão 2.0 — Filtros Profissionais
# ============================================================

# --- Filtro Temporal ---
SEARCH_PERIOD_DAYS = 7

# --- Rate Limiting / Delay Adaptativo ---
BASE_DELAY = 1.5
MAX_DELAY = 10.0
BACKOFF_FACTOR = 2.0
RECOVERY_FACTOR = 0.8

# --- Caminhos ---
CITIES_FILE = "cidades.json"
OUTPUT_DIR = "output"

# --- Google News RSS ---
GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?"
    "q={query}+when:{when}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
)

# ============================================================
# QUERIES DE BUSCA
# ============================================================
# Cada categoria agrupa termos com OR para minimizar requisições.
# Foco cirúrgico: apenas o que gera insight operacional para a 99.
SEARCH_QUERIES = {
    "Concorrência": [
        "Uber",
        "inDrive",
        "aplicativo de transporte",
        "motorista de aplicativo",
    ],
    "Legislação & Regulação": [
        "regulamentação aplicativo transporte",
        "lei motorista aplicativo",
        "decreto transporte aplicativo",
        "tarifa aplicativo transporte",
        "regulamentação locadora veículos",
    ],
    "Clima Severo": [
        "alagamento",
        "enchente",
        "temporal interdição",
        "deslizamento",
    ],
    "Eventos de Grande Porte": [
        "show lotado",
        "festival ingressos",
        "vestibular",
        "greve ônibus",
        "paralisação transporte",
    ],
    "Governo (fonte oficial)": [
        "aplicativo transporte site:gov.br",
        "motorista aplicativo site:gov.br",
        "regulamentação aplicativo site:leg.br",
        "decreto transporte site:gov.br",
    ],
}

# ============================================================
# FILTRO DE RELEVÂNCIA (whitelist pós-coleta)
# ============================================================
# Para cada categoria, a notícia DEVE conter ao menos UMA dessas
# palavras no título+resumo para ser aceita. Case-insensitive.
RELEVANCE_KEYWORDS = {
    "Concorrência": [
        "uber", "indrive", "99", "99app", "aplicativo",
        "motorista de app", "corrida", "tarifa", "desconto",
        "concorrente", "mobilidade", "passageiro",
    ],
    "Legislação & Regulação": [
        "regulamentação", "regulação", "projeto de lei", "decreto",
        "câmara", "prefeitura", "sanção", "alvará", "licença",
        "aplicativo", "locadora", "transporte por aplicativo",
    ],
    "Clima Severo": [
        "alagamento", "enchente", "temporal", "interdição",
        "deslizamento", "defesa civil", "bloqueio", "inundação",
    ],
    "Eventos de Grande Porte": [
        "show", "festival", "vestibular", "enem", "greve",
        "paralisação", "manifestação", "arena", "estádio",
        "ingresso", "lotado", "esgotado",
    ],
    "Governo (fonte oficial)": [
        "aplicativo", "transporte", "motorista", "decreto",
        "regulamentação", "projeto de lei", "sanção", "tarifa",
        "prefeitura", "câmara", "locadora",
    ],
}

# ============================================================
# BLACKLIST — Descarte automático de ruídos
# ============================================================
# Se o título+resumo contiver QUALQUER uma dessas palavras,
# a notícia é descartada IMEDIATAMENTE, mesmo que tenha keywords
# relevantes. Ordem: blacklist roda ANTES do filtro de relevância.
BLACKLIST_KEYWORDS = [
    # --- Crimes e Violência ---
    "assassinato", "homicídio", "morte", "morre", "morreu", "faleceu",
    "tiroteio", "tiros", "tráfico", "polícia", "policial",
    "prisão", "preso", "presa", "delegacia", "delegado",
    "crime", "criminoso", "roubo", "furto", "assalto",
    "estupro", "violência", "vítima", "suspeito", "flagrante",
    "esfaqueado", "cadáver", "corpo encontrado",
    "sequestro", "feminicídio", "latrocínio",
    # --- Fofocas e Celebridades ---
    "fofoca", "famoso", "famosa", "celebridade",
    "atriz", "ator", "cantor", "cantora",
    "namoro", "separação", "casamento",
    "filha de", "filho de", "ex-marido", "ex-mulher",
    "novela", "bbb", "reality", "big brother",
    # --- Política Partidária (não regulatória) ---
    "impeachment", "cpi", "corrupção", "lava jato",
    "bolsonaro", "lula", "eleição", "eleições",
    "partido", "deputado federal", "senador",
    # --- Esporte Genérico (resultado, não evento) ---
    "placar", "gol de", "campeonato",
    "seleção brasileira", "copa do mundo",
    # --- Outros Ruídos ---
    "receita de", "culinária", "dieta",
    "horóscopo", "signo", "previsão astral",
    "obituário", "velório", "enterro",
    "golpe", "fraude", "pirâmide",
    "pornografia", "nude",
]

# ============================================================
# FILTRO DE LOCALIDADE — Garantir que é notícia do Brasil
# ============================================================
# Se o título+resumo contiver essas palavras, é provável que a
# notícia NÃO seja do Brasil (ex: Lagos = Portugal/Nigéria).
# Descartada automaticamente.
FOREIGN_INDICATORS = [
    "portugal", "lisboa", "porto alegre" if False else "",  # placeholder
    "nigéria", "nigeria", "africa", "áfrica",
    "estados unidos", "eua", "usa",
    "china", "japão", "japan", "taiwan",
    "índia", "india",
    "argentina", "colômbia", "colombia",
    "europa", "ásia", "asia",
    "hanói", "hanoi", "tóquio", "tokyo",
    "new york", "london", "londres", "paris", "madrid",
    "algarve", "faro", "portimão",
]
# Limpar strings vazias do placeholder
FOREIGN_INDICATORS = [x for x in FOREIGN_INDICATORS if x]

# ============================================================
# DEDUPLICAÇÃO GLOBAL — Evitar a mesma notícia em várias cidades
# ============================================================
# Notícias nacionais (ex: "Uber lança recurso em todo Brasil")
# aparecem repetidas para cada cidade buscada. Ativar deduplicação
# global por título normalizado elimina essas repetições.
ENABLE_GLOBAL_DEDUP = True
