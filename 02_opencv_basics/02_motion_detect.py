"""
02-2. 움직임 감지 — "고양이가 움직였나?"를 가장 싸게 알아내기

두 가지 방법을 키로 전환하며 비교한다.
  [d] 프레임 차분(frame differencing): 직전 프레임과 지금 프레임의 차이
  [b] 배경 차분(MOG2):               "배경 모델"을 계속 학습하고, 거기서 벗어난 픽셀을 전경으로

파이프라인 (둘 다 공통):
  프레임 → Gray → 블러(노이즈 제거) → [차분 or MOG2] → 임계값 → 모폴로지(구멍 메우기)
        → 컨투어(덩어리 찾기) → 작은 덩어리 버림 → 바운딩 박스

왜: 돔 카메라 30대에 전부 YOLO를 돌리면 GPU가 못 버틴다.
    움직임이 있는 카메라/영역만 골라 YOLO를 돌리는 "1차 필터"가 이것.

실행:  python 02_motion_detect.py --url 0
키:    q 종료 / d 프레임차분 / b 배경차분(MOG2) / m 마스크 창 토글 / +,- 임계값
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import open_capture, put_text, FpsMeter   # noqa: E402


class FrameDiff:
    """직전 프레임과의 절대 차이. 단순하지만 카메라가 흔들리거나 조명이 변하면 오탐."""
    name = "frame-diff"

    def __init__(self):
        self.prev = None

    def apply(self, gray: np.ndarray, thresh: int) -> np.ndarray:
        if self.prev is None:
            self.prev = gray
            return np.zeros_like(gray)
        diff = cv2.absdiff(self.prev, gray)              # |prev - now|
        self.prev = gray
        _, mask = cv2.threshold(diff, thresh, 255, cv2.THRESH_BINARY)
        return mask


class BackgroundSub:
    """MOG2: 픽셀마다 가우시안 혼합으로 배경을 모델링. 천천히 변하는 조명에 적응."""
    name = "MOG2"

    def __init__(self):
        # history: 배경으로 인정하기까지 볼 프레임 수. detectShadows: 그림자를 회색(127)으로 따로 표시
        self.sub = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=25, detectShadows=True)

    def apply(self, gray: np.ndarray, thresh: int) -> np.ndarray:
        fg = self.sub.apply(gray)                        # 0 배경 / 127 그림자 / 255 전경
        _, mask = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)   # 그림자(127)는 버림
        return mask


def clean_mask(mask: np.ndarray) -> np.ndarray:
    """모폴로지: 열기(작은 점 제거) → 닫기(구멍 메우기) → 팽창(덩어리 키우기)."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    return cv2.dilate(mask, k, iterations=2)


def find_boxes(mask: np.ndarray, min_area: int):
    """마스크에서 덩어리(컨투어)를 찾아 일정 크기 이상만 (x, y, w, h) 로 반환."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in contours:
        if cv2.contourArea(c) < min_area:
            continue
        boxes.append(cv2.boundingRect(c))
    return boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="0")
    ap.add_argument("--min-area", type=int, default=800, help="이보다 작은 덩어리는 무시 (픽셀)")
    args = ap.parse_args()

    cap = open_capture(args.url)
    if not cap.isOpened():
        raise SystemExit(f"열 수 없음: {args.url}")

    detectors = {"d": FrameDiff(), "b": BackgroundSub()}
    det = detectors["b"]
    thresh = 25
    show_mask = True
    meter = FpsMeter()

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.resize(frame, (960, 540))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)      # 센서 노이즈를 뭉개서 오탐 감소

        mask = det.apply(gray, thresh)
        mask = clean_mask(mask)
        boxes = find_boxes(mask, args.min_area)

        motion_ratio = float(np.count_nonzero(mask)) / mask.size * 100   # 화면의 몇 %가 움직였나
        for (x, y, w, h) in boxes:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        put_text(frame, f"{det.name}  thresh {thresh}  {meter.tick():4.1f}fps")
        put_text(frame, f"motion {motion_ratio:4.1f}%  boxes {len(boxes)}", y=52,
                 color=(0, 0, 255) if boxes else (0, 255, 0))
        if boxes:
            put_text(frame, "MOTION", y=80, color=(0, 0, 255))

        cv2.imshow("02-2 motion", frame)
        if show_mask:
            cv2.imshow("02-2 mask", mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key in (ord("d"), ord("b")):
            det = detectors[chr(key)]
        elif key == ord("m"):
            show_mask = not show_mask
            if not show_mask:
                cv2.destroyWindow("02-2 mask")
        elif key in (ord("+"), ord("=")):
            thresh = min(thresh + 5, 250)
        elif key == ord("-"):
            thresh = max(thresh - 5, 5)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
