#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cities News Scrapper — Coletor de Notícias Hiper-Locais
========================================================
Script Python para varrer o Google News RSS em busca de notícias
operacionalmente relevantes para 100+ cidades brasileiras.

O output é um JSON estruturado que será consumido pela IA interna
da 99 para classificação e geração de insights de incentivo.

Uso:
    python scrapper.py
"""

import json
import os
import sys
import time
import logging
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
# Funções Auxiliares
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


def build_rss_url(city: str, search_term: str) -> str:
    """
    Monta a URL do Google News RSS para uma cidade + termo de busca.
    Usa aspas ao redor do nome da cidade para busca exata.
    """
    # Busca exata: "Nome da Cidade" + termo
    query = f'"{city}" {search_term}'
    encoded_query = quote(query)
    when = f"{SEARCH_PERIOD_DAYS}d"
    url = GOOGLE_NEWS_RSS_URL.format(query=encoded_query, when=when)
    return url


def parse_published_date(entry) -> str | None:
    """
    Extrai a data de publicação de uma entrada do feed RSS.
    Retorna string ISO 8601 ou None se não disponível.
    """
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (ValueError, TypeError):
            pass

    # Fallback: tentar o campo 'published' como string
    if hasattr(entry, "published") and entry.published:
        return entry.published

    return None


def is_within_period(entry, cutoff_date: datetime) -> bool:
    """
    Verifica se a notícia está dentro da janela temporal.
    Se não conseguir determinar a data, inclui a notícia por segurança.
    """
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt >= cutoff_date
        except (ValueError, TypeError):
            pass
    # Se não tem data, inclui por segurança (o Google News já filtra por 'when')
    return True


def clean_summary(raw_summary: str) -> str:
    """
    Limpa o resumo do Google News removendo tags HTML básicas.
    O feed RSS do Google News retorna resumos com tags <a>, <b>, etc.
    """
    import re
    # Remove tags HTML
    clean = re.sub(r"<[^>]+>", "", raw_summary)
    # Remove espaços extras
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def is_relevant(title: str, summary: str, category: str) -> bool:
    """
    Verifica se a notícia é relevante para a categoria.
    O título ou resumo deve conter ao menos UMA keyword de validação.
    Se a categoria não tiver keywords definidas, aceita tudo.
    """
    keywords = RELEVANCE_KEYWORDS.get(category)
    if not keywords:
        return True  # Sem filtro para essa categoria

    text = f"{title} {summary}".lower()
    return any(kw in text for kw in keywords)


def identify_matched_query(title: str, summary: str, terms: list[str]) -> str:
    """
    Identifica qual dos termos de busca deu match no título ou resumo.
    Se não for possível identificar, retorna uma string combinada ou o primeiro termo.
    """
    text = f"{title} {summary}".lower()
    for term in terms:
        if term.lower() in text:
            return term
    return terms[0] if terms else "Vários"


def fetch_news_for_category(
    city: str,
    category: str,
    terms: list[str],
    seen_links: set,
    cutoff_date: datetime,
    current_delay: float,
) -> tuple[list[dict], float, int]:
    """
    Busca notícias para uma categoria agrupando os termos de busca com OR.
    Retorna a lista de notícias (deduplicadas e filtradas),
    o delay atualizado e a quantidade de notícias descartadas por irrelevância.
    """
    # Agrupa termos: (termo1 OR termo2 OR termo3)
    # Termos com mais de uma palavra devem conter aspas no Google News se quisermos busca exata,
    # mas o Google RSS lida bem com termos simples. Vamos juntá-los com OR.
    grouped_terms = " OR ".join(f'"{t}"' if " " in t else t for t in terms)
    query_str = f"({grouped_terms})"
    
    url = build_rss_url(city, query_str)
    news_items = []
    filtered_count = 0

    try:
        feed = feedparser.parse(url)

        # Verificar se o feed retornou com sucesso
        if feed.bozo and not feed.entries:
            # Feed com erro e sem entradas → possível bloqueio
            logger.warning(
                f"  ⚠️  Feed com erro para '{city} + {category}' "
                f"— aumentando delay para {min(current_delay * BACKOFF_FACTOR, MAX_DELAY):.1f}s"
            )
            current_delay = min(current_delay * BACKOFF_FACTOR, MAX_DELAY)
            return news_items, current_delay, filtered_count

        for entry in feed.entries:
            # Filtrar por período
            if not is_within_period(entry, cutoff_date):
                continue

            link = entry.get("link", "")

            # Deduplicação por link
            if link in seen_links:
                continue
            seen_links.add(link)

            title = entry.get("title", "Sem título")
            summary = clean_summary(entry.get("summary", ""))

            # Filtro de relevância: verificar se a notícia é de fato sobre o tema
            if not is_relevant(title, summary, category):
                filtered_count += 1
                logger.debug(
                    f"    🚫 Descartada (irrelevante): {title[:80]}..."
                )
                continue

            # Identifica qual termo exato da lista deu match
            matched_term = identify_matched_query(title, summary, terms)

            # Extrair e estruturar a notícia
            news_item = {
                "titulo": title,
                "link": link,
                "resumo_google": summary,
                "categoria": category,
                "query": matched_term,
                "data_publicacao": parse_published_date(entry),
            }
            news_items.append(news_item)

        # Sucesso → recuperar delay gradualmente
        if current_delay > BASE_DELAY:
            new_delay = max(current_delay * RECOVERY_FACTOR, BASE_DELAY)
            if new_delay < current_delay:
                logger.info(f"  ✅ Sucesso — reduzindo delay para {new_delay:.1f}s")
            current_delay = new_delay

    except Exception as e:
        logger.error(f"  ❌ Erro ao buscar '{city} + {category}': {e}")
        current_delay = min(current_delay * BACKOFF_FACTOR, MAX_DELAY)
        logger.warning(f"  ⚠️  Aumentando delay para {current_delay:.1f}s")

    return news_items, current_delay, filtered_count


import csv

def save_results(results: list[dict], output_dir: str) -> str:
    """
    Salva os resultados em um arquivo CSV (flat table).
    Cada linha representa uma notícia com seus respectivos metadados.
    Usa 'utf-8-sig' para compatibilidade nativa com o Excel do Windows.
    """
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"relatorio_{today}.csv"
    filepath = os.path.join(output_dir, filename)

    # Campos que serão salvos na planilha
    headers = [
        "cidade",
        "categoria",
        "query_termo",
        "titulo",
        "link",
        "resumo_google",
        "data_publicacao"
    ]

    try:
        # utf-8-sig adiciona o BOM no início do arquivo, forçando o Excel a ler acentos corretamente
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=",")
            writer.writeheader()

            for city_data in results:
                cidade = city_data.get("cidade", "")
                for news in city_data.get("noticias", []):
                    writer.writerow({
                        "cidade": cidade,
                        "categoria": news.get("categoria", ""),
                        "query_termo": news.get("query", ""),
                        "titulo": news.get("titulo", ""),
                        "link": news.get("link", ""),
                        "resumo_google": news.get("resumo_google", ""),
                        "data_publicacao": news.get("data_publicacao", "")
                    })

    except Exception as e:
        logger.error(f"❌ Erro ao salvar arquivo CSV: {e}")

    return filepath



# ============================================================
# Função Principal
# ============================================================

def main():
    """Executa o coletor de notícias para todas as cidades."""
    logger.info("=" * 60)
    logger.info("🚀 Cities News Scrapper — Iniciando coleta")
    logger.info("=" * 60)

    # Carregar cidades
    cities = load_cities(CITIES_FILE)

    # Calcular data de corte
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=SEARCH_PERIOD_DAYS)
    logger.info(f"📅 Buscando notícias dos últimos {SEARCH_PERIOD_DAYS} dias (desde {cutoff_date.strftime('%d/%m/%Y')})")

    # Contabilizar total de queries (agora 1 por categoria por cidade)
    total_categories = len(SEARCH_QUERIES)
    total_queries = len(cities) * total_categories
    logger.info(f"🔍 Total de buscas a realizar (agrupadas por OR): {len(cities)} cidades × {total_categories} categorias = {total_queries} queries\n")

    # Estado
    current_delay = BASE_DELAY
    results = []
    total_news = 0
    total_filtered = 0
    cities_with_news = 0
    query_count = 0

    start_time = time.time()

    for city_index, city in enumerate(cities, 1):
        logger.info(f"🏙️  [{city_index}/{len(cities)}] Processando: {city}")

        city_news = []
        city_filtered = 0
        seen_links = set()  # Deduplicação por cidade

        for category, terms in SEARCH_QUERIES.items():
            query_count += 1

            # Buscar notícias agrupadas por categoria
            news_items, current_delay, filtered = fetch_news_for_category(
                city=city,
                category=category,
                terms=terms,
                seen_links=seen_links,
                cutoff_date=cutoff_date,
                current_delay=current_delay,
            )

            city_filtered += filtered

            if news_items:
                city_news.extend(news_items)
                logger.info(
                    f"    📰 Categoria '{category}': {len(news_items)} relevante(s)"
                    + (f", {filtered} descartada(s)" if filtered else "")
                )
            elif filtered:
                logger.info(
                    f"    🚫 Categoria '{category}': {filtered} descartada(s) por irrelevância"
                )

            # Delay entre requisições
            time.sleep(current_delay)

        # Montar resultado da cidade
        city_result = {
            "cidade": city,
            "total_noticias": len(city_news),
            "noticias": city_news,
        }
        results.append(city_result)
        total_filtered += city_filtered

        if city_news:
            cities_with_news += 1
            total_news += len(city_news)
            logger.info(
                f"    ✅ Total para {city}: {len(city_news)} notícia(s)"
                + (f" ({city_filtered} descartada(s))" if city_filtered else "")
                + "\n"
            )
        else:
            logger.info(f"    ⚪ Nenhuma notícia relevante para {city}\n")

    # Salvar resultados
    filepath = save_results(results, OUTPUT_DIR)
    elapsed = time.time() - start_time

    # Resumo final
    logger.info("=" * 60)
    logger.info("📊 RESUMO DA COLETA")
    logger.info("=" * 60)
    logger.info(f"  🏙️  Cidades processadas: {len(cities)}")
    logger.info(f"  🔍 Queries realizadas:   {query_count}")
    logger.info(f"  📰 Notícias relevantes:  {total_news}")
    logger.info(f"  🚫 Notícias descartadas: {total_filtered}")
    logger.info(f"  ✅ Cidades com notícias: {cities_with_news}")
    logger.info(f"  ⚪ Cidades sem notícias: {len(cities) - cities_with_news}")
    logger.info(f"  ⏱️  Tempo total:          {elapsed:.1f} segundos")
    logger.info(f"  💾 Relatório salvo em:   {filepath}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
