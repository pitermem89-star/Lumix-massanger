import asyncio
import websockets
import os

# Сюда будут сохраняться все, кто зашел на сайт мессенджера
CLIENTS = set()

async def echo(websocket):
    CLIENTS.add(websocket)
    print(f"Кто-то подключился! Онлайн: {len(CLIENTS)}")
    try:
        async for message in websocket:
            if CLIENTS:
                # Рассылаем пришедшее сообщение абсолютно всем онлайн-пользователям
                await asyncio.gather(*[client.send(message) for client in CLIENTS])
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.remove(websocket)
        print(f"Пользователь вышел. Онлайн: {len(CLIENTS)}")

async def main():
    # Render сам выдаст нужный порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 8000))
    async with websockets.serve(echo, "0.0.0.0", port):
        print(f"Сервер Lumix успешно запущен на порту {port}...")
        await asyncio.Future() # Держим сервер включенным бесконечно

if __name__ == "__main__":
    asyncio.run(main())
  
