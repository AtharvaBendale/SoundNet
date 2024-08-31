import numpy as np
import pyaudio
import time
import math

class Sender:

    def __init__(self, messsage : int | list[str]):
        pass

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

    def encode_bits_to_audio(self, bits: np.ndarray, sample_rate: int = 44100, duration: float =0.2, amplitude: float =1):
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
        frequencies = {0: 1000, 1:4000 ,2:2000}  # Frequencies for bits 0 and 1
        audio_signal = np.array([])
        
        for bit in bits:
            if bit==1:
                tone = self.generate_tone(frequencies[bit], duration, sample_rate, amplitude)
                audio_signal = np.concatenate((audio_signal, tone))
                tone = self.generate_tone(frequencies[2], duration, sample_rate, amplitude)
            else:
                tone = self.generate_tone(frequencies[bit], duration, sample_rate, amplitude)
                audio_signal = np.concatenate((audio_signal, tone))
                tone = self.generate_tone(frequencies[2], duration, sample_rate, amplitude)
            audio_signal = np.concatenate((audio_signal, tone))
                
        
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
