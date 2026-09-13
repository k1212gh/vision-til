"""
01. 스마트폰(IP 카메라) 영상 받아오기

핵심 흐름:
    cap = cv2.VideoCapture(주소)   # 카메라/스트림 열기
    ok, frame = cap.read()         # 프레임 한 장 읽기 (numpy 배열)
    ...처리...
    cv2.imshow(...)                # 화면에 표시

이 세 줄이 앞으로 모든 비전 프로그램의 뼈대입니다.
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np


def open_capture(url: str) -> cv2.VideoCapture:
    """숫자면 로컬 웹캠, 아니면 네트워크 스트림."""
    if url.isdigit():
        # CAP_DSHOW: 윈도우 웹캠을 빠르게 여는 백엔드
        cap = cv2.VideoCapture(int(url), cv2.CAP_DSHOW)
    else:
        # CAP_FFMPEG: http/rtsp 스트림 디코딩용 백엔드
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    # 버퍼를 1로 → 오래된 프레임을 쌓아두지 않아 지연이 줄어듦 (스트림에 따라 무시되기도 함)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def draw_hud(frame: np.ndarray, fps: float, read_ms: float, mode: str) -> None:
    """프레임 위에 상태 정보 그리기. 검은 반투명 박스 + 흰 글씨."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (360, 78), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)  # 반투명 합성
    lines = [
        f"{w}x{h}  FPS {fps:5.1f}",
        f"read() {read_ms:5.1f} ms   mode: {mode}",
        "q quit  s snap  g gray  p pixel",
    ]
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (8, 22 + i * 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 1, cv2.LINE_AA)


class PixelProbe:
    """마우스로 클릭한 픽셀의 (x, y)와 BGR 값을 보여주는 도구."""

    def __init__(self):
        self.point = None

    def on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.point = (x, y)

    def draw(self, frame: np.ndarray) -> None:
        if self.point is None:
            return
        x, y = self.point
        h, w = frame.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return
        b, g, r = (int(v) for v in frame[y, x][:3])  # frame[행=y, 열=x] 순서 주의!
        cv2.circle(frame, (x, y), 6, (0, 255, 255), 2)
        cv2.putText(frame, f"({x},{y}) B{b} G{g} R{r}", (x + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="0",
                    help="예: http://192.168.0.10:8080/video  /  rtsp://...  /  0(웹캠)")
    ap.add_argument("--width", type=int, default=0, help="표시 폭 리사이즈(0이면 원본)")
    args = ap.parse_args()

    cap = open_capture(args.url)
    if not cap.isOpened():
        raise SystemExit(f"스트림을 열 수 없음: {args.url}\n"
                         "  - 폰과 PC가 같은 Wi-Fi인지\n  - 앱에서 Start server 했는지\n"
                         "  - URL 끝에 /video 붙였는지 확인")

    snap_dir = Path(__file__).parent / "snapshots"
    snap_dir.mkdir(exist_ok=True)

    win = "01 phone cam"
    cv2.namedWindow(win)
    probe = PixelProbe()
    cv2.setMouseCallback(win, probe.on_mouse)

    gray_mode = False
    pixel_mode = False
    fps = 0.0
    t_prev = time.perf_counter()
    first = True

    while True:
        t0 = time.perf_counter()
        ok, frame = cap.read()
        read_ms = (time.perf_counter() - t0) * 1000  # 프레임 하나 받는 데 걸린 시간
        if not ok:
            print("프레임 수신 실패 - 재연결 시도")
            cap.release()
            time.sleep(0.5)
            cap = open_capture(args.url)
            continue

        if first:
            # 프레임의 정체 확인: numpy 배열
            print(f"frame type={type(frame).__name__} shape={frame.shape} dtype={frame.dtype}")
            print(f"  -> 높이 {frame.shape[0]}, 너비 {frame.shape[1]}, 채널 {frame.shape[2]} (BGR)")
            print(f"  -> 총 {frame.nbytes/1024:.0f} KB / 프레임")
            first = False

        # FPS: 지수이동평균으로 부드럽게
        now = time.perf_counter()
        inst = 1.0 / max(now - t_prev, 1e-6)
        t_prev = now
        fps = inst if fps == 0 else fps * 0.9 + inst * 0.1

        if args.width:
            scale = args.width / frame.shape[1]
            frame = cv2.resize(frame, None, fx=scale, fy=scale)

        if gray_mode:
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)   # (H, W) 1채널
            frame = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)   # 그리기 편하게 다시 3채널로

        mode = ("gray " if gray_mode else "") + ("pixel" if pixel_mode else "")
        draw_hud(frame, fps, read_ms, mode.strip() or "color")
        if pixel_mode:
            probe.draw(frame)

        cv2.imshow(win, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            path = snap_dir / f"snap_{int(time.time())}.jpg"
            cv2.imwrite(str(path), frame)
            print("저장:", path)
        elif key == ord("g"):
            gray_mode = not gray_mode
        elif key == ord("p"):
            pixel_mode = not pixel_mode
            probe.point = None

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
