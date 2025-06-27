import os
from datetime import datetime
# from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import requests
import telebot
from openai import OpenAI
from database import Database
import config
from statistics import get_stat
from telebot import types
import base64
from google import genai

TOKEN = config.prod_bot_token
bot = telebot.TeleBot(TOKEN)
db = Database(config.database_path)
CHAT_BY_DATETIME = dict()
google_client = genai.Client(api_key=config.genai_api_key)

def write_statistics(statistics_type, user_id):
    now = datetime.now().strftime("%d.%m.%y")
    date_list = db.get_date_str_statistics()
    if now not in date_list:
        db.write_new_date_statistics()
    db.write_statistics(statistics_type, user_id)


@bot.message_handler(commands=['start'])
def start(message):
    db.create_db()
    if db.check_new_user(message.from_user.id):
        db.write_new_user(message)
        write_statistics("new_user", message.from_user.id)
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}!')
    return new_chat(message)

def new_chat(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    text = "Описание моделей:\n"
    for name in config.model_names.keys():
        btn = types.KeyboardButton(name)
        markup.row(btn)
        text += f'{name}: {config.model_description[name]}\n'
    bot.send_message(message.chat.id, text)
    bot.send_message(message.chat.id, f'Выбери модель', reply_markup=markup)
    bot.register_next_step_handler(message, new_chat2)

def new_chat2(message):
    if message.text not in list(config.model_names.keys()):
        bot.send_message(message.chat.id, f'Ошибка! Такой модели я не знаю. Попробуйте еще раз.')
        return new_chat(message)
    db.update_user_model(message.from_user.id, message.text)
    db.clear_chat_history(message.from_user.id)
    bot.send_message(message.chat.id, f'Я {message.text}. Чем сегодня могу тебе помочь?')
    return bot.register_next_step_handler(message, gpt_answer)


@bot.message_handler(commands=['stat'])
def stat(message):
    if message.from_user.id == config.admin_tg_id:
        cnt = get_stat()
        bot.send_message(message.chat.id, f'Всего пользователей {cnt}')
        bot.register_next_step_handler(message, stat_step2)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn1 = types.KeyboardButton('Да')
        btn2 = types.KeyboardButton('Нет')
        markup.row(btn1, btn2)
        bot.send_message(message.chat.id, f'Хотите получить полную статистику по боту?', reply_markup=markup)


def stat_step2(message):
    if 'да' in message.text.lower():
        with open("./statistics.xlsx", 'rb') as f:
            bot.send_document(message.chat.id, f)
        with open("./users_information.xlsx", 'rb') as f:
            bot.send_document(message.chat.id, f)
    return new_chat(message)

def send_long_text(message, answer):
    if answer == "":
        bot.send_message(message.chat.id, f'{"Ошибка! Повторите запрос позже."}')
        return 
    char_cnt = 4000
    text = answer.split("\n\n")
    send_text = ""
    for t in text:
        if len(send_text + t) > char_cnt:
            bot.send_message(message.chat.id, f'{send_text}')
            send_text = t
        else:
            send_text = send_text + t + "\n\n"
    bot.send_message(message.chat.id, f'{send_text}')

def llm_answer(message, chat_history, model_name):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.open_router_api_key,
    )
    if message.content_type == 'photo':
        model = config.gemini_model
        file_id = message.photo[-1].file_id  # Get the highest resolution photo
        file_info = bot.get_file(file_id)
        # Download the photo
        downloaded_file = bot.download_file(file_info.file_path)

        # Convert the downloaded file to a Base64 encoded string
        base64_encoded_image = f"data:image/jpeg;base64,{base64.b64encode(downloaded_file).decode('utf-8')}"

        caption = message.caption
        if caption is None:
            caption = "Расскажи что это и что с этим можно сделать?"
        content = {
                    "role": "user",
                    "content": [{"type": "text", "text": caption},
                                {"type": "image_url", "image_url": {"url": base64_encoded_image}}]
        }
        chat_history.append(content)
    else:
        model = model_name
    if model == "google/gemini-2.0-flash-001":
        chat_messages = ", ".join(item["content"] for item in chat_history)
        try:
            response = google_client.models.generate_content(
                model = "gemini-2.0-flash",
                contents = [chat_messages]
            )
            answer = response.text
        except Exception as e:
            print(e)
            answer = ""
    else:
        try:
            completion = client.chat.completions.create(
                extra_headers={},
                extra_body={},
                model=model,
                messages=chat_history
            )
            answer = completion.choices[0].message.content
        except Exception as e:
            print(e)
        answer = ""
    return answer

