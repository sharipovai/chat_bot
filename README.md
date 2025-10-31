## Описание:

Telegram-бот на Python с интеграцией нескольких LLM-моделей (DeepSeek, Qwen, Gemini).  
Реализована динамическая смена моделей, маршрутизация сообщений и гибкое управление контекстом.  
Поддерживаются следующие модели: DeepSeek v3, DeepSeek r1, Qwen3 235b-a22b, Qwen3 32b, Gemini 2.0 Flash  

## Технические детали:

Язык: Python 3.10+  
Основные библиотеки: telebot, openai, google, sqlite3  
Используется асинхронное взаимодействие с API google и openrouter  
Поддерживается текстовый и графический контент при взаимодействии с моделями  
Возможность выбора модели пользователем прямо из чата  
Поддержка режима “истории сообщений” для контекста  

## Структура:

main.py - обработка сообщений и логика маршрутизации  
config_example.py - параметры и ключи  
database.py - взаимодействие с базой данных  
statistics.py - получение статистической информации по использованию бота  

## Установка:
git clone https://github.com/sharipovai/chat_bot  
cd chat_bot  
mv config_example.py config.py (добавить ключи и параметры)  
pip install -r requirements.txt  
python main.py  

