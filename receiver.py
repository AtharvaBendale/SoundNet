import pyaudio
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
# import noisereduce as nr
from crc import *
import math

class Receiver:
    def __init__(self):
        self.len=64

        self.freq=np.array([800])
        for _ in range(self.len):
            self.freq=np.append(self.freq, self.freq[-1]+200)

        self.noise=np.array([0.0]*(self.len+1))
    def open_audio_stream(self, sample_rate: int = 44100):
        """
        Open the audio stream.
        
        :param sample_rate: Sampling rate in Hz
        :return: The audio stream object
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

        :param stream: The open audio stream
        :param duration: Duration of the audio signal to receive in seconds
        :param samcorrectedple_rate: Sampling rate in Hz
        :return: Numpy array containing the received audio signal
        """
        frames = []
        for _ in range(0, int(sample_rate / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)

        return np.frombuffer(b''.join(frames), dtype=np.float32)

    def calibrate(self, sample_rate: int = 44100, bit_duration: float = 0.04):
        segment_size = int(sample_rate*bit_duration)
        white_noise_sample_size = 50

        stream, audio = self.open_audio_stream(sample_rate)

        for _ in range(0, segment_size*white_noise_sample_size, segment_size):
            segment = self.receive_audio(stream, bit_duration, sample_rate)
            freqs, power = signal.welch(segment, sample_rate)
            for i in range(self.len+1):
                self.noise[i] += np.sum(power[(freqs >= self.freq[i]-100) & (freqs <= self.freq[i]+100)])
        for i in range(self.len+1):
            self.noise[i] = self.noise[i]/white_noise_sample_size
        stream.stop_stream()
        stream.close()
        audio.terminate()

    def index_to_bits(self, index:int):
        bits=np.array([])
        index=index-1
        for _ in range(int(math.log2(self.len))):
            bits=np.append(bits,int(index%2))
            index=index//2
        return bits[::-1].astype(int)
    
    def preamble_check(self, preamble):
        n=0
        for i in preamble:
            n=n*2+i
        return int(n)

    def decode_audio_to_bits(self, sample_rate: int = 44100, bit_duration: float = 0.3):
        m_m = np.array([])
        flag = 0
        original_message_length = 0
        transmitted_message_length = 0
        m_p = np.array([])
        # peaks = []
        prev=1
        stream, audio = self.open_audio_stream(sample_rate)

        switch_zero_count = 0

        print("Starting to receive audio: --------------------------------\n\n")  
        while True:
            segment = self.receive_audio(stream, bit_duration/10, sample_rate)
            freq_power=np.array([0.0]*(self.len+1)) #0 is return to zero freq
            freqs, power = signal.welch(segment, sample_rate)
            for i in range(self.len+1):
                freq_power[i] = np.abs(np.sum(power[(freqs >= self.freq[i]-100) & (freqs <= self.freq[i]+100)]) - self.noise[i])

            if freq_power[-1] >= np.max(freq_power[:-1]) and prev==0: 
                if switch_zero_count >= 4:
                    print("high")
                    break
                else:
                    switch_zero_count = 0
                    prev=-1
            elif freq_power[0] >= max(freq_power) :
                prev=0
            elif freq_power[1]>=max(freq_power):
                if prev == 0:
                    switch_zero_count += 1
                prev=1
            else:
                switch_zero_count=0
                prev=np.argmax(freq_power) #if not mid 00 or 11

        self.receive_audio(stream, bit_duration*0.9, sample_rate)
        prev = 0
        max_ind = 0
        while True:
            prev = max_ind
            max_ind = 0
            segment = self.receive_audio(stream, bit_duration/10, sample_rate)
            freqs, power = signal.welch(segment, sample_rate)
            for i in  range(self.len+1):
                freq_power[i] = np.abs(np.sum(power[(freqs >= self.freq[i]-100) & (freqs <= self.freq[i]+100)]) - self.noise[i])
            max_ind=np.argmax(freq_power)
            
            if prev == 0 and max_ind != 0:
                if not flag:
                    if len(m_p)+int(math.log2(self.len))>=5:
                        flag=1
                        m_p = np.append(m_p, self.index_to_bits(max_ind)[0:5-len(m_p)])
                        original_message_length = self.preamble_check(m_p)
                        transmitted_message_length = int(transmissionLength(original_message_length))

                    else:
                        m_p = np.append(m_p, self.index_to_bits(max_ind))
                else:
                    if len(m_m)+int(math.log2(self.len))>=transmitted_message_length:
                        m_m = np.append(m_m, (self.index_to_bits(max_ind))[0:transmitted_message_length-len(m_m)])
                        break
                    else:
                        m_m = np.append(m_m, self.index_to_bits(max_ind))
        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("\n\nAudio reception complete: --------------------------------")
        print("Preamble: ",m_p)
        print("Transmitted message after preamble:", m_m)

        assert len(m_m) == transmissionLength(original_message_length)
        print(f"Original message length: {original_message_length}")

        print(f"Transmitted message length after preamble: {len(m_m)}")
        return original_message_length, list(m_m.astype(int))
