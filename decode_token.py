"""
Quick token decoder to verify admin JWT structure
"""

import sys

from jose import jwt


def decode_token(token):
    """Decode JWT without verification to inspect payload"""
    try:
        # Decode without verification to see the payload
        payload = jwt.decode(token, options={"verify_signature": False})
        print("\n📋 Token Payload:")
        print("-" * 60)
        for key, value in payload.items():
            print(f"   {key}: {value}")
        print("-" * 60)
        return payload
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        token = sys.argv[1]
        decode_token(token)
    else:
        print("Usage: python decode_token.py <JWT_TOKEN>")
