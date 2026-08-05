# backend/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
import os
import re
import time
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import timedelta, datetime, timezone
import secrets

import bcrypt
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

from backend.database import get_db
from backend.models.user import User
from backend.schemas import UserLogin, BankDetailsUpdate, PaypalEmailUpdate, ForgotPasswordRequest, ResetPasswordRequest
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

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

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
        email = email.strip().lower()

        if not EMAIL_REGEX.match(email):
            raise HTTPException(status_code=400, detail="Please enter a valid email address")

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
                subject="Application received - under verification",
                body=f"Hi {new_user.username},\n\nThank you for registering with Truckify. Your account and documents are currently under verification. You will receive another email once your account has been reviewed.\n\nRegards,\nTruckify Team"
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

        role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
        if role_value != "admin" and not user.is_active:
            raise HTTPException(status_code=403, detail="Account pending approval")

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
# FORGOT PASSWORD (request reset code)
# -------------------------
@router.post("/forgot-password/")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    normalized_email = data.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    generic_response = {
        "message": "If that email is registered, a reset code has been sent."
    }

    if not user:
        return generic_response

    code = f"{secrets.randbelow(1000000):06d}"
    user.reset_token = code
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=15)

    db.commit()

    try:
        send_email(
            to_email=user.email,
            subject="Your Truckify password reset code",
            body=(
                f"Hi {user.username},\n\n"
                f"Your password reset code is: {code}\n\n"
                f"This code expires in 15 minutes. If you didn't request this, "
                f"you can safely ignore this email.\n\n"
                f"Regards,\nTruckify Team"
            )
        )
    except Exception as e:
        print("RESET EMAIL ERROR:", e)

    return generic_response


# -------------------------
# RESET PASSWORD (verify code + set new password)
# -------------------------
@router.post("/reset-password/")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    normalized_email = data.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not user.reset_token or not user.reset_token_expiry:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    if user.reset_token != data.code:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    expiry = user.reset_token_expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expiry:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user.password = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expiry = None

    db.commit()

    return {"message": "Password has been reset successfully"}


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

# -------------------------
# BANK DETAILS
# -------------------------
@router.put("/bank-details")
def update_bank_details(
    data: BankDetailsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.bank_code = data.bank_code
    current_user.bank_account_number = data.bank_account_number
    current_user.bank_account_name = data.bank_account_name

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Bank details updated successfully",
        "bank_code": current_user.bank_code,
        "bank_account_number": current_user.bank_account_number,
        "bank_account_name": current_user.bank_account_name
    }


# -------------------------
# CONTRACTOR PAYSTACK SUBACCOUNT SETUP
# -------------------------
@router.post("/setup-subaccount")
def setup_subaccount(
    data: BankDetailsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from backend.payments_service import create_paystack_subaccount

    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_value != "main_contractor":
        raise HTTPException(status_code=403, detail="Only contractors can set up a payout subaccount")

    result = create_paystack_subaccount(
        business_name=data.bank_account_name,
        bank_code=data.bank_code,
        account_number=data.bank_account_number,
        percentage_charge=0
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("message"))

    current_user.bank_code = data.bank_code
    current_user.bank_account_number = data.bank_account_number
    current_user.bank_account_name = data.bank_account_name
    current_user.paystack_subaccount_code = result["data"]["subaccount_code"]

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Subaccount created successfully",
        "subaccount_code": current_user.paystack_subaccount_code
    }


# -------------------------
# CONTRACTOR PAYPAL EMAIL SETUP
# -------------------------
@router.post("/setup-paypal-payee")
def setup_paypal_payee(
    data: PaypalEmailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_value != "main_contractor":
        raise HTTPException(status_code=403, detail="Only contractors can set up PayPal payout email")

    current_user.paypal_email = data.paypal_email
    db.commit()
    db.refresh(current_user)

    return {
        "message": "PayPal payout email set successfully",
        "paypal_email": current_user.paypal_email
    }
