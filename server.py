import asyncio
import json
import websockets



async def your_parser(config: dict):
    print("Starting with config:", config)
    for i in range(config.get("count", 100)):
        yield {"id": i, "value": i * 2.5}
        await asyncio.sleep(config.get("interval", 0.1))

async def handle(ws):
    config = json.loads(await ws.recv())
    print("Received config:", config)

    with open("config.json", "w") as f:
        json.dump(config, f)

    async for datum in your_parser(config):
        await ws.send(json.dumps(datum))

    await ws.send(json.dumps({"__done": True}))  # signal end

async def main():
    async with websockets.serve(handle, "localhost", 8765):
        print("WS server running on ws://localhost:8765")
        await asyncio.Future()  # run forever

asyncio.run(main())