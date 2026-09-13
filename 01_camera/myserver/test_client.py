"""
M5 채점 도구 (학습 대상 아님, 그냥 실행만)

폰 대신 노트북 웹캠 프레임을 JPEG로 압축해 wss://127.0.0.1:8443/ws 로 계속 보낸다.
server.py 를 먼저 띄워 두고 다른 터미널에서 실행:
    python test_client.py            # 기본 15fps, 100프레임
    python test_client.py --fps 30 --n 300
"""
import argparse
import asyncio
import ssl
import time

import aiohttp
import cv2


async def run(url: str, fps: int, n: int):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE          # 자체 서명 인증서라 검증 끔
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise SystemExit("웹캠 열기 실패")
    async with aiohttp.ClientSession() as s, s.ws_connect(url, ssl=ctx) as ws:
        print("연결됨:", url)
        t0 = time.perf_counter()
        for i in range(n):
            ok, frame = cap.read()
            if not ok:
                break
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            await ws.send_bytes(buf.tobytes())
            await asyncio.sleep(1 / fps)
        print(f"{i + 1}장 전송, {(time.perf_counter() - t0):.1f}s, 마지막 {len(buf) / 1024:.0f}KB")
    cap.release()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://127.0.0.1:8443/ws")
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    asyncio.run(run(a.url, a.fps, a.n))
