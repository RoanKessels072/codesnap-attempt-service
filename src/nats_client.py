import nats
from nats.aio.client import Client as NATS
import json
from src.config import settings

class NATSClient:
    def __init__(self):
        self.nc: NATS = None
        
    async def connect(self):
        self.nc = await nats.connect(settings.nats_url)
        print(f"Connected to NATS at {settings.nats_url}")
        
    async def close(self):
        if self.nc:
            await self.nc.close()
            
    async def request(self, subject: str, data: dict, timeout: float = 10.0):
        if not self.nc:
             raise Exception("NATS not connected")
        try:
            response = await self.nc.request(
                subject, 
                json.dumps(data).encode(), 
                timeout=timeout
            )
            return json.loads(response.data.decode())
        except Exception as e:
            print(f"NATS Request Error: {e}")
            print(f"NATS Request Error: {e}")
            return {"error": str(e)}

    async def publish(self, subject: str, data: dict):
        if not self.nc:
             raise Exception("NATS not connected")
        try:
            await self.nc.publish(subject, json.dumps(data).encode())
        except Exception as e:
            print(f"NATS Publish Error: {e}")
            raise e

    async def subscribe(self, subject: str, handler):
        async def message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                response = await handler(data)
                if msg.reply:
                    await self.nc.publish(
                        msg.reply, 
                        json.dumps(response, default=str).encode()
                    )
            except Exception as e:
                print(f"Error handling message on {subject}: {e}")
                if msg.reply:
                    await self.nc.publish(
                        msg.reply,
                        json.dumps({"error": str(e)}).encode()
                    )
        
        await self.nc.subscribe(subject, cb=message_handler)
        print(f"Subscribed to {subject}")