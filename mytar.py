#!/usr/bin/env python3

"""
mytar.py - toy archiver implementing create (c) and extract (x)
Uses ONLY POSIX-style system calls via the os module for I/O.

Archive format (repeated until EOF):
[4 bytes] filename length (big-endian unsigned int)
[N bytes] filename (utf-8)
[8 bytes] file size (big-endian unsigned int)
[M bytes] file contents
"""

import os
import sys

BUF_SIZE = 4096


def die(msg: str, code: int = 1):
    os.write(2, ("mytar: " + msg + "\n").encode())
    sys.exit(code)


def read_exact(fd: int, n: int) -> bytes:
    """Read exactly n bytes from fd or return fewer bytes if EOF is hit."""
    chunks = []
    remaining = n
    while remaining > 0:
        data = os.read(fd, remaining)
        if not data:
            break
        chunks.append(data)
        remaining -= len(data)
    return b"".join(chunks)


def create_archive(filenames):
    out_fd = 1  # stdout

    for name in filenames:
        try:
            fd = os.open(name, os.O_RDONLY)
        except OSError:
            die(f"cannot open file '{name}'")

        try:
            st = os.fstat(fd)
        except OSError:
            os.close(fd)
            die(f"cannot stat file '{name}'")

        size = st.st_size
        name_bytes = name.encode('utf-8')

        # write filename length (4 bytes)
        os.write(out_fd, len(name_bytes).to_bytes(4, 'big'))
        # write filename
        os.write(out_fd, name_bytes)
        # write file size (8 bytes)
        os.write(out_fd, size.to_bytes(8, 'big'))

        # stream file contents
        remaining = size
        while remaining > 0:
            chunk = os.read(fd, min(BUF_SIZE, remaining))
            if not chunk:
                os.close(fd)
                die(f"unexpected EOF reading '{name}'")
            os.write(out_fd, chunk)
            remaining -= len(chunk)

        os.close(fd)


def extract_archive():
    in_fd = 0  # stdin

    while True:
        # read filename length
        raw_len = read_exact(in_fd, 4)
        if len(raw_len) == 0:
            # normal EOF
            return
        if len(raw_len) < 4:
            die("corrupted archive (incomplete filename length)")

        name_len = int.from_bytes(raw_len, 'big')
        if name_len <= 0:
            die("corrupted archive (invalid filename length)")

        # read filename
        name_bytes = read_exact(in_fd, name_len)
        if len(name_bytes) < name_len:
            die("corrupted archive (incomplete filename)")

        try:
            name = name_bytes.decode('utf-8')
        except UnicodeDecodeError:
            die("corrupted archive (filename encoding)")

        # read file size
        raw_size = read_exact(in_fd, 8)
        if len(raw_size) < 8:
            die("corrupted archive (incomplete file size)")

        size = int.from_bytes(raw_size, 'big')
        if size < 0:
            die("corrupted archive (invalid file size)")

        try:
            out_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        except OSError:
            die(f"cannot create output file '{name}'")

        # read file contents
        remaining = size
        while remaining > 0:
            chunk = os.read(in_fd, min(BUF_SIZE, remaining))
            if not chunk:
                os.close(out_fd)
                die("corrupted archive (unexpected EOF in file data)")
            os.write(out_fd, chunk)
            remaining -= len(chunk)

        os.close(out_fd)


def main():
    if len(sys.argv) < 2:
        die("usage: mytar.py c file... | mytar.py x")

    mode = sys.argv[1]

    if mode == 'c':
        if len(sys.argv) < 3:
            die("create mode requires at least one file")
        create_archive(sys.argv[2:])
    elif mode == 'x':
        extract_archive()
    else:
        die("unknown mode (use 'c' or 'x')")


if __name__ == '__main__':
    main()
