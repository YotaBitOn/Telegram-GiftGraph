import json
from channels.generic.websocket import AsyncWebsocketConsumer
from graph import parser


class GraphConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        print('WS successfully connected')

    async def receive(self, text_data):
        print("Handling connection...")
        config = json.loads(text_data)
        print("Received config:", config)
        print("Started parsing...")

        async for datum in parser.parse(config):
            message = json.dumps(datum)
            await self.send(message)

    async def disconnect(self, close_code):
        print(f"WebSocket closed with code: {close_code}")