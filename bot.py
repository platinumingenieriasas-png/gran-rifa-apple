import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ── CONFIGURACIÓN ──────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8529825261:AAHWm_zaEzLpevxYj-rr6DScbf6JIn8D1GA")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5012720317"))
TOTAL_BOLETOS = 200
PRECIO_CONTADO = 55000
PRECIO_CUOTA = 11000
CUOTAS = 5
DATA_FILE = "boletos.json"
# ───────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ELIGIENDO_BOLETO, ELIGIENDO_PAGO, INGRESANDO_NOMBRE, INGRESANDO_TELEFONO = range(4)

def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"reservados": {}, "confirmados": []}

def guardar_datos(datos):
    with open(DATA_FILE, "w") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🍎 *¡Bienvenido a la Gran Rifa Apple!*\n\n"
        "🏆 *Premios:*\n"
        "📱 iPhone 17 256GB\n"
        "⌚ Apple Watch SE 40mm\n"
        "🎧 AirPods 4 con Cancelación de Ruido\n\n"
        "💰 *Precio:* $55.000 COP contado ó 5 cuotas de $11.000/semana\n\n"
        "🎯 *El sorteo se realizará una vez se vendan los 200 boletos.*\n"
        "📺 Sorteo en vivo para total transparencia.\n\n"
        "Usa los botones para participar 👇"
    )
    teclado = [
        [InlineKeyboardButton("🎟 Ver boletos disponibles", callback_data="ver_boletos")],
        [InlineKeyboardButton("📊 Estado de la rifa", callback_data="estado")],
    ]
    await update.message.reply_text(
        texto,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

async def ver_boletos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    datos = cargar_datos()
    reservados = set(datos["reservados"].keys())
    confirmados = set(str(n) for n in datos["confirmados"])
    pagina = context.user_data.get("pagina", 0)
    inicio = pagina * 50 + 1
    fin = min(inicio + 49, TOTAL_BOLETOS)
    lineas = []
    for i in range(inicio, fin + 1):
        key = str(i)
        num = str(i).zfill(3)
        if key in confirmados:
            lineas.append(f"🔴{num}")
        elif key in reservados:
            lineas.append(f"🟡{num}")
        else:
            lineas.append(f"🟢{num}")
    texto = (
        f"🎟 *Boletos {inicio}-{fin}*\n\n"
        + "  ".join(lineas) +
        "\n\n🟢 Disponible  🟡 Reservado  🔴 Vendido"
    )
    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton("⬅ Anteriores", callback_data=f"pagina_{pagina-1}"))
    if fin < TOTAL_BOLETOS:
        nav.append(InlineKeyboardButton("Siguientes ➡", callback_data=f"pagina_{pagina+1}"))
    teclado = []
    if nav:
        teclado.append(nav)
    teclado.append([InlineKeyboardButton("🎯 Reservar mi boleto", callback_data="reservar")])
    teclado.append([InlineKeyboardButton("🔙 Volver", callback_data="inicio")])
    await query.edit_message_text(
        texto,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

async def cambiar_pagina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pagina = int(query.data.split("_")[1])
    context.user_data["pagina"] = pagina
    await ver_boletos(update, context)

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    datos = cargar_datos()
    confirmados = len(datos["confirmados"])
    reservados = len(datos["reservados"])
    disponibles = TOTAL_BOLETOS - confirmados - reservados
    pct = round((confirmados / TOTAL_BOLETOS) * 100)
    barra = "█" * (pct // 10) + "░" * (10 - pct // 10)
    texto = (
        f"📊 *Estado de la Gran Rifa Apple*\n\n"
        f"`{barra}` {pct}%\n\n"
        f"🟢 Disponibles: *{disponibles}*\n"
        f"🟡 Reservados: *{reservados}*\n"
        f"🔴 Vendidos: *{confirmados}*\n"
        f"📦 Total: *{TOTAL_BOLETOS}*\n\n"
        f"🎯 ¡Faltan *{TOTAL_BOLETOS - confirmados}* boletos para el sorteo!"
    )
    teclado = [
        [InlineKeyboardButton("🎟 Ver boletos", callback_data="ver_boletos")],
        [InlineKeyboardButton("🎯 Reservar", callback_data="reservar")],
        [InlineKeyboardButton("🔙 Volver", callback_data="inicio")],
    ]
    await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(teclado))

async def iniciar_reserva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎯 *Reservar boleto*\n\nEscribe el número que deseas reservar (del 1 al 200):",
        parse_mode="Markdown"
    )
    return ELIGIENDO_BOLETO

