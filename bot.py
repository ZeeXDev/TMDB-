import os
import sys
import asyncio
import requests
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from html import escape
from datetime import datetime
from flask import Flask
from threading import Thread
import time
import json
from deep_translator import GoogleTranslator
import aiohttp

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration Flask pour Render.com
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "🤖 Bot TMDB & AniList en ligne et fonctionnel! | @Godanimes"

@app_web.route('/health')
def health():
    return {"status": "ok", "timestamp": time.time()}

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Configuration TMDB
API_KEY = "f2bed62b5977bce26540055276d0046c"
BASE_URL = "https://api.themoviedb.org/3"
LANGUE = "fr-FR"
TIMEOUT_API = 30  

# Configuration AniList
ANILIST_URL = "https://graphql.anilist.co"

# Configuration Kitsu
KITSU_URL = "https://kitsu.io/api/edge"

# Configuration Pyrogram
API_ID = 25926022
API_HASH = "30db27d9e56d854fb5e943723268db32"
BOT_TOKEN = "7703477452:AAEAiU6PixR50YCkkCBRegZskbVsOqs6KRY"

GENRES_EMOJI = {
    28: "🔫 Action", 12: "🌍 Aventure", 16: "🎨 Animation", 35: "😂 Comédie",
    80: "🔪 Crime", 99: "📽 Documentaire", 18: "🎭 Drame", 10751: "👪 Familial",
    14: "⚔ Fantaisie", 36: "📜 Historique", 27: "👻 Horreur", 10402: "🎵 Musique",
    9648: "🕵️ Mystère", 10749: "💘 Romance", 878: "👽 Science-Fiction",
    10770: "📺 Téléfilm", 53: "🎭 Thriller", 10752: "💥 Guerre", 37: "🤠 Western",
    10759: "🎬 Action & Aventure", 10762: "👶 Kids", 10763: "🌐 News",
    10764: "🏟 Reality", 10765: "🚀 Sci-Fi & Fantasy", 10766: "📺 Soap",
    10767: "🗣 Talk", 10768: "⚔ War & Politics",
    1001: "😳 Ecchi", 1002: "👨‍👩‍👧‍👦 Harem", 1003: "🌌 Isekai", 1004: "👊 Shounen",
    1005: "💝 Shoujo", 1006: "🎯 Seinen", 1007: "💄 Josei", 1008: "🤖 Mecha",
    1009: "🏫 Slice of Life", 1010: "🎤 Idol", 1011: "🧠 Psychologique",
    1012: "👻 Supernaturel", 1013: "⚔️ Dark Fantasy", 1014: "🤣 Comédie romantique",
    1015: "👮‍♂️ Policier", 1016: "🏟️ Sports", 1017: "🍳 Cuisine", 1018: "🎮 Jeu vidéo",
    1019: "🕰️ Historique", 1020: "🧊 Tranche de vie"
}

ANILIST_GENRES_EMOJI = {
    "Action": "🔫 Action", "Adventure": "🌍 Aventure", "Comedy": "😂 Comédie",
    "Drama": "🎭 Drame", "Ecchi": "😳 Ecchi", "Fantasy": "⚔ Fantaisie",
    "Hentai": "🔞 Hentai", "Horror": "👻 Horreur", "Mahou Shoujo": "✨ Magical Girl",
    "Mecha": "🤖 Mecha", "Music": "🎵 Musique", "Mystery": "🕵️ Mystère",
    "Psychological": "🧠 Psychologique", "Romance": "💘 Romance",
    "Sci-Fi": "👽 Science-Fiction", "Slice of Life": "🏫 Tranche de Vie",
    "Sports": "🏟️ Sports", "Supernatural": "👻 Supernaturel", "Thriller": "🎭 Thriller",
    "Isekai": "🌌 Isekai", "Shounen": "👊 Shounen", "Shoujo": "💝 Shoujo",
    "Seinen": "🎯 Seinen", "Josei": "💄 Josei", "Harem": "👨‍👩‍👧‍👦 Harem"
}

MOIS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}


try:
    app = Client(
        "tmdb_bot", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        bot_token=BOT_TOKEN,
        workers=20,
        sleep_threshold=60
    )
except Exception as e:
    logger.error(f"Erreur d'initialisation du client Pyrogram: {e}")
    sys.exit(1)

recherches_en_cours = {}

async def traduire_texte(texte, src='auto', dest='fr'):
    """Traduit le texte en français en utilisant Deep Translator"""
    if not texte or texte == "Aucun résumé disponible.":
        return texte
    
    try:
        # Nettoyer le texte des balises HTML
        import re
        texte_propre = re.sub(r'<.*?>', '', texte)
        
        # Traduire avec Deep Translator
        if src == 'auto':
            translated = GoogleTranslator(source='auto', target=dest).translate(texte_propre)
        else:
            translated = GoogleTranslator(source=src, target=dest).translate(texte_propre)
        
        return translated
    except Exception as e:
        logger.error(f"Erreur de traduction: {e}")
        return texte

async def download_image_hd(url):
    """Télécharge une image en qualité HD maximale"""
    try:
        if not url:
            return None
            
        # Forcer la qualité maximale pour les URLs TMDB
        if "image.tmdb.org" in url:
            # S'assurer qu'on utilise la qualité originale
            url = url.replace("/w500", "/original").replace("/w780", "/original")
        
        # Pour AniList/Kitsu, utiliser l'URL directement
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    # Retourner les données binaires pour une qualité maximale
                    from io import BytesIO
                    return BytesIO(image_data)
                    
    except Exception as e:
        logger.error(f"Erreur download_image_hd: {e}")
        # Fallback: retourner l'URL pour que Pyrogram gère le téléchargement
        return url

