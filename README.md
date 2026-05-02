# Telegram-GiftGraph
Telegram GiftGraph is an app created for exploring connvetions between people through telegram's stargifts

Connections are saved as JSON or

## Obsidian graph like this one
<img width="964" height="832" alt="image" src="https://github.com/user-attachments/assets/9583b788-509c-46f7-9a41-5e27a2c6998d" />

Processing each user takes 2.5 seconds to avoid flood ban
You of course can choose depth and limit of users visited

## Install instructions:

```
git clone https://github.com/YotaBitOn/Telegram-GiftGraph
pip install telethon dotenv
python python main.py
```

## Use instructions:

Go to config section of file
```
API_ID       = os.getenv("API_ID") 
API_HASH     = os.getenv("API_HASH")
SESSION_NAME = "gift_session"
```
You need to put these API_ID and API_HASH variables in .env file like this

```
API_ID="YOUR-API-ID"
API_HASH="YOUR-API-HASH"
```

To get those ID's you need to create your own app on [https://my.telegram.org/apps](url)

Be reasoneble when setting these params
```
MAX_DEPTH    = 6     #depth of looking 
MAX_USERS    = 100    #limit of users viewed
DELAY        = 2.5      #delay between viewing user profile to avoid flood ban
```
