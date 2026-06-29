# Telegram GiftGraph

Telegram GiftGraph is an app created for exploring connections between people through telegram's stargifts

Connections are saved as JSON or visualized using d3.js in form of a

## Graph like this one
<img width="1224" height="824" alt="image" src="https://github.com/user-attachments/assets/cad24d86-1307-4c5e-9848-eda05e1d4be7" />

Processing each user takes 2.5 seconds to avoid rate limits<br>
You of course can choose depth and limit of users visited on page
<img width="882" height="826" alt="image" src="https://github.com/user-attachments/assets/afc04e71-4425-45f0-80b2-73963d68e7fa" />

## Stack

**d3.js** for graph vilualization<br>
**Websockets** for front and back end communication<br>
**Telethon** for getting info about user connections from Telegram<br>


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

On first run server will ask you to login into telegram using your number and 2fa password.<br>
Don't worry, your privacy will not be violated becuase there's no way for me to get your data<br>
It is needed because I as developer can`t  use my account to make requests for possible users of GiftGraph<br> 
because my acc will get banned

Be reasoneble when setting these params
```
MAX_DEPTH    = 6     #depth of looking 
MAX_USERS    = 100    #limit of users viewed
DELAY        = 2.5      #delay between viewing user profile to avoid flood ban
```
