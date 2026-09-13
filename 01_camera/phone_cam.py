"""
M1~M2. 카메라 영상 받아서 화면에 띄우기 (뼈대)

핵심 뼈대 세 줄:
    cap = cv2.VideoCapture(...)   # 열기
    ok, frame = cap.read()        # 프레임 한 장 (numpy 배열)
    cv2.imshow(...)               # 표시

실행:
    python phone_cam.py --url 0                          # 노트북 웹캠
    python phone_cam.py --url http://192.168.x.x:8080/video   # 나중에 IP 카메라
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np


def open_capture(url: str) -> cv2.VideoCapture:
    """숫자 문자열("0")이면 로컬 웹캠, 아니면 네트워크 스트림 주소.

    TODO(M1):
      - url.isdigit() 로 분기
      - 웹캠: cv2.VideoCapture(int(url), cv2.CAP_DSHOW)   # 윈도우에서 빠르게 열리는 백엔드
      - 스트림: cv2.VideoCapture(url, cv2.CAP_FFMPEG)
      - 열린 cap 반환
    """
    raise NotImplementedError


def draw_hud(frame: np.ndarray, fps: float, read_ms: float) -> None:
    """프레임 위에 '해상도 / FPS / read() 소요 ms' 텍스트 그리기. frame을 직접 수정(in-place).

    TODO(M2):
      - h, w = frame.shape[:2]
      - cv2.putText(frame, 문자열, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 크기, (B,G,R), 두께)
      - 색은 BGR 순서라는 것 기억
    """
    raise NotImplementedError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="0")
    args = ap.parse_args()

    # TODO(M1): open_capture 로 열고, cap.isOpened() 가 False면 에러 메시지 출력 후 종료

    # TODO(M2): 스냅샷 저장 폴더 준비 (Path(__file__).parent / "snapshots", mkdir(exist_ok=True))

    # TODO(M2): FPS 계산용 변수 (직전 시각 t_prev = time.perf_counter(), fps = 0.0)

    while True:
        # TODO(M1): 프레임 읽기. ok가 False면 "수신 실패" 출력하고 break
        # TODO(M2): read() 전후 시각 차이로 read_ms 계산
        # TODO(M2): FPS 계산. 순간 fps = 1 / (now - t_prev). 튀는 걸 막으려면
        #           fps = fps*0.9 + inst*0.1 (지수이동평균)
        # TODO(M2): 첫 프레임일 때 frame.shape, frame.dtype 을 print 해서 "영상 = 숫자 배열" 확인
        # TODO(M2): draw_hud 호출
        # TODO(M1): cv2.imshow("01 cam", frame)
        # TODO(M1): key = cv2.waitKey(1) & 0xFF ; 'q' 면 break
        # TODO(M2): 's' 면 cv2.imwrite 로 snapshots/ 에 저장
        raise NotImplementedError

    # TODO(M1): cap.release(), cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
