"""앱 아이콘(.ico) 생성기 — 외부 패키지 없이 표준 라이브러리만 사용.

실행: python tools/make_icon.py
결과: assets/easysaving.ico  (256x256, PNG 내장 ICO)
"""

import os
import struct
import zlib

SIZE = 256
SS = 2                      # 계단현상을 줄이려고 2배로 그린 뒤 축소
W = SIZE * SS

TOP = (0x4C, 0x8BF0 >> 8, 0xF5)      # 그라데이션 위쪽 (밝은 파랑)
BOTTOM = (0x1E, 0x56, 0xC8)          # 그라데이션 아래쪽 (진한 파랑)
WHITE = (255, 255, 255)


def make_pixels():
    buf = bytearray(W * W * 4)
    radius = int(W * 0.22)

    def put(x, y, rgb, alpha=255):
        index = (y * W + x) * 4
        if alpha == 255:
            buf[index:index + 4] = bytes((rgb[0], rgb[1], rgb[2], 255))
            return
        # 단순 알파 합성
        base = buf[index:index + 4]
        inv = 255 - alpha
        for channel in range(3):
            buf[index + channel] = (rgb[channel] * alpha + base[channel] * inv) // 255
        buf[index + 3] = max(base[3], alpha)

    def inside_round_rect(x, y, x1, y1, x2, y2, r):
        if x < x1 or x > x2 or y < y1 or y > y2:
            return False
        cx = min(max(x, x1 + r), x2 - r)
        cy = min(max(y, y1 + r), y2 - r)
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r

    # 배경 (둥근 사각형 + 세로 그라데이션)
    for y in range(W):
        ratio = y / (W - 1)
        color = tuple(int(TOP[i] * (1 - ratio) + BOTTOM[i] * ratio) for i in range(3))
        for x in range(W):
            if inside_round_rect(x, y, 0, 0, W - 1, W - 1, radius):
                put(x, y, color)

    # 뒤쪽 문서 (반투명 흰색)
    _fill_page(put, inside_round_rect, 0.20, 0.16, 0.58, 0.72, alpha=150)
    # 앞쪽 문서 (불투명 흰색)
    _fill_page(put, inside_round_rect, 0.36, 0.28, 0.80, 0.86, alpha=255)
    # 앞쪽 문서 안의 글줄
    line_x1, line_x2 = int(W * 0.43), int(W * 0.73)
    for i in range(3):
        y1 = int(W * (0.40 + i * 0.11))
        y2 = y1 + int(W * 0.035)
        for y in range(y1, y2):
            for x in range(line_x1, line_x2 if i < 2 else int(W * 0.63)):
                put(x, y, (0x2F, 0x6F, 0xED))
    return buf


def _fill_page(put, inside, x1r, y1r, x2r, y2r, alpha):
    x1, y1 = int(W * x1r), int(W * y1r)
    x2, y2 = int(W * x2r), int(W * y2r)
    radius = int(W * 0.035)
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            if inside(x, y, x1, y1, x2, y2, radius):
                put(x, y, WHITE, alpha)


def downsample(buf):
    out = bytearray(SIZE * SIZE * 4)
    for y in range(SIZE):
        for x in range(SIZE):
            r = g = b = a = 0
            for dy in range(SS):
                for dx in range(SS):
                    index = ((y * SS + dy) * W + (x * SS + dx)) * 4
                    r += buf[index]
                    g += buf[index + 1]
                    b += buf[index + 2]
                    a += buf[index + 3]
            count = SS * SS
            index = (y * SIZE + x) * 4
            out[index:index + 4] = bytes((r // count, g // count, b // count, a // count))
    return out


def to_png(pixels):
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)                                   # 필터 없음
        start = y * SIZE * 4
        raw += pixels[start:start + SIZE * 4]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def to_ico(png_bytes):
    header = struct.pack("<HHH", 0, 1, 1)               # reserved, type=icon, count
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png_bytes), 22)
    return header + entry + png_bytes


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets = os.path.join(root, "assets")
    os.makedirs(assets, exist_ok=True)

    print("아이콘 그리는 중…")
    png = to_png(downsample(make_pixels()))

    png_path = os.path.join(assets, "easysaving.png")
    with open(png_path, "wb") as fp:
        fp.write(png)
    ico_path = os.path.join(assets, "easysaving.ico")
    with open(ico_path, "wb") as fp:
        fp.write(to_ico(png))
    print(f"완료: {ico_path} ({os.path.getsize(ico_path):,} bytes)")
    print(f"      {png_path} ({os.path.getsize(png_path):,} bytes)")


if __name__ == "__main__":
    main()
