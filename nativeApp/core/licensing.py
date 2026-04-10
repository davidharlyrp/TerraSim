# core/licensing.py
import hashlib
import base64

def _get_salt():
    """
    Kunci Garam (Salt) yang digunakan untuk verifikasi.
    """
    return "T3rr4S1m_2oz4"

def _compute_hash(data_part: str) -> str:
    """
    Internal verification hasher.
    """
    salt = _get_salt()
    first = hashlib.sha256(f"{data_part}{salt}".encode()).hexdigest()
    return hashlib.sha256(first.encode()).hexdigest()[:6].upper()

def unpack_license_data(data_part: str) -> dict:
    """
    Membaca Metadata (ID, Nama, Email) dari string Base32.
    Digunakan oleh UI untuk menampilkan info lisensi.
    """
    try:
        missing_padding = len(data_part) % 8
        if missing_padding:
            data_part += '=' * (8 - missing_padding)
        raw = base64.b32decode(data_part.encode('utf-8'))
        parts = raw.decode('utf-8').split('|')
        if len(parts) == 3:
            return {"id": parts[0], "name": parts[1], "email": parts[2]}
    except:
        pass
    return None

def verify_serial(serial: str) -> bool:
    """
    HANYA MELAKUKAN VERIFIKASI.
    Memastikan signature cocok dengan data yang ada di serial.
    """
    if not (serial and serial.startswith("TS-")):
        return False
    parts = serial.split("-")
    if len(parts) != 3:
        return False
    
    # TS - [DATA] - [SIG]
    _, data_part, signature = parts
    return _compute_hash(data_part) == signature
