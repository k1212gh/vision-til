"""
03-1. YOLO 객체 탐지 — "화면 어디에 고양이가 있는가"

한 프레임을 YOLO에 넣으면 [박스(x1,y1,x2,y2), 신뢰도, 클래스] 목록이 나온다.
COCO 80종으로 학습된 기본 모델에 이미 cat(15), dog(16), person(0) 이 들어 있어서
추가 학습 없이 바로 고양이를 찾을 수 있다.

실행:
    python 01_detect_cat.py --url 0                       # 모든 클래스
    python 01_detect_cat.py --url 0 --classes cat,person  # 고양이·사람만
    python 01_detect_cat.py --url 0 --model s             # 더 큰 모델 (정확 ↑, 속도 ↓)
키: q 종료 / g GPU·CPU 전환 / +,- 신뢰도 임계값 / a 전체 클래스 토글
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import open_capture, put_text, FpsMeter   # noqa: E402

MODELS = ROOT / "models"


def load_model(size: str) -> YOLO:
    """yolo11{n,s,m}.pt 를 models/ 에서 읽고, 없으면 자동 다운로드."""
    MODELS.mkdir(exist_ok=True)
    path = MODELS / f"yolo11{size}.pt"
    return YOLO(str(path))


def class_ids(model: YOLO, names_csv: str):
    """'cat,dog' → [15, 16]. 빈 문자열이면 None(전체)."""
    if not names_csv:
        return None
    wanted = {n.strip() for n in names_csv.split(",")}
    ids = [i for i, n in model.names.items() if n in wanted]
    missing = wanted - {model.names[i] for i in ids}
    if missing:
        raise SystemExit(f"COCO에 없는 클래스: {missing}. 목록: {sorted(model.names.values())}")
    return ids


def draw_detections(frame, result, names) -> int:
    """result.boxes 를 프레임에 그리고 개수 반환."""
    boxes = result.boxes
    if boxes is None:
        return 0
    xyxy = boxes.xyxy.cpu().numpy().astype(int)   # (N, 4) 픽셀 좌표
    conf = boxes.conf.cpu().numpy()               # (N,)   0~1
    cls = boxes.cls.cpu().numpy().astype(int)     # (N,)   클래스 id
    for (x1, y1, x2, y2), c, k in zip(xyxy, conf, cls):
        color = (0, 200, 255) if names[k] == "cat" else (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{names[k]} {c:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
        cv2.putText(frame, label, (x1 + 3, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    return len(xyxy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="0")
    ap.add_argument("--model", default="n", choices=["n", "s", "m"], help="모델 크기 (n 가장 빠름)")
    ap.add_argument("--classes", default="", help="예: cat,dog,person  (비우면 전체)")
    ap.add_argument("--conf", type=float, default=0.4, help="이 신뢰도 미만은 버림")
    ap.add_argument("--imgsz", type=int, default=640, help="추론 입력 크기 (작을수록 빠름)")
    args = ap.parse_args()

    model = load_model(args.model)
    names = model.names
    wanted = class_ids(model, args.classes)
    device = 0 if torch.cuda.is_available() else "cpu"
    conf = args.conf
    filter_on = wanted is not None

    cap = open_capture(args.url)
    if not cap.isOpened():
        raise SystemExit(f"열 수 없음: {args.url}")
    meter = FpsMeter()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        t0 = time.perf_counter()
        # predict 한 줄이 전처리(리사이즈·정규화) → 신경망 → 후처리(NMS) 전부
        result = model.predict(frame, device=device, conf=conf, imgsz=args.imgsz,
                               classes=wanted if filter_on else None, verbose=False)[0]
        infer_ms = (time.perf_counter() - t0) * 1000

        n = draw_detections(frame, result, names)
        n_cat = int((result.boxes.cls == 15).sum()) if result.boxes is not None else 0

        dev = "GPU" if device == 0 else "CPU"
        put_text(frame, f"yolo11{args.model} {dev} {infer_ms:5.1f}ms  {meter.tick():4.1f}fps  conf>{conf:.2f}")
        put_text(frame, f"objects {n}  cats {n_cat}  filter {'on' if filter_on else 'off'}", y=52,
                 color=(0, 200, 255) if n_cat else (0, 255, 0))
        cv2.imshow("03-1 yolo", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("g") and torch.cuda.is_available():
            device = "cpu" if device == 0 else 0
        elif key in (ord("+"), ord("=")):
            conf = min(conf + 0.05, 0.95)
        elif key == ord("-"):
            conf = max(conf - 0.05, 0.05)
        elif key == ord("a") and wanted is not None:
            filter_on = not filter_on

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
