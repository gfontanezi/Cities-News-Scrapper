#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cities News Scrapper v2.0 — Coletor Profissional de Notícias Hiper-Locais
==========================================================================
Desenvolvido para o time de Operações da 99.
Coleta notícias via Google News RSS, aplica filtros em camadas
(blacklist → localidade → relevância → deduplicação global) e exporta
um CSV limpo pronto para consumo pela IA corporativa.

Uso:
    python scrapper.py
"""

import csv
import json
import os
import re
import sys
import time
import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser

from config import (
    SEARCH_PERIOD_DAYS,
    BASE_DELAY,
    MAX_DELAY,
    BACKOFF_FACTOR,
    RECOVERY_FACTOR,
    CITIES_FILE,
    OUTPUT_DIR,
    GOOGLE_NEWS_RSS_URL,
    SEARCH_QUERIES,
    RELEVANCE_KEYWORDS,
    BLACKLIST_KEYWORDS,
    FOREIGN_INDICATORS,
    ENABLE_GLOBAL_DEDUP,
)

# ============================================================
# Logging
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
# Funções de Texto e Normalização
# ============================================================

def normalize_text(text: str) -> str:
    """Remove acentos e converte para minúsculas para comparação."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_text.lower().strip()


def clean_html(raw: str) -> str:
    """Remove tags HTML e entidades, retornando texto limpo."""
    clean = re.sub(r"<[^>]+>", "", raw)
    clean = clean.replace("&nbsp;", " ").replace("&amp;", "&")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def normalize_title_for_dedup(title: str) -> str:
    """
    Normaliza título para deduplicação global.
    Remove o nome do portal (tudo após o último ' - '), acentos e pontuação.
    Ex: 'Uber lança recurso no Brasil - G1' → 'uber lanca recurso no brasil'
    """
    # Remove sufixo do portal
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]
    # Remove pontuação e normaliza
    title = re.sub(r"[^\w\s]", "", title)
    return normalize_text(title)


# ============================================================
# Funções de Carregamento
# ============================================================

def load_cities(filepath: str) -> list[str]:
    """Carrega a lista de cidades a partir do arquivo JSON."""
    if not os.path.exists(filepath):
        logger.error(f"Arquivo de cidades não encontrado: {filepath}")
        logger.error("Crie o arquivo cidades.json com uma lista de cidades.")
        sys.exit(1)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            cities = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao ler JSON de cidades: {e}")
        sys.exit(1)

    if not isinstance(cities, list) or len(cities) == 0:
        logger.error("O arquivo cidades.json deve conter uma lista não-vazia de cidades.")
        sys.exit(1)

    logger.info(f"📋 {len(cities)} cidades carregadas de '{filepath}'")
    return cities


# ============================================================
# Funções de URL e RSS
# ============================================================

def build_rss_url(city: str, search_term: str) -> str:
    """Monta a URL do Google News RSS com busca exata por cidade."""
    query = f'"{city}" {search_term}'
    encoded_query = quote(query)
    when = f"{SEARCH_PERIOD_DAYS}d"
    return GOOGLE_NEWS_RSS_URL.format(query=encoded_query, when=when)


def build_grouped_query(terms: list[str]) -> str:
    """
    Agrupa termos de busca com OR, tratando termos compostos e operador site:.
    Ex: ['Uber', 'aplicativo de transporte', 'motorista site:gov.br']
    → '(Uber OR "aplicativo de transporte" OR (motorista site:gov.br))'
    """
    parts = []
    for t in terms:
        if " site:" in t:
            term_part, site_part = t.split(" site:", 1)
            site_part = f"site:{site_part}"
            if " " in term_part:
                term_part = f'"{term_part}"'
            parts.append(f"({term_part} {site_part})")
        elif " " in t:
            parts.append(f'"{t}"')
        else:
            parts.append(t)
    return f"({' OR '.join(parts)})"


def parse_published_date(entry) -> str | None:
    """Extrai a data de publicação como ISO 8601."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (ValueError, TypeError):
            pass
    if hasattr(entry, "published") and entry.published:
        return entry.published
    return None


def is_within_period(entry, cutoff_date: datetime) -> bool:
    """Verifica se a notícia está dentro da janela temporal."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt >= cutoff_date
        except (ValueError, TypeError):
            pass
    return True


# ============================================================
# Pipeline de Filtros (executados em ordem)
# ============================================================

