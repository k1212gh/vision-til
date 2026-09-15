"""
02-1. 색공간 — 같은 프레임을 다른 숫자로 보기

한 프레임을 BGR / Gray / HSV 로 나눠 보고, HSV 범위로 "특정 색만 남기는 마스크"를 만든다.
왜: 고양이 장난감(빨간 공, 초록 깃털)을 색으로 찾는 가장 싼 방법이고,
    나중에 YOLO 결과를 보정하거나 특정 물체를 빠르게 걸러낼 때 씀.

실행:  python 01_color_space.py --url 0
키:    q 종료 / 트랙바로 H,S,V 하한·상한 조절 → 마스크 창에 흰색으로 남는 부분이 "그 색"
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import open_capture, put_text, FpsMeter   # noqa: E402

WIN = "02-1 color space"
MASK = "02-1 mask (white = selected color)"


def nothing(_):
    pass


def make_trackbars():
    """HSV 하한/상한 6개 트랙바. OpenCV의 H 범위는 0~179 (360도를 반으로 접음)."""
    cv2.namedWindow(MASK)
    for name, maxv, init in [("H_low", 179, 0), ("H_high", 179, 179),
                             ("S_low", 255, 80), ("S_high", 255, 255),
                             ("V_low", 255, 80), ("V_high", 255, 255)]:
        cv2.createTrackbar(name, MASK, init, maxv, nothing)


def read_trackbars():
    g = lambda n: cv2.getTrackbarPos(n, MASK)
    lo = np.array([g("H_low"), g("S_low"), g("V_low")], dtype=np.uint8)
    hi = np.array([g("H_high"), g("S_high"), g("V_high")], dtype=np.uint8)
    return lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="0")
    args = ap.parse_args()

    cap = open_capture(args.url)
    if not cap.isOpened():
        raise SystemExit(f"열 수 없음: {args.url}")
    make_trackbars()
    meter = FpsMeter()

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.resize(frame, (640, 360))            # 4분할 표시를 위해 축소

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)   # (H, W)   밝기만
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)     # (H, W, 3) 색상/채도/명도

        lo, hi = read_trackbars()
        mask = cv2.inRange(hsv, lo, hi)                  # 범위 안이면 255, 아니면 0
        picked = cv2.bitwise_and(frame, frame, mask=mask)  # 마스크가 255인 픽셀만 남김

        # 4분할: 원본 / Gray / HSV(그대로 BGR로 해석하면 이상한 색이 됨 → 그게 정상) / 색 추출
        gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        put_text(frame, f"BGR  {meter.tick():4.1f}fps")
        put_text(gray3, "GRAY (1 channel)")
        hsv_show = hsv.copy()
        put_text(hsv_show, "HSV raw (looks weird = normal)")
        put_text(picked, f"inRange H{lo[0]}-{hi[0]} S{lo[1]}-{hi[1]} V{lo[2]}-{hi[2]}")

        top = np.hstack([frame, gray3])
        bottom = np.hstack([hsv_show, picked])
        cv2.imshow(WIN, np.vstack([top, bottom]))
        cv2.imshow(MASK, mask)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