async def get_kitsu_poster(anime_title):
    """Récupère le poster d'un anime depuis Kitsu"""
    try:
        # Recherche l'anime sur Kitsu
        search_url = f"{KITSU_URL}/anime"
        params = {
            "filter[text]": anime_title,
            "page[limit]": 1
        }
        
        headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json"
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=TIMEOUT_API)
        response.raise_for_status()
        
        data = response.json()
        if data.get("data") and len(data["data"]) > 0:
            anime_data = data["data"][0]
            poster_image = anime_data.get("attributes", {}).get("posterImage", {})
            
            # Essayer différentes qualités d'image
            if poster_image.get("original"):
                return poster_image["original"]
            elif poster_image.get("large"):
                return poster_image["large"]
            elif poster_image.get("medium"):
                return poster_image["medium"]
        
        return None
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du poster Kitsu: {e}")
        return None

def limiter_texte(texte, limite=1024):
    """Limite la longueur du texte pour les légendes Telegram"""
    if len(texte) > limite:
        return texte[:limite-3] + "..."
    return texte

def convertir_note(note):
    """Convertit la note en étoiles (échelle 0-100)"""
    try:
        note = min(100, max(0, float(note)))
        etoiles_pleines = int(round(note / 20))
        return "★" * etoiles_pleines + "☆" * (5 - etoiles_pleines)
    except:
        return "☆☆☆☆☆"

def convertir_note_tmdb(note):
    """Convertit la note TMDB en étoiles (échelle 0-10)"""
    try:
        note = min(10, max(0, float(note)))
        etoiles_pleines = int(round(note / 2))
        return "★" * etoiles_pleines + "☆" * (5 - etoiles_pleines)
    except:
        return "☆☆☆☆☆"

def determiner_origine(details):
    """Détermine l'origine de l'œuvre"""
    try:
        keywords = [k.get("name", "").lower() for k in details.get("keywords", {}).get("keywords", [])]
        
        if any(k in keywords for k in ["anime", "manga", "animé"]):
            if "ecchi" in keywords:
                return "🇯🇵 Animé Ecchi"
            elif "harem" in keywords:
                return "🇯🇵 Animé Harem"
            elif "isekai" in keywords:
                return "🇯🇵 Animé Isekai"
            elif "shounen" in keywords:
                return "🇯🇵 Animé Shounen"
            elif "shoujo" in keywords:
                return "🇯🇵 Animé Shoujo"
            elif "seinen" in keywords:
                return "🇯🇵 Animé Seinen"
            return "🇯🇵 Adapté d'un manga/animé"
            
        elif "novel" in keywords:
            return "📚 Adapté d'un roman"
        elif "manhwa" in keywords:
            return "🇰🇷 Adapté d'un manhwa"
        elif "comic" in keywords:
            return "🖍 Adapté d'une BD"
    except:
        pass
    return "🎬 Œuvre originale"

def formater_date(date_str):
    """Convertit une date YYYY-MM-DD en format 'jour mois année'"""
    if not date_str or date_str == "Inconnue":
        return "Inconnue"
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{date_obj.day} {MOIS[date_obj.month]} {date_obj.year}"
    except:
        return date_str

def formater_date_anilist(date):
    """Formate la date AniList"""
    if not date or not date.get("year"):
        return "Inconnue"
    
    try:
        year = date["year"]
        month = date.get("month", 1)
        day = date.get("day", 1)
        return f"{day} {MOIS.get(month, '')} {year}"
    except:
        return "Inconnue"

async def rechercher_media_multiple(query):
    """Recherche multiple de médias dans l'API TMDB"""
    try:
        params = {
            "api_key": API_KEY,
            "query": query,
            "language": LANGUE,
            "include_adult": True
        }
        response = requests.get(f"{BASE_URL}/search/multi", params=params, timeout=TIMEOUT_API)
        response.raise_for_status()
        results = response.json().get("results", [])

        media_results = [r for r in results if r.get("media_type") in ["movie", "tv"]]
        return media_results[:20]
        
    except Exception as e:
        logger.error(f"Erreur recherche multiple: {str(e)}")
        return None

