"""
M1~M2. 카메라 영상 받아서 화면에 띄우기

핵심 뼈대 세 줄:
    cap = cv2.VideoCapture(...)   # 열기
    ok, frame = cap.read()        # 프레임 한 장 (numpy 배열)
    cv2.imshow(...)               # 표시

실행:
    python phone_cam.py --url 0                               # 노트북 웹캠
    python phone_cam.py --url http://192.168.x.x:8080/video   # IP 카메라(MJPEG)
    python phone_cam.py --url rtsp://192.168.x.x:8554/live    # IP 카메라(RTSP)
키: q 종료 / s 스냅샷 저장
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np


def open_capture(url: str) -> cv2.VideoCapture:
    """숫자 문자열("0")이면 로컬 웹캠, 아니면 네트워크 스트림 주소."""
    if url.isdigit():
        # CAP_DSHOW: 윈도우에서 웹캠을 빠르게 여는 백엔드 (기본 MSMF는 첫 오픈이 수 초 걸리기도 함)
        cap = cv2.VideoCapture(int(url), cv2.CAP_DSHOW)
    else:
        # CAP_FFMPEG: http/rtsp 스트림 디코딩 백엔드
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    # 내부 버퍼를 1로 → 오래된 프레임을 쌓아두지 않아 지연이 줄어듦 (백엔드에 따라 무시되기도 함)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def draw_hud(frame: np.ndarray, fps: float, read_ms: float) -> None:
    """프레임 위에 '해상도 / FPS / read() 소요 ms' 텍스트 그리기. frame을 직접 수정(in-place)."""
    h, w = frame.shape[:2]
    text = f"{w}x{h}  {fps:5.1f} fps  read {read_ms:5.1f} ms"
    # 글자 뒤에 검은 띠를 깔아 밝은 배경에서도 읽히게
    cv2.rectangle(frame, (0, 0), (420, 34), (0, 0, 0), -1)
    # 색은 BGR 순서. (0, 255, 0) = 초록
    cv2.putText(frame, text, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="0")
    args = ap.parse_args()

    cap = open_capture(args.url)
    if not cap.isOpened():
        raise SystemExit(f"스트림을 열 수 없음: {args.url}\n"
                         "  - 웹캠이면 다른 프로그램이 점유 중인지\n"
                         "  - 폰이면 같은 Wi-Fi인지, 주소 끝에 /video 붙였는지 확인")

    snap_dir = Path(__file__).parent / "snapshots"
    snap_dir.mkdir(exist_ok=True)

    fps = 0.0
    t_prev = time.perf_counter()
    first = True

    while True:
        t0 = time.perf_counter()
        ok, frame = cap.read()
        read_ms = (time.perf_counter() - t0) * 1000  # 프레임 하나 받는 데 걸린 시간
        if not ok:
            print("프레임 수신 실패")
            break

        if first:
            # "영상 = 숫자 배열" 눈으로 확인
            print(f"frame: shape={frame.shape} dtype={frame.dtype} → "
                  f"높이 {frame.shape[0]}, 너비 {frame.shape[1]}, 채널 {frame.shape[2]} (BGR), "
                  f"{frame.nbytes / 1024:.0f} KB")
            first = False

        # FPS: 순간값은 심하게 튀므로 지수이동평균으로 부드럽게
        now = time.perf_counter()
        inst = 1.0 / max(now - t_prev, 1e-6)
        t_prev = now
        fps = inst if fps == 0 else fps * 0.9 + inst * 0.1

        draw_hud(frame, fps, read_ms)
        cv2.imshow("01 cam", frame)

        # waitKey(1) 이 없으면 imshow 가 실제로 그리지 않음 (GUI 이벤트 처리가 여기서 일어남)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            path = snap_dir / f"snap_{int(time.time())}.jpg"
            cv2.imwrite(str(path), frame)
            print("저장:", path)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
