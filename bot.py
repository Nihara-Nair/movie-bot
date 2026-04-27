from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os 
from dotenv import load_dotenv
import httpx
import html

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

if not BOT_TOKEN or not TMDB_API_KEY:
    raise ValueError("Missing BOT_TOKEN or TMDB_API_KEY")

# /start command 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /movie <name> 🎬")

async def movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a movie name.\nExample: /movie Avatar")
        return
    
    # 1️⃣ Add loading message
    loading_msg = await update.message.reply_text("⏳ Searching...")
    
    query = " ".join(context.args)
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"User-Agent": "MovieBot/1.0"}
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        if "results" in data and data["results"]:
            results = data["results"][:5] # show top 5 choices

            # 2️⃣ Add inline buttons
            keyboard = []
            for m in results:
                title = m.get("title") or "N/A"
                release_date = m.get("release_date")
                year = release_date[:4] if isinstance(release_date, str) else ""
                
                btn_text = f"🎬 {title} ({year})" if year else f"🎬 {title}"
                movie_id = m.get("id")
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"movie_{movie_id}")])
                
            reply_markup = InlineKeyboardMarkup(keyboard)
            await loading_msg.edit_text("Here is what we found. Tap to see details: 👇", reply_markup=reply_markup)

        else:
             await loading_msg.edit_text("❌ Movie not found")
                  

    except httpx.HTTPStatusError as e:
          print(f"HTTP Error: {e.response.status_code}")
          await loading_msg.edit_text(f"⚠️ TMDB API Error: {e.response.status_code}")
    except Exception as e:
          print(f"ERROR: {e}") 
          await loading_msg.edit_text("⚠️ Error fetching search results")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("movie_"):
        movie_id = data.split("_")[1]
        
        await query.edit_message_text("⏳ Fetching movie details...")

        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {
            "api_key": TMDB_API_KEY
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                headers = {"User-Agent": "MovieBot/1.0"}
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                m = response.json()
                
            title = m.get("title") or "N/A"
            rating = m.get("vote_average") or "N/A"
            if isinstance(rating, float):
                rating = round(rating, 1)
                
            overview = m.get("overview") or "No description available"
            overview = overview[:300] + "..." if len(overview) > 300 else overview
            
            poster_path = m.get("poster_path")

            # Escape HTML to prevent Telegram parsing errors
            title_esc = html.escape(str(title))
            overview_esc = html.escape(str(overview))

            msg = (
                f"🎬 <b>{title_esc}</b>\n"
                f"⭐ Rating: {rating}\n\n"
                f"📖 {overview_esc}"
            )
             
            if poster_path:
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                await query.delete_message()
                try:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=poster_url,
                        caption=msg,
                        parse_mode="HTML"
                    )
                except Exception as photo_err:
                    print(f"Error sending photo: {photo_err}")
                    await context.bot.send_message(chat_id=query.message.chat_id, text=msg, parse_mode="HTML")
            else:
                await query.edit_message_text(text=msg, parse_mode="HTML")

        except Exception as e:
            print(f"ERROR: {e}")
            await query.edit_message_text("⚠️ Error fetching details.")


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("movie", movie))
app.add_handler(CallbackQueryHandler(button_callback))

if __name__=="__main__":
    print("Bot is running...")
    app.run_polling()
