import argparse
import json
import secrets
from enum import Enum


class EncryptionAlgorithm(Enum):
    HS256 = 'HS256'
    HS384 = 'HS384'
    HS512 = 'HS512'


def generate_keys(algorithm: EncryptionAlgorithm):
    """Generates encryption keys based on the chosen algorithm."""
    if algorithm in {EncryptionAlgorithm.HS256, EncryptionAlgorithm.HS384, EncryptionAlgorithm.HS512}:
        # Symmetric Key (HMAC)
        KEY_SIZES = {
            EncryptionAlgorithm.HS256: 32,  # 256-bit key
            EncryptionAlgorithm.HS384: 48,  # 384-bit key
            EncryptionAlgorithm.HS512: 64  # 512-bit key
        }
        secret_key = secrets.token_hex(KEY_SIZES[algorithm])
        return secret_key, secret_key  # public key and private key are the same for HMAC
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


if __name__ == '__main__':
    # argparse the output directory
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--output', '-O', type=str, default='./jwt_secret.json')
    arg_parser.add_argument('--algorithm', '-A', type=EncryptionAlgorithm, choices=list(EncryptionAlgorithm), default=EncryptionAlgorithm.HS256)
    args = arg_parser.parse_args()

    # Generate keys based on the selected algorithm
    private_key, public_key = generate_keys(args.algorithm)

    output_json = {
        "algorithm": args.algorithm.value,
        "private_key": private_key,
        "public_key": public_key,  # None for HS256, HS384, HS512
    }

    # Save to file
    with open(args.output, 'w') as f:
        f.write(json.dumps(output_json, indent=4))

    print(f"Keys generated and saved to {args.output}")
