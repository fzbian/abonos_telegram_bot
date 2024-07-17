import socket
import requests
import os
import random
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

load_dotenv()
# Replace with your actual bot token and user ID
TOKEN = os.getenv("TOKEN")
USER_ID = os.getenv("CHAT_ID")


# Define the states
NAME, DATE, PHOTO, VALUE = range(4)

# Initialize an empty list to store data
data = []

def send_message(message, photo_path=None):
    url = f'https://api.telegram.org/bot{TOKEN}/sendPhoto' if photo_path else f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    if photo_path:
        files = {'photo': open(photo_path, 'rb')}
        data = {'chat_id': USER_ID, 'caption': message}
        response = requests.post(url, files=files, data=data)
    else:
        data = {'chat_id': USER_ID, 'text': message}
        response = requests.post(url, json=data)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Bienvenido. Por favor, dime el nombre del cliente.")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Por favor, ingresa un nombre válido.")
        return NAME
    user_data = {'name': text}
    context.user_data['user_data'] = user_data
    await update.message.reply_text("Gracias. Ahora dime la fecha en el formato DD-MM.")
    return DATE


def validate_date_format(date_text):
    try:
        day, month = date_text.split('-')
        if len(day) != 2 or len(month) != 2:
            return False
        day = int(day)
        month = int(month)
        if day < 1 or day > 31 or month < 1 or month > 12:
            return False
        return True
    except ValueError:
        return False


async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not validate_date_format(text):
        await update.message.reply_text(
            "Formato de fecha no válido. Recuerda usar el formato DD-MM. Por favor, intenta de nuevo.")
        return DATE

    user_data = context.user_data.get('user_data')
    if not user_data:
        await update.message.reply_text("Por favor, inicia el proceso con /start.")
        return ConversationHandler.END

    user_data['date'] = text
    await update.message.reply_text("Gracias. Ahora envíame la foto del comprobante.")
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data.get('user_data')
    if not user_data:
        await update.message.reply_text("Por favor, inicia el proceso con /start.")
        return ConversationHandler.END

    folder_name = f"{user_data['name']}-{user_data['date']}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Generate a random number to append to the file name
    random_number = random.randint(10000000, 99999999)

    photo_list = update.message.photo
    if not photo_list:
        await update.message.reply_text("No se ha enviado ninguna foto. Por favor, envía la foto del comprobante.")
        return PHOTO

    photo_file = await photo_list[-1].get_file()
    photo_extension = photo_file.file_path.split('.')[-1]
    photo_path = os.path.join(folder_name, f'comprobante-{random_number}.{photo_extension}')
    await photo_file.download_to_drive(photo_path)

    user_data['photo'] = photo_path
    await update.message.reply_text("Gracias. Ahora dime el valor del abono.")
    return VALUE


async def get_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data.get('user_data')
    if not user_data:
        await update.message.reply_text("Por favor, inicia el proceso con /start.")
        return ConversationHandler.END

    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Por favor, ingresa un valor válido.")
        return VALUE

    user_data['value'] = text
    data.append(user_data)

    # Construct the message for sending
    message = f"Nuevo abono registrado:\n\n"
    message += f"Nombre del cliente: {user_data['name']}\n"
    message += f"Fecha: {user_data['date']}\n"
    formatted_value = "{:,}".format(int(user_data['value']))
    message += f"Valor: ${formatted_value}\n"

    # Send message with photo
    send_message(message, user_data['photo'])

    message = f"Has enviado el siguiente abono:\n\n"
    message += f"Nombre del cliente: {user_data['name']}\n"
    message += f"Fecha: {user_data['date']}\n"
    formatted_value = "{:,}".format(int(user_data['value']))
    message += f"Valor: ${formatted_value}\n"

    # Send message with photo
    await update.message.reply_text(message)

    await update.message.reply_text(
        "Datos enviados y guardados. Si quieres registrar otro abono, por favor, empieza de nuevo con /start. Si has terminado, usa /stop.")
    return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Proceso terminado. Gracias.")
    return ConversationHandler.END


def main():
    # Replace 'YOUR TOKEN HERE' with your actual bot token
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_value)]
        },
        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
