import requests
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from html import escape
from datetime import datetime

# Configuration TMDB
API_KEY = "f2bed62b5977bce26540055276d0046c"
BASE_URL = "https://api.themoviedb.org/3"
LANGUE = "fr-FR"
TIMEOUT_API = 10

# Configuration Telegram
API_ID = 25926022
API_HASH = "30db27d9e56d854fb5e943723268db32"
BOT_TOKEN = "7703477452:AAFToIODwRMbYkwmxCYikvufYvZVflr9YzU"

# Emojis pour les genres
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
    
    # Genres spécifiques aux animés
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

# Noms des mois en français
MOIS = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

# Initialisation
app = Client("tmdb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
logger = logging.getLogger(__name__)

def limiter_texte(texte, limite=1024):
    """Limite la longueur du texte pour les légendes Telegram"""
    if len(texte) > limite:
        return texte[:limite-3] + "..."
    return texte

def traduire_texte(texte):
    """Fonction de traduction simplifiée"""
    if texte is None:
        return "Aucun résumé disponible."
    return str(texte)

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

async def rechercher_media(query):
    """Recherche un média dans l'API TMDB"""
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

        if not results:
            return None

        media = results[0]
        media_type = media.get("media_type")
        media_id = media.get("id")

        # Si c'est un animé, on force le type à 'tv' pour avoir plus d'informations
        if "anime" in query.lower() or "animé" in query.lower():
            media_type = "tv"

        if media_type not in ["movie", "tv"]:
            return None

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

        return details, media_type, media_id
    except Exception as e:
        logger.error(f"Erreur recherche: {str(e)}")
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

def create_season_buttons(seasons):
    """Crée les boutons pour les saisons"""
    buttons = []
    for season in seasons:
        if season.get("season_number", 0) > 0:  # Ignorer la saison 0
            buttons.append(
                [InlineKeyboardButton(
                    f"📺 Saison {season['season_number']}",
                    callback_data=f"season_{season['season_number']}"
                )]
            )
    return InlineKeyboardMarkup(buttons)

def create_year_buttons(years):
    """Crée les boutons pour les années"""
    buttons = []
    for year in sorted(years, reverse=True):
        buttons.append(
            [InlineKeyboardButton(
                f"🎬 Version {year}",
                callback_data=f"year_{year}"
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
    # Réduction du résumé à 250 caractères
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
        "Envoyez-moi un titre de film, série ou animé pour obtenir des informations détaillées.\n\n"
        "<b>Exemples :</b>\n"
        "- Films: Inception, Titanic\n"
        "- Séries: The Mandalorian, Breaking Bad\n"
        "- Animés: Naruto, Attack on Titan, Sword Art Online\n\n"
        "<i>Je reconnais les genres spécifiques aux animés : Ecchi, Harem, Isekai, Shounen, etc.</i>",
        parse_mode=enums.ParseMode.HTML
    )

@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def search(client, message):
    """Gère les requêtes de recherche"""
    requete = message.text.strip()
    
    if len(requete) < 3:
        return await message.reply_text("🔍 La recherche doit contenir au moins 3 caractères.")
    
    msg = await message.reply_text("🔍 Recherche en cours...")
    try:
        result = await rechercher_media(requete)
        if not result:
            return await msg.edit_text("❌ Aucun résultat trouvé. Essayez avec un autre titre.")
        
        details, media_type, media_id = result
        
        if media_type == "tv":
            seasons = await get_series_seasons(media_id)
            if seasons and len(seasons) > 1:  # Si plusieurs saisons
                await message.reply_text(
                    "📺 <b>Plusieurs saisons disponibles :</b>",
                    reply_markup=create_season_buttons(seasons),
                    parse_mode=enums.ParseMode.HTML
                )
                return await msg.delete()
        
        elif media_type == "movie":
            years = await get_movie_release_years(media_id)
            if years and len(years) > 1:  # Si plusieurs versions
                await message.reply_text(
                    "🎬 <b>Plusieurs versions disponibles :</b>",
                    reply_markup=create_year_buttons(years),
                    parse_mode=enums.ParseMode.HTML
                )
                return await msg.delete()
        
        # Si un seul résultat, envoyer directement les infos
        await send_media_info(message, details, media_type, media_id)
        await msg.delete()
        
    except Exception as e:
        logger.error(f"Erreur recherche: {e}")
        await msg.edit_text("⚠️ Une erreur s'est produite. Veuillez réessayer.")

@app.on_callback_query(filters.regex("^season_"))
async def season_callback(client, callback):
    """Gère le clic sur une saison"""
    try:
        # Vérification initiale du callback
        if not callback or not callback.data:
            logger.error("Callback ou callback.data est None")
            return

        try:
            parts = callback.data.split("_")
            season_num = int(parts[1]) if len(parts) > 1 else None
        except (AttributeError, ValueError, IndexError) as e:
            logger.error(f"Erreur traitement callback data: {e}")
            return

        if not callback.message or not callback.message.reply_to_message:
            logger.error("Message original introuvable")
            return

        original_message = callback.message.reply_to_message
        if not original_message.text:
            logger.error("Texte du message original vide")
            return

        # Recherche du média
        result = await rechercher_media(original_message.text)
        if not result:
            try:
                await callback.answer("❌ Erreur de recherche", show_alert=True)
            except:
                pass
            return
            
        details_serie, media_type, media_id = result
        
        # Vérification du type de média
        if media_type != "tv":
            try:
                await callback.answer("❌ Ce n'est pas une série TV", show_alert=True)
            except:
                pass
            return
        
        # Récupération des détails de la saison
        details_saison = await get_season_details(media_id, season_num)
        if not details_saison:
            try:
                await callback.answer("❌ Saison non trouvée", show_alert=True)
            except:
                pass
            return

        # Formatage des informations
        titre = f"{details_serie.get('name', 'Série inconnue')} (Saison {season_num})"
        titre_original = details_serie.get('original_name', titre)
        date_sortie = details_saison.get('air_date', 'Inconnue')
        date_formatee = formater_date(date_sortie)
        annee = date_sortie.split('-')[0] if date_sortie and date_sortie != 'Inconnue' else 'Inconnue'
        genres = " / ".join([GENRES_EMOJI.get(g["id"], g["name"]) for g in details_serie.get("genres", [])]) if details_serie.get("genres") else "Inconnu"
        pays = details_serie.get("production_countries", [{}])[0].get("name", "Inconnu") if details_serie.get("production_countries") else "Inconnu"
        
        # Gestion du réalisateur avec vérification de la liste created_by
        created_by = details_serie.get("created_by", [])
        realisateur = created_by[0].get("name", "Inconnu") if created_by else "Inconnu"
        
        studios = details_serie.get("production_companies", [])
        studio = studios[0]["name"] if studios else "Inconnu"
        duree = f"{details_serie.get('episode_run_time', [0])[0]} min/épisode" if details_serie.get('episode_run_time') else "Inconnue"
        origine = determiner_origine(details_serie)
        note = convertir_note(details_saison.get("vote_average", 0))
        episodes_count = details_saison.get("episode_count", "Inconnu")
        
        # Gestion du résumé (limité à 250 caractères)
        resume = details_saison.get("overview", "Aucun résumé disponible.")
        resume_court = escape(resume[:250] + "..." if len(resume) > 250 else resume)
        
        # Gestion de l'image
        poster_path = details_saison.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None
        
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
            f"☾ - 𝗘‌𝗽𝗶𝘀𝗼𝗱𝗲𝘀 𝗧𝗼𝘁𝗮𝗹: {escape(str(episodes_count))}\n"
            f"☾ - 𝗢𝗿𝗶𝗴𝗶𝗻𝗲: {escape(origine)}\n"
            f"☾ - 𝗡𝗼𝘁𝗲: {note}\n\n"
            f"╔═══『 ✦ 』═══╗\n"
            f"    <a href='t.me/Godanimes'>@𝗚𝗼𝗱𝗮𝗻𝗶𝗺𝗲𝘀</a>\n"
            f"╚═══『 ✦ 』═══╝\n\n"
            f"<blockquote expandable>𝗥𝗲𝘀𝘂𝗺𝗲‌:\n{resume_court}</blockquote>"
        )
        
        try:
            await callback.answer()
        except:
            pass
        
        if poster_url:
            await original_message.reply_photo(
                photo=poster_url,
                caption=limiter_texte(texte),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await original_message.reply_text(
                limiter_texte(texte),
                parse_mode=enums.ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Erreur season_callback: {e}", exc_info=True)
        try:
            await callback.answer("⚠️ Erreur lors du traitement", show_alert=True)
        except:
            pass

@app.on_callback_query(filters.regex("^year_"))
async def year_callback(client, callback):
    """Gère le clic sur une année"""
    try:
        if not callback or not callback.data:
            return
            
        try:
            year = callback.data.split("_")[1]
        except IndexError:
            return

        if not callback.message or not callback.message.reply_to_message or not callback.message.reply_to_message.text:
            return

        original_message = callback.message.reply_to_message
        
        # Recherche à nouveau les détails pour cette année
        result = await rechercher_media(original_message.text)
        if not result:
            try:
                await callback.answer("❌ Erreur lors de la récupération des données", show_alert=True)
            except:
                pass
            return
        
        details, media_type, media_id = result
        
        try:
            await callback.answer()
        except:
            pass
            
        await send_media_info(original_message, details, media_type, media_id, None, year)
        
    except Exception as e:
        logger.error(f"Erreur year_callback: {e}", exc_info=True)
        try:
            await callback.answer("⚠️ Erreur lors du traitement", show_alert=True)
        except:
            pass

if __name__ == "__main__":
    print("🚀 Lancement du bot...")
    app.run()