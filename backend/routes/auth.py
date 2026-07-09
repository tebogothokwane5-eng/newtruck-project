# backend/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
import os
import time
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import timedelta

import bcrypt
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

from backend.database import get_db
from backend.models.user import User
from backend.schemas import UserLogin
from backend.utils.email import send_email
from backend.utils.security import hash_password
from backend.utils.storage import upload_file
from backend.auth_utils import (
    SECRET_KEY,
    ALGORITHM,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# ✅ SINGLE router (DO NOT redefine later)
router = APIRouter(prefix="/auth", tags=["Authentication"])

UPLOAD_DOC_DIR = "uploads/documents"
os.makedirs(UPLOAD_DOC_DIR, exist_ok=True)

# -------------------------
# AUTH CONFIG
# -------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/")


# -------------------------
# PASSWORD VERIFY
# -------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = str(plain_password).strip().encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


@router.post("/register/", status_code=201)
def register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    phone_no: str = Form(...),
    id_no: str = Form(...),
    role: str = Form(...),
    document: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # 🔍 VALIDATIONS
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already taken")

        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        if db.query(User).filter(User.phone_no == phone_no).first():
            raise HTTPException(status_code=400, detail="Phone number already in use")

        if db.query(User).filter(User.id_no == id_no).first():
            raise HTTPException(status_code=400, detail="ID Number already registered")

        # 📄 UPLOAD FILE TO R2
        filename = f"{int(time.time())}_{document.filename.replace(' ', '_')}"
        document_url = upload_file(document.file, f"documents/{filename}", document.content_type)

        # 🧱 CREATE USER
        new_user = User(
            username=username,
            password=hash_password(password),
            email=email,
            phone_no=phone_no,
            id_no=id_no,
            role=role,
            document=document_url
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 📧 EMAIL (safe fail)
        try:
            send_email(
                to_email=new_user.email,
                subject="Welcome to Trucking Trust",
                body=f"Hi {new_user.username},\n\nYour registration was successful!"
            )
        except Exception as e:
            print("EMAIL ERROR:", e)

        return {
            "message": "Registered successfully",
            "id": new_user.id
        }

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database constraint error")

    except Exception as e:
        db.rollback()
        import traceback
        print("REGISTER ERROR TRACEBACK:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

        raise HTTPException(status_code=400, detail="Database constraint error")

    except Exception as e:
        db.rollback()
        import traceback
        print("REGISTER ERROR TRACEBACK:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


# -------------------------
# LOGIN
# -------------------------
@router.post("/login/")
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == data.username).first()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(data.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "id": user.id,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role)
        }

    except HTTPException:
        raise

    except Exception as e:
        print("LOGIN ERROR:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# -------------------------
# CURRENT USER
# -------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        print("🔐 RAW TOKEN:", token)

        # ✅ safety cleanup
        token = token.strip()

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("🔐 JWT PAYLOAD:", payload)

        username: str = payload.get("sub")

        if not username:
            print("❌ Missing 'sub' in token")
            raise credentials_exception

    except JWTError as e:
        print("❌ JWT ERROR:", str(e))
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()

    if not user:
        print("❌ USER NOT FOUND:", username)
        raise credentials_exception

    return user