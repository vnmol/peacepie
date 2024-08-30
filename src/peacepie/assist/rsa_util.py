import binascii
import logging
import os

import rsa

from peacepie.assist import dir_operations

KEY_DIR = 'keys'


class RsaManager:

    def __init__(self):
        self.logger = logging.getLogger()
        self.pubkey = None
        self.prvkey = None
        dir_operations.makedir(KEY_DIR)
        if os.path.isfile(f'{KEY_DIR}/id_rsa.pub') and os.path.isfile(f'{KEY_DIR}/id_rsa.pub'):
            with open(f'{KEY_DIR}/id_rsa.pub', 'br') as f:
                data = f.read()
            self.pubkey = rsa.PublicKey.load_pkcs1(data)
            with open(f'{KEY_DIR}/id_rsa', 'br') as f:
                data = f.read()
            self.prvkey = rsa.PrivateKey.load_pkcs1(data)
        else:
            dir_operations.makedir(KEY_DIR, True)
            self.pubkey, self.prvkey = rsa.newkeys(256)
            with open(f'{KEY_DIR}/id_rsa.pub', 'bw') as f:
                f.write(rsa.PublicKey.save_pkcs1(self.pubkey))
            with open(f'{KEY_DIR}/id_rsa', 'bw') as f:
                f.write(rsa.PrivateKey.save_pkcs1(self.prvkey))

    def encode(self, value):
        res = None
        try:
            res = binascii.b2a_uu(rsa.encrypt(value.encode(), self.pubkey)).decode()
        except Exception as e:
            self.logger.exception(e)
        return res

    def decode(self, value):
        try:
            return rsa.decrypt(binascii.a2b_uu(value.encode()), self.prvkey).decode()
        except Exception as e:
            self.logger.exception(e)


instance = RsaManager()
