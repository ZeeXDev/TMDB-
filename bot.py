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

# Configuration Flask pour Render.com
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "🤖 Bot TMDB en ligne et fonctionnel! | @Godanimes"

@app_web.route('/health')
def health():
    return {"status": "ok", "timestamp": time.time()}

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Lance Flask dans un thread séparé
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

API_KEY = "f2bed62b5977bce26540055276d0046c"
BASE_URL = "https://api.themoviedb.org/3"
LANGUE = "fr-FR"
TIMEOUT_API = 30  

API_ID = 25926022
API_HASH = "30db27d9e56d854fb5e943723268db32"
BOT_TOKEN = "7703477452:AAFToIODwRMbYkwmxCYikvufYvZVflr9YzU"

GENRES_EMOJI = {
    # Genres de films/séries
    28: "🔫 Action",
    12: "🌍 Aventure",
    16: "🎨 Animation",
    35: "😂 Comédie",
    80: "🔪 Crime",
    99: "📽 Documentaire",
    18: "🎭 Drame",
    10751: "👪 Familial",
    14: "⚔ Fantaisie",
    36: "📜 Historique",
    27: "👻 Horreur",
    10402: "🎵 Musique",
    9648: "🕵️ Mystère",
    10749: "💘 Romance",
    878: "👽 Science-Fiction",
    10770: "📺 Téléfilm",
    53: "🎭 Thriller",
    10752: "💥 Guerre",
    37: "🤠 Western",
    10759: "🎬 Action & Aventure",
    10762: "👶 Kids",
    10763: "🌐 News",
    10764: "🏟 Reality",
    10765: "🚀 Sci-Fi & Fantasy",
    10766: "📺 Soap",
    10767: "🗣 Talk",
    10768: "⚔ War & Politics",
    
    # Genres animés
    1001: "😳 Ecchi",
    1002: "👨‍👩‍👧‍👦 Harem",
    1003: "🌌 Isekai",
    1004: "👊 Shounen",
    1005: "💝 Shoujo",
    1006: "🎯 Seinen",
    1007: "💄 Josei",
    1008: "🤖 Mecha",
    1009: "🏫 Slice of Life",
    1010: "🎤 Idol",
    1011: "🧠 Psychologique",
    1012: "👻 Supernaturel",
    1013: "⚔️ Dark Fantasy",
    1014: "🤣 Comédie romantique",
    1015: "👮‍♂️ Policier",
    1016: "🏟️ Sports",
    1017: "🍳 Cuisine",
    1018: "🎮 Jeu vidéo",
    1019: "🕰️ Historique",
    1020: "🧊 Tranche de vie"
}

MOIS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

