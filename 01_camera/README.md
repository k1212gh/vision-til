# 01. 카메라 연결 & "영상"의 정체

## 왜 이걸 먼저 하나
돔 안에는 카메라가 수십 대 들어갑니다. 전부 **네트워크로 영상을 보내는 카메라(IP 카메라)** 가 됩니다.
스마트폰을 IP 카메라로 만들어 쓰면, 나중에 실제 IP 카메라로 바꿔도 코드가 거의 그대로입니다.

## 핵심 개념 4가지

### 1. 프레임(frame) = 숫자 배열
영상은 "사진(프레임)이 초당 30장 연속으로 오는 것"입니다.
프레임 하나는 높이 x 너비 x 3 크기의 숫자 배열(numpy)입니다.
- 1280x720 프레임 → shape (720, 1280, 3), 값은 0~255
- 마지막 3은 색상 채널. **OpenCV는 BGR 순서** (RGB 아님! 자주 헷갈리는 포인트)
- 픽셀 하나 = frame[y, x] → [B, G, R] 세 숫자. 행(y)이 먼저인 것도 주의

### 2. FPS (frames per second)
초당 프레임 수. 30fps면 프레임 하나 처리에 **33ms** 안에 끝내야 밀리지 않습니다.
나중에 YOLO 탐지를 붙이면 이 33ms 예산을 어떻게 쓸지가 핵심 설계 문제가 됩니다.

### 3. 지연(latency)
카메라가 찍은 순간 → 내 화면에 보이는 순간까지의 시간.
사용자가 드론을 조작할 때 지연이 500ms면 조작이 불가능합니다. 목표는 보통 **100~200ms 이하**.
지연 = [카메라 인코딩] + [네트워크] + [디코딩] + [처리] 의 합.

### 4. 스트림 프로토콜
| 프로토콜 | 특징 | 언제 쓰나 |
|---|---|---|
| MJPEG over HTTP | JPEG 연속 전송. 단순, 지연 낮음, 대역폭 큼 | 실습, 소수 카메라 |
| RTSP (H.264) | 압축 효율 좋음, 대부분의 IP 카메라 표준 | 실제 돔 카메라 |
| WebRTC | 브라우저 직접 재생, 초저지연 | 사용자에게 송출할 때 |

## 실습 준비 (스마트폰)
### 기본: 폰 브라우저 + 내가 만든 PC 서버 (앱 설치 없음)
구조 설명은 [ARCHITECTURE.md](ARCHITECTURE.md), 실행 순서는 [MISSIONS.md](MISSIONS.md), 서버 설명은 [myserver/README.md](myserver/README.md).
```powershell
cd C:\Users\k1212\Desktop\Toy\vision\01_camera\myserver
python make_cert.py     # 최초 1회
python server.py        # 터미널에 뜨는 https://192.168.x.x:8443 을 폰 브라우저에서 열기
```
폰: 인증서 경고 → [고급] → [계속] → **카메라 시작** → 권한 허용. PC 창에 폰 영상이 뜨면 성공.
PC와 폰이 **같은 Wi-Fi** 에 있어야 함.

### 대안: IP Webcam 앱 (남의 서버를 빌리는 방식, 비교용)
- Android: Play 스토어 **IP Webcam** → Start server → http://192.168.x.x:8080/video
- iPhone: **IP Camera Lite** → 앱이 보여주는 RTSP 주소
- 이 주소를 아래 phone_cam.py 의 --url 로 넘기면 됨

## 실행 (phone_cam.py — VideoCapture 방식)
```powershell
cd C:\Users\k1212\Desktop\Toy\vision\01_camera
python phone_cam.py --url 0                                 # 노트북 웹캠 (가상캠이 0번이면 1 또는 2)
python phone_cam.py --url http://192.168.0.10:8080/video    # IP Webcam 앱
```

키: q 종료 / s 스냅샷 저장

## 과제
1. 폰 카메라를 연결해서 FPS와 해상도를 확인하고 적어 두기
2. 폰 앞에서 손을 흔들고, PC 화면에 보이기까지 얼마나 늦는지 체감 지연 측정
   (팁: 폰으로 PC 화면의 시계를 찍으면 두 시계 차이가 곧 지연)
3. index.html 의 JPEG 품질(50/70/90%)과 fps(10/15/30)를 바꾸면 KB/s 와 지연이 어떻게 변하는지 비교
4. 스냅샷을 찍고 파이썬에서 cv2.imread 로 열어 frame[y, x] 값이 실제 색과 맞는지 확인 (BGR 순서!)
