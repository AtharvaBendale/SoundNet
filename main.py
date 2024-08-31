from crc import encodeCrc, decodeCrc, preamble
import math
import argparse
from receiver import Receiver
from sender import Sender

def send() -> None:

    bitstring = input("Please enter the message to be transmitted : ")
    message = [int(element) for element in bitstring]
    bits = len(message)
    encoding = encodeCrc(message = message)
    print(f"The bit-string constructed to transmit : {''.join([str(element) for element in encoding])}")
    num_errors = int(input("Please enter the number of bit errors to be introduced : "))

    for error_t in range(num_errors):
        error_fraction = float(input(f"Please enter fraction number {error_t+1} : "))
        encoding[math.ceil(error_fraction * len(encoding))-1] = 1 - encoding[math.ceil(error_fraction * len(encoding))-1]

    print(f"The bit-string with errors : {''.join([str(element) for element in encoding])}")
    print(f"The preamble is :", preamble(bits))
    print(f"The combined transmission is : 01{preamble(bits)}{''.join([str(element) for element in encoding])}")
    input("Press Enter to start transmission ")
    sender = Sender()
    encoded_audio = sender.encode_bits_to_audio([0, 1] + [(bits>>i) & 1 for i in range(4, -1, -1)] + encoding )
    sender.send_audio(encoded_audio)

def recv():
    
    receiver = Receiver()
    receiver.calibrate(bit_duration=0.04)
    bits, transmission = receiver.decode_audio_to_bits()

    message = decodeCrc(transmission = transmission, bits = bits)

    print(f"The obtained and error corrected message is : {''.join([str(bit) for bit in message])}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Provide the mode to be used (send/recv)")
    parser.add_argument('--send', action='store_true', default = False, help='Flag to send')
    parser.add_argument('--recv', action='store_true', default = False, help='Flag to receive')
    args = parser.parse_args()

    if args.send:
        send()
    elif args.recv:
        recv()
    else:
        raise AssertionError("Please provide --send or --recv flag")