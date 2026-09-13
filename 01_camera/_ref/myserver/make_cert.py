"""
자체 서명 인증서 생성.

왜 필요한가:
  스마트폰 브라우저는 보안상 카메라 접근(getUserMedia)을 HTTPS 페이지에서만 허용합니다.
  (예외는 localhost 뿐. 폰에서 PC로 접속하면 localhost가 아니므로 HTTPS 필수)
  공인 인증서는 도메인이 있어야 하니, 실습용으로 자체 서명 인증서를 만듭니다.
  폰에서 "안전하지 않음" 경고가 뜨면 [고급] → [계속 진행] 누르면 됩니다.
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
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                x509.IPAddress(ipaddress.ip_address(ip)),
            ]), critical=False)
        .sign(key, hashes.SHA256())
    )
    (here / "key.pem").write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()))
    (here / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    print(f"cert.pem / key.pem 생성 완료 (IP {ip} 포함)")


if __name__ == "__main__":
    main()
