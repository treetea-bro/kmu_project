import datetime
import threading
import time
import wave
from pathlib import Path
from typing import Callable

import numpy as np
import openai
import sounddevice as sd
from dotenv import load_dotenv
from pynput import keyboard

from env import AUDIOS_DIR
from utils.dpg_ui import log

load_dotenv()

SAMPLE_RATE = 16000
recording = False
pressed_keys = set()


def transcribe_audio(file_path: Path) -> str:
    """Whisper를 이용해 음성을 텍스트로 변환"""
    with open(file_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return transcript.text.strip()


def stt(call_back: Callable[[str], None]):
    """Ctrl + Shift + Alt 누르고 있을 때만 녹음 후 Whisper 변환"""

    global recording
    frames = []  # 녹음된 프레임 버퍼

    def callback(indata, frames_count, time_info, status):
        if recording:
            frames.append(indata.copy())

    def save_and_transcribe():
        """녹음이 끝나면 파일로 저장 후 변환"""
        nonlocal frames
        if not frames:
            log("⚠️ 녹음된 데이터가 없습니다.")
            return

        audio = np.concatenate(frames, axis=0)
        frames.clear()

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = Path(AUDIOS_DIR) / f"recording_{timestamp}.wav"

        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())

        log(f"파일 저장 완료: {file_path}")

        try:
            text = transcribe_audio(file_path)
            call_back(text)
        except Exception as e:
            log(f"오류: {e}")

    def recorder_thread():
        """항상 InputStream 유지하면서 recording=True일 때만 버퍼에 추가"""
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
            while True:
                time.sleep(0.1)

    def on_press(key):
        global recording
        pressed_keys.add(key)

        required_keys = {keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.alt}

        if required_keys.issubset(pressed_keys) and not recording:
            recording = True
            log("녹음 시작 (Ctrl + Shift + Alt 누르는 중)")

    def on_release(key):
        global recording
        pressed_keys.discard(key)

        required_keys = {keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.alt}
        if recording and not required_keys.issubset(pressed_keys):
            recording = False
            log("키를 떼서 녹음 종료됨.")
            threading.Thread(target=save_and_transcribe, daemon=True).start()

    # 🔹 백그라운드 녹음 스레드
    threading.Thread(target=recorder_thread, daemon=True).start()

    # 🔹 키보드 리스너
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()


if __name__ == "__main__":

    def print_result(text):
        print("🗣️ 변환 결과:", text)

    print("🎧 Ctrl + Shift + Alt(Option)을 누르면 녹음이 시작됩니다.")
    stt(print_result)

    while True:
        time.sleep(1)
