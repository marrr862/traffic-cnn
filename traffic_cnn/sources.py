"""Video sources: local files, webcams, network streams (RTSP/HTTP/HLS) and YouTube links."""
import threading
import time
from pathlib import Path

LIVE_PREFIXES = ('rtsp://', 'rtsps://', 'rtmp://', 'http://', 'https://', 'udp://', 'tcp://')


def is_live(source):
    """True for webcams (an integer index) and network URLs; False for local files."""
    source = str(source).strip()
    return source.isdigit() or source.lower().startswith(LIVE_PREFIXES)


def is_youtube(source):
    s = str(source).lower()
    return 'youtube.com/' in s or 'youtu.be/' in s


def resolve(source):
    """Return something cv2.VideoCapture can open. YouTube pages are resolved with yt-dlp."""
    source = str(source).strip()
    if source.isdigit():
        return int(source)
    if is_youtube(source):
        try:
            import yt_dlp
        except ImportError as exc:
            raise ValueError('YouTube links need the yt-dlp package: pip install yt-dlp') from exc
        options = dict(quiet=True, no_warnings=True, format='best[height<=1080][vcodec!=none]/best')
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(source, download=False)
        url = info.get('url') or (info.get('requested_formats') or [{}])[0].get('url')
        if not url:
            raise ValueError('Could not resolve the YouTube stream URL')
        return url
    return source


def describe(source):
    source = str(source).strip()
    if source.isdigit():
        return f'webcam {source}'
    if is_youtube(source):
        return 'YouTube stream'
    if source.lower().startswith(LIVE_PREFIXES):
        return source.split('://')[0].upper() + ' stream'
    return Path(source).name


class LatestFrameReader:
    """Reads a live source in a background thread and keeps only the newest frame.

    Analysis is usually slower than the camera; keeping only the latest frame keeps the
    delay constant instead of letting a buffer grow. Each frame carries its wall-clock time.
    """

    def __init__(self, capture):
        self.capture = capture
        self.lock = threading.Lock()
        self.frame, self.stamp, self.sequence = None, None, 0
        self.running, self.failed = True, False
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            ok, frame = self.capture.read()
            if not ok:
                self.failed = True
                time.sleep(0.05)
                if not self.capture.isOpened():
                    break
                continue
            with self.lock:
                self.frame, self.stamp = frame, time.perf_counter()
                self.sequence += 1

    def read(self, last_sequence, timeout=10.0):
        """Wait for a frame newer than last_sequence. Returns (ok, frame, stamp, sequence)."""
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            with self.lock:
                if self.frame is not None and self.sequence != last_sequence:
                    return True, self.frame.copy(), self.stamp, self.sequence
            if not self.thread.is_alive():
                break
            time.sleep(0.005)
        return False, None, None, last_sequence

    def stop(self):
        self.running = False
        self.thread.join(timeout=2)
