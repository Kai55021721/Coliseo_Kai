# bot.py
import asyncio
import json
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from telegram.constants import ParseMode

import config
import database
from game import Game, ABSURD_SKILLS

# --- CONFIGURACIÓN IMPORTANTE ---
ADMIN_CHAT_ID = 1890046858 # <--- REEMPLAZA CON TU USER ID
CHANNEL_ID = -1003186635788 # <--- REEMPLAZA CON EL ID DE TU CANAL
WEBAPP_URL = "https://Kai55021721.github.io/Coliseo_Kai/webapp/"  # <--- REEMPLAZA CON TU URL DE GITHUB PAGES

# Estados para la conversación
GET_EVIDENCE = range(1)

# Instancias
game = Game(config.GEMINI_API_KEY)
database.initialize_db()

# --- COMANDOS DE ADMIN ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Soy el Heraldo de Kai. Usa /abrir_convocatoria para iniciar un nuevo torneo.")

async def abrir_convocatoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_CHAT_ID: return
    database.clear_all_players()
    game.end_game()
    keyboard = [[InlineKeyboardButton("✨ Inscribirme en el Torneo ✨", web_app=WebAppInfo(url=WEBAPP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text="⚔️ **¡LA CONVOCATORIA HA COMENZADO!** ⚔️\n\nGuerreros, pulsad el botón inferior para forjar vuestra leyenda. La gloria aguarda.",
        reply_markup=reply_markup
    )

async def accion_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_CHAT_ID: return
    
    player_rows = database.get_approved_players()
    if len(player_rows) < 2:
        await update.message.reply_text("No hay suficientes guerreros aprobados para comenzar.")
        return

    game.load_players(player_rows)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🔥 **¡EL COMBATE ETERNO COMIENZA CON {len(game.active_players)} GUERREROS!** 🔥")
    
    # Bucle principal del juego
    while len(game.active_players) > 1:
        # Panel de estado inicial de la ronda
        status_text = f"--- **RONDA CON {len(game.active_players)} GUERREROS** ---\n\n" + game.get_player_list_text()
        status_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=status_text)
        await asyncio.sleep(5)

        pairings, survivors = game.play_next_round()
        
        if survivors:
            for survivor in survivors:
                title = "👑 Campeón" if survivor.is_champion else "🍀 Afortunado"
                await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{title} **{survivor.character_name}** ({survivor.mention()}) avanza directamente.")

        for player1, player2 in pairings:
            # Cuenta regresiva
            countdown_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Próximo combate: **{player1.character_name}** vs **{player2.character_name}**\nComienza en 60 segundos...")
            for i in range(45, 0, -15):
                await asyncio.sleep(15)
                await countdown_message.edit_text(f"Próximo combate: **{player1.character_name}** vs **{player2.character_name}**\nComienza en {i} segundos...")
            await asyncio.sleep(15)
            await countdown_message.edit_text("¡El combate comienza AHORA!")

            # Simulación y resultado
            combat_text, winner, loser = game.simulate_combat(player1, player2)
            await context.bot.send_message(chat_id=CHANNEL_ID, text=combat_text, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(5)

            # Actualizar panel de estado
            new_status_text = status_text.replace(f"• {title} **{loser.character_name}** (@{loser.user_name})", f"• ~{title} **{loser.character_name}** (@{loser.user_name})~ (Eliminado)")
            await status_message.edit_text(new_status_text, parse_mode=ParseMode.MARKDOWN)
            game.active_players = [p for p in game.active_players if p.user_id != loser.user_id] # Actualizar lista interna

            await asyncio.sleep(60) # Pausa de 1 minuto

    # Anuncio del ganador
    if len(game.active_players) == 1:
        winner = game.active_players[0]
        win_message = f"✨ **¡UNA NUEVA LEYENDA HA NACIDO!** ✨\n\nEl combate ha concluido. El único vencedor es...\n\n**¡¡{winner.character_name.upper()} ({winner.mention()})!!**"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=win_message, parse_mode=ParseMode.MARKDOWN)
    
    game.end_game()

# --- FLUJO DE INSCRIPCIÓN ---

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if database.player_exists(user.id):
        await update.message.reply_text("Ya tienes una solicitud en proceso.")
        return ConversationHandler.END

    data = json.loads(update.message.web_app_data.data)
    context.user_data['submission'] = {
        'user_id': user.id, 'user_name': user.username,
        'character_name': data['character_name'], 'specialty': data['specialty']
    }
    await update.message.reply_text("Datos recibidos. Envía ahora la imagen de evidencia para completar tu solicitud.")
    return GET_EVIDENCE

async def get_evidence_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    submission_data = context.user_data.get('submission')
    if not submission_data: return ConversationHandler.END

    user_id = submission_data['user_id']
    is_champion = user_id in config.SUBSCRIBER_USER_IDS
    absurd_skill = random.choice(ABSURD_SKILLS)
    database.add_player_submission(user_id, submission_data['user_name'], submission_data['character_name'], submission_data['specialty'], absurd_skill, is_champion)

    caption = (f"**Nueva Solicitud**\n\n"
               f"**Usuario:** @{submission_data['user_name']} (`{user_id}`)\n"
               f"**Guerrero:** {submission_data['character_name']}\n"
               f"¿Es digno?")
    
    keyboard = [[InlineKeyboardButton("✅ Aprobar", callback_data=f"approve_{user_id}"),
                 InlineKeyboardButton("❌ Rechazar", callback_data=f"reject_{user_id}")]]
    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text("Tu ofrenda ha sido enviada para su juicio.")
    context.user_data.clear()
    return ConversationHandler.END

async def handle_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id_str = query.data.split('_')
    user_id = int(user_id_str)
    
    player_info = database.get_player_info(user_id)
    if not player_info:
        await query.edit_message_caption(caption=f"Decisión ya procesada para el usuario {user_id}.", reply_markup=None)
        return

    character_name = player_info[0]
    if action == "approve":
        database.approve_player(user_id)
        await query.edit_message_caption(caption=f"✅ APROBADO: {character_name}", reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text="¡Kai ha aceptado tu ofrenda! Has sido invocado al Coliseo.")
    elif action == "reject":
        database.reject_player(user_id)
        await query.edit_message_caption(caption=f"❌ RECHAZADO: {character_name}", reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text="Tu ofrenda no ha sido suficiente. Tu alma ha sido devuelta.")

def main():
    print("Iniciando el bot del Coliseo...")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data)],
        states={GET_EVIDENCE: [MessageHandler(filters.PHOTO, get_evidence_image)]},
        fallbacks=[],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("abrir_convocatoria", abrir_convocatoria))
    app.add_handler(CommandHandler("accion", accion_command))
    app.add_handler(CallbackQueryHandler(handle_admin_decision))

    print("Bot en línea.")
    app.run_polling()

if __name__ == '__main__':
    main()