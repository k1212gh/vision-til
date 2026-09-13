# 01-b. 앱 없이 내가 직접 만든 서버로 폰 영상 받기

## 세 가지 길
| 방법 | 폰 쪽 | PC 쪽 | 난이도 | 배우는 것 |
|---|---|---|---|---|
| A. 남의 앱 (IP Webcam) | 앱이 서버 | 받기만 | 쉬움 | 거의 없음 |
| **B. 폰 브라우저 + 내 PC 서버** | 웹페이지 하나 | HTTPS + WebSocket 서버 | 중간 | 스트리밍의 뼈대 전부 |
| C. 폰 앱 직접 개발 (Android/Kotlin) | 앱이 서버 | 받기 | 높음 | 모바일 개발 |

여기서는 **B**를 합니다. 폰에는 아무것도 설치하지 않고, 브라우저로 PC 주소만 열면 됩니다.
실제 돔에서도 카메라(IP캠)는 남이 만든 걸 사고, **받아서 처리하고 다시 사용자에게 보내는 서버**를
우리가 만듭니다. 즉 B가 곧 실전 구조입니다.

## 구조
```
폰 브라우저                                PC (server.py)
 카메라 → <video> → <canvas>              aiohttp 스레드
   → JPEG 압축(toBlob)                      /      : index.html 제공
   → WebSocket 전송 ─────(wss)──────────►   /ws    : JPEG bytes 수신 → FrameQueue
                                          메인 스레드
                                            queue.get → cv2.imdecode → imshow
```

## 실행
```powershell
cd C:\Users\k1212\Desktop\Toy\vision\01_camera\myserver
python make_cert.py     # 최초 1회. 폰 브라우저가 HTTPS를 요구해서 필요
python server.py        # 터미널에 뜨는 https://192.168.x.x:8443 을 폰에서 열기
```
폰 브라우저에서: 인증서 경고 → [고급] → [계속] → **카메라 시작** 버튼 → 권한 허용.

## 핵심 개념
1. **HTTPS 없이는 폰 카메라를 못 연다.** 브라우저 보안 정책. 그래서 자체 서명 인증서를 만든다.
2. **WebSocket** = 한 번 연결하면 양쪽이 계속 데이터를 주고받는 통로. HTTP처럼 매번 요청/응답이 아님.
   나중에 사용자 조작 명령(드론 왼쪽으로!)을 보낼 때도 이 통로를 쓴다.
3. **인코딩/디코딩**: 프레임(720p, 2.7MB) 그대로 보내면 초당 80MB. JPEG로 줄이면 50~150KB.
   `canvas.toBlob(jpeg)` ↔ `cv2.imdecode` 가 한 쌍.
4. **프레임 버리기(drop)가 정상이다.** 처리가 느리면 밀린 프레임을 버려야 지연이 안 쌓인다.
   폰 쪽 `bufferedAmount` 체크와 PC 쪽 `FrameQueue(maxsize=2)` 두 군데서 버린다.
   "모든 프레임을 처리"가 아니라 "항상 최신 프레임을 처리"가 실시간 시스템의 원칙.

## 과제
1. index.html에서 JPEG 품질을 50% / 90%로 바꿔 보고 KB/s와 화질 차이 관찰
2. fps를 30으로 올렸을 때 PC 화면의 drop 카운트가 올라가는지 확인
3. 폰으로 PC 화면의 시계를 찍어서 지연(ms) 재기 → IP Webcam 앱과 비교
4. (도전) server.py에서 받은 프레임을 흑백으로 바꿔서 보여주기
