# bot.py
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from telegram.constants import ParseMode

import config
import database
from game import Game, ABSURD_SKILLS

# --- CONFIGURACIÓN ---
ADMIN_CHAT_ID = 1890046858
CHANNEL_ID = -1003186635788
BOT_USERNAME = "Coliseo_Shitsumon_Kai_bot"

# --- ESTADOS PARA LA CONVERSACIÓN ---
GET_EVIDENCE = range(1)

# --- INSTANCIAS ---
game = Game(config.GEMINI_API_KEY)
database.initialize_db()

# --- COMANDOS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Da la bienvenida y explica cómo inscribirse."""
    await update.message.reply_text(
        "Saludos, guerrero. Soy el Heraldo de Kai. Si las puertas del Templo están abiertas, "
        "puedes unirte al torneo con el comando: \n\n"
        "`/invocacion <Tu Nombre de Guerrero> | <Tu Dominio de Combate>`\n\n"
        "Si eres el administrador, usa /abrir_convocatoria para iniciar el evento.",
        parse_mode=ParseMode.MARKDOWN
    )

async def abrir_convocatoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Anuncia la apertura de inscripciones en el canal."""
    if update.message.from_user.id != ADMIN_CHAT_ID: return
    
    database.clear_all_players()
    game.end_game()
    game.is_invocation_open = True
    
    announcement_text = (
        f"⚔️ **¡LA CONVOCATORIA HA COMENZADO!** ⚔️\n\n"
        f"Guerreros, la arena os espera. Para forjar vuestra leyenda, "
        f"iniciad una conversación con nuestro heraldo (`@{BOT_USERNAME}`) "
        f"y usad el comando `/invocacion` para registraros."
    )
    
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=announcement_text,
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text("Anuncio de convocatoria publicado en el canal.")

# --- FLUJO DE INSCRIPCIÓN POR COMANDOS ---

async def invocacion_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paso 1: Recibe el comando de inscripción y los datos."""
    if not game.is_invocation_open:
        await update.message.reply_text("Las puertas del Templo están cerradas. No puedes inscribirte ahora.")
        return ConversationHandler.END

    user = update.message.from_user
    if database.player_exists(user.id):
        await update.message.reply_text("Ya tienes una solicitud en proceso o has sido aceptado.")
        return ConversationHandler.END

    try:
        args_text = " ".join(context.args)
        if '|' not in args_text:
            await update.message.reply_text("Formato incorrecto. Usa: `/invocacion Nombre | Dominio`")
            return ConversationHandler.END
            
        character_name, specialty = [part.strip() for part in args_text.split('|', 1)]
        if not character_name or not specialty:
            await update.message.reply_text("Debes proporcionar un nombre y un dominio.")
            return ConversationHandler.END

        # Guardar datos temporalmente para el siguiente paso
        context.user_data['submission'] = {
            'user_id': user.id,
            'user_name': user.username,
            'character_name': character_name,
            'specialty': specialty
        }

        await update.message.reply_text(
            f"Guerrero '{character_name}' registrado. Para completar tu invocación, **envía ahora la imagen de evidencia** en este chat."
        )
        return GET_EVIDENCE

    except Exception as e:
        await update.message.reply_text("Ha ocurrido un error al procesar tu solicitud. Inténtalo de nuevo.")
        print(f"Error en invocacion_start: {e}")
        return ConversationHandler.END

async def get_evidence_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paso 2: Recibe la foto y la envía al admin para aprobación."""
    submission_data = context.user_data.get('submission')
    if not submission_data:
        await update.message.reply_text("Parece que ha habido un problema. Por favor, empieza de nuevo con /invocacion.")
        return ConversationHandler.END
    
    user_id = submission_data['user_id']
    absurd_skill = random.choice(ABSURD_SKILLS)
    
    database.add_player_submission(user_id, submission_data['user_name'], submission_data['character_name'], submission_data['specialty'], absurd_skill)
    
    caption = (f"**Nueva Solicitud**\n\n"
               f"**Usuario:** @{submission_data['user_name']} (`{user_id}`)\n"
               f"**Guerrero:** {submission_data['character_name']}\n\n"
               f"¿Cómo deseas clasificar a este guerrero?")
    
    keyboard = [[InlineKeyboardButton("✅ Aprobar como Aspirante", callback_data=f"approve_aspirant_{user_id}"),
                 InlineKeyboardButton("👑 Aprobar como Campeón", callback_data=f"approve_champion_{user_id}")],
                [InlineKeyboardButton("❌ Rechazar", callback_data=f"reject_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        await update.message.reply_text("Tu ofrenda ha sido enviada para su juicio. Recibirás un cuervo con la decisión final.")
    except Exception as e:
        print(f"ERROR AL ENVIAR NOTIFICACIÓN AL ADMIN: {e}")
        await update.message.reply_text("Hubo un error al contactar al Templo. Por favor, inténtalo de nuevo más tarde.")
        
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la conversación si el usuario se atasca."""
    context.user_data.clear()
    await update.message.reply_text("Proceso de inscripción cancelado.")
    return ConversationHandler.END

