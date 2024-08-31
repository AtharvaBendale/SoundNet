import numpy as np
import pyaudio
import time
import math

class Sender:

    def __init__(self, messsage : int | list[str]):
        self.len=64 

        self.frequencies = np.array([800])
        for i in range(self.len):
            self.frequencies = np.append(self.frequencies, self.frequencies[-1]+200)


    def generate_tone(self, frequency: int, duration: float, sample_rate: int = 44100, amplitude: float=1):
        '''
        Generate a sine wave tone of given frequency and duration.
        Parameters:
            frequency (int): Frequency of the tone in Hz
            duration (float): Duration of the tone in seconds
            sample_rate (int): Sampling rate in Hz (default: 44100)
            amplitude (float): Amplitude of the wave (0.0 to 1.0, default: 0.5)
        Returns:
            wave (np.ndarray): Numpy array containing the audio signal
        '''
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = amplitude * np.sin(2 * np.pi * frequency * t)
        return wave
    
    def num_conv(self, message: list[int], base : int) -> np.ndarray:
        """
        Convert a list of bits to a list of integers.
        Parameters:
            message (list[int]): List of bits
            base (int): Base to convert the bits to
        Returns:
            converted_array (np.ndarray): Numpy array containing the converted integers
        """
        converted_array = np.array([])
        message=np.array(message)
        n=int(math.log2(base))
        if len(message)%n!= 0:
            message = np.append(message, np.zeros(n - len(message)%n))
        for i in range(0, len(message), n):
            num = 0
            for j in range(0, n):
                num += message[i+j]*(2**(n-j-1))
            converted_array = np.append(converted_array, int(num)+1)

        return converted_array

    def change_base(self, message: list[int], base:int = 2) -> np.ndarray:
        """
        Convert a list of bits to a list of integers in a different base.
        Parameters:
            message (list[int]): List of bits
            base (int): Base to convert the bits to
        Returns:
            transmission (np.ndarray): Numpy array containing the converted integers
        """

        transmission=np.array([1,1,1,1,1,-1])
        #preamble 10-14
        #TODO: remove special sequence from Atharva's main.py
        transmission = np.append(transmission, self.num_conv(message[6:11], base))

        #actual message
        transmission = np.append(transmission, self.num_conv(message[11:], base))
        return transmission

    def encode_bits_to_audio(self, bits: np.ndarray, sample_rate: int = 44100, duration: float =0.15, amplitude: float =1):
        """
        Encode a list of bits into an audio signal.
        Parameters:
            bits (np.ndarray): List of bits (0s and 1s)
            sample_rate (int): Sampling rate in Hz
            duration (float): Duration of each bit's tone in seconds
            amplitude (float): Amplitude of the wave
        Returns
            audio_signal (np.ndarray): Numpy array containing the audio signal
        """
        audio_signal = np.array([])
        
        tranmission_msg_in_changed_base = self.change_base(bits, self.len)

        for i in tranmission_msg_in_changed_base:
            audio_signal = np.append(audio_signal, self.generate_tone(self.frequencies[int(i)], duration, sample_rate, amplitude))
            audio_signal = np.append(audio_signal, self.generate_tone(self.frequencies[0], duration, sample_rate, amplitude))
        print(tranmission_msg_in_changed_base)
        return audio_signal


    def send_audio(self, audio_signal: np.ndarray, sample_rate: int = 44100):
        """
        Send an audio signal to the default audio output device.
        Parameters:
            audio_signal (np.ndarray): Numpy array containing the audio signal
            sample_rate (int): Sampling rate in Hz
        """

        audio = pyaudio.PyAudio()
        
        stream = audio.open(format=pyaudio.paFloat32,
                            channels=1,
                            rate=sample_rate,
                            output=True)
        
        # Playing the audio signal
        while(True):
            if(math.floor(time.time()*10)%2==0):
                stream.write(audio_signal.astype(np.float32).tobytes())
                break
        
        # Closing the stream
        stream.stop_stream()
        stream.close()
        audio.terminate()