"""
모든 강의에서 공통으로 쓰는 작은 도구 모음.

사용법 (각 강의 폴더의 스크립트에서):
    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 저장소 루트를 import 경로에 추가
    from common import open_capture, put_text, FpsMeter
"""
import time

import cv2
import numpy as np


def open_capture(url: str) -> cv2.VideoCapture:
    """"0" 같은 숫자면 로컬 웹캠, 아니면 http/rtsp 스트림 주소. (01강 phone_cam.py 와 동일)"""
    if url.isdigit():
        cap = cv2.VideoCapture(int(url), cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def put_text(frame: np.ndarray, text: str, y: int = 24, color=(0, 255, 0)) -> None:
    """검은 띠 위에 글자. y는 줄의 기준선(baseline) 픽셀."""
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    cv2.rectangle(frame, (0, y - th - 8), (tw + 16, y + 8), (0, 0, 0), -1)
    cv2.putText(frame, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)


class FpsMeter:
    """호출할 때마다 지수이동평균 FPS를 갱신해서 돌려준다."""

    def __init__(self, alpha: float = 0.1):
        self.alpha = alpha
        self.fps = 0.0
        self._t = time.perf_counter()

    def tick(self) -> float:
        now = time.perf_counter()
        inst = 1.0 / max(now - self._t, 1e-6)
        self._t = now
        self.fps = inst if self.fps == 0 else self.fps * (1 - self.alpha) + inst * self.alpha
        return self.fps
