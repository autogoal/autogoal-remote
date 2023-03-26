from typing import Callable
from fastapi import WebSocket
from functools import wraps
import json


async def send_large_message(websocket: WebSocket, data: str, chunk_size: int):
    async def send(data):
        func = (
            websocket.send_text 
            if hasattr(websocket, "send_text") 
            else websocket.send
        )
        return await func(json.dumps(data))

    # Split the data into chunks
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
    # Send the number of chunks to the client
    await send({"type": "chunk_count", "count": len(chunks)})
    # Send each chunk separately
    for chunk in chunks:
        await send({"type": "chunk", "data": chunk})


async def receive_large_message(websocket: WebSocket):
    async def receive():
        func = (
            websocket.receive_text
            if hasattr(websocket, "receive_text")
            else websocket.recv
        )
        return json.loads(await func())

    # Receive the number of chunks
    message = await receive()
    assert message["type"] == "chunk_count"
    chunk_count = message["count"]
    # Receive each chunk separately
    chunks = []
    for _ in range(chunk_count):
        message = await receive()
        assert message["type"] == "chunk"
        chunks.append(message["data"])
    # Reassemble the original message
    data = "".join(chunks)
    return data