# (El resto de funciones como accion_command, handle_admin_decision, etc., no cambian y son necesarias)
async def handle_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #... (código idéntico a la versión anterior)
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    action = "_".join(parts[:-1])
    user_id = int(parts[-1])
    player_info = database.get_player_info(user_id)
    if not player_info:
        await query.edit_message_caption(caption=f"Decisión ya procesada para el usuario {user_id}.", reply_markup=None)
        return
    character_name = player_info[0]
    if action == "approve_aspirant":
        database.approve_player(user_id, is_champion=False)
        await query.edit_message_caption(caption=f"✅ APROBADO (Aspirante): {character_name}", reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text="¡Kai ha aceptado tu ofrenda! Has sido invocado como un Aspirante.")
    elif action == "approve_champion":
        database.approve_player(user_id, is_champion=True)
        await query.edit_message_caption(caption=f"👑 APROBADO (Campeón): {character_name}", reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text="¡Kai te reconoce como un Campeón! Ocupa tu lugar de honor.")
    elif action == "reject":
        database.reject_player(user_id)
        await query.edit_message_caption(caption=f"❌ RECHAZADO: {character_name}", reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text="Tu ofrenda no ha sido suficiente. Tu alma ha sido devuelta.")

async def accion_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #... (código idéntico a la versión anterior)
    if update.message.from_user.id != ADMIN_CHAT_ID: return
    game.is_invocation_open = False
    player_rows = database.get_approved_players()
    if len(player_rows) < 2:
        await update.message.reply_text("No hay suficientes guerreros aprobados para comenzar (se necesitan al menos 2).")
        return
    game.load_players(player_rows)
    await update.message.reply_text(f"Iniciando la acción en el canal con {len(game.active_players)} guerreros...")
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🔥 **¡EL COMBATE ETERNO COMIENZA!** 🔥", parse_mode=ParseMode.MARKDOWN)
    while len(game.active_players) > 1:
        status_text = game.start_new_round()
        status_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=status_text, parse_mode=ParseMode.MARKDOWN)
        await asyncio.sleep(5)
        pairings, survivors = game.play_next_round_pairings()
        active_survivors = []
        if survivors:
            for survivor in survivors:
                title = "👑 Campeón" if survivor.is_champion else "🍀 Afortunado"
                await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{title} **{survivor.character_name}** ({survivor.mention()}) avanza directamente.", parse_mode=ParseMode.MARKDOWN)
                active_survivors.append(survivor)
        game.active_players = [p for p in game.active_players if p not in active_survivors]
        for player1, player2 in pairings:
            countdown_msg_text = f"Próximo combate: **{player1.character_name}** vs **{player2.character_name}**"
            countdown_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{countdown_msg_text}\nComienza en 60 segundos...", parse_mode=ParseMode.MARKDOWN)
            for i in range(45, 0, -15):
                await asyncio.sleep(15)
                await countdown_message.edit_text(f"{countdown_msg_text}\nComienza en {i} segundos...", parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(15)
            await countdown_message.edit_text(f"¡El combate entre **{player1.character_name}** y **{player2.character_name}** comienza AHORA!", parse_mode=ParseMode.MARKDOWN)
            combat_text, winner, loser = game.simulate_combat(player1, player2)
            await context.bot.send_message(chat_id=CHANNEL_ID, text=combat_text, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(5)
            active_survivors.append(winner)
            status_text = game.update_status_text(status_text, loser)
            await status_message.edit_text(status_text, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(60)
        game.active_players = active_survivors
    if len(game.active_players) == 1:
        winner = game.active_players[0]
        win_message = (f"✨ **¡UNA NUEVA LEYENDA HA NACIDO!** ✨\n\nEl combate ha concluido. El único vencedor es...\n\n"
                       f"**¡¡{winner.character_name.upper()} ({winner.mention()})!!**\n\n"
                       f"¡Su nombre será grabado en las estrellas!")
        await context.bot.send_message(chat_id=CHANNEL_ID, text=win_message, parse_mode=ParseMode.MARKDOWN)
    game.end_game()

def main():
    """Función principal que inicia el bot."""
    print("Iniciando el bot del Coliseo (Modo Telegram)...")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("invocacion", invocacion_start)],
        states={
            GET_EVIDENCE: [MessageHandler(filters.PHOTO, get_evidence_image)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        conversation_timeout=600 # 10 minutos para enviar la foto
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("abrir_convocatoria", abrir_convocatoria))
    app.add_handler(CommandHandler("accion", accion_command))
    app.add_handler(CallbackQueryHandler(handle_admin_decision))
    
    print("Bot en línea. A la espera de la llamada de los guerreros.")
    app.run_polling()

if __name__ == '__main__':
    main()