async def recibir_boleto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        num = int(texto)
        if num < 1 or num > TOTAL_BOLETOS:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Por favor escribe un número válido entre 1 y 200.")
        return ELIGIENDO_BOLETO
    datos = cargar_datos()
    key = str(num)
    if key in datos["reservados"] or num in datos["confirmados"]:
        await update.message.reply_text(
            f"😔 El boleto *#{str(num).zfill(3)}* ya no está disponible.\n\nEscribe otro número:",
            parse_mode="Markdown"
        )
        return ELIGIENDO_BOLETO
    context.user_data["boleto"] = num
    teclado = [
        [InlineKeyboardButton("💵 Contado — $55.000", callback_data="pago_contado")],
        [InlineKeyboardButton("📅 5 Cuotas — $11.000/semana", callback_data="pago_cuotas")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")],
    ]
    await update.message.reply_text(
        f"✅ El boleto *#{str(num).zfill(3)}* está disponible.\n\n💰 ¿Cómo deseas pagar?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(teclado)
    )
    return ELIGIENDO_PAGO

async def recibir_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pago = query.data.split("_")[1]
    context.user_data["pago"] = pago
    pago_texto = "Contado — $55.000 COP" if pago == "contado" else "5 cuotas de $11.000/semana"
    context.user_data["pago_texto"] = pago_texto
    await query.edit_message_text(
        f"💳 Forma de pago: *{pago_texto}*\n\n👤 ¿Cuál es tu nombre completo?",
        parse_mode="Markdown"
    )
    return INGRESANDO_NOMBRE

async def recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text.strip()
    await update.message.reply_text("📱 ¿Cuál es tu número de celular?")
    return INGRESANDO_TELEFONO

async def recibir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telefono = update.message.text.strip()
    context.user_data["telefono"] = telefono
    boleto = context.user_data["boleto"]
    nombre = context.user_data["nombre"]
    pago_texto = context.user_data["pago_texto"]
    user = update.effective_user
    key = str(boleto)
    datos = cargar_datos()
    if key in datos["reservados"] or boleto in datos["confirmados"]:
        await update.message.reply_text("😔 Lo sentimos, ese boleto acaba de ser reservado. Intenta con otro.")
        return ConversationHandler.END
    datos["reservados"][key] = {
        "nombre": nombre,
        "telefono": telefono,
        "pago": pago_texto,
        "telegram_id": user.id,
        "telegram_user": user.username or user.first_name
    }
    guardar_datos(datos)
    await update.message.reply_text(
        f"🎉 *¡Reserva recibida!*\n\n"
        f"🎟 Boleto: *#{str(boleto).zfill(3)}*\n"
        f"👤 Nombre: {nombre}\n"
        f"📱 Celular: {telefono}\n"
        f"💰 Pago: {pago_texto}\n\n"
        f"✅ El administrador verificará tu pago y te confirmará la participación.\n"
        f"¡Mucha suerte! 🍀",
        parse_mode="Markdown"
    )
    teclado_admin = [
        [
            InlineKeyboardButton("✅ Confirmar pago", callback_data=f"confirmar_{key}"),
            InlineKeyboardButton("❌ Liberar boleto", callback_data=f"liberar_{key}"),
        ]
    ]
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"🔔 *Nueva reserva*\n\n"
            f"🎟 Boleto: *#{str(boleto).zfill(3)}*\n"
            f"👤 Nombre: {nombre}\n"
            f"📱 Celular: {telefono}\n"
            f"💰 Pago: {pago_texto}\n"
            f"🆔 Telegram: @{user.username or user.first_name} (ID: {user.id})"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(teclado_admin)
    )
    return ConversationHandler.END

