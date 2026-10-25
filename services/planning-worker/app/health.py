"""Small internal probe server; no public Service or external credentials."""

import asyncio


async def status(path, worker, client):
    if path == "/health/live":
        return 200
    if path != "/health/ready":
        return 404
    if not worker.is_running or worker.is_shutdown:
        return 503
    try:
        healthy = await asyncio.wait_for(client.service_client.check_health(), timeout=2)
        return 200 if healthy else 503
    except Exception:  # noqa: BLE001 - a probe failure must report unready, not crash the worker.
        return 503


async def serve_health(worker, client):
    async def respond(reader, writer):
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=3)
            parts = line.decode("ascii", errors="replace").split()
            code = await status(parts[1] if len(parts) > 1 else "", worker, client)
            reason = {200: "OK", 404: "Not Found", 503: "Service Unavailable"}[code]
            body = reason.encode()
            writer.write(
                f"HTTP/1.1 {code} {reason}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
                + body
            )
            await writer.drain()
        except (TimeoutError, ConnectionError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    return await asyncio.start_server(respond, "0.0.0.0", 8081, limit=4096)