async def rechercher_anime_anilist(query):
    """Recherche d'anime sur AniList"""
    try:
        query_graphql = """
        query ($search: String, $type: MediaType) {
            Page(page: 1, perPage: 20) {
                media(search: $search, type: $type, sort: SEARCH_MATCH) {
                    id
                    title {
                        romaji
                        english
                        native
                        userPreferred
                    }
                    type
                    format
                    status
                    description
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    season
                    episodes
                    duration
                    chapters
                    volumes
                    genres
                    averageScore
                    meanScore
                    popularity
                    favourites
                    isAdult
                    coverImage {
                        extraLarge
                        large
                        medium
                        color
                    }
                    bannerImage
                    studios {
                        edges {
                            node {
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {"search": query, "type": "ANIME"}
        
        response = requests.post(ANILIST_URL, json={"query": query_graphql, "variables": variables}, timeout=TIMEOUT_API)
        response.raise_for_status()
        data = response.json()
        
        return data.get("data", {}).get("Page", {}).get("media", [])
        
    except Exception as e:
        logger.error(f"Erreur recherche AniList: {str(e)}")
        return None

async def get_anime_details_anilist(anime_id):
    """Récupère les détails complets d'un anime depuis AniList"""
    try:
        query_graphql = """
        query ($id: Int) {
            Media(id: $id) {
                id
                title {
                    romaji
                    english
                    native
                    userPreferred
                }
                type
                format
                status
                description
                startDate {
                    year
                    month
                    day
                }
                endDate {
                    year
                    month
                    day
                }
                season
                episodes
                duration
                chapters
                volumes
                genres
                averageScore
                meanScore
                popularity
                favourites
                isAdult
                coverImage {
                    extraLarge
                    large
                    medium
                    color
                    }
                bannerImage
                studios {
                    edges {
                        node {
                            name
                        }
                        isMain
                    }
                }
            }
        }
        """
        
        variables = {"id": anime_id}
        
        response = requests.post(ANILIST_URL, json={"query": query_graphql, "variables": variables}, timeout=TIMEOUT_API)
        response.raise_for_status()
        data = response.json()
        
        return data.get("data", {}).get("Media", {})
        
    except Exception as e:
        logger.error(f"Erreur détails AniList: {str(e)}")
        return None

async def get_media_details(media_type, media_id):
    """Récupère les détails complets d'un média TMDB"""
    try:
        endpoint = "movie" if media_type == "movie" else "tv"
        details = requests.get(
            f"{BASE_URL}/{endpoint}/{media_id}",
            params={
                "api_key": API_KEY,
                "language": LANGUE,
                "append_to_response": "credits,keywords,content_ratings"
            },
            timeout=TIMEOUT_API
        ).json()

        if media_type == "tv":
            keywords = [k.get("name", "").lower() for k in details.get("keywords", {}).get("results", [])]
            if "anime" in keywords or "animation" in keywords:
                if "harem" in keywords:
                    details.setdefault("genres", []).append({"id": 1002, "name": "Harem"})
                if "isekai" in keywords:
                    details.setdefault("genres", []).append({"id": 1003, "name": "Isekai"})
                if "ecchi" in keywords:
                    details.setdefault("genres", []).append({"id": 1001, "name": "Ecchi"})
                if "shounen" in keywords:
                    details.setdefault("genres", []).append({"id": 1004, "name": "Shounen"})
                if "shoujo" in keywords:
                    details.setdefault("genres", []).append({"id": 1005, "name": "Shoujo"})

        return details
    except Exception as e:
        logger.error(f"Erreur détails média: {str(e)}")
        return None

async def get_series_seasons(series_id):
    """Récupère les saisons d'une série TMDB"""
    try:
        response = requests.get(f"{BASE_URL}/tv/{series_id}", params={"api_key": API_KEY, "language": LANGUE}, timeout=TIMEOUT_API)
        details = response.json()
        return details.get("seasons", [])
    except Exception as e:
        logger.warning(f"Erreur get_series_seasons: {e}")
        return []

async def get_season_details(series_id, season_num):
    """Récupère les détails d'une saison spécifique TMDB"""
    try:
        response = requests.get(f"{BASE_URL}/tv/{series_id}/season/{season_num}", params={"api_key": API_KEY, "language": LANGUE}, timeout=TIMEOUT_API)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning(f"Erreur get_season_details: {e}")
        return None

async def get_movie_release_years(movie_id):
    """Récupère les années de sortie pour les films TMDB"""
    try:
        response = requests.get(f"{BASE_URL}/movie/{movie_id}/release_dates", params={"api_key": API_KEY}, timeout=TIMEOUT_API)
        dates = response.json().get("results", [])
        return list({d.get("release_date", "")[:4] for d in dates if d.get("release_date")})
    except Exception as e:
        logger.warning(f"Erreur get_movie_release_years: {e}")
        return []

def create_selection_buttons(results, source="tmdb"):
    """Crée les boutons de sélection pour les résultats multiples"""
    buttons = []
    for result in results:
        if source == "tmdb":
            media_type = result.get("media_type")
            title = result.get("title") or result.get("name") or "Sans titre"
            year = result.get("release_date", result.get("first_air_date", ""))[:4]
            
            emoji = "🎬" if media_type == "movie" else "📺"
            button_text = f"{emoji} {title}"
            if year:
                button_text += f" ({year})"
                
            callback_data = f"select_{media_type}_{result['id']}"
            
        else:
            title_obj = result.get("title", {})
            title = title_obj.get("userPreferred") or title_obj.get("romaji") or title_obj.get("english") or "Sans titre"
            year = result.get("startDate", {}).get("year", "")
            
            emoji = "🇯🇵"
            button_text = f"{emoji} {title}"
            if year:
                button_text += f" ({year})"
                
            callback_data = f"select_anilist_{result['id']}"
        
        if len(button_text) > 35:
            button_text = button_text[:32] + "..."
            
        buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="cancel_search")])
    
    return InlineKeyboardMarkup(buttons)

def create_season_buttons(seasons, media_id):
    """Crée les boutons pour les saisons"""
    buttons = []
    for season in seasons:
        if season.get("season_number", 0) > 0:
            buttons.append([InlineKeyboardButton(f"📺 Saison {season['season_number']}", callback_data=f"season_{media_id}_{season['season_number']}")])
    return InlineKeyboardMarkup(buttons)

def create_year_buttons(years, media_id):
    """Crée les boutons pour les années"""
    buttons = []
    for year in sorted(years, reverse=True):
        buttons.append([InlineKeyboardButton(f"🎬 Version {year}", callback_data=f"year_{media_id}_{year}")])
    return InlineKeyboardMarkup(buttons)

