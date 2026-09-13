"""
01-b. 직접 만든 영상 수신 서버

구조:
    [폰 브라우저] --(HTTPS)--> index.html 내려받음
    [폰 브라우저] --(WSS, JPEG 바이너리 연속)--> /ws --> 큐 --> OpenCV 디코드 --> 화면

왜 스레드가 2개인가:
    - aiohttp(네트워크)는 asyncio 이벤트 루프에서 돌아야 하고
    - cv2.imshow(화면)는 메인 스레드에서 돌리는 게 안전해서
    두 세계를 queue로 연결합니다. 이 "수신 스레드 + 처리 스레드" 패턴은
    나중에 카메라 수십 대를 다룰 때도 그대로 씁니다.

실행:
    python make_cert.py          # 최초 1회
    python server.py             # https://<PC IP>:8443 을 폰 브라우저에서 열기
"""
import argparse
import asyncio
import queue
import ssl
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from aiohttp import web, WSMsgType

HERE = Path(__file__).parent


class FrameQueue:
    """최신 프레임만 유지하는 큐. 처리가 느리면 오래된 프레임을 버린다 (지연 누적 방지)."""

    def __init__(self, maxsize: int = 2):
        self.q: queue.Queue = queue.Queue(maxsize=maxsize)
        self.dropped = 0

    def put(self, item) -> None:
        while True:
            try:
                self.q.put_nowait(item)
                return
            except queue.Full:
                try:
                    self.q.get_nowait()
                    self.dropped += 1
                except queue.Empty:
                    pass

    def get(self, timeout: float):
        return self.q.get(timeout=timeout)


async def index(request: web.Request) -> web.Response:
    return web.FileResponse(HERE / "index.html")


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(max_msg_size=8 * 1024 * 1024)
    await ws.prepare(request)
    peer = request.remote
    frames: FrameQueue = request.app["frames"]
    print(f"[ws] 연결: {peer}")
    n = 0
    async for msg in ws:
        if msg.type == WSMsgType.BINARY:
            # 받은 바이트(JPEG)를 그대로 큐에. 디코드는 화면 스레드가 한다.
            frames.put((time.perf_counter(), peer, msg.data))
            n += 1
        elif msg.type == WSMsgType.ERROR:
            print("[ws] 오류:", ws.exception())
    print(f"[ws] 종료: {peer} (프레임 {n}장)")
    return ws


def create_app() -> web.Application:
    app = web.Application()
    app["frames"] = FrameQueue(maxsize=2)
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    return app


def make_ssl_context() -> ssl.SSLContext:
    cert, key = HERE / "cert.pem", HERE / "key.pem"
    if not cert.exists():
        raise SystemExit("cert.pem 없음 → 먼저 python make_cert.py 실행")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    return ctx


def start_server_thread(app: web.Application, host: str, port: int, ssl_ctx) -> threading.Thread:
    """aiohttp 서버를 별도 스레드의 asyncio 루프에서 실행."""
    ready = threading.Event()

    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def serve():
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port, ssl_context=ssl_ctx)
            await site.start()
            ready.set()
            while True:
                await asyncio.sleep(3600)

        loop.run_until_complete(serve())

    t = threading.Thread(target=run, daemon=True)
    t.start()
    ready.wait(timeout=5)
    return t


def decode_jpeg(data: bytes):
    """bytes → numpy 배열. 네트워크로 온 압축 이미지를 프레임으로 되돌리는 핵심 한 줄."""
    arr = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8443)
    ap.add_argument("--no-ssl", action="store_true", help="http로 실행(폰 카메라는 안 열리지만 디버그용)")
    args = ap.parse_args()

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()

    app = create_app()
    ssl_ctx = None if args.no_ssl else make_ssl_context()
    start_server_thread(app, "0.0.0.0", args.port, ssl_ctx)
    scheme = "http" if args.no_ssl else "https"
    print(f"\n폰 브라우저에서 열기 →  {scheme}://{ip}:{args.port}\n   (인증서 경고가 뜨면 고급 → 계속 진행)\n")

    frames: FrameQueue = app["frames"]
    win = "01-b my server"
    fps, t_prev = 0.0, time.perf_counter()
    while True:
        try:
            t_recv, peer, data = frames.get(timeout=0.05)
        except queue.Empty:
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue
        frame = decode_jpeg(data)
        if frame is None:
            continue
        now = time.perf_counter()
        inst = 1.0 / max(now - t_prev, 1e-6); t_prev = now
        fps = inst if fps == 0 else fps * 0.9 + inst * 0.1
        h, w = frame.shape[:2]
        cv2.putText(frame, f"{w}x{h} {fps:4.1f}fps {len(data)/1024:4.0f}KB drop{frames.dropped}",
                    (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow(win, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