async def confirmar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ No tienes permiso.", show_alert=True)
        return
    await query.answer()
    key = query.data.split("_")[1]
    datos = cargar_datos()
    if key not in datos["reservados"]:
        await query.edit_message_text("⚠️ Este boleto ya no está en reserva.")
        return
    info = datos["reservados"].pop(key)
    datos["confirmados"].append(int(key))
    guardar_datos(datos)
    await query.edit_message_text(
        f"✅ *Pago confirmado*\n\n"
        f"🎟 Boleto #{key.zfill(3)} — {info['nombre']}\n"
        f"📱 {info['telefono']}\n"
        f"💰 {info['pago']}",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            chat_id=info["telegram_id"],
            text=(
                f"🎊 *¡Tu pago fue confirmado!*\n\n"
                f"🎟 Boleto: *#{key.zfill(3)}*\n"
                f"✅ Ya eres participante oficial de la Gran Rifa Apple.\n\n"
                f"Serás agregado al grupo del sorteo. ¡Mucha suerte! 🍀🍎"
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass

async def liberar_boleto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ No tienes permiso.", show_alert=True)
        return
    await query.answer()
    key = query.data.split("_")[1]
    datos = cargar_datos()
    if key in datos["reservados"]:
        info = datos["reservados"].pop(key)
        guardar_datos(datos)
        await query.edit_message_text(f"🔓 Boleto #{key.zfill(3)} liberado.\n({info['nombre']} — {info['telefono']})")
        try:
            await context.bot.send_message(
                chat_id=info["telegram_id"],
                text=f"😔 Tu reserva del boleto *#{key.zfill(3)}* fue cancelada.\n\nSi crees que es un error, contacta al administrador.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    else:
        await query.edit_message_text("⚠️ No se encontró esa reserva.")

async def panel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    datos = cargar_datos()
    confirmados = len(datos["confirmados"])
    reservados = len(datos["reservados"])
    disponibles = TOTAL_BOLETOS - confirmados - reservados
    texto = (
        f"🔐 *Panel de Administrador*\n\n"
        f"🟢 Disponibles: {disponibles}\n"
        f"🟡 Reservados: {reservados}\n"
        f"🔴 Vendidos: {confirmados}\n\n"
        f"*Reservas pendientes:*\n"
    )
    if datos["reservados"]:
        for k, v in datos["reservados"].items():
            texto += f"• #{k.zfill(3)} — {v['nombre']} ({v['telefono']})\n"
    else:
        texto += "Ninguna por ahora.\n"
    teclado = [[InlineKeyboardButton("🔓 Liberar un número", callback_data="admin_liberar")]]
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(teclado))

async def admin_liberar_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Sin permiso.", show_alert=True)
        return
    await query.answer()
    await query.edit_message_text("🔓 Escribe el número de boleto que deseas liberar (ej: 45):")
    context.user_data["esperando_liberar"] = True

async def manejar_texto_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.user_data.get("esperando_liberar"):
        context.user_data["esperando_liberar"] = False
        try:
            num = int(update.message.text.strip())
            key = str(num)
            datos = cargar_datos()
            if key in datos["reservados"]:
                info = datos["reservados"].pop(key)
                guardar_datos(datos)
                await update.message.reply_text(f"✅ Boleto #{str(num).zfill(3)} liberado. Era de {info['nombre']}.")
                try:
                    await context.bot.send_message(
                        chat_id=info["telegram_id"],
                        text=f"😔 Tu reserva del boleto *#{key.zfill(3)}* fue cancelada por el administrador.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            elif num in datos["confirmados"]:
                datos["confirmados"].remove(num)
                guardar_datos(datos)
                await update.message.reply_text(f"✅ Boleto #{str(num).zfill(3)} liberado (estaba confirmado).")
            else:
                await update.message.reply_text(f"⚠️ El boleto #{str(num).zfill(3)} ya está disponible.")
        except ValueError:
            await update.message.reply_text("❌ Número inválido.")

async def volver_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    teclado = [
        [InlineKeyboardButton("🎟 Ver boletos disponibles", callback_data="ver_boletos")],
        [InlineKeyboardButton("📊 Estado de la rifa", callback_data="estado")],
    ]
    await query.edit_message_text(
        "🍎 *Gran Rifa Apple*\n\n¿Qué deseas hacer?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Reserva cancelada. Escribe /start para volver a comenzar.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(iniciar_reserva, pattern="^reservar$")],
        states={
            ELIGIENDO_BOLETO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_boleto)],
            ELIGIENDO_PAGO: [CallbackQueryHandler(recibir_pago, pattern="^pago_")],
            INGRESANDO_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre)],
            INGRESANDO_TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_telefono)],
        },
        fallbacks=[CallbackQueryHandler(cancelar, pattern="^cancelar$")],
        per_message=False
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", panel_admin))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(ver_boletos, pattern="^ver_boletos$"))
    app.add_handler(CallbackQueryHandler(cambiar_pagina, pattern="^pagina_"))
    app.add_handler(CallbackQueryHandler(estado, pattern="^estado$"))
    app.add_handler(CallbackQueryHandler(confirmar_pago, pattern="^confirmar_"))
    app.add_handler(CallbackQueryHandler(liberar_boleto, pattern="^liberar_"))
    app.add_handler(CallbackQueryHandler(volver_inicio, pattern="^inicio$"))
    app.add_handler(CallbackQueryHandler(admin_liberar_prompt, pattern="^admin_liberar$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto_admin))
    print("🤖 Bot Gran Rifa Apple corriendo...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
