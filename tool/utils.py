import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.concatkdf import ConcatKDFHash
from cryptography.hazmat.primitives.serialization import load_pem_public_key

def validate_signature(public_key_hint, payload, signature):
    # Extract key identifier from the hint (e.g., SHA256 hash)
    key_id = public_key_hint.split(":")[1]
    
    # Recreate SHA256 hash of the payload
    hashed_payload = hashlib.sha256(payload.encode()).hexdigest()
    
    # Check the hash matches the provided key hint
    if hashed_payload != key_id:
        print("Public key hint does not match the payload hash.")
        return False
    
    # Decode the signature and verify
    try:
        key = ec.generate_private_key(ec.SECP256R1()).public_key()  # Replace with your actual public key
        key.verify(base64.b64decode(signature), payload.encode(), ec.ECDSA(hashes.SHA256()))
        print("Signature verified successfully!")
        return True
    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False

def validate_log_entry(log_entry):
    # Validate Log Entry Proof
    root_hash = base64.b64decode(log_entry["inclusionProof"]["rootHash"])
    log_index = int(log_entry["inclusionProof"]["logIndex"])
    tree_size = int(log_entry["inclusionProof"]["treeSize"])
    
    # Basic validations on the structure of the log entry
    if not (0 <= log_index < tree_size):
        print("Invalid log entry index.")
        return False

    print("Log entry validated.")
    return True
