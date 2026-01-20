import hashlib
import logging
import os
import base64
import hmac


class PasswordHasher:

    KEY_LENGTH = 32
    SALT_SIZE = 32
    ITERATIONS = 310000
    ALGORITHM = 'pbkdf2_sha256'

    @staticmethod
    def hash_name(algorithm):
        match algorithm:
            case 'pbkdf2_sha256':
                return 'sha256'
        return None

    @classmethod
    def hash_password(cls, password):
        salt = os.urandom(cls.SALT_SIZE)
        dk = hashlib.pbkdf2_hmac(
            cls.hash_name(cls.ALGORITHM),
            password.encode('utf-8'),
            salt,
            cls.ITERATIONS,
            dklen=cls.KEY_LENGTH
        )
        return {
            'pass_hash': base64.b64encode(dk).decode('ascii'),
            'salt': base64.b64encode(salt).decode('ascii'),
            'iterations': cls.ITERATIONS,
            'algorithm': cls.ALGORITHM
        }

    @classmethod
    def verify_password(cls, password, password_hash):
        try:
            pass_hash = base64.b64decode(password_hash.get('pass_hash').encode('ascii'))
            salt = base64.b64decode(password_hash.get('salt').encode('ascii'))
            dk = hashlib.pbkdf2_hmac(
                cls.hash_name(password_hash.get('algorithm')),
                password.encode('utf-8'),
                salt,
                password_hash.get('iterations'),
                dklen=len(pass_hash)
            )
            return hmac.compare_digest(dk, pass_hash)
        except Exception as e:
            logging.exception(e)
            return False