def fast_message(message):
    current_time = datetime.now()
    last_datetime = CHAT_BY_DATETIME.get(message.chat.id)
    if not last_datetime:
        CHAT_BY_DATETIME[message.chat.id] = current_time
    else:
        delta_seconds = (current_time - last_datetime).total_seconds()
        CHAT_BY_DATETIME[message.chat.id] = current_time
        if delta_seconds < 2:
            return 1
    return 0
@bot.message_handler()
def gpt_answer(message):
    if message.text is None and message.content_type == "text":
        bot.send_message(message.chat.id, f'Ваш запрос пустой, повторите попытку.')
        return bot.register_next_step_handler(message, gpt_answer)
    if '/start' == message.text:
        return start(message)
    if '/new_chat' == message.text:
        return new_chat(message)
    if fast_message(message):
        return
    if '/stat' == message.text:
        return stat(message)
    if db.check_new_user(message.from_user.id):
        db.write_new_user(message)
        write_statistics("new_user", message.from_user.id)
        return new_chat(message)
    if message.content_type == 'photo':
        content = message.caption
    else:
        content = message.text
    if content != "" and content is not None:
        db.update_user_chat_history(message.from_user.id, 'user', content)
    chat_history = db.get_user_chat_history(message.from_user.id)
    mes = bot.send_message(message.chat.id, f'Подождите....')
    model_name = config.model_names[db.get_user_model(message.from_user.id)]
    answer = llm_answer(message, chat_history, model_name)
    bot.delete_message(message.chat.id, mes.id)
    if answer != "":
        send_long_text(message, answer)
        db.update_user_chat_history(message.from_user.id, 'assistant', answer)
    else:
        bot.send_message(message.chat.id, 'Достигнут лимит запросов в одном чате! Продолжайте общение в новом чате.')
        return bot.register_next_step_handler(message, new_chat)
    return bot.register_next_step_handler(message, gpt_answer)

# @bot.message_handler(content_types=['voice', 'audio'])
# def handle_audio(message):
#     file_id = message.voice.file_id if message.content_type == "voice" else message.audio.file_id
#     local_dir = "./whisper-medium-local"
#     model = AutoModelForSpeechSeq2Seq.from_pretrained(
#         local_dir, low_cpu_mem_usage=True, use_safetensors=True
#     )
#     model.config.forced_decoder_ids = None
#     model.generation_config.forced_decoder_ids = None
#
#     processor = AutoProcessor.from_pretrained(local_dir)
#     device = "cpu"
#     pipe = pipeline(
#         "automatic-speech-recognition",
#         model=model,
#         tokenizer=processor.tokenizer,
#         feature_extractor=processor.feature_extractor,
#         device=device,
#     )
#     # Получаем ссылку на файл
#     file_info = bot.get_file(file_id)
#     file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
#
#     # Скачиваем голосовое
#     response = requests.get(file_url)
#     # Сохраняем файл на диск (например, в формате .ogg)
#     audio_path = f"./{message.from_user.id}.ogg"
#     with open(audio_path, "wb") as file:
#         file.write(response.content)
#
#     mes = bot.send_message(message.chat.id, f"Идет распознование голосового сообщения...")
#     # Передаём в pipe правильный формат
#     result = pipe(
#         audio_path,
#         generate_kwargs={"language": "russian", "task": "transcribe"}
#     )
#     text = result["text"]
#     bot.delete_message(message.chat.id, mes.id)
#     os.remove(audio_path)
#     bot.send_message(message.chat.id, f"Распознанный текст:\n{text}")
#     mes = bot.send_message(message.chat.id, f'Подождите....')
#     answer = llm_answer(message, text)
#     bot.delete_message(message.chat.id, mes.id)
#     send_long_text(message, answer)
#     return dialog(message)


bot.infinity_polling()
