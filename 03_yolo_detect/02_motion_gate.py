"""
03-2. 움직임 게이트 — 2강(움직임 감지)로 3강(YOLO)의 비용을 줄이기

아이디어: 화면에 움직임이 없으면 고양이 위치도 안 변했다. 그러면 YOLO를 건너뛰고
직전 결과를 재사용한다. 움직임이 있을 때만(또는 N프레임마다 한 번은) YOLO를 돌린다.

    프레임 → MOG2 움직임 % ──(≥ 문턱)──► YOLO → 박스 갱신
                          └─(< 문턱)──► 직전 박스 그대로

돔 카메라 30대 중 고양이가 있는 곳은 몇 대뿐이므로, 이 게이트 하나로 GPU 부하가 크게 줄어든다.

실행:  python 02_motion_gate.py --url 0
키:    q 종료 / +,- 움직임 문턱(%) / f 게이트 끄기(매 프레임 YOLO)
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import open_capture, put_text, FpsMeter   # noqa: E402


class MotionGate:
    """MOG2로 '화면의 몇 %가 움직였나'를 계산. 2강 02_motion_detect.py 의 축약판."""

    def __init__(self):
        self.sub = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=25, detectShadows=False)
        self.k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def ratio(self, frame: np.ndarray) -> float:
        small = cv2.resize(frame, (320, 180))                 # 게이트는 싸야 하니 작게
        gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (11, 11), 0)
        mask = self.sub.apply(gray)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.k)
        return float(np.count_nonzero(mask)) / mask.size * 100


def draw_boxes(frame, boxes, names):
    for (x1, y1, x2, y2), c, k in boxes:
        color = (0, 200, 255) if names[k] == "cat" else (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{names[k]} {c:.2f}", (x1 + 3, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="0")
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--motion", type=float, default=0.5, help="이 %% 이상 움직이면 YOLO 실행")
    ap.add_argument("--every", type=int, default=30, help="움직임이 없어도 N프레임마다 한 번은 YOLO")
    args = ap.parse_args()

    model = YOLO(str(ROOT / "models" / "yolo11n.pt"))
    names = model.names
    device = 0 if torch.cuda.is_available() else "cpu"
    gate = MotionGate()
    cap = open_capture(args.url)
    if not cap.isOpened():
        raise SystemExit(f"열 수 없음: {args.url}")

    meter = FpsMeter()
    motion_thresh = args.motion
    gate_on = True
    last_boxes = []
    frames = yolo_calls = 0
    yolo_ms_total = 0.0
    since_last = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames += 1
        since_last += 1

        t0 = time.perf_counter()
        m = gate.ratio(frame)
        gate_ms = (time.perf_counter() - t0) * 1000

        run_yolo = (not gate_on) or (m >= motion_thresh) or (since_last >= args.every)
        yolo_ms = 0.0
        if run_yolo:
            t0 = time.perf_counter()
            r = model.predict(frame, device=device, conf=args.conf, verbose=False)[0]
            yolo_ms = (time.perf_counter() - t0) * 1000
            yolo_calls += 1
            yolo_ms_total += yolo_ms
            since_last = 0
            b = r.boxes
            last_boxes = list(zip(b.xyxy.cpu().numpy().astype(int),
                                  b.conf.cpu().numpy(), b.cls.cpu().numpy().astype(int)))

        draw_boxes(frame, last_boxes, names)
        saved = 100 * (1 - yolo_calls / frames)
        put_text(frame, f"motion {m:4.1f}%  gate {gate_ms:3.1f}ms  yolo {yolo_ms:4.1f}ms  {meter.tick():4.1f}fps")
        put_text(frame, f"YOLO {yolo_calls}/{frames} frames  ({saved:4.1f}% skipped)  thresh {motion_thresh:.1f}%  gate {'on' if gate_on else 'off'}",
                 y=52, color=(0, 200, 255) if run_yolo else (0, 255, 0))
        if run_yolo:
            put_text(frame, "YOLO", y=80, color=(0, 0, 255))
        cv2.imshow("03-2 motion gate", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key in (ord("+"), ord("=")):
            motion_thresh = min(motion_thresh + 0.25, 20)
        elif key == ord("-"):
            motion_thresh = max(motion_thresh - 0.25, 0)
        elif key == ord("f"):
            gate_on = not gate_on

    cap.release()
    cv2.destroyAllWindows()
    if yolo_calls:
        print(f"프레임 {frames}, YOLO 호출 {yolo_calls} ({saved:.1f}% 절약), YOLO 평균 {yolo_ms_total / yolo_calls:.1f} ms")


if __name__ == "__main__":
    main()