async def formater_reponse(details, media_type, season_num=None, year=None):
    """Formatage des informations du média TMDB avec traduction"""
    titre = details.get("title") or details.get("name") or "Inconnu"
    titre_original = details.get("original_title") or details.get("original_name") or titre
    
    if media_type == "tv" and season_num:
        for season in details.get("seasons", []):
            if season.get("season_number") == season_num:
                date_sortie = season.get("air_date", "Inconnue")
                episode_count = season.get("episode_count", "Inconnu")
                titre = f"{titre} (Saison {season_num})"
                break
    else:
        date_sortie = details.get("release_date") or details.get("first_air_date") or "Inconnue"
        episode_count = details.get("number_of_episodes", "Inconnu") if media_type == "tv" else None
    
    annee = date_sortie.split("-")[0] if date_sortie != "Inconnue" else "Inconnue"
    date_formatee = formater_date(date_sortie)
    
    if media_type == "movie" and year:
        titre = f"{titre} ({year})"
    
    genres = " / ".join([GENRES_EMOJI.get(g["id"], g["name"]) for g in details.get("genres", [])]) or "Inconnu"
    note = convertir_note_tmdb(details.get("vote_average", 0))
    pays = details.get("production_countries", [{}])[0].get("name", "Inconnu") if details.get("production_countries") else "Inconnu"
    
    if media_type == "movie":
        realisateur = next((p["name"] for p in details.get("credits", {}).get("crew", []) if p.get("job") == "Director"), "Inconnu")
    else:
        created_by = details.get("created_by", [])
        realisateur = created_by[0].get("name", "Inconnu") if created_by else "Inconnu"
    
    studios = details.get("production_companies", [])
    studio = studios[0]["name"] if studios else "Inconnu"
    
    if media_type == "movie":
        duree = f"{details.get('runtime', 0)} min" if details.get('runtime') else "Inconnue"
    else:
        duree = f"{details.get('episode_run_time', [0])[0]} min/épisode" if details.get('episode_run_time') else "Inconnue"
    
    origine = determiner_origine(details)
    resume = details.get("overview", "Aucun résumé disponible.")
    
    # Traduire le résumé si nécessaire
    if resume != "Aucun résumé disponible." and "en" in details.get('original_language', ''):
        resume_traduit = await traduire_texte(resume)
    else:
        resume_traduit = resume
    
    resume_court = escape(resume_traduit[:250] + "..." if len(resume_traduit) > 250 else resume_traduit)
    
    texte = (
        f"<blockquote>🎬 𝗧𝗶𝘁𝗿𝗲: <a href='t.me/WorldZPrime'>{escape(titre)}</a></blockquote>\n"
        f"🌐 𝗧𝗶𝘁𝗿𝗲 𝗢𝗿𝗶𝗴𝗶𝗻𝗮𝗹: {escape(titre_original)}\n\n"
        f"☾ - 𝗚𝗲𝗻𝗿𝗲𝘀: {escape(genres)}\n\n"
        f"☾ - 𝗔𝗻𝗻é𝗲: {escape(annee)}\n"
        f"☾ - 𝗣𝗮𝘆𝘀: {escape(pays)}\n"
        f"☾ - 𝗥é𝗮𝗹𝗶𝘀𝗮𝘁𝗲𝘂𝗿: {escape(realisateur)}\n"
        f"☾ - 𝗦𝘁𝘂𝗱𝗶𝗼: {escape(studio)}\n"
        f"☾ - 𝗗𝘂𝗿𝗲‌𝗲: {escape(duree)}\n"
        f"☾ - 𝗦𝗼𝗿𝘁𝗶𝗲: {escape(date_formatee)}\n"
    )
    
    if media_type == "tv":
        texte += f"☾ - 𝗘‌𝗽𝗶𝘀𝗼𝗱𝗲𝘀 𝗧𝗼𝘁𝗮𝗹: {escape(str(episode_count))}\n"
    
    texte += (
        f"☾ - 𝗢𝗿𝗶𝗴𝗶𝗻𝗲: {escape(origine)}\n"
        f"☾ - 𝗡𝗼𝘁𝗲: {note}\n\n"
        f"╔═══『 ✦ 』═══╗\n"
        f"    <b>@WorldZPrime</b>\n"
        f"╚═══『 ✦ 』═══╝\n\n"
        f"<blockquote expandable>𝗥𝗲𝘀𝘂𝗺𝗲‌:\n{resume_court}</blockquote>"
    )
    
    # URL d'image en qualité maximale
    poster_path = details.get('poster_path')
    if poster_path:
        # Utiliser l'URL originale pour la meilleure qualité
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
    else:
        poster_url = None
    
    return {
        "texte": texte,
        "poster": poster_url
    }

