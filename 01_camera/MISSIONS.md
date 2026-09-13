# 01 미션 시트

규칙: 한 미션씩. 끝나면 코드를 보여주고 리뷰 받기. 막히면 힌트 요청 (힌트 1 → 힌트 2 → _ref 위치).
읽을 순서: [ARCHITECTURE.md](ARCHITECTURE.md) → 이 문서 → 뼈대 파일의 TODO.

| # | 파일 | 목표 | 성공 확인 |
|---|---|---|---|
| M1 | phone_cam.py | 웹캠 열고 창에 띄우고 q로 종료 | `python phone_cam.py --url 0` 실행 시 창이 뜨고 q로 닫힘 |
| M2 | phone_cam.py | 해상도·FPS·read() ms HUD, s로 스냅샷 | 화면에 `1280x720 30.0fps` 근처 표시, snapshots/에 jpg 생성 |
| M3 | myserver/make_cert.py | TODO 2개 채우기 | 실행 시 cert.pem/key.pem 생성, 출력에 PC IP(192.168.x.x) 포함 |
| M4 | myserver/server.py | HTTPS로 index.html 서빙 (`index`, `create_app`, `make_ssl_context`, `start_server_thread`, main 앞부분) | PC 브라우저에서 https://localhost:8443 → 경고 무시 → "카메라 시작" 버튼 보임 |
| M5 | myserver/server.py | `/ws` 수신 + `FrameQueue` + `decode_jpeg` + 메인 루프 imshow | server.py 띄우고 `python test_client.py` 실행 → PC 창에 웹캠 영상 보임 |
| M6 | myserver/index.html | 카메라 → canvas → JPEG → WebSocket 송신 | 폰에서 https://<PC IP>:8443 열고 카메라 시작 → stat에 fps/KB/s 표시 |
| M7 | 전체 | 엔드투엔드 + 계측 | 폰 영상이 PC 창에 보임. 지연(ms), JPEG 50/70/90% 별 KB/s, fps 30일 때 dropped 카운트 기록 |

## 각 미션의 포인트

**M1** — `cap.read()`가 돌려주는 `ok`를 반드시 검사. `waitKey(1)`이 없으면 창이 안 그려짐(imshow는 waitKey가 있어야 실제로 그림).

**M2** — FPS를 그냥 `1/(now-prev)`로 찍으면 숫자가 심하게 튐. 지수이동평균으로 부드럽게. 첫 프레임에서 `frame.shape`를 찍어 "영상 = (720,1280,3) 배열"을 눈으로 확인.

**M3** — `local_ip()`의 UDP connect 트릭은 실제 패킷을 안 보냄. SAN에 PC IP가 없으면 폰 브라우저가 더 강하게 막음.

**M4** — 서버 스레드는 `daemon=True`(메인이 끝나면 같이 죽게). 브라우저 경고는 자체 서명 인증서 때문이며 정상.

**M5** — 큐에는 **디코드 전 bytes**를 넣는다(디코드는 메인 스레드 몫, 네트워크 스레드는 최대한 가볍게). `queue.Empty`일 때도 `waitKey`를 호출해야 창이 안 멈춤.

**M6** — `getUserMedia`는 https에서만 됨. `canvas.width`는 `video.play()` 이후에 잡아야 0이 아님. `bufferedAmount` 체크가 지연 누적을 막는 핵심.

**M7** — 지연 측정법: 폰으로 PC 화면의 시계(초 단위 스톱워치 등)를 찍고, PC 창에 보이는 시각과 실제 시각의 차이를 읽는다.

## 이해 확인 (ARCHITECTURE.md 6절) 답을 먼저 채팅에 적고 M1 시작
1. JPEG 품질 90%로 올리면?
2. FrameQueue maxsize=100이면?
3. imshow를 aiohttp 핸들러 안에서 부르면?
