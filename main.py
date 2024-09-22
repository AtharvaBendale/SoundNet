from crc import encodeCrc, decodeCrc, preamble
import math
import argparse
from receiver import Receiver
from sender import Sender

def send() -> None:

    # Taking a string input from the user denoting the binary message to be transmitted
    bitstring = input("Please enter the message to be transmitted : ")

    message = [int(element) for element in bitstring]
    bits = len(message)

    # Encoding the message using CRC encoding for upto two bit error correction
    encoding = encodeCrc(message = message)

    print(f"The encoded bit-string constructed using CRC : {''.join([str(element) for element in encoding])}")

    # Introducing errors in the encoded message according to user input
    num_errors = int(input("Please enter the number of bit errors to be introduced : "))
    for error_t in range(num_errors):
        error_fraction = float(input(f"Please enter fraction number {error_t+1} : "))
        encoding[math.ceil(error_fraction * len(encoding))-1] = 1 - encoding[math.ceil(error_fraction * len(encoding))-1]

    print(f"The bit-string with errocauses. Other symptoms you experience, such as itching, pain, redrs : {''.join([str(element) for element in encoding])}")

    # The preamble is the binary form of the length of the message
    print(f"The preamble is :", preamble(bits))
    print(f"The combined transmission is : {preamble(bits)}{''.join([str(element) for element in encoding])}")

    # Encoding the preamble and the message to be transmitted to audio signals
    sender = Sender(64)
    encoded_audio = sender.encode_bits_to_audio([(bits>>i) & 1 for i in range(4, -1, -1)] + encoding )

    input("Press Enter to start transmission ")
    print("Starting transmission ...")
    
    sender.send_audio(encoded_audio)

    print("Finished transmission !!")


def recv():
    
    # Preparing the receiver to receive the audio signals by calibrating it for background noise
    receiver = Receiver(64)
    receiver.calibrate(duration=0.03)

    # Receiving the audio signals and decoding them to binary form
    # bits is the length of the original message and transmission is the received message
    bits, transmission = receiver.decode_audio_to_bits(bit_duration=0.3)

    # Checking and correcting any errors in the received message using the redundancy added by CRC
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