async def formater_reponse_anilist(details):
    """Formatage des informations d'anime depuis AniList avec traduction"""
    title_obj = details.get("title", {})
    titre = title_obj.get("userPreferred") or title_obj.get("romaji") or title_obj.get("english") or "Inconnu"
    titre_original = title_obj.get("native") or titre
    titre_romaji = title_obj.get("romaji") or titre  # AJOUT DU TITRE ROMAJI
    
    format_anime = details.get("format", "Inconnu")
    status = details.get("status", "Inconnu").replace("_", " ").title()
    
    start_date = details.get("startDate", {})
    end_date = details.get("endDate", {})
    
    date_debut = formater_date_anilist(start_date)
    date_fin = formater_date_anilist(end_date)
    annee = start_date.get("year", "Inconnue")
    
    episodes = details.get("episodes", "Inconnu")
    duree = f"{details.get('duration', 'Inconnu')} min/épisode"
    
    genres = details.get("genres", [])
    genres_formates = " / ".join([ANILIST_GENRES_EMOJI.get(g, g) for g in genres]) or "Inconnu"
    
    studios = details.get("studios", {}).get("edges", [])
    studio_principal = next((s["node"]["name"] for s in studios if s.get("isMain")), "Inconnu")
    if studio_principal == "Inconnu" and studios:
        studio_principal = studios[0]["node"]["name"]
    
    note = convertir_note(details.get("averageScore", 0))
    popularite = details.get("popularity", "Inconnu")
    
    resume = details.get("description", "Aucun résumé disponible.")
    
    # Traduire le résumé depuis l'anglais si nécessaire
    if resume != "Aucun résumé disponible.":
        resume_traduit = await traduire_texte(resume, 'en', 'fr')
    else:
        resume_traduit = resume
    
    # Nettoyer le résumé des balises HTML
    import re
    resume_propre = re.sub(r'<.*?>', '', resume_traduit)
    resume_court = escape(resume_propre[:250] + "..." if len(resume_propre) > 250 else resume_propre)
    
    is_adult = "🔞 " if details.get("isAdult") else ""
    
    texte = (
        f"<blockquote>{is_adult}🇯🇵 𝗔𝗻𝗶𝗺𝗲: <a href='t.me/WorldZPrime'>{escape(titre)}</a></blockquote>\n"
        f"🌐 𝗧𝗶𝘁𝗿𝗲 𝗢𝗿𝗶𝗴𝗶𝗻𝗮𝗹: {escape(titre_original)}\n"
        f"📝 𝗧𝗶𝘁𝗿𝗲 𝗥𝗼𝗺𝗮𝗷𝗶: {escape(titre_romaji)}\n\n"  # AJOUT DE LA LIGNE ROMAJI
        f"☾ - 𝗙𝗼𝗿𝗺𝗮𝘁: {escape(format_anime)}\n"
        f"☾ - 𝗦𝘁𝗮𝘁𝘂𝘁: {escape(status)}\n"
        f"☾ - 𝗚𝗲𝗻𝗿𝗲𝘀: {escape(genres_formates)}\n\n"
        f"☾ - 𝗔𝗻𝗻é𝗲: {escape(str(annee))}\n"
        f"☾ - 𝗗é𝗯𝘂𝘁: {escape(date_debut)}\n"
        f"☾ - 𝗙𝗶𝗻: {escape(date_fin)}\n"
        f"☾ - 𝗦𝘁𝘂𝗱𝗶𝗼: {escape(studio_principal)}\n"
        f"☾ - 𝗘𝗽𝗶𝘀𝗼𝗱𝗲𝘀: {escape(str(episodes))}\n"
        f"☾ - 𝗗𝘂𝗿𝗲‌𝗲: {escape(duree)}\n"
        f"☾ - 𝗣𝗼𝗽𝘂𝗹𝗮𝗿𝗶𝘁é: #{escape(str(popularite))}\n"
        f"☾ - 𝗡𝗼𝘁𝗲: {note}\n\n"
        f"╔═══『 ✦ 』═══╗\n"
        f"    <b>@WorldZPrime</b>\n"
        f"╚═══『 ✦ 』═══╝\n\n"
        f"<blockquote expandable>𝗥𝗲𝘀𝘂𝗺𝗲‌:\n{resume_court}</blockquote>"
    )
    
    # Récupérer le poster depuis Kitsu au lieu d'AniList
    poster_url = await get_kitsu_poster(titre)
    
    return {
        "texte": texte,
        "poster": poster_url,
        "banner": details.get("bannerImage")
    }