def is_blacklisted(text: str) -> bool:
    """FILTRO 1: Rejeita notícias com palavras da blacklist."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in BLACKLIST_KEYWORDS)


def is_foreign(text: str) -> bool:
    """FILTRO 2: Rejeita notícias que parecem ser de outros países."""
    text_normalized = normalize_text(text)
    return any(indicator in text_normalized for indicator in
               [normalize_text(fi) for fi in FOREIGN_INDICATORS])


def is_relevant(text: str, category: str) -> bool:
    """FILTRO 3: Aceita apenas notícias com keywords da categoria."""
    keywords = RELEVANCE_KEYWORDS.get(category)
    if not keywords:
        return True
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def identify_matched_term(text: str, terms: list[str]) -> str:
    """Identifica qual termo original deu match na notícia."""
    text_lower = text.lower()
    for term in terms:
        # Limpa o operador site: para comparação
        clean_term = term.split(" site:")[0] if " site:" in term else term
        if clean_term.lower() in text_lower:
            return clean_term
    return terms[0].split(" site:")[0] if terms else "—"


# ============================================================
# Coleta Principal
# ============================================================

def fetch_news_for_category(
    city: str,
    category: str,
    terms: list[str],
    seen_links: set,
    global_titles: set,
    cutoff_date: datetime,
    current_delay: float,
) -> tuple[list[dict], float, dict]:
    """
    Busca notícias para uma cidade+categoria e aplica todos os filtros.
    Retorna (notícias_aceitas, delay_atualizado, contadores_de_filtro).
    """
    query_str = build_grouped_query(terms)
    url = build_rss_url(city, query_str)

    news_items = []
    stats = {"blacklisted": 0, "foreign": 0, "irrelevant": 0, "duplicate": 0, "accepted": 0}

    try:
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            logger.warning(
                f"  ⚠️  Feed com erro para '{city} / {category}' "
                f"— backoff para {min(current_delay * BACKOFF_FACTOR, MAX_DELAY):.1f}s"
            )
            current_delay = min(current_delay * BACKOFF_FACTOR, MAX_DELAY)
            return news_items, current_delay, stats

        for entry in feed.entries:
            if not is_within_period(entry, cutoff_date):
                continue

            link = entry.get("link", "")
            if link in seen_links:
                continue
            seen_links.add(link)

            title = entry.get("title", "Sem título")
            summary = clean_html(entry.get("summary", ""))
            full_text = f"{title} {summary}"

            # --- FILTRO 1: Blacklist ---
            if is_blacklisted(full_text):
                stats["blacklisted"] += 1
                continue

            # --- FILTRO 2: Notícia estrangeira ---
            if is_foreign(full_text):
                stats["foreign"] += 1
                continue

            # --- FILTRO 3: Relevância para a categoria ---
            if not is_relevant(full_text, category):
                stats["irrelevant"] += 1
                continue

            # --- FILTRO 4: Deduplicação global por título ---
            if ENABLE_GLOBAL_DEDUP:
                norm_title = normalize_title_for_dedup(title)
                if norm_title in global_titles:
                    stats["duplicate"] += 1
                    continue
                global_titles.add(norm_title)

            # --- ACEITA: Notícia passou em todos os filtros ---
            matched = identify_matched_term(full_text, terms)

            # Limpa o nome do portal do título para o CSV
            clean_title = title.rsplit(" - ", 1)[0] if " - " in title else title

            news_items.append({
                "titulo": clean_title,
                "fonte": title.rsplit(" - ", 1)[1].strip() if " - " in title else "—",
                "link": link,
                "resumo_google": summary,
                "categoria": category,
                "query": matched,
                "data_publicacao": parse_published_date(entry),
            })
            stats["accepted"] += 1

        # Recovery de delay
        if current_delay > BASE_DELAY:
            new_delay = max(current_delay * RECOVERY_FACTOR, BASE_DELAY)
            if new_delay < current_delay:
                logger.info(f"  ✅ Recovery — delay reduzido para {new_delay:.1f}s")
            current_delay = new_delay

    except Exception as e:
        logger.error(f"  ❌ Erro ao buscar '{city} / {category}': {e}")
        current_delay = min(current_delay * BACKOFF_FACTOR, MAX_DELAY)

    return news_items, current_delay, stats


# ============================================================
# Exportação CSV
# ============================================================

def save_results(results: list[dict], output_dir: str) -> str:
    """Salva resultados em CSV com codificação UTF-8-SIG (compatível Excel/IA)."""
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(output_dir, f"relatorio_{today}.csv")

    headers = [
        "cidade", "categoria", "query_termo", "titulo",
        "fonte", "link", "resumo_google", "data_publicacao",
    ]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter=",")
        writer.writeheader()

        for city_data in results:
            cidade = city_data["cidade"]
            for news in city_data["noticias"]:
                writer.writerow({
                    "cidade": cidade,
                    "categoria": news["categoria"],
                    "query_termo": news["query"],
                    "titulo": news["titulo"],
                    "fonte": news["fonte"],
                    "link": news["link"],
                    "resumo_google": news["resumo_google"],
                    "data_publicacao": news["data_publicacao"] or "",
                })

    return filepath


# ============================================================
# Função Principal
# ============================================================

def main():
    logger.info("=" * 65)
    logger.info("🚀 Cities News Scrapper v2.0 — Coleta Profissional")
    logger.info("=" * 65)

    cities = load_cities(CITIES_FILE)

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=SEARCH_PERIOD_DAYS)
    logger.info(f"📅 Período: últimos {SEARCH_PERIOD_DAYS} dias (desde {cutoff_date.strftime('%d/%m/%Y')})")

    total_categories = len(SEARCH_QUERIES)
    total_queries = len(cities) * total_categories
    logger.info(f"🔍 Queries planejadas: {len(cities)} cidades × {total_categories} categorias = {total_queries}")
    logger.info(f"🛡️  Filtros ativos: Blacklist → Localidade → Relevância → Dedup Global\n")

    # Estado global
    current_delay = BASE_DELAY
    global_titles = set()  # Deduplicação global por título
    results = []

    # Contadores globais
    totals = {"accepted": 0, "blacklisted": 0, "foreign": 0, "irrelevant": 0, "duplicate": 0}
    cities_with_news = 0

    start_time = time.time()

    for idx, city in enumerate(cities, 1):
        logger.info(f"🏙️  [{idx}/{len(cities)}] {city}")

        city_news = []
        seen_links = set()

        for category, terms in SEARCH_QUERIES.items():
            news_items, current_delay, stats = fetch_news_for_category(
                city=city,
                category=category,
                terms=terms,
                seen_links=seen_links,
                global_titles=global_titles,
                cutoff_date=cutoff_date,
                current_delay=current_delay,
            )

            # Acumular contadores
            for k in totals:
                totals[k] += stats.get(k, 0)

            if news_items:
                city_news.extend(news_items)
                filtered_total = stats["blacklisted"] + stats["foreign"] + stats["irrelevant"] + stats["duplicate"]
                logger.info(
                    f"    📰 {category}: {len(news_items)} aceita(s)"
                    + (f" | {filtered_total} filtrada(s)" if filtered_total else "")
                )

            time.sleep(current_delay)

        results.append({
            "cidade": city,
            "total_noticias": len(city_news),
            "noticias": city_news,
        })

        if city_news:
            cities_with_news += 1
            logger.info(f"    ✅ Total: {len(city_news)} notícia(s) relevante(s)\n")
        else:
            logger.info(f"    ⚪ Sem notícias relevantes\n")

    # Salvar
    filepath = save_results(results, OUTPUT_DIR)
    elapsed = time.time() - start_time

    # Resumo
    total_filtered = totals["blacklisted"] + totals["foreign"] + totals["irrelevant"] + totals["duplicate"]

    logger.info("=" * 65)
    logger.info("📊 RESUMO DA COLETA v2.0")
    logger.info("=" * 65)
    logger.info(f"  🏙️  Cidades processadas:    {len(cities)}")
    logger.info(f"  ✅ Cidades com notícias:    {cities_with_news}")
    logger.info(f"  📰 Notícias ACEITAS:        {totals['accepted']}")
    logger.info(f"  🚫 Total filtradas:         {total_filtered}")
    logger.info(f"      ├─ Blacklist (crime):   {totals['blacklisted']}")
    logger.info(f"      ├─ Estrangeiras:        {totals['foreign']}")
    logger.info(f"      ├─ Irrelevantes:        {totals['irrelevant']}")
    logger.info(f"      └─ Duplicadas (global): {totals['duplicate']}")
    logger.info(f"  ⏱️  Tempo total:             {elapsed:.1f}s")
    logger.info(f"  💾 Relatório:               {filepath}")
    logger.info("=" * 65)


if __name__ == "__main__":
    main()