# Initialisation
app = Client("tmdb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
logger = logging.getLogger(__name__)

recherches_en_cours = {}

def limiter_texte(texte, limite=1024):
    """Limite la longueur du texte pour les légendes Telegram"""
    if len(texte) > limite:
        return texte[:limite-3] + "..."
    return texte

def convertir_note(note):
    """Convertit la note en étoiles"""
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
        
        # Détection des animés en premier
        if any(k in keywords for k in ["anime", "manga", "animé"]):
            # Détection des sous-genres
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

        # Filtrer seulement les films et séries
        media_results = [r for r in results if r.get("media_type") in ["movie", "tv"]]
        return media_results[:20]  # Limiter à 10 résultats maximum
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout recherche TMDB pour: {query}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Erreur connexion TMDB pour: {query}")
        return None
    except Exception as e:
        logger.error(f"Erreur recherche multiple: {str(e)}")
        return None

async def get_media_details(media_type, media_id):
    """Récupère les détails complets d'un média"""
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

        # Détection spéciale pour les animés
        if media_type == "tv":
            keywords = [k.get("name", "").lower() for k in details.get("keywords", {}).get("results", [])]
            if "anime" in keywords or "animation" in keywords:
                # Ajout de genres spécifiques aux animés
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
    """Récupère les saisons d'une série"""
    try:
        response = requests.get(
            f"{BASE_URL}/tv/{series_id}",
            params={"api_key": API_KEY, "language": LANGUE},
            timeout=TIMEOUT_API
        )
        details = response.json()
        return details.get("seasons", [])
    except Exception as e:
        logger.warning(f"Erreur get_series_seasons: {e}")
        return []

async def get_season_details(series_id, season_num):
    """Récupère les détails d'une saison spécifique"""
    try:
        response = requests.get(
            f"{BASE_URL}/tv/{series_id}/season/{season_num}",
            params={"api_key": API_KEY, "language": LANGUE},
            timeout=TIMEOUT_API
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Erreur get_season_details: {e}")
        return None

async def get_movie_release_years(movie_id):
    """Récupère les années de sortie pour les films"""
    try:
        response = requests.get(
            f"{BASE_URL}/movie/{movie_id}/release_dates",
            params={"api_key": API_KEY},
            timeout=TIMEOUT_API
        )
        dates = response.json().get("results", [])
        return list({d.get("release_date", "")[:4] for d in dates if d.get("release_date")})
    except Exception as e:
        logger.warning(f"Erreur get_movie_release_years: {e}")
        return []

def create_selection_buttons(results):
    """Crée les boutons de sélection pour les résultats multiples"""
    buttons = []
    for result in results:
        media_type = result.get("media_type")
        title = result.get("title") or result.get("name") or "Sans titre"
        year = result.get("release_date", result.get("first_air_date", ""))[:4]
        
        emoji = "🎬" if media_type == "movie" else "📺"
        button_text = f"{emoji} {title}"
        if year:
            button_text += f" ({year})"
            
        # Limiter la longueur du texte du bouton
        if len(button_text) > 35:
            button_text = button_text[:32] + "..."
            
        buttons.append(
            [InlineKeyboardButton(
                button_text,
                callback_data=f"select_{media_type}_{result['id']}"
            )]
        )
    
    # Bouton annuler
    buttons.append([InlineKeyboardButton("❌ Annuler", callback_data="cancel_search")])
    
    return InlineKeyboardMarkup(buttons)

def create_season_buttons(seasons, media_id):
    """Crée les boutons pour les saisons"""
    buttons = []
    for season in seasons:
        if season.get("season_number", 0) > 0:  # Ignorer la saison 0
            buttons.append(
                [InlineKeyboardButton(
                    f"📺 Saison {season['season_number']}",
                    callback_data=f"season_{media_id}_{season['season_number']}"
                )]
            )
    return InlineKeyboardMarkup(buttons)

def create_year_buttons(years, media_id):
    """Crée les boutons pour les années"""
    buttons = []
    for year in sorted(years, reverse=True):
        buttons.append(
            [InlineKeyboardButton(
                f"🎬 Version {year}",
                callback_data=f"year_{media_id}_{year}"
            )]
        )
    return InlineKeyboardMarkup(buttons)

def formater_reponse(details, media_type, season_num=None, year=None):
    """Formatage des informations du média"""
    titre = details.get("title") or details.get("name") or "Inconnu"
    titre_original = details.get("original_title") or details.get("original_name") or titre
    
    # Gestion spéciale pour les saisons de séries
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
    
    # Gestion spéciale pour les versions de films
    if media_type == "movie" and year:
        titre = f"{titre} ({year})"
    
    genres = " / ".join([GENRES_EMOJI.get(g["id"], g["name"]) for g in details.get("genres", [])]) or "Inconnu"
    note = convertir_note(details.get("vote_average", 0))
    pays = details.get("production_countries", [{}])[0].get("name", "Inconnu") if details.get("production_countries") else "Inconnu"
    
    if media_type == "movie":
        realisateur = next(
            (p["name"] for p in details.get("credits", {}).get("crew", []) 
            if p.get("job") == "Director"), "Inconnu"
        )
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
    resume_court = escape(resume[:250] + "..." if len(resume) > 250 else resume)
    
    # Construction du texte
    texte = (
        f"<blockquote>🎬 𝗧𝗶𝘁𝗿𝗲: <a href='t.me/Godanimes'>{escape(titre)}</a></blockquote>\n"
        f"🌐 𝗧𝗶𝘁𝗿𝗲 𝗢𝗿𝗶𝗴𝗶𝗻𝗮𝗹: {escape(titre_original)}\n\n"
        f"☾ - 𝗚𝗲𝗻𝗿𝗲𝘀: {escape(genres)}\n\n"
        f"☾ - 𝗔𝗻𝗻é𝗲: {escape(annee)}\n"
        f"☾ - 𝗣𝗮𝘆𝘀: {escape(pays)}\n"
        f"☾ - 𝗥é𝗮𝗹𝗶𝘀𝗮𝘁𝗲𝘂𝗿: {escape(realisateur)}\n"
        f"☾ - 𝗦𝘁𝘂𝗱𝗶𝗼: {escape(studio)}\n"
        f"☾ - 𝗗𝘂𝗿𝗲‌𝗲: {escape(duree)}\n"
        f"☾ - 𝗦𝗼𝗿𝘁𝗶𝗲: {escape(date_formatee)}\n"
    )
    
    # Ajout du nombre d'épisodes pour les séries
    if media_type == "tv":
        texte += f"☾ - 𝗘‌𝗽𝗶𝘀𝗼𝗱𝗲𝘀 𝗧𝗼𝘁𝗮𝗹: {escape(str(episode_count))}\n"
    
    texte += (
        f"☾ - 𝗢𝗿𝗶𝗴𝗶𝗻𝗲: {escape(origine)}\n"
        f"☾ - 𝗡𝗼𝘁𝗲: {note}\n\n"
        f"╔═══『 ✦ 』═══╗\n"
        f"    <a href='t.me/Godanimes'>@𝗚𝗼𝗱𝗮𝗻𝗶𝗺𝗲𝘀</a>\n"
        f"╚═══『 ✦ 』═══╝\n\n"
        f"<blockquote expandable>𝗥𝗲𝘀𝘂𝗺𝗲‌:\n{resume_court}</blockquote>"
    )
    
    return {
        "texte": texte,
        "poster": f"https://image.tmdb.org/t/p/original{details.get('poster_path')}" if details.get('poster_path') else None
    }

async def send_media_info(message, details, media_type, media_id, season_num=None, year=None):
    """Envoie les informations du média"""
    formatted = formater_reponse(details, media_type, season_num, year)
    
    if formatted["poster"]:
        await message.reply_photo(
            photo=formatted["poster"],
            caption=limiter_texte(formatted["texte"]),
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply_text(
            limiter_texte(formatted["texte"]),
            parse_mode=enums.ParseMode.HTML
        )

@app.on_message(filters.command(["start", "aide"]))
async def demarrage(client, message):
    """Gère la commande start"""
    await message.reply_text(
        "🍿 <b>Bienvenue sur le Bot Cinéma & Animé !</b>\n\n"
        "Envoyez-moi simplement le nom d'un film ou série et je vous trouverai toutes les versions disponibles !\n\n"
        "<b>Exemples :</b>\n"
        "- Le Comte de Monte-Cristo\n"
        "- Avatar\n"
        "- Naruto\n"
        "- The Mandalorian\n\n"
        "<i>Je vous proposerai tous les résultats trouvés sur TMDB !</i>",
        parse_mode=enums.ParseMode.HTML
    )

@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def search(client, message):
    """Gère les requêtes de recherche avec sélection multiple"""
    requete = message.text.strip()
    
    if len(requete) < 3:
        return await message.reply_text("🔍 La recherche doit contenir au moins 3 caractères.")
    
    msg = await message.reply_text("🔍 Recherche en cours sur TMDB...")
    
    try:
        # Recherche multiple sur TMDB
        results = await rechercher_media_multiple(requete)
        
        if results is None:
            return await msg.edit_text("🌐 <b>Problème de connexion avec TMDB</b>\n\nVeuillez réessayer dans quelques secondes.")
        
        if not results:
            return await msg.edit_text("❌ Aucun résultat trouvé sur TMDB. Essayez avec un autre titre.")
        
        if len(results) == 1:
            # Un seul résultat, afficher directement
            result = results[0]
            details = await get_media_details(result["media_type"], result["id"])
            if details:
                await send_media_info(message, details, result["media_type"], result["id"])
                await msg.delete()
                
                # Stocker les infos pour les callbacks
                recherches_en_cours[message.chat.id] = {
                    "media_type": result["media_type"],
                    "media_id": result["id"],
                    "details": details
                }
                
                # Proposer les saisons si c'est une série
                if result["media_type"] == "tv":
                    seasons = await get_series_seasons(result["id"])
                    if seasons and len(seasons) > 1:
                        await message.reply_text(
                            "📺 <b>Plusieurs saisons disponibles :</b>",
                            reply_markup=create_season_buttons(seasons, result["id"]),
                            parse_mode=enums.ParseMode.HTML
                        )
                
                # Proposer les années si c'est un film
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
            # Multiple résultats, afficher les boutons de sélection
            await msg.edit_text(
                f"🎭 <b>J'ai trouvé {len(results)} résultats sur TMDB pour \"{requete}\"</b>\n\n"
                "📋 <i>Sélectionnez celui qui vous intéresse :</i>",
                reply_markup=create_selection_buttons(results),
                parse_mode=enums.ParseMode.HTML
            )
            
            # Stocker les résultats pour le callback
            recherches_en_cours[message.chat.id] = {
                "results": results,
                "query": requete
            }
            
    except Exception as e:
        logger.error(f"Erreur recherche: {e}")
        await msg.edit_text("⚠️ Une erreur s'est produite. Veuillez réessayer.")

@app.on_callback_query(filters.regex("^select_"))
async def select_callback(client, callback):
    """Gère le clic sur une sélection de média"""
    try:
        data = callback.data.split("_")
        if len(data) < 3:
            return await callback.answer("❌ Données invalides", show_alert=True)
        
        media_type = data[1]
        media_id = int(data[2])
        
        # Récupérer les détails complets
        details = await get_media_details(media_type, media_id)
        if not details:
            return await callback.answer("❌ Erreur de chargement", show_alert=True)
        
        # Afficher les informations
        formatted = formater_reponse(details, media_type)
        
        await callback.answer()
        await callback.message.delete()
        
        if formatted["poster"]:
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
        
        # Stocker les infos pour les callbacks
        recherches_en_cours[callback.message.chat.id] = {
            "media_type": media_type,
            "media_id": media_id,
            "details": details,
            "message_id": msg.id
        }
        
        # Proposer les saisons si c'est une série
        if media_type == "tv":
            seasons = await get_series_seasons(media_id)
            if seasons and len(seasons) > 1:
                await callback.message.reply_text(
                    "📺 <b>Plusieurs saisons disponibles :</b>",
                    reply_markup=create_season_buttons(seasons, media_id),
                    parse_mode=enums.ParseMode.HTML
                )
        
        # Proposer les années si c'est un film
        elif media_type == "movie":
            years = await get_movie_release_years(media_id)
            if years and len(years) > 1:
                await callback.message.reply_text(
                    "🎬 <b>Plusieurs versions disponibles :</b>",
                    reply_markup=create_year_buttons(years, media_id),
                    parse_mode=enums.ParseMode.HTML
                )
            
    except Exception as e:
        logger.error(f"Erreur select_callback: {e}", exc_info=True)
        await callback.answer("⚠️ Erreur lors de la sélection", show_alert=True)

@app.on_callback_query(filters.regex("^season_"))
async def season_callback(client, callback):
    """Gère le clic sur une saison"""
    try:
        data = callback.data.split("_")
        if len(data) < 3:
            return await callback.answer("❌ Données invalides", show_alert=True)
        
        media_id = int(data[1])
        season_num = int(data[2])
        
        # Récupérer les détails de la série
        details_serie = await get_media_details("tv", media_id)
        if not details_serie:
            return await callback.answer("❌ Série non trouvée", show_alert=True)
        
        # Récupérer les détails de la saison
        details_saison = await get_season_details(media_id, season_num)
        if not details_saison:
            return await callback.answer("❌ Saison non trouvée", show_alert=True)

        # Formatage des informations de la saison
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
        note = convertir_note(details_saison.get("vote_average", 0))
        episodes_count = details_saison.get("episode_count", "Inconnu")
        resume = details_saison.get("overview", "Aucun résumé disponible.")
        resume_court = escape(resume[:250] + "..." if len(resume) > 250 else resume)
        poster_path = details_saison.get("poster_path") or details_serie.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None
        
        texte = (
            f"<blockquote>🎬 𝗧𝗶𝘁𝗿𝗲: <a href='t.me/Godanimes'>{escape(titre)}</a></blockquote>\n"
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
            f"    <a href='t.me/Godanimes'>@𝗚𝗼𝗱𝗮𝗻𝗶𝗺𝗲𝘀</a>\n"
            f"╚═══『 ✦ 』═══╝\n\n"
            f"<blockquote expandable>𝗥𝗲𝘀𝘂𝗺𝗲‌:\n{resume_court}</blockquote>"
        )
        
        await callback.answer()
        await callback.message.delete()
        
        if poster_url:
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
        logger.error(f"Erreur season_callback: {e}", exc_info=True)
        await callback.answer("⚠️ Erreur lors du traitement", show_alert=True)

@app.on_callback_query(filters.regex("^year_"))
async def year_callback(client, callback):
    """Gère le clic sur une année"""
    try:
        data = callback.data.split("_")
        if len(data) < 3:
            return await callback.answer("❌ Données invalides", show_alert=True)
        
        media_id = int(data[1])
        year = data[2]
        
        # Récupérer les détails du film
        details = await get_media_details("movie", media_id)
        if not details:
            return await callback.answer("❌ Film non trouvé", show_alert=True)
        
        # Afficher les informations avec l'année spécifique
        formatted = formater_reponse(details, "movie", None, year)
        
        await callback.answer()
        await callback.message.delete()
        
        if formatted["poster"]:
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
        logger.error(f"Erreur year_callback: {e}", exc_info=True)
        await callback.answer("⚠️ Erreur lors du traitement", show_alert=True)

@app.on_callback_query(filters.regex("^cancel_search"))
async def cancel_search(client, callback):
    """Annule la recherche"""
    await callback.answer("Recherche annulée")
    await callback.message.delete()
    # Nettoyer la recherche en cours
    if callback.message.chat.id in recherches_en_cours:
        del recherches_en_cours[callback.message.chat.id]

if __name__ == "__main__":
    print("🚀 Démarrage du bot TMDB avec serveur web...")
    
    # Démarre le bot Pyrogram dans le thread principal
    try:
        app.run()
    except Exception as e:
        print(f"Erreur: {e}")
