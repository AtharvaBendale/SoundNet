import pyaudio
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
# import noisereduce as nr
from crc import *
import math

class Receiver:
    def __init__(self, base):
        self.base= base
        self.freq = np.arange(800, 800 + 200 * (self.base+1) , 200)
        self.noise=np.array([0.0]*(self.base+1))

    def open_audio_stream(self, sample_rate: int = 44100):
        """
        Open the audio stream.
        
        Parameters:
            sample_rate (int): Sampling rate in Hz
        
        Returns:
            stream: The audio stream object
            audio: The audio object
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
            stream: The audio stream object
            duration (float): Duration of each signal in seconds
            sample_rate (int): Sampling rate in Hz

        Returns:
            np.ndarray: Numpy array containing the audio signal
        """
        frames = []
        for _ in range(0, int(sample_rate / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)

        return np.frombuffer(b''.join(frames), dtype=np.float32)

    def calibrate(self, sample_rate: int = 44100, duration: float = 0.03):
        """
        Calculates the noise power for each frequency range

        Parameters:
            sample_rate (int): Sampling rate in Hz
            duration (float): Duration of each measurement in seconds

        """
        segment_size = int(sample_rate*duration)
        white_noise_sample_size = 50

        stream, audio = self.open_audio_stream(sample_rate)

        for _ in range(0, segment_size*white_noise_sample_size, segment_size):
            segment = self.receive_audio(stream, duration, sample_rate)
            freqs, power = signal.welch(segment, sample_rate)
            for i in range(self.base+1):
                self.noise[i] += np.sum(power[(freqs >= self.freq[i]-100) & (freqs <= self.freq[i]+100)])
        for i in range(self.base+1):
            self.noise[i] = self.noise[i]/white_noise_sample_size
        stream.stop_stream()
        stream.close()
        audio.terminate()

    def index_to_bits(self, index : int):
        """
        Convert an index to a list of bits.
        Parameters:
            index (int): Index to convert

        Returns:
            bits (np.ndarray): Numpy array containing the bits
        """
        bits=np.array([])
        index=index-1
        for _ in range(int(math.log2(self.base))):
            bits=np.append(bits,int(index%2))
            index=index//2
        return bits[::-1].astype(int)
    
    def preamble_check(self, preamble : np.ndarray):
        """
        Convert a preamble to an integer.
        Parameters:
            preamble (np.ndarray): Preamble to convert

        Returns:
            int: Integer converted from the preamble
        """
        n=0
        for i in preamble:
            n=n*2+i
        return int(n)

    def decode_audio_to_bits(self, sample_rate: int = 44100, bit_duration: float = 0.3):
        """
        Decode an audio signal to a list of bits.

        Parameters:
            sample_rate (int): Sampling rate in Hz
            bit_duration (float): Duration of each bit in seconds

        Returns:
            int: Length of the original message
            list[int]: List of bits of the message after preamble
        """
        message_after_preamble = np.array([])
        preamble = np.array([])
        flag = 0
        switch_zero_count = 0
        original_message_length = 0
        transmitted_message_length = 0
        prev=1
        
        stream, audio = self.open_audio_stream(sample_rate)

        print("Starting to receive audio: --------------------------------\n\n")  

        while True:
            segment = self.receive_audio(stream, bit_duration/10, sample_rate)
            freq_power=np.array([0.0]*(self.base+1)) 
            freqs, power = signal.welch(segment, sample_rate)
            for i in range(self.base+1):
                freq_power[i] = np.abs(np.sum(power[(freqs >= self.freq[i]-100) & (freqs <= self.freq[i]+100)]) - self.noise[i])

            if freq_power[-1] >= np.max(freq_power[:-1]) and prev==0: 
                if switch_zero_count >= 4:
                    print("Special sequence ends. Now recieving preamble ... \n\n")  
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
                prev=np.argmax(freq_power) 

        self.receive_audio(stream, bit_duration*0.9, sample_rate)
        prev = 0
        max_ind = 0
        while True:
            prev = max_ind
            max_ind = 0
            segment = self.receive_audio(stream, bit_duration/10, sample_rate)
            freqs, power = signal.welch(segment, sample_rate)
            for i in  range(self.base+1):
                freq_power[i] = np.abs(np.sum(power[(freqs >= self.freq[i]-100) & (freqs <= self.freq[i]+100)]) - self.noise[i])
            max_ind=np.argmax(freq_power)
            
            if prev == 0 and max_ind != 0:
                if not flag:
                    if len(preamble)+int(math.log2(self.base))>=5:
                        flag=1
                        preamble = np.append(preamble, self.index_to_bits(max_ind)[0:5-len(preamble)])
                        original_message_length = self.preamble_check(preamble)
                        transmitted_message_length = int(transmissionLength(original_message_length))

                    else:
                        preamble = np.append(preamble, self.index_to_bits(max_ind))
                else:
                    if len(message_after_preamble)+int(math.log2(self.base))>=transmitted_message_length:
                        message_after_preamble = np.append(message_after_preamble, (self.index_to_bits(max_ind))[0:transmitted_message_length-len(message_after_preamble)])
                        break
                    else:
                        message_after_preamble = np.append(message_after_preamble, self.index_to_bits(max_ind))
        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("\n\nAudio reception complete: --------------------------------")
        assert len(message_after_preamble) == transmissionLength(original_message_length)
        
        print("Preamble: ",preamble)
        print("Transmitted message after preamble:", message_after_preamble)
        print(f"Original message length: {original_message_length}")
        print(f"Transmitted message length after preamble: {len(message_after_preamble)}")
        return original_message_length, list(message_after_preamble.astype(int))
