"""
M4~M5. 영상 수신 서버 (뼈대)

구조 (ARCHITECTURE.md 1절):
    [스레드 A: aiohttp]   GET /   → index.html
                          GET /ws → JPEG bytes 수신 → FrameQueue.put
    [스레드 B: 메인]      FrameQueue.get → cv2.imdecode → cv2.imshow

실행:
    python make_cert.py     # 최초 1회
    python server.py        # https://<PC IP>:8443
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

    TODO(M5):
      __init__ : self.q = queue.Queue(maxsize=maxsize), self.dropped = 0
      put(item): q.put_nowait 시도 → queue.Full 이면 q.get_nowait()로 하나 버리고(dropped += 1) 다시 시도
      get(timeout): return self.q.get(timeout=timeout)   # 비어 있으면 queue.Empty 발생
    """

    def __init__(self, maxsize: int = 2):
        raise NotImplementedError

    def put(self, item) -> None:
        raise NotImplementedError

    def get(self, timeout: float):
        raise NotImplementedError


async def index(request: web.Request) -> web.Response:
    """GET / → index.html 파일을 그대로 응답.

    TODO(M4): return web.FileResponse(HERE / "index.html")
    """
    raise NotImplementedError


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    """GET /ws → WebSocket으로 업그레이드하고, 오는 바이너리 메시지를 큐에 넣는다.

    TODO(M5):
      ws = web.WebSocketResponse(max_msg_size=8 * 1024 * 1024)   # 8MB까지 허용
      await ws.prepare(request)
      frames = request.app["frames"]
      async for msg in ws:
          if msg.type == WSMsgType.BINARY:
              frames.put((time.perf_counter(), request.remote, msg.data))
      return ws
    연결/종료 시 print 로 로그 남기면 디버깅에 좋음.
    """
    raise NotImplementedError


def create_app() -> web.Application:
    """라우팅 등록. app["frames"] 에 FrameQueue 를 넣어 핸들러가 꺼내 쓰게 한다.

    TODO(M4): app = web.Application(); app["frames"] = FrameQueue(maxsize=2)
              app.router.add_get("/", index); app.router.add_get("/ws", ws_handler)
    """
    raise NotImplementedError


def make_ssl_context() -> ssl.SSLContext:
    """cert.pem / key.pem 을 읽어 서버용 SSL 컨텍스트 생성.

    TODO(M4): ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
              ctx.load_cert_chain(HERE / "cert.pem", HERE / "key.pem")
              cert.pem 이 없으면 안내 메시지와 함께 SystemExit
    """
    raise NotImplementedError


def start_server_thread(app: web.Application, host: str, port: int, ssl_ctx) -> threading.Thread:
    """aiohttp 서버를 별도 스레드의 asyncio 루프에서 띄운다 (메인 스레드는 OpenCV가 써야 하므로).

    TODO(M4):
      def run():
          loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
          async def serve():
              runner = web.AppRunner(app); await runner.setup()
              site = web.TCPSite(runner, host, port, ssl_context=ssl_ctx); await site.start()
              while True: await asyncio.sleep(3600)     # 루프를 살려 두기
          loop.run_until_complete(serve())
      t = threading.Thread(target=run, daemon=True); t.start(); return t
    (선택) threading.Event 로 "서버 준비됨" 신호를 보내면 main 이 안전하게 기다릴 수 있음.
    """
    raise NotImplementedError


def decode_jpeg(data: bytes):
    """JPEG bytes → numpy (H, W, 3) BGR. 실패하면 None.

    TODO(M5): arr = np.frombuffer(data, dtype=np.uint8)   # 아직 압축 상태의 1차원 배열
              return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    """
    raise NotImplementedError


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

    # TODO(M4): app 생성, ssl 컨텍스트 생성, 서버 스레드 시작
    # TODO(M4): print(f"폰에서 열기 → https://{local_ip()}:{args.port}")

    # TODO(M5): 메인 루프
    #   frames = app["frames"]
    #   while True:
    #       try: t_recv, peer, data = frames.get(timeout=0.05)
    #       except queue.Empty:   # 프레임이 없어도 waitKey 는 돌려야 창이 안 멈춤
    #           if cv2.waitKey(1) & 0xFF == ord("q"): break
    #           continue
    #       frame = decode_jpeg(data); None 이면 continue
    #       (M7) FPS / KB / frames.dropped 를 putText 로 표시
    #       cv2.imshow(...); waitKey 'q' 로 종료
    raise NotImplementedError


if __name__ == "__main__":
    main()
