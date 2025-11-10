from typing import Callable

from dotenv import load_dotenv

load_dotenv()

import datetime
import threading
import time
import wave
from pathlib import Path

import numpy as np
import openai
import sounddevice as sd
from pynput import keyboard

from env import AUDIOS_DIR
from utils.dpg_ui import log

SAMPLE_RATE = 16000
recording = False
pressed_keys = set()  # 현재 눌린 키 추적용


def record_audio():
    """Ctrl + Shift + Alt(Option) 누르고 있을 때 오디오 입력 수집"""
    global recording
    frames = []

    log(
        "Ctrl + Shift + Alt(Option) 키를 누르고 있는 동안 녹음 중... (말을 마치면 키를 떼세요)"
    )

    def callback(indata, frames_count, time_info, status):
        if recording:
            frames.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
        while recording:
            sd.sleep(100)

    if not frames:
        log("⚠️ 녹음된 데이터가 없습니다.")
        return None

    audio = np.concatenate(frames, axis=0)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = Path(AUDIOS_DIR) / f"recording_{timestamp}.wav"

    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())

    log(f"파일 저장 완료: {file_path}")
    return file_path


def transcribe_audio(file_path: Path) -> str:
    """Whisper를 이용해 음성을 텍스트로 변환"""
    with open(file_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return transcript.text.strip()


def stt(call_back: Callable[[str], None]):
    """Ctrl + Shift + Alt(Option) 눌렸을 때만 녹음 후 Whisper 변환, 결과를 콜백으로 전달"""

    def _record_and_transcribe():
        try:
            audio_file = record_audio()
            if audio_file:
                text = transcribe_audio(audio_file)
                call_back(text)
        except Exception as e:
            log(f"오류: {e}")

    def on_press(key):
        global recording
        pressed_keys.add(key)

        required_keys = {
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.Key.alt,
        }

        if required_keys.issubset(pressed_keys) and not recording:
            recording = True
            threading.Thread(target=_record_and_transcribe, daemon=True).start()

    def on_release(key):
        global recording
        pressed_keys.discard(key)

        if recording and not {
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.Key.alt,
        }.issubset(pressed_keys):
            recording = False
            log("키를 떼서 녹음이 종료되었습니다.")

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()


if __name__ == "__main__":

    def print_result(text):
        print("🗣️ 변환 결과:", text)

    print("🎧 Ctrl + Shift + Alt(Option) 키를 누르면 녹음이 시작됩니다.")
    stt(print_result)

    while True:
        time.sleep(1)
