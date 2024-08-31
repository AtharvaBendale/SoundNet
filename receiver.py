import pyaudio
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
import noisereduce as nr
from crc import *

class Receiver:
    def __init__(self):
        self.high_noise_avg = 0
        self.low_noise_avg = 0
        self.mid_noise_avg = 0
        self.high_freq = 4000
        self.low_freq = 1000
        self.mid_freq = 2000

    def open_audio_stream(self, sample_rate: int = 44100):
        """
        Open the audio stream.
        Parameters:
            sample_rate (int): Sampling rate in Hz
        Returns:
            (audio, stream): The audio & stream objects
        """
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paFloat32,
                            channels=1,
                            rate=sample_rate,
                            input=True,
                            frames_per_buffer=1024)
        return stream, audio

    def receive_audio(self, stream, duration: float, sample_rate: int = 44100):
        """
        Receive an audio signal from the default audio input device.
        Parameters:
            stream: The open audio stream
            duration (float): Duration of the audio signal to receive in seconds
            sample_rate (int): Sampling rate in Hz
        Returns:
            Out (np.ndarray): Numpy array containing the received audio signal
        """
        frames = []
        for _ in range(0, int(sample_rate / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)

        return np.frombuffer(b''.join(frames), dtype=np.float32)

    def calibrate(self, sample_rate: int = 44100, bit_duration: float = 0.04):
        """
        Receive a white noise signal to calibrate the noise levels.

        Parameters:
            sample_rate (int): Sampling rate in Hz
            bit_duration (float): Duration of each bit in seconds
        """
        segment_size = int(sample_rate*bit_duration)
        white_noise_sample_size = 50

        stream, audio = self.open_audio_stream(sample_rate)

        for _ in range(0, segment_size*white_noise_sample_size, segment_size):
            segment = self.receive_audio(stream, bit_duration, sample_rate)
            freqs, power = signal.welch(segment, sample_rate)
            low_freq_power = np.sum(power[(freqs >= self.low_freq-100) & (freqs <= self.low_freq+100)])
            mid_freq_power = np.sum(power[(freqs >= self.mid_freq-100) & (freqs <= self.mid_freq+100)])
            high_freq_power = np.sum(power[(freqs >= self.high_freq-100) & (freqs <= self.high_freq+100)])

            self.low_noise_avg += low_freq_power
            self.high_noise_avg += high_freq_power
            self.mid_noise_avg += mid_freq_power

        self.low_noise_avg = self.low_noise_avg / white_noise_sample_size
        self.high_noise_avg = self.high_noise_avg / white_noise_sample_size
        self.mid_noise_avg = self.mid_noise_avg / white_noise_sample_size

        stream.stop_stream()
        stream.close()
        audio.terminate()

    def preprocess_audio(self, audio_signal: np.ndarray, sample_rate: int = 44100):
        reduced_noise_signal = nr.reduce_noise(y=audio_signal, sr=sample_rate)
        return reduced_noise_signal

    def decode_audio_to_bits(self, sample_rate: int = 44100, bit_duration: float = 0.4):
        """
        Receive an audio signal and decode it to bits.
        
        Parameters:
            sample_rate (int): Sampling rate in Hz
            bit_duration (float): Duration of each bit in seconds
        Returns:
            (int, list): The original message length and the received message bits after preamble
        """
        message_crc = []
        flag = 0
        original_message_length = 0
        transmitted_message_length = 0
        preamble = []
        prev=0
        switch_zero_count = 0
        stream, audio = self.open_audio_stream(sample_rate)

        print("Starting to receive audio: --------------------------------\n\n")  
        while True:
            segment = self.receive_audio(stream, bit_duration/10, sample_rate)

            freqs, power = signal.welch(segment, sample_rate)
            low_freq_power = abs(np.sum(power[(freqs >= self.low_freq-100) & (freqs <= self.low_freq+100)]) - self.low_noise_avg)
            mid_freq_power = abs(np.sum(power[(freqs >= self.mid_freq-100) & (freqs <= self.mid_freq+100)]) - self.mid_noise_avg)
            high_freq_power = abs(np.sum(power[(freqs >= self.high_freq-100) & (freqs <= self.high_freq+100)]) - self.high_noise_avg)

            if high_freq_power >= max(low_freq_power, mid_freq_power) and prev==-1:
                if switch_zero_count >= 4:
                    print("High")
                    flag = 1
                    break
                else:
                    switch_zero_count = 0
                    prev=1
            elif mid_freq_power >= max(low_freq_power, high_freq_power) :
                prev=-1
            else:
                if prev == -1:
                    switch_zero_count += 1
                prev=0
        self.receive_audio(stream, bit_duration*0.9, sample_rate)
        prev = -1
        bit = -1
        while True:
            prev = bit
            bit = -1
            segment = self.receive_audio(stream, bit_duration/10, sample_rate)

            freqs, power = signal.welch(segment, sample_rate)
            low_freq_power = abs(np.sum(power[(freqs >= self.low_freq-100) & (freqs <= self.low_freq+100)]) - self.low_noise_avg)
            mid_freq_power = abs(np.sum(power[(freqs >= self.mid_freq-100) & (freqs <= self.mid_freq+100)]) - self.mid_noise_avg)
            high_freq_power = abs(np.sum(power[(freqs >= self.high_freq-100) & (freqs <= self.high_freq+100)]) - self.high_noise_avg)
            
            if low_freq_power > max(high_freq_power,mid_freq_power):
                bit = 0
            elif high_freq_power > max(low_freq_power,mid_freq_power):
                bit = 1
            
            if len(preamble) < 5:
                if prev == -1 and bit !=  prev:
                    preamble.append(bit)
                    original_message_length += bit * int(2**(5 - len(preamble)))
                    if len(preamble) == 5:
                        flag = 2
                        transmitted_message_length = transmissionLength(original_message_length)
                        continue

            if flag == 2:
                if prev == -1 and bit != prev:
                    message_crc.append(bit)
                    if len(message_crc) == transmitted_message_length:
                        break
        stream.stop_stream()
        stream.close()
        audio.terminate()

        print("\n\nAudio reception complete: --------------------------------")
        print("Preamble:", preamble)
        print("Transmitted message after preamble:", message_crc)

        assert len(message_crc) == transmissionLength(original_message_length)
        print(f"Original message length: {original_message_length}")

        print(f"Transmitted message length after preamble: {len(message_crc)}")
        return original_message_length, message_crc
