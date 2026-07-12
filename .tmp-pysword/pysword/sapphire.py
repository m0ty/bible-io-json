# -*- coding: utf-8 -*-
"""
    This is a direct port of the original C++ code to Python done by Tomas Groth in 2019.
    The original copyright note is below. This port is also Public Domain.

/* sapphire.cpp -- the Sapphire II stream cipher class.
   Dedicated to the Public Domain the author and inventor:
   (Michael Paul Johnson).  This code comes with no warranty.
   Use it at your own risk.
   Ported from the Pascal implementation of the Sapphire Stream
   Cipher 9 December 1994.
   Added hash pre- and post-processing 27 December 1994.
   Modified initialization to make index variables key dependent,
   made the output function more resistant to cryptanalysis,
   and renamed to Sapphire II 2 January 1995
*/
"""


class Sapphire:

    def __init__(self, key):
        """
        Constructor. Initializes the stream cipher.

        :param key: The cipher key to use.
        """
        self.initial_cards = [0] * 256
        self.initial_rsum = 0
        self.cards = [0] * 256
        self.rotor = 0
        self.ratchet = 0
        self.avalanche = 0
        self.last_plain = 0
        self.last_cipher = 0
        bytes_key = bytearray(key, 'utf-8')
        if key:
            self._initialize(bytes_key, len(bytes_key))

    def _initialize(self, key, keysize):
        """
        Key size may be up to 256 bytes.
        Pass phrases may be used directly, with longer length
        compensating for the low entropy expected in such keys.
        Alternatively, shorter keys hashed from a pass phrase or
        generated randomly may be used. For random keys, lengths
        of from 4 to 16 bytes are recommended, depending on how
        secure you want this to be.

        :param key: The cipher key to use.
        :param keysize: The size of the cipher key.
        """

        # If we have been given no key, assume the default hash setup.
        if not key:
            self._hash_init()
            return

        # Start with cards all in order, one of each.
        self.cards = list(range(0, 256))

        # Swap the card at each position with some other card.
        toswap = 0
        keypos = 0  # Start with first byte of user key.
        rsum = 0
        for i in range(255, -1, -1):
            toswap, rsum, keypos = self._keyrand(i, key, keysize, rsum, keypos)
            swaptemp = self.cards[i]
            self.cards[i] = self.cards[toswap]
            self.cards[toswap] = swaptemp

        # Initialize the indices and data dependencies.
        # Indices are set to different values instead of all 0
        # to reduce what is known about the state of the cards
        # when the first byte is emitted.
        self.rotor = self.cards[1]
        self.ratchet = self.cards[3]
        self.avalanche = self.cards[5]
        self.last_plain = self.cards[7]
        self.last_cipher = self.cards[rsum]

        # Save initial cards and rsum for easy reset, might be a security risk.
        # Note that this was added for python and was not in the original C++ code
        self.initial_cards = self.cards[:]
        self.initial_rsum = rsum

    def reset(self):
        """
        Resets the cipher stream for new data.
        Note that this was added for python and was not in the original C++ code.
        The data save to be able to reset might be a security risk.
        """
        if self.initial_cards:
            self.cards = self.initial_cards[:]
            self.rotor = self.cards[1]
            self.ratchet = self.cards[3]
            self.avalanche = self.cards[5]
            self.last_plain = self.cards[7]
            self.last_cipher = self.cards[self.initial_rsum]
        else:
            self._hash_init()

    def _keyrand(self, limit, user_key, keysize, rsum, keypos):
        """
        Helper function used to determine which cards to swap randomly
        based on the user key.

        :param limit: Value from 0 to limit to return.
        :param user_key: The user key.
        :param keysize: Size of the user key.
        :param keypos: Current position/index of the user key to start from.
        :return: Three values are returned: card to swap, new rsum, new keypos
        """
        u = limit + 1      # Value from 0 to limit to return.
        retry_limiter = 0  # No infinite loops allowed.
        mask = 0           # Select just enough bits.

        if limit == 0:  # Avoid divide by zero error.
            return 0, rsum, keypos
        mask = 1                # Fill mask with enough bits to cover
        while mask < limit:     # the desired range.
            mask = (mask << 1) + 1

        while (u > limit):
            rsum = self.cards[rsum] + user_key[keypos]
            keypos += 1
            if keypos >= keysize:
                keypos = 0        # Recycle the user key.
                rsum += keysize   # key "aaaa" != key "aaaaaaaa"
            rsum &= 0xFF
            u = mask & rsum
            retry_limiter += 1
            if retry_limiter > 11:
                u %= limit     # Prevent very rare long loops.

        return u, rsum, keypos

    def _hash_init(self):
        """
        This function is used to initialize non-keyed hash
        computation.
        """
        # Initialize the indices and data dependencies.
        self.rotor = 1
        self.ratchet = 3
        self.avalanche = 5
        self.last_plain = 7
        self.last_cipher = 11

        # Start with cards all in inverse order.
        self.cards = list(range(255, -1, -1))

    def _burn(self):
        """
        Destroy the key and state information in RAM.
        """
        self.initial_cards = [0] * 256
        self.initial_rsum = 0
        self.cards = [0] * 256
        self.rotor = 0
        self.ratchet = 0
        self.avalanche = 0
        self.last_plain = 0
        self.last_cipher = 0

    def __del__(self):
        """
        Destructor
        """
        self._burn()

    def encrypt(self, b):
        """
        Picture a single enigma rotor with 256 positions, rewired
        on the fly by card-shuffling.
        This cipher is a variant of one invented and written
        by Michael Paul Johnson in November, 1993.

        :param b: Byte to encrypt
        :return: Encrypted byte
        """
        swaptemp = 0

        # Shuffle the deck a little more.
        self.ratchet = (self.ratchet + self.cards[self.rotor]) & 0xFF
        self.rotor = (1 + self.rotor) & 0xFF
        swaptemp = self.cards[self.last_cipher]
        self.cards[self.last_cipher] = self.cards[self.ratchet]
        self.cards[self.ratchet] = self.cards[self.last_plain]
        self.cards[self.last_plain] = self.cards[self.rotor]
        self.cards[self.rotor] = swaptemp
        self.avalanche = (self.avalanche + self.cards[swaptemp]) & 0xFF

        # Output one byte from the state in such a way as to make it
        # very hard to figure out which one you are looking at.
        self.last_cipher = b ^ self.cards[(self.cards[self.ratchet] + self.cards[self.rotor]) & 0xFF] ^ \
            self.cards[self.cards[(self.cards[self.last_plain] + self.cards[self.last_cipher] +
                                   self.cards[self.avalanche]) & 0xFF]]
        self.last_plain = b
        return self.last_cipher

    def decrypt_bytes(self, encrypted_data):
        """
        Helper function to make it easier for the users to decrypt data.
        Added in the python version

        :param encrypted_data: Bytes to decrypt
        :return: Decrypted bytes
        """
        self.reset()
        decrypted_data = []
        for b in bytearray(encrypted_data):
            decrypted_data.append(self.decrypt(b))
        # Doing both bytes and bytearray to make it work on both python2 and 3
        return bytes(bytearray(decrypted_data))

    def decrypt(self, b):
        """
        Decrypts a byte

        :param b: Byte to decrypt
        :return: Decrypted byte
        """
        swaptemp = 0

        # Shuffle the deck a little more.
        self.ratchet = (self.ratchet + self.cards[self.rotor]) & 0xFF
        self.rotor = (1 + self.rotor) & 0xFF
        swaptemp = self.cards[self.last_cipher]
        self.cards[self.last_cipher] = self.cards[self.ratchet]
        self.cards[self.ratchet] = self.cards[self.last_plain]
        self.cards[self.last_plain] = self.cards[self.rotor]
        self.cards[self.rotor] = swaptemp
        self.avalanche = (self.avalanche + self.cards[swaptemp]) & 0xFF

        # Output one byte from the state in such a way as to make it
        # very hard to figure out which one you are looking at.
        self.last_plain = b ^ self.cards[(self.cards[self.ratchet] + self.cards[self.rotor]) & 0xFF] ^ \
            self.cards[self.cards[(self.cards[self.last_plain] + self.cards[self.last_cipher] +
                                   self.cards[self.avalanche]) & 0xFF]]
        self.last_cipher = b
        return self.last_plain

    def hash_final(self, hashlength):
        """
        Generates a hash of the given length

        :param hashlength: Length of the hash to generate
        :return: Decrypted byte
        """
        for i in range(255, -1, -1):
            self.encrypt(i)
        hash_out = []
        for i in range(0, hashlength):
            hash_out.append(self.encrypt(0))
        # Doing both bytes and bytearray to make it work on both python2 and 3
        return bytes(bytearray(hash_out))