async def send_media_info(message, details, media_type, media_id, season_num=None, year=None):
    """Envoie les informations du média TMDB avec image HD"""
    formatted = await formater_reponse(details, media_type, season_num, year)
    
    if formatted["poster"]:
        # Optimiser l'URL TMDB pour la qualité maximale
        poster_url = formatted["poster"].replace("/w500", "/original").replace("/w780", "/original")
        
        # Télécharger l'image en qualité HD
        image_data = await download_image_hd(poster_url)
        
        try:
            if image_data and hasattr(image_data, 'read'):
                # Envoyer les données binaires pour une qualité maximale
                await message.reply_photo(
                    photo=image_data,
                    caption=limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                # Fallback: utiliser l'URL optimisée
                await message.reply_photo(
                    photo=poster_url,
                    caption=limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Erreur envoi image: {e}")
            # Dernier fallback: envoyer sans image
            await message.reply_text(
                limiter_texte(formatted["texte"]),
                parse_mode=enums.ParseMode.HTML
            )
    else:
        await message.reply_text(
            limiter_texte(formatted["texte"]),
            parse_mode=enums.ParseMode.HTML
        )

async def send_anime_info(message, details):
    """Envoie les informations d'anime AniList avec image HD depuis Kitsu"""
    formatted = await formater_reponse_anilist(details)
    
    if formatted["poster"]:
        # Télécharger l'image depuis Kitsu en qualité HD
        image_data = await download_image_hd(formatted["poster"])
        
        try:
            if image_data and hasattr(image_data, 'read'):
                # Envoyer les données binaires pour une qualité maximale
                await message.reply_photo(
                    photo=image_data,
                    caption=limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                # Fallback: utiliser l'URL directement
                await message.reply_photo(
                    photo=formatted["poster"],
                    caption=limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Erreur envoi image AniList/Kitsu: {e}")
            # Dernier fallback: envoyer sans image
            await message.reply_text(
                limiter_texte(formatted["texte"]),
                parse_mode=enums.ParseMode.HTML
            )
    else:
        # Si pas de poster Kitsu, essayer avec l'image AniList en fallback
        title_obj = details.get("title", {})
        titre = title_obj.get("userPreferred") or title_obj.get("romaji") or title_obj.get("english") or "Inconnu"
        
        poster_url = details.get("coverImage", {}).get("extraLarge")
        if poster_url:
            image_data = await download_image_hd(poster_url)
            
            if image_data and hasattr(image_data, 'read'):
                await message.reply_photo(
                    photo=image_data,
                    caption=limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                await message.reply_photo(
                    photo=poster_url,
                    caption=limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
        else:
            await message.reply_text(
                limiter_texte(formatted["texte"]),
                parse_mode=enums.ParseMode.HTML
            )

# Gestionnaires de commandes
@app.on_message(filters.command(["start", "aide", "help"]))
async def demarrage(client, message):
    try:
        await message.reply_text(
            "🍿 <b>Bienvenue sur le Bot Cinéma & Animé !</b>\n\n"
            "🎬 <b>Commandes disponibles :</b>\n"
            "- Envoyez un titre de film/série pour rechercher sur TMDB\n"
            "- <code>/ani &lt;titre&gt;</code> pour rechercher un anime sur AniList\n\n"
            "<b>Exemples :</b>\n"
            "- Le Comte de Monte-Cristo\n"
            "- Avatar\n"
            "- <code>/ani Naruto</code>\n"
            "- <code>/ani Attack on Titan</code>\n\n"
            "<i>Je vous proposerai tous les résultats trouvés !</i>",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Erreur dans la commande start: {e}")

@app.on_message(filters.command("ani"))
async def search_anilist(client, message):
    try:
        if len(message.command) < 2:
            return await message.reply_text("❌ Utilisation: <code>/ani &lt;titre de l'anime&gt;</code>", parse_mode=enums.ParseMode.HTML)
        
        requete = " ".join(message.command[1:]).strip()
        
        if len(requete) < 3:
            return await message.reply_text("🔍 La recherche doit contenir au moins 3 caractères.")
        
        msg = await message.reply_text("🔍 Recherche en cours sur AniList...")
        
        results = await rechercher_anime_anilist(requete)
        
        if results is None:
            return await msg.edit_text("🌐 <b>Problème de connexion avec AniList</b>\n\nVeuillez réessayer dans quelques secondes.")
        
        if not results:
            return await msg.edit_text("❌ Aucun anime trouvé sur AniList. Essayez avec un autre titre.")
        
        if len(results) == 1:
            result = results[0]
            details = await get_anime_details_anilist(result["id"])
            if details:
                await send_anime_info(message, details)
                await msg.delete()
                
                recherches_en_cours[message.chat.id] = {
                    "source": "anilist",
                    "media_id": result["id"],
                    "details": details
                }
            else:
                await msg.edit_text("❌ Erreur lors de la récupération des détails.")
        
        else:
            await msg.edit_text(
                f"🎭 <b>J'ai trouvé {len(results)} animes sur AniList pour \"{requete}\"</b>\n\n"
                "📋 <i>Sélectionnez celui qui vous intéresse :</i>",
                reply_markup=create_selection_buttons(results, "anilist"),
                parse_mode=enums.ParseMode.HTML
            )
            
            recherches_en_cours[message.chat.id] = {
                "results": results,
                "query": requete,
                "source": "anilist"
            }
            
    except Exception as e:
        logger.error(f"Erreur dans la commande ani: {e}")
        await message.reply_text("❌ Une erreur s'est produite lors de la recherche.")

@app.on_message(filters.text & ~filters.command(["start", "help", "aide", "ani"]))
async def search_tmdb(client, message):
    try:
        requete = message.text.strip()
        
        if len(requete) < 3:
            return await message.reply_text("🔍 La recherche doit contenir au moins 3 caractères.")
        
        msg = await message.reply_text("🔍 Recherche en cours sur TMDB...")
        
        results = await rechercher_media_multiple(requete)
        
        if results is None:
            return await msg.edit_text("🌐 <b>Problème de connexion avec TMDB</b>\n\nVeuillez réessayer dans quelques secondes.")
        
        if not results:
            return await msg.edit_text("❌ Aucun résultat trouvé sur TMDB. Essayez avec un autre titre.")
        
        if len(results) == 1:
            result = results[0]
            details = await get_media_details(result["media_type"], result["id"])
            if details:
                await send_media_info(message, details, result["media_type"], result["id"])
                await msg.delete()
                
                recherches_en_cours[message.chat.id] = {
                    "source": "tmdb",
                    "media_type": result["media_type"],
                    "media_id": result["id"],
                    "details": details
                }
                
                if result["media_type"] == "tv":
                    seasons = await get_series_seasons(result["id"])
                    if seasons and len(seasons) > 1:
                        await message.reply_text(
                            "📺 <b>Plusieurs saisons disponibles :</b>",
                            reply_markup=create_season_buttons(seasons, result["id"]),
                            parse_mode=enums.ParseMode.HTML
                        )
                
                elif result["media_type"] == "movie":
                    years = await get_movie_release_years(result["id"])
                    if years and len(years) > 1:
                        await message.reply_text(
                            "🎬 <b>Plusieurs versions disponibles :</b>",
                            reply_markup=create_year_buttons(years, result["id"]),
                            parse_mode=enums.ParseMode.HTML
                        )
                        
            else:
                await msg.edit_text("❌ Erreur lors de la récupération des détails.")
        
        else:
            await msg.edit_text(
                f"🎭 <b>J'ai trouvé {len(results)} résultats sur TMDB pour \"{requete}\"</b>\n\n"
                "📋 <i>Sélectionnez celui qui vous intéresse :</i>",
                reply_markup=create_selection_buttons(results, "tmdb"),
                parse_mode=enums.ParseMode.HTML
            )
            
            recherches_en_cours[message.chat.id] = {
                "results": results,
                "query": requete,
                "source": "tmdb"
            }
            
    except Exception as e:
        logger.error(f"Erreur dans la recherche TMDB: {e}")
        await message.reply_text("❌ Une erreur s'est produite lors de la recherche.")

@app.on_callback_query(filters.regex("^select_"))
async def select_callback(client, callback):
    try:
        data = callback.data.split("_")
        if len(data) < 3:
            return await callback.answer("❌ Données invalides", show_alert=True)
        
        source = data[1]
        
        if source == "anilist":
            media_id = int(data[2])
            
            details = await get_anime_details_anilist(media_id)
            if not details:
                return await callback.answer("❌ Erreur de chargement", show_alert=True)
            
            await callback.answer("✅ Chargement des informations...")
            await callback.message.delete()
            await send_anime_info(callback.message, details)
            
            recherches_en_cours[callback.message.chat.id] = {
                "source": "anilist",
                "media_id": media_id,
                "details": details
            }
            
        else:
            media_type = source
            media_id = int(data[2])
            
            details = await get_media_details(media_type, media_id)
            if not details:
                return await callback.answer("❌ Erreur de chargement", show_alert=True)
            
            formatted = await formater_reponse(details, media_type)
            
            await callback.answer("✅ Chargement des informations...")
            await callback.message.delete()
            
            if formatted["poster"]:
                image_data = await download_image_hd(formatted["poster"])
                
                if image_data:
                    msg = await callback.message.reply_photo(
                        photo=image_data,
                        caption=limiter_texte(formatted["texte"]),
                        parse_mode=enums.ParseMode.HTML
                    )
                else:
                    msg = await callback.message.reply_photo(
                        photo=formatted["poster"],
                        caption=limiter_texte(formatted["texte"]),
                        parse_mode=enums.ParseMode.HTML
                    )
            else:
                msg = await callback.message.reply_text(
                    limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
            
            recherches_en_cours[callback.message.chat.id] = {
                "source": "tmdb",
                "media_type": media_type,
                "media_id": media_id,
                "details": details,
                "message_id": msg.id
            }
            
            if media_type == "tv":
                seasons = await get_series_seasons(media_id)
                if seasons and len(seasons) > 1:
                    await callback.message.reply_text(
                        "📺 <b>Plusieurs saisons disponibles :</b>",
                        reply_markup=create_season_buttons(seasons, media_id),
                        parse_mode=enums.ParseMode.HTML
                    )
            
            elif media_type == "movie":
                years = await get_movie_release_years(media_id)
                if years and len(years) > 1:
                    await callback.message.reply_text(
                        "🎬 <b>Plusieurs versions disponibles :</b>",
                        reply_markup=create_year_buttons(years, media_id),
                        parse_mode=enums.ParseMode.HTML
                    )
            
    except Exception as e:
        logger.error(f"Erreur dans select_callback: {e}")
        await callback.answer("❌ Erreur lors de la sélection", show_alert=True)

@app.on_callback_query(filters.regex("^season_"))
async def season_callback(client, callback):
    try:
        data = callback.data.split("_")
        if len(data) < 3:
            return await callback.answer("❌ Données invalides", show_alert=True)
        
        media_id = int(data[1])
        season_num = int(data[2])
        
        details_serie = await get_media_details("tv", media_id)
        if not details_serie:
            return await callback.answer("❌ Série non trouvée", show_alert=True)
        
        details_saison = await get_season_details(media_id, season_num)
        if not details_saison:
            return await callback.answer("❌ Saison non trouvée", show_alert=True)

        titre = f"{details_serie.get('name', 'Série inconnue')} (Saison {season_num})"
        titre_original = details_serie.get('original_name', titre)
        date_sortie = details_saison.get('air_date', 'Inconnue')
        date_formatee = formater_date(date_sortie)
        genres = " / ".join([GENRES_EMOJI.get(g["id"], g["name"]) for g in details_serie.get("genres", [])]) or "Inconnu"
        pays = details_serie.get("production_countries", [{}])[0].get("name", "Inconnu") if details_serie.get("production_countries") else "Inconnu"
        created_by = details_serie.get("created_by", [])
        realisateur = created_by[0].get("name", "Inconnu") if created_by else "Inconnu"
        studios = details_serie.get("production_companies", [])
        studio = studios[0]["name"] if studios else "Inconnu"
        duree = f"{details_serie.get('episode_run_time', [0])[0]} min/épisode" if details_serie.get('episode_run_time') else "Inconnue"
        origine = determiner_origine(details_serie)
        note = convertir_note_tmdb(details_saison.get("vote_average", 0))
        episodes_count = details_saison.get("episode_count", "Inconnu")
        resume = details_saison.get("overview", "Aucun résumé disponible.")
        
        # Traduire le résumé si nécessaire
        if resume != "Aucun résumé disponible." and "en" in details_serie.get('original_language', ''):
            resume_traduit = await traduire_texte(resume)
        else:
            resume_traduit = resume
        
        resume_court = escape(resume_traduit[:250] + "..." if len(resume_traduit) > 250 else resume_traduit)
        poster_path = details_saison.get("poster_path") or details_serie.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None
        
        texte = (
            f"<blockquote>🎬 𝗧𝗶𝘁𝗿𝗲: <a href='t.me/WorldZPrime'>{escape(titre)}</a></blockquote>\n"
            f"🌐 𝗧𝗶𝘁𝗿𝗲 𝗢𝗿𝗶𝗴𝗶𝗻𝗮𝗹: {escape(titre_original)}\n\n"
            f"☾ - 𝗚𝗲𝗻𝗿𝗲𝘀: {escape(genres)}\n\n"
            f"☾ - 𝗔𝗻𝗻é𝗲: {date_sortie.split('-')[0] if date_sortie != 'Inconnue' else 'Inconnue'}\n"
            f"☾ - 𝗣𝗮𝘆𝘀: {escape(pays)}\n"
            f"☾ - 𝗥é𝗮𝗹𝗶𝘀𝗮𝘁𝗲𝘂𝗿: {escape(realisateur)}\n"
            f"☾ - 𝗦𝘁𝘂𝗱𝗶𝗼: {escape(studio)}\n"
            f"☾ - 𝗗𝘂𝗿𝗲‌𝗲: {escape(duree)}\n"
            f"☾ - 𝗦𝗼𝗿𝘁𝗶𝗲: {escape(date_formatee)}\n"
            f"☾ - 𝗘‌𝗽𝗶𝘀𝗼𝗱𝗲𝘀 𝗧𝗼𝘁𝗮𝗹: {escape(str(episodes_count))}\n"
            f"☾ - 𝗢𝗿𝗶𝗴𝗶𝗻𝗲: {escape(origine)}\n"
            f"☾ - 𝗡𝗼𝘁𝗲: {note}\n\n"
            f"╔═══『 ✦ 』═══╗\n"
            f"    <b>@WorldZPrime</b>\n"
            f"╚═══『 ✦ 』═══╝\n\n"
            f"<blockquote expandable>𝗥𝗲𝘀𝘂𝗺𝗲‌:\n{resume_court}</blockquote>"
        )
        
        await callback.answer("✅ Chargement de la saison...")
        await callback.message.delete()
        
        if poster_url:
            image_data = await download_image_hd(poster_url)
            
            if image_data:
                await callback.message.reply_photo(
                    photo=image_data,
                    caption=limiter_texte(texte),
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                await callback.message.reply_photo(
                    photo=poster_url,
                    caption=limiter_texte(texte),
                    parse_mode=enums.ParseMode.HTML
                )
        else:
            await callback.message.reply_text(
                limiter_texte(texte),
                parse_mode=enums.ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Erreur dans season_callback: {e}")
        await callback.answer("⚠️ Erreur lors du traitement", show_alert=True)

@app.on_callback_query(filters.regex("^year_"))
async def year_callback(client, callback):
    try:
        data = callback.data.split("_")
        if len(data) < 3:
            return await callback.answer("❌ Données invalides", show_alert=True)
        
        media_id = int(data[1])
        year = data[2]
        
        details = await get_media_details("movie", media_id)
        if not details:
            return await callback.answer("❌ Film non trouvé", show_alert=True)
        
        formatted = await formater_reponse(details, "movie", None, year)
        
        await callback.answer("✅ Chargement de la version...")
        await callback.message.delete()
        
        if formatted["poster"]:
            image_data = await download_image_hd(formatted["poster"])
            
            if image_data:
                await callback.message.reply_photo(
                    photo=image_data,
                    caption=limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                await callback.message.reply_photo(
                    photo=formatted["poster"],
                    caption=limiter_texte(formatted["texte"]),
                    parse_mode=enums.ParseMode.HTML
                )
        else:
            await callback.message.reply_text(
                limiter_texte(formatted["texte"]),
                parse_mode=enums.ParseMode.HTML
            )
        
    except Exception as e:
        logger.error(f"Erreur dans year_callback: {e}")
        await callback.answer("⚠️ Erreur lors du traitement", show_alert=True)

@app.on_callback_query(filters.regex("^cancel_search"))
async def cancel_search(client, callback):
    try:
        await callback.answer("Recherche annulée")
        await callback.message.delete()
        if callback.message.chat.id in recherches_en_cours:
            del recherches_en_cours[callback.message.chat.id]
    except Exception as e:
        logger.error(f"Erreur dans cancel_search: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage du bot TMDB & AniList avec serveur web...")
    
    # Lance Flask dans un thread séparé
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Démarre le bot Pyrogram dans le thread principal
    try:
        app.run()
    except Exception as e:
        print(f"Erreur: {e}")
        if "SESSION_REVOKED" in str(e):
            print("🗑️ Suppression du fichier de session corrompu...")
            if os.path.exists("tmdb_bot.session"):
                os.remove("tmdb_bot.session")
            print("🔁 Veuillez redémarrer le bot pour créer une nouvelle session")