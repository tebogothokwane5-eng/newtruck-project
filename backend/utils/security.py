import bcrypt

def hash_password(password: str) -> str:
    pwd_bytes = str(password).strip().encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")