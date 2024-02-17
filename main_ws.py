import asyncio
import websockets
import json
import time
import logging

# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VoyagerASClient")

autoreconnect = True
max_reconnect_attempts = 5
uri = "ws://localhost:5950"

class VoyagerASClient:
    def __init__(self, uri):
        self.uri = uri
        self.connection = None
        self.reconnect_attempts = 0

    async def run(self):
        await self.connect()
        asyncio.create_task(self.keep_alive())
        await self.receive_message()

    async def stop(self):
        if self.connection:
            await self.connection.close()
        logger.info("Connection closed gracefully.")

    async def connect(self):
        try:
            self.connection = await websockets.connect(self.uri)
            logger.info(f"Connected to {self.uri}")
            self.reconnect_attempts = 0
        except (websockets.exceptions.InvalidURI, websockets.exceptions.WebSocketException) as e:
            logger.error(f"Connection failed: {e}")
            if autoreconnect:
                await self.reconnect()
            else:
                raise

    async def reconnect(self):
        if self.reconnect_attempts < max_reconnect_attempts:
            self.reconnect_attempts += 1
            wait_time = min(2 ** self.reconnect_attempts, 30)
            logger.info(f"Attempting to reconnect in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            await self.run()
        else:
            logger.error("Max reconnect attempts reached, stopping.")
            await self.stop()

    async def send_json(self, data):
        if self.connection:
            await self.connection.send(json.dumps(data) + "\r\n")
            logger.info(f"Sent: {data}")

    async def receive_message(self):
        while self.connection:
            try:
                message = await self.connection.recv()
                logger.info(f"Received: {message}")
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(f"Connection closed unexpectedly: {e}")
                if autoreconnect and self.reconnect_attempts < max_reconnect_attempts:
                    await self.reconnect()
                else:
                    logger.error("Max reconnect attempts reached or auto-reconnect disabled.")
                    
    async def keep_alive(self):
        while self.connection:
            try:
                await self.connection.ping()
            except Exception as e:
                logger.error(f"Failed to send ping: {e}")
            await asyncio.sleep(10)  # Send a ping every 10 seconds

async def send_polling_message(client):
    while True:
        message = {
            "Event": "Polling",
            "Timestamp": time.time(),
            "Host": "Pier1",
            "Inst": 1
        }
        await client.send_json(message)
        await asyncio.sleep(5)

async def main():
    client = VoyagerASClient(uri)
    await asyncio.gather(client.run(), send_polling_message(client))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Application error: {e}")
        asyncio.run(VoyagerASClient(uri).stop())
