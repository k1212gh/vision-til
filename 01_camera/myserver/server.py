"""
M4~M5. 영상 수신 서버

구조 (ARCHITECTURE.md 1절):
    [스레드 A: aiohttp]   GET /   → index.html
                          GET /ws → JPEG bytes 수신 → FrameQueue.put
    [스레드 B: 메인]      FrameQueue.get → cv2.imdecode → cv2.imshow

실행:
    python make_cert.py     # 최초 1회
    python server.py        # 터미널에 뜨는 https://<PC IP>:8443 을 폰 브라우저에서 열기
    python test_client.py   # (폰 없이 검증) 다른 터미널에서 웹캠 프레임을 보내 봄
키: q 종료
"""
import argparse
import asyncio
import queue
import socket
import ssl
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from aiohttp import web, WSMsgType

HERE = Path(__file__).parent


class FrameQueue:
    """최신 프레임만 유지하는 큐. 가득 차면 오래된 것을 버리고 새 것을 넣는다.

    "모든 프레임 처리"가 아니라 "항상 최신 프레임 처리"가 실시간 시스템의 원칙 (ARCHITECTURE.md 3절).
    queue.Queue 는 스레드 안전하므로 네트워크 스레드가 put, 메인 스레드가 get 해도 안전.
    """

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
                    self.q.get_nowait()   # 가장 오래된 것 하나 버림
                    self.dropped += 1
                except queue.Empty:
                    pass

    def get(self, timeout: float):
        """비어 있으면 timeout 뒤 queue.Empty 발생."""
        return self.q.get(timeout=timeout)


async def index(request: web.Request) -> web.Response:
    """GET / → index.html 파일을 그대로 응답."""
    return web.FileResponse(HERE / "index.html")


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    """GET /ws → WebSocket으로 업그레이드하고, 오는 바이너리 메시지를 큐에 넣는다.

    여기서는 디코드하지 않는다. 네트워크 스레드는 최대한 가볍게, 무거운 일은 메인 스레드로.
    """
    ws = web.WebSocketResponse(max_msg_size=8 * 1024 * 1024)   # 8MB 까지 허용
    await ws.prepare(request)
    frames: FrameQueue = request.app["frames"]
    peer = request.remote
    print(f"[ws] 연결: {peer}")
    n = 0
    async for msg in ws:
        if msg.type == WSMsgType.BINARY:
            frames.put((time.perf_counter(), peer, msg.data))
            n += 1
        elif msg.type == WSMsgType.ERROR:
            print("[ws] 오류:", ws.exception())
    print(f"[ws] 종료: {peer} (프레임 {n}장)")
    return ws


def create_app() -> web.Application:
    """라우팅 등록. app["frames"] 에 FrameQueue 를 넣어 핸들러가 꺼내 쓰게 한다."""
    app = web.Application()
    app["frames"] = FrameQueue(maxsize=2)
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    return app


def make_ssl_context() -> ssl.SSLContext:
    """cert.pem / key.pem 을 읽어 서버용 SSL 컨텍스트 생성."""
    cert, key = HERE / "cert.pem", HERE / "key.pem"
    if not cert.exists() or not key.exists():
        raise SystemExit("cert.pem / key.pem 없음 → 먼저  python make_cert.py  실행")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    return ctx


def start_server_thread(app: web.Application, host: str, port: int, ssl_ctx) -> threading.Thread:
    """aiohttp 서버를 별도 스레드의 asyncio 루프에서 띄운다 (메인 스레드는 OpenCV가 써야 하므로)."""
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
            while True:                       # 루프를 살려 두기
                await asyncio.sleep(3600)

        loop.run_until_complete(serve())

    t = threading.Thread(target=run, daemon=True)   # daemon: 메인이 끝나면 같이 종료
    t.start()
    ready.wait(timeout=5)
    return t


def decode_jpeg(data: bytes):
    """JPEG bytes → numpy (H, W, 3) BGR. 실패하면 None."""
    arr = np.frombuffer(data, dtype=np.uint8)   # 아직 압축 상태의 1차원 배열
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8443)
    args = ap.parse_args()

    app = create_app()
    start_server_thread(app, "0.0.0.0", args.port, make_ssl_context())
    print(f"\n폰 브라우저에서 열기 →  https://{local_ip()}:{args.port}\n"
          "   (인증서 경고가 뜨면 고급 → 계속 진행)\n")

    frames: FrameQueue = app["frames"]
    win = "01-b my server"
    fps, t_prev = 0.0, time.perf_counter()

    while True:
        try:
            t_recv, peer, data = frames.get(timeout=0.05)
        except queue.Empty:
            # 프레임이 없어도 waitKey 는 돌려야 창이 안 멈춤
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        frame = decode_jpeg(data)
        if frame is None:
            continue

        now = time.perf_counter()
        inst = 1.0 / max(now - t_prev, 1e-6)
        t_prev = now
        fps = inst if fps == 0 else fps * 0.9 + inst * 0.1

        h, w = frame.shape[:2]
        text = f"{w}x{h} {fps:4.1f}fps {len(data) / 1024:4.0f}KB drop {frames.dropped}"
        cv2.rectangle(frame, (0, 0), (460, 34), (0, 0, 0), -1)
        cv2.putText(frame, text, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow(win, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
