"""
M3. 자체 서명 인증서 생성

왜 필요한가: 폰 브라우저는 https 페이지에서만 카메라를 열어 준다 (ARCHITECTURE.md 3절).
x509 API 자체는 비전 학습 대상이 아니므로 흐름만 보면 됩니다: 개인키 생성 → 인증서에 IP 목록(SAN) 넣고 서명 → 파일 저장.

실행:  python make_cert.py  →  cert.pem, key.pem 생성
"""
import datetime as dt
import ipaddress
import socket
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def local_ip() -> str:
    """이 PC가 Wi-Fi에서 쓰는 IP (예: 192.168.75.6) 를 문자열로 반환.

    트릭: UDP 소켓을 외부 주소(8.8.8.8:80)에 connect 하면 실제 패킷은 나가지 않지만
    OS가 "이 목적지로 나갈 때 쓸 내 IP"를 골라 준다 → getsockname()[0]
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def main():
    here = Path(__file__).parent
    ip = local_ip()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "catdome-dev")])
    now = dt.datetime.now(dt.timezone.utc)

    # SAN(Subject Alternative Name): 이 인증서가 유효한 주소 목록.
    # 여기 없는 주소로 접속하면 브라우저가 더 강하게 거부한다.
    san = x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.IPAddress(ipaddress.ip_address(ip)),   # 폰이 접속할 PC의 Wi-Fi IP
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=365))
        .add_extension(san, critical=False)
        .sign(key, hashes.SHA256())
    )

    (here / "key.pem").write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    (here / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    print(f"cert.pem / key.pem 생성 완료 (IP {ip} 포함)")


if __name__ == "__main__":
    main()
