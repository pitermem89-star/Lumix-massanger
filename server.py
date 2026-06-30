import asyncio
import websockets
import os

CLIENTS = set()

async def echo(websocket):
    CLIENTS.add(websocket)
    try:
        async for message in websocket:
            if CLIENTS:
                # Сервер просто берет сообщение и рассылает его всем онлайн
                await asyncio.gather(*[client.send(message) for client in CLIENTS])
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.remove(websocket)

async def main():
    port = int(os.environ.get("PORT", 8000))
    async with websockets.serve(echo, "0.0.0.0", port):
        print(f"Сервер Lumix работает на порту {port}...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
