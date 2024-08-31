CRC_POLY = {
    2 : [
        (4, 7, 0xe5),
        (9, 8, 0x1d7),
        (13, 9, 0x30b),
        (21, 10, 0x573),
        (26, 11, 0xbaf),
        (53, 12, 0x175d),
        (113, 14, 0x425b),
        (136, 15, 0xd51b),
        (241, 16, 0x15935),
        (493, 18, 0x72aa7),
        (494, 19, 0xad0b5),
        (1005, 20, 0x191513)
    ],
    3 : [
        (5, 10, 0x29b),
        (12, 11, 0x571),
        (13, 14, 0x28a9),
        (16, 15, 0x5bd5),
        (46, 17, 0x1751b),
        (49, 20, 0x8810e),
        (106, 21, 0x12faa5),
        (231, 24, 0x880ee6),
        (484, 27, 0x521f64b),
    ]
}

def preamble(bits : int) -> int:
    '''
        Returns the binary representation of the given integer in a string format
        Parameters:
            bits (int): The integer to be converted to binary
        Returns:
            preamble (str): The binary representation of the given integer
    '''
    preamble_bits = [ str((bits>>i) & 1) for i in range(4, -1, -1)]
    return "".join(preamble_bits)

def transmissionLength(original_length : int) -> int:
    '''
        Returns the length of the transmission after adding redundancy using CRC
        Parameters:
            original_length (int): The length of the original message
        Returns:
            transmission_length (int): The length of the transmission after adding redundancy using CRC
    '''
    return original_length + bitsToPoly(original_length)[1]

def bitsToPoly(bits : int, error_bits : int  = 2) :
    '''
        Gives you the optimal CRC polynomial and its length just enough to completely correct two bit errors in any message of size 'bits'
        Parameters:
            bits (int): The size of the message to be handled
            error_bits (int): The number of bit errors needed to be handled (Default value 2)
        Returns:
            (poly, degree) (tuple[int]): 'poly' is an integer representing the optimal polynomial, 'degree' is the degree of the optimal polynomial
    '''
    for (bitCapacity, degree, poly) in CRC_POLY[error_bits]:
        if bitCapacity >= bits:
            return poly, degree
    raise AssertionError("The given message size is too large to be handled by the current implementation")    

def polyDivision(dividend : int, poly : int, degree : int) :
    '''
        Divided the given dividend by the given polynomial and returns the remainder
        Parameters:
            dividend (int): An integer which has to be divided
            poly (int): An integer representing the polynomial used as divisor
            degree (int): The degree of the given polynomial
        Returns:
            remainder (int): Returns the remainder of the polynomial division
    '''
    i : int = 60
    while i >= 0 and (not ((dividend >> i) & 1)):
        i -= 1
    while i >= degree :
        dividend ^= (poly<<(i-degree))
        i -= 1
        while i >= 0 and (not ((dividend >> i) & 1)):
            i -= 1
    return dividend

def bruteCheck(dividend : int, degree : int, poly : int, bits : int, error_bits : int = 2) :
    '''
        Iterates over all possible double/triple bit errors and checks whether the modified dividend is perfectly divisible by the polynomial
        Parameters:
            dividend (int): The dividend containing error on any two/three indices
            poly (int): An integer representing the polynomial used as divisor
            degree (int): The degree of the given polynomial
            bits (int): The size of the message to be handled
            error_bits (int): The number of bit errors needed to be handled; Default value 2; Supported values are 2 & 3
        Returns:
            possible (list[int]): The list of all possible double/triple bit error corrected messages which makes this dividend divisible by the given polynomial
    '''
    possible = []
    if error_bits == 2:
        for i in range(bits + degree - 1):
            for j in range(i+1, bits + degree):
                if polyDivision(dividend ^ (1 << i) ^ (1 << j), poly = poly, degree = degree) == 0:
                    possible.append(dividend ^ (1 << i) ^ (1 << j))
    else:
        for i in range(bits + degree - 2):
            for j in range(i+1, bits + degree - 1):
                for k in range(j+1, bits + degree):
                    if polyDivision(dividend ^ (1 << i) ^ (1 << j) ^ (1 << k), poly = poly, degree = degree) == 0:
                        possible.append(dividend ^ (1 << i) ^ (1 << j) ^ (1 << k))

    if len(possible) == 0:
        for i in range(bits + degree):
            if polyDivision(dividend = dividend ^ (1 << i), poly = poly, degree = degree) == 0:
                possible.append(dividend ^ (1 << i))
    return possible

def encodeCrc(message, error_bits : int = 2) :
    '''
        Encodes the given message and adds redundancy using CRC for error detection and correction
        Parameters:
            messages (list[int]): The bit stream message to be encoded
            error_bits (int): The number of bit errors needed to be handled; Default value 2; Supported values are 2 & 3
        Returns:
            encoding (list[int]): The encoded form of the give input bit stream
    '''
    bits = len(message)
    poly, degree = bitsToPoly(bits = bits, error_bits = error_bits)
    messageInt = 0
    for bit in message:
        messageInt = 2 * messageInt + bit
    encoding = (messageInt << degree) ^ polyDivision(dividend = (messageInt << degree), poly = poly, degree = degree)
    return [(encoding >> i) & 1 for i in range(bits + degree - 1, -1, -1)]

def decodeCrc(transmission, bits : int, error_bits : int = 2) :
    '''
        Decodes the given transmission, detects and corrects errors
        Parameters:
            transmission (list[int]): The bit stream message received after the preamble
            bits (int): Denotes the size of the original message without the redundancy, this is obtained from preamble
            error_bits (int): The number of bit errors needed to be handled; Default value 2; Supported values are 2 & 3
        Returns:
            decoded (list[int]): The original message without any redundancy and errors
    '''
    poly, degree = bitsToPoly(bits = bits)
    transmissionInt = 0
    for bit in transmission:
        transmissionInt = 2 * transmissionInt + bit
    if polyDivision(dividend = transmissionInt, poly = poly, degree = degree) == 0:
        decoded = transmissionInt
    else:
        possible = bruteCheck(dividend = transmissionInt, degree = degree, poly = poly, bits = bits, error_bits = error_bits)
        if len(possible) != 1:
            raise AssertionError(f"CRC Decoding Error, total {len(possible)} possible decodings!")
        decoded = possible[0]
    decoded >>= degree
    return [(decoded >> i) & 1 for i in range(bits - 1, -1, -1)]
