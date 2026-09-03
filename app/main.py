from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivymd.toast import toast
from kivy.properties import ObjectProperty
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from plyer import filechooser
from kivymd.uix.card import MDCard
from kivymd.uix.fitimage import FitImage

import webbrowser
from app.utils.network import NetworkClient
import requests
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import TwoLineListItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.label import MDLabel
from kivy.clock import Clock
import random
from kivymd.uix.list import (
    MDList,
    TwoLineListItem,
    OneLineListItem,
    TwoLineAvatarIconListItem,
    IconRightWidget
)
from kivy.uix.scrollview import ScrollView

import os
from kivy.storage.jsonstore import JsonStore

# Initialize permanent storage for tokens
from kivy.utils import platform
if platform == "android":
    from android.storage import app_storage_path
    _store_path = os.path.join(app_storage_path(), 'user_session.json')
else:
    _store_path = 'user_session.json'
store = JsonStore(_store_path)


def pick_document(callback):
    """
    Cross-platform document picker.
    On Android, resolves content:// URIs to a real local file by reading
    bytes via ContentResolver, since plyer's legacy _data-column lookup
    fails on modern Android (Scoped Storage). Calls callback(path_or_none).
    """
    if platform != "android":
        filechooser.open_file(on_selection=lambda sel: callback(sel[0] if sel else None))
        return

    import random
    import os
    from jnius import autoclass
    from android import activity, mActivity
    from android.storage import app_storage_path

    Intent = autoclass("android.content.Intent")
    Activity = autoclass("android.app.Activity")

    request_code = random.randint(100000, 999999)

    def on_result(request_code_recv, result_code, data):
        if request_code_recv != request_code:
            return
        activity.unbind(on_activity_result=on_result)
        if result_code != Activity.RESULT_OK or data is None:
            callback(None)
            return
        uri = data.getData()
        if uri is None:
            callback(None)
            return
        try:
            resolver = mActivity.getContentResolver()

            filename = f"upload_{random.randint(10000, 99999)}"
            try:
                cursor = resolver.query(uri, None, None, None, None)
                if cursor and cursor.moveToFirst():
                    name_idx = cursor.getColumnIndex("_display_name")
                    if name_idx != -1:
                        filename = cursor.getString(name_idx)
                if cursor:
                    cursor.close()
            except Exception:
                pass

            dest_dir = os.path.join(app_storage_path(), "uploads_cache")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)

            input_stream = resolver.openInputStream(uri)
            JavaByteArray = autoclass("[B")
            buf = JavaByteArray(4096)
            with open(dest_path, "wb") as out_f:
                while True:
                    n = input_stream.read(buf)
                    if n == -1:
                        break
                    out_f.write(bytes(buf[:n]))
            input_stream.close()

            callback(dest_path)
        except Exception as e:
            print("FILE RESOLVE ERROR:", e)
            callback(None)

    activity.bind(on_activity_result=on_result)

    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("*/*")
    mActivity.startActivityForResult(intent, request_code)



def get_token():
    if store.exists("auth"):
        return store.get("auth").get("token")
    return None

API_URL = "https://newtruck-project.onrender.com"



KV = """

ScreenManager:
    SplashScreen:
        name: "splash"
    LoginScreen:
        name: "login"
    RegisterScreen:
        name: "register"
    ForgotPasswordScreen:
        name: "forgot_password"
    ResetPasswordScreen:
        name: "reset_password"
    ContractorHome:
        name: "contractor_home"
    TruckOwnerHome:
        name: "truck_owner"
    JobApplicationsScreen:
        name: "job_applications"
    UploadSlipFeedbackScreen:
        name: "upload_slip"

    


# ---------------- SPLASH ----------------
<SplashScreen>:
    MDFloatLayout:

        MDLabel:
            text: "TRUCKIFY"
            halign: "center"
            font_style: "H4"
            pos_hint: {"center_y": .65}

        MDSpinner:
            size_hint: None, None
            size: "46dp", "46dp"
            pos_hint: {"center_x": .5, "center_y": .45}
            active: True


# ---------------- LOGIN ----------------
<LoginScreen>:
    ScrollView:

        MDBoxLayout:
            orientation: "vertical"
            spacing: "20dp"
            padding: "30dp"
            size_hint_y: None
            height: self.minimum_height

            Widget:
                size_hint_y: None
                height: "80dp"

            MDCard:
                orientation: "vertical"
                padding: "25dp"
                spacing: "20dp"
                size_hint_y: None
                height: self.minimum_height
                radius: [20]

                MDLabel:
                    text: "Welcome Back"
                    halign: "center"
                    font_style: "H5"

                MDTextField:
                    id: username
                    hint_text: "Username"
                    icon_right: "account"

                MDTextField:
                    id: password
                    hint_text: "Password"
                    password: True
                    icon_right: "lock"

                MDRaisedButton:
                    text: "LOGIN"
                    pos_hint: {"center_x": .5}
                    on_release: root.login()

                MDTextButton:
                    text: "Create account"
                    pos_hint: {"center_x": .5}
                    on_release: app.root.current = "register"
                MDTextButton:
                    text: "Forgot Password?"
                    pos_hint: {"center_x": .5}
                    on_release: app.root.current = "forgot_password"


# ---------------- FORGOT PASSWORD ----------------
<ForgotPasswordScreen>:
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Forgot Password"
            left_action_items: [["arrow-left", lambda x: app.root.__setattr__("current", "login")]]
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                spacing: "20dp"
                padding: "30dp"
                size_hint_y: None
                height: self.minimum_height
                MDCard:
                    orientation: "vertical"
                    padding: "25dp"
                    spacing: "20dp"
                    size_hint_y: None
                    height: self.minimum_height
                    radius: [20]
                    MDLabel:
                        text: "Enter your account email. We'll send you a 6-digit reset code."
                        halign: "center"
                    MDTextField:
                        id: email
                        hint_text: "Email"
                        icon_right: "email"
                    MDRaisedButton:
                        text: "SEND CODE"
                        pos_hint: {"center_x": .5}
                        on_release: root.send_code()

# ---------------- RESET PASSWORD ----------------
<ResetPasswordScreen>:
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Reset Password"
            left_action_items: [["arrow-left", lambda x: app.root.__setattr__("current", "login")]]
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                spacing: "20dp"
                padding: "30dp"
                size_hint_y: None
                height: self.minimum_height
                MDCard:
                    orientation: "vertical"
                    padding: "25dp"
                    spacing: "20dp"
                    size_hint_y: None
                    height: self.minimum_height
                    radius: [20]
                    MDLabel:
                        text: "Enter the code we emailed you and your new password."
                        halign: "center"
                    MDTextField:
                        id: code
                        hint_text: "6-digit code"
                        icon_right: "numeric"
                    MDTextField:
                        id: new_password
                        hint_text: "New password"
                        password: True
                        icon_right: "lock"
                    MDTextField:
                        id: confirm_password
                        hint_text: "Confirm new password"
                        password: True
                        icon_right: "lock-check"
                    MDRaisedButton:
                        text: "RESET PASSWORD"
                        pos_hint: {"center_x": .5}
                        on_release: root.reset_password()

# ---------------- REGISTER ----------------
<RegisterScreen>:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Create Account"
            left_action_items: [["arrow-left", lambda x: app.root.__setattr__("current", "login")]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: "20dp"
                spacing: "15dp"
                size_hint_y: None
                height: self.minimum_height

                MDTextField:
                    id: reg_username
                    hint_text: "Username"
                    required: True

                MDTextField:
                    id: reg_email
                    hint_text: "Email"
                    required: True

                MDTextField:
                    id: reg_phone
                    hint_text: "Phone Number"

                MDTextField:
                    id: reg_id_no
                    hint_text: "ID Number"

                MDTextField:
                    id: reg_password
                    hint_text: "Password"
                    password: True
                    required: True

                MDDropDownItem:
                    id: reg_role
                    text: "Select Role"
                    pos_hint: {"center_x": .5}
                    on_release: root.open_role_menu()

                MDRaisedButton:
                    text: "UPLOAD DOCUMENT"
                    pos_hint: {"center_x": .5}
                    on_release: root.open_file_chooser()

                MDLabel:
                    id: doc_label
                    text: "No document selected"
                    halign: "center"

                MDRaisedButton:
                    text: "REGISTER"
                    pos_hint: {"center_x": .5}
                    on_release: root.register()


<ContractorHome>:
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0.08, 0.08, 0.08, 1

        # ---------------- TOP BAR ----------------
        MDTopAppBar:
            title: "Contractor Dashboard"
            elevation: 4
            md_bg_color: 0.1, 0.1, 0.1, 1
            right_action_items: [["logout", lambda x: app.logout()]]

        # ---------------- SCROLLABLE CONTENT ----------------
        ScrollView:
            do_scroll_x: False

            MDBoxLayout:
                orientation: "vertical"
                padding: "12dp"
                spacing: "12dp"
                size_hint_y: None
                height: self.minimum_height

                # ================= PAYMENTS PANEL =================
                MDCard:
                    size_hint_y: None
                    height: "80dp"
                    padding: "12dp"
                    radius: [12]
                    md_bg_color: 0.12, 0.12, 0.12, 1

                    MDBoxLayout:
                        orientation: "horizontal"
                        spacing: "12dp"

                        MDBoxLayout:
                            orientation: "vertical"

                            MDLabel:
                                text: "Payments"
                                theme_text_color: "Custom"
                                text_color: 1, 1, 1, 1
                                font_style: "H6"
                                size_hint_y: None
                                height: self.texture_size[1]

                            MDLabel:
                                text: "Tap to pay a completed job"
                                theme_text_color: "Custom"
                                text_color: 0.7, 0.7, 0.7, 1
                                font_size: "12sp"
                                size_hint_y: None
                                height: self.texture_size[1]

                        MDIconButton:
                            icon: "bank"
                            theme_icon_color: "Custom"
                            icon_color: 0.2, 0.6, 1, 1
                            pos_hint: {"center_y": 0.5}
                            on_release: root.open_payments_menu()

                # ================= JOBS HEADER =================
                MDLabel:
                    text: "Your Jobs"
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 1
                    font_style: "H6"
                    size_hint_y: None
                    height: self.texture_size[1]

                # ✅ FIX: Wrap list inside container
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height

                    MDList:
                        id: jobs_list
                        size_hint_y: None
                        height: self.minimum_height

                # ✅ Better spacer for phones
                Widget:
                    size_hint_y: None
                    height: "100dp"

        # ---------------- BOTTOM ACTION BAR ----------------
   
        MDBoxLayout:
            size_hint_y: None
            height: "70dp"
            padding: "10dp"
            spacing: "10dp"
            md_bg_color: 0.12, 0.12, 0.12, 1

            Widget:  # 🔥 left spacer

            MDIconButton:
                icon: "briefcase-plus"
                theme_icon_color: "Custom"
                icon_color: 0.2, 0.6, 1, 1
                user_font_size: "28sp"
                on_release: root.post_job()

            Widget:

            MDIconButton:
                icon: "refresh"
                theme_icon_color: "Custom"
                icon_color: 0.2, 0.7, 0.4, 1
                user_font_size: "28sp"
                on_release: root.load_jobs()

            Widget:

            MDIconButton:
                icon: "account-search"
                theme_icon_color: "Custom"
                icon_color: 0.8, 0.4, 0.2, 1
                user_font_size: "28sp"
                on_release: root.load_applicants()

            Widget:  # 🔥 right spacer


# ---------------- TRUCK OWNER ----------------
<TruckOwnerHome>:
    MDBoxLayout:
        orientation: "vertical"

        # ---------------- TOP BAR ----------------
        MDTopAppBar:
            title: "Truck Owner"
            left_action_items: [["refresh", lambda x: root.load_jobs()]]
            right_action_items: [["bank", lambda x: root.open_bank_details()]]

        # ---------------- MAIN SCROLL AREA ----------------
        ScrollView:
            do_scroll_x: False
            do_scroll_y: True

            MDBoxLayout:
                orientation: "vertical"
                spacing: "15dp"
                padding: "15dp"
                size_hint_y: None
                height: self.minimum_height

                # ---------------- JOBS ----------------
                MDLabel:
                    text: "Available Jobs"
                    bold: True
                    size_hint_y: None
                    height: "30dp"

                MDList:
                    id: jobs_list
                    size_hint_y: None
                    height: self.minimum_height



# ---------------- APPLICATIONS ----------------
<JobApplicationsScreen>:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Applications"

        ScrollView:
            MDList:
                id: apps_list


# ---------------- UPLOAD ----------------
<UploadSlipFeedbackScreen>:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Upload Feedback"
            left_action_items: [["arrow-left", lambda x: app.root.__setattr__("current", "truck_owner")]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                spacing: "20dp"
                padding: "20dp"
                size_hint_y: None
                height: self.minimum_height

                MDRaisedButton:
                    text: "Choose File"
                    on_release: root.select_file()

                MDRaisedButton:
                    text: "Submit"
                    on_release: root.submit_feedback()

# ---------------- POST JOB ----------------
"""
from kivy.utils import platform

if platform == "android":
    from android.permissions import request_permissions, Permission

# ------------------ LOGIC ------------------
class SplashScreen(MDScreen):
    def on_enter(self, *args):
        Clock.schedule_once(self.switch_to_main, 5)

    def switch_to_main(self, dt):
        self.manager.current = 'login'

from requests.exceptions import RequestException
from kivy.storage.jsonstore import JsonStore
from kivymd.app import MDApp

# Initialize storage (this creates a file on the phone)

from functools import partial
from kivy.clock import Clock
import requests

class LoginScreen(MDScreen):

    def login(self):
        username = self.ids.username.text.strip()
        password = self.ids.password.text.strip()

        if not username or not password:
            toast("Fill all fields")
            return

        self._do_login(username, password)

    def _do_login(self, username, password):
        try:
            res = requests.post(
                f"{API_URL}/auth/login/",
                json={"username": username, "password": password},
                #timeout=10
            )

            print("LOGIN:", res.text)

            if res.status_code != 200:
                toast("Invalid credentials")
                return

            data = res.json()

            token = data.get("access_token")
            user_id = data.get("id")
            role = data.get("role")

            app = MDApp.get_running_app()

            app.current_user = {
                "token": token,
                "id": user_id,
                "role": role
            }

            store.put("auth", token=token, id=user_id, role=role)

            toast("Login successful")

            self._go(role)

        except Exception as e:
            print("LOGIN ERROR:", e)
            toast("Server error")

    def _go(self, role):
        if not self.manager:
            return

        if role == "truck_owner":
            self.manager.current = "truck_owner"

        elif role == "main_contractor":
            self.manager.current = "contractor_home"

        else:
            self.manager.current = "login"




from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.toast import toast
from plyer import filechooser 
import requests


class ForgotPasswordScreen(MDScreen):
    def send_code(self):
        email = self.ids.email.text.strip()
        if not email:
            toast("Enter your email")
            return
        try:
            res = requests.post(
                f"{API_URL}/auth/forgot-password/",
                json={"email": email},
            )
            print("FORGOT PASSWORD:", res.text)
            if res.status_code != 200:
                toast("Something went wrong, try again")
                return
            toast("If that email is registered, a code was sent")
            reset_screen = self.manager.get_screen("reset_password")
            reset_screen.email = email
            self.manager.current = "reset_password"
        except Exception as e:
            print("FORGOT PASSWORD ERROR:", e)
            toast("Server error")


class ResetPasswordScreen(MDScreen):
    email = ""

    def reset_password(self):
        code = self.ids.code.text.strip()
        new_password = self.ids.new_password.text.strip()
        confirm_password = self.ids.confirm_password.text.strip()

        if not code or not new_password or not confirm_password:
            toast("Fill all fields")
            return

        if new_password != confirm_password:
            toast("Passwords do not match")
            return

        if not self.email:
            toast("Missing email - go back and try again")
            return

        try:
            res = requests.post(
                f"{API_URL}/auth/reset-password/",
                json={
                    "email": self.email,
                    "code": code,
                    "new_password": new_password,
                },
            )
            print("RESET PASSWORD:", res.text)
            if res.status_code != 200:
                data = res.json()
                toast(data.get("detail", "Invalid or expired code"))
                return
            toast("Password reset successfully - please log in")
            self.manager.current = "login"
        except Exception as e:
            print("RESET PASSWORD ERROR:", e)
            toast("Server error")


class RegisterScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.selected_role = None
        self.selected_file = None

    # ---------------- ROLE ----------------

    def open_role_menu(self):
        self.role_menu.open()

    def set_role(self, role_value):
        self.selected_role = role_value

        # display friendly text only
        self.ids.reg_role.text = role_value.replace("_", " ").title()

        if hasattr(self, "role_menu"):
            self.role_menu.dismiss()

    # ---------------- FILE PICKER ----------------

    def open_file_chooser(self):
        def select_file(path):
            if not path:
                toast("No file selected")
                return
            self.selected_file = path
            self.ids.doc_label.text = self.selected_file.split("/")[-1]
        pick_document(select_file)

    # ---------------- REGISTER ----------------

    def register(self):
        file_obj = None   # ✅ MOVE HERE (outside try)
        files = None      # optional but good

        try:
            username = self.ids.reg_username.text.strip()
            password = self.ids.reg_password.text.strip()
            phone = self.ids.reg_phone.text.strip()
            id_no = self.ids.reg_id_no.text.strip()
            email = self.ids.reg_email.text.strip()

            role = self.selected_role

            # validation
            if not all([username, password, phone, id_no, email, role]):
                toast("All fields are required!")
                return

            if len(phone) != 10 or not phone.isdigit():
                toast("Phone number must be exactly 10 digits")
                return

            if role not in ["main_contractor", "truck_owner"]:
                toast("Invalid role selected")
                return

            payload = {
                "username": username,
                "password": password[:72],
                "phone_no": phone,
                "id_no": id_no,
                "email": email,
                "role": role,
            }

            if self.selected_file:
                file_obj = open(self.selected_file, "rb")
                files = {
                    "document": (
                        self.selected_file.split("/")[-1],
                        file_obj
                    )
                }

            r = requests.post(
                f"{API_URL}/auth/register/",
                data=payload,
                files=files,
                timeout=10
            )

            if r.status_code in [200, 201]:
                toast("Registered successfully")
                self.manager.current = "login"
            else:
                try:
                    error_msg = r.json().get("detail", r.text)
                except:
                    error_msg = r.text

                toast(f"Error: {error_msg}")
                print("SERVER ERROR:", error_msg)

        except Exception as e:
            print("REGISTER ERROR:", e)
            toast("Connection failed")

        finally:
            if file_obj:
                file_obj.close()



    def on_kv_post(self, base_widget):
        self.role_menu = MDDropdownMenu(
            caller=self.ids.reg_role,
            items=[
                {
                "text": "Truck Owner",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="truck_owner": self.set_role(x),
                },
                {
                    "text": "Main Contractor",
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x="main_contractor": self.set_role(x),
                },
            ],
            width_mult=4,
        ) 

import requests
import smtplib
import os
import webbrowser
import time
import shutil

from email.mime.text import MIMEText
from kivy.properties import ObjectProperty
from kivy.uix.image import AsyncImage
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import (
    ThreeLineAvatarIconListItem,
    IconRightWidget,
    TwoLineAvatarIconListItem
)
from kivymd.toast import toast
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel




class ContractorHome(MDScreen):
    
    dialog = None
  

    def on_pre_enter(self, *args):
        Clock.schedule_once(lambda dt: self.load_jobs(), 0)
        # Periodic refresh for jobs
        self.job_refresh_event = Clock.schedule_interval(lambda dt: self.load_jobs(), 200)

    def on_leave(self, *args):
        if hasattr(self, "job_refresh_event"):
            self.job_refresh_event.cancel()


    # ---------------- JOB POST ----------------
    def post_job(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivy.uix.scrollview import ScrollView
        from kivymd.app import MDApp
        from kivymd.toast import toast

        app = MDApp.get_running_app()

        if not app.current_user:
            toast("User not logged in")
            return

        # ---------- INPUT STYLE ----------
        def styled_input(hint, is_int=False, multiline=False, height="56dp"):
            return MDTextField(
                hint_text=hint,
                mode="rectangle",
                multiline=multiline,
                size_hint_y=None,
                height=height,
                line_color_normal=(0.5, 0.5, 0.5, 1),
                line_color_focus=(0.2, 0.6, 1, 1),
                input_filter="int" if is_int else None
            )

        # ---------- CONTENT ----------
        content = MDBoxLayout(
            orientation="vertical",
            spacing="15dp",
            padding="10dp",
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter("height"))

        # ---------- INPUTS ----------
        title_input = styled_input("Job Title")

        desc_input = styled_input(
            "Description",
            multiline=True,
            height="120dp"   # 🔥 IMPORTANT: makes it visible & usable
        )

        limit_input = styled_input("Target Limit", is_int=True)

        content.add_widget(title_input)
        content.add_widget(desc_input)
        content.add_widget(limit_input)
 
        # ---------- SCROLL ----------
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)

        # ---------- FIX: WRAPPER CONTAINER ----------
        container = MDBoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height="320dp"   # 🔥 CRITICAL FIX (prevents invisible fields)
        )
        container.add_widget(scroll)

        # ---------- DIALOG ----------
        self.dialog = MDDialog(
            title="Post New Job",
            type="custom",
            content_cls=container,   # ✅ use container, NOT scroll directly
            size_hint=(0.9, None),
            height="450dp",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="POST",
                    on_release=lambda x: self.submit_job(
                        title_input.text,
                        desc_input.text,
                         limit_input.text
                    )
                ),
            ],
        )

        self.dialog.open()

    def submit_job(self, title, desc, limit):
        app = MDApp.get_running_app()

        title = title.strip()
        desc = desc.strip()
        limit = limit.strip()

        if not title or not limit:
            toast("Title and Target Limit are required!")
            return

        try:
            token = app.current_user["token"]

            payload = {
                "title": title,
                "description": desc,
                "contractor_id": int(app.current_user["id"]),
                "target_limit": int(limit),
            }

            headers = {"Authorization": f"Bearer {token}"}

            r = requests.post(
                f"{API_URL}/jobs/",
                json=payload,
                headers=headers
            )

            if r.status_code in [200, 201]:
                toast("Job posted successfully!")
                self.dialog.dismiss()
                self.load_jobs()
            else:
                print(r.text)
                toast(f"Error: {r.status_code}")

        except Exception as e:
            print("Post job error:", e)
            toast("Server error")

    # ---------------- PAYMENTS ----------------
    def _get_jobs_for_payment(self, on_result):
        """Fetch this contractor's jobs, then call on_result(list_of_jobs)."""
        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")

        if not token:
            toast("Please login again")
            return

        headers = {"Authorization": f"Bearer {token}"}

        def handle_response(response, error=None):
            def ui(dt):
                if error or response is None or response.status_code != 200:
                    toast("Could not load jobs")
                    return

                jobs = response.json()

                if not jobs:
                    toast("No jobs found")
                    return

                on_result(jobs)

            Clock.schedule_once(ui)

        NetworkClient.get(f"{API_URL}/jobs/", headers=headers, callback=handle_response)

    def _pick_job_dialog(self, jobs, on_pick):
        """Show a simple list dialog to pick a job, then call on_pick(job)."""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog

        layout = MDBoxLayout(orientation="vertical", spacing="10dp", size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        for job in jobs:
            btn = MDFlatButton(
                text=f"{job.get('title', 'Untitled')} (#{job.get('id')})",
                size_hint_y=None,
                height="40dp"
            )
            btn.bind(on_release=lambda x, j=job: (self.dialog.dismiss(), on_pick(j)))
            layout.add_widget(btn)

        self.dialog = MDDialog(
            title="Select a job",
            type="custom",
            content_cls=layout,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss())],
        )
        self.dialog.open()

    def _fetch_approved_applications(self, job_id, on_result):
        """Fetch approved applications for a job, then call on_result(list_of_applications)."""
        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")
        headers = {"Authorization": f"Bearer {token}"}

        def handle_response(response, error=None):
            def ui(dt):
                if error or response is None or response.status_code != 200:
                    toast("Could not load applications")
                    return

                applications = response.json()
                approved = [a for a in applications if str(a.get("status", "")).lower() == "approved"]

                if not approved:
                    toast("No approved truck owners for this job")
                    return

                on_result(approved)

            Clock.schedule_once(ui)

        NetworkClient.get(f"{API_URL}/jobs/{job_id}/applications", headers=headers, callback=handle_response)

    def _pick_application_dialog(self, applications, on_pick):
        """Show a list of approved truck owner applications with full details to pick from."""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.label import MDLabel
        from kivy.uix.scrollview import ScrollView

        scroll = ScrollView(size_hint=(1, None), height="350dp")

        layout = MDBoxLayout(orientation="vertical", spacing="12dp", padding="5dp", size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        for a in applications:
            row = MDBoxLayout(
                orientation="vertical",
                spacing="4dp",
                size_hint_y=None,
                padding="8dp"
            )
            row.bind(minimum_height=row.setter("height"))

            row.add_widget(MDLabel(
                text=a.get('truck_owner_username', 'Unknown'),
                bold=True,
                size_hint_y=None,
                height="24dp"
            ))
            row.add_widget(MDLabel(
                text=f"Order #: {a.get('order_number') or 'N/A'}",
                theme_text_color="Secondary",
                font_size="12sp",
                size_hint_y=None,
                height="20dp"
            ))
            row.add_widget(MDLabel(
                text=f"Location: {a.get('location') or 'N/A'}",
                theme_text_color="Secondary",
                font_size="12sp",
                size_hint_y=None,
                height="20dp"
            ))
            row.add_widget(MDLabel(
                text=f"Application #{a.get('application_id')}",
                theme_text_color="Secondary",
                font_size="11sp",
                size_hint_y=None,
                height="18dp"
            ))

            select_btn = MDRaisedButton(
                text="Select to Pay",
                md_bg_color=(0.2, 0.6, 1, 1),
                size_hint_x=1
            )
            select_btn.bind(on_release=lambda x, app=a: (self.dialog.dismiss(), on_pick(app)))
            row.add_widget(select_btn)

            layout.add_widget(row)

            divider = MDBoxLayout(size_hint_y=None, height="1dp", md_bg_color=(1, 1, 1, 0.1))
            layout.add_widget(divider)

        scroll.add_widget(layout)

        self.dialog = MDDialog(
            title="Select truck owner to pay",
            type="custom",
            content_cls=scroll,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss())],
        )
        self.dialog.open()


    def _initiate_payment(self, application, method):
        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"method": method}

        def handle_response(response, error=None):
            def ui(dt):
                if error or response is None:
                    toast("Network error")
                    return

                if response.status_code not in (200, 201):
                    print("PAYMENT ERROR:", response.text)
                    toast(f"Payment error: {response.status_code}")
                    return

                data = response.json()
                payment_url = data.get("payment_url")

                if payment_url:
                    webbrowser.open(payment_url)
                    toast("Opening payment page...")
                else:
                    toast("No payment URL returned")

            Clock.schedule_once(ui)

        toast(f"Starting {method} payment...")

        application_id = application.get("application_id")

        NetworkClient.post(
            f"{API_URL}/payments/initiate/application/{application_id}",
            json=payload,
            headers=headers,
            callback=handle_response
        )

    def open_payments_menu(self):
        from kivy.uix.modalview import ModalView
        from kivymd.uix.card import MDCard
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton
        from kivymd.uix.label import MDLabel

        modal = ModalView(
            size_hint=(0.9, None),
            background_color=(0, 0, 0, 0.6)
        )

        card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="18dp",
            radius=[16],
            md_bg_color=(0.14, 0.14, 0.14, 1),
            size_hint_y=None,
            adaptive_height=True
        )

        # ---------- TITLE ----------
        card.add_widget(MDLabel(
            text="Payments",
            font_style="H6",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            halign="center",
            adaptive_height=True
        ))

        # ---------- HELPER ----------
        def icon_item(icon, text, color, action):
            box = MDBoxLayout(
                orientation="vertical",
                size_hint_x=1
            )

            btn = MDIconButton(
                icon=icon,
                theme_icon_color="Custom",
                icon_color=color,
                user_font_size="26sp",
                pos_hint={"center_x": 0.5}
            )
            btn.bind(on_release=action)

            label = MDLabel(
                text=text,
                halign="center",
                font_size="11sp",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1)
            )

            box.add_widget(btn)
            box.add_widget(label)
            return box

         # ---------- HORIZONTAL ROW ----------
        row = MDBoxLayout(
            orientation="horizontal",
            spacing="12dp",
            size_hint_y=None,
            height="90dp"
        )

        row.add_widget(icon_item(
            "credit-card",
            "Paystack",
            (0.2, 0.6, 1, 1),
            lambda x: (modal.dismiss(), self.open_paystack())
        ))

        row.add_widget(icon_item(
            "alpha-p-circle",   # 🔥 FIX: visible PayPal icon
            "PayPal",
            (0.0, 0.6, 1, 1),   # 🔥 blue color (visible)
            lambda x: (modal.dismiss(), self.open_paypal())
        ))

        row.add_widget(icon_item(
            "refresh",
            "Status",
            (0.3, 0.8, 0.4, 1),
            lambda x: (modal.dismiss(), self.check_payment_status())
        ))

        row.add_widget(icon_item(
            "cog",
            "Setup",
            (0.7, 0.4, 1, 1),
            lambda x: (modal.dismiss(), self.open_setup_payout())
        ))

        # ADD ROW
        card.add_widget(row)

        # ---------- CLOSE BUTTON ----------
        close_row = MDBoxLayout(
            size_hint_y=None,
            height="60dp"
        )

        close_btn = MDIconButton(
            icon="close",
            theme_icon_color="Custom",
            icon_color=(0.7, 0.7, 0.7, 1),
            user_font_size="26sp",
            pos_hint={"center_x": 0.5}
        )
        close_btn.bind(on_release=lambda x: modal.dismiss())

        close_label = MDLabel(
            text="Close",
            halign="center",
            font_size="11sp",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1)
        )

        close_box = MDBoxLayout(orientation="vertical")
        close_box.add_widget(close_btn)
        close_box.add_widget(close_label)

        close_row.add_widget(close_box)

        card.add_widget(close_row)

        modal.add_widget(card)
        modal.open()



    def open_setup_payout(self):
        from kivy.uix.modalview import ModalView
        from kivymd.uix.card import MDCard
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDRaisedButton, MDFlatButton
        from kivymd.uix.label import MDLabel

        modal = ModalView(
            size_hint=(0.85, None),
            height="260dp",
            background_color=(0, 0, 0, 0.6)
        )

        card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="10dp",
            radius=[16],
            md_bg_color=(0.14, 0.14, 0.14, 1),
            size_hint=(1, 1)
        )

        card.add_widget(MDLabel(
            text="Setup Payout Details",
            font_style="H6",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            halign="center",
            size_hint_y=None,
            height="30dp"
        ))

        paystack_btn = MDRaisedButton(
            text="Paystack Bank Details",
            md_bg_color=(0.2, 0.6, 1, 1),
            size_hint_x=1
        )
        paystack_btn.bind(on_release=lambda x: (modal.dismiss(), self.open_paystack_setup_form()))

        paypal_btn = MDRaisedButton(
            text="PayPal Email",
            md_bg_color=(1, 0.6, 0.2, 1),
            size_hint_x=1
        )
        paypal_btn.bind(on_release=lambda x: (modal.dismiss(), self.open_paypal_setup_form()))

        close_btn = MDFlatButton(
            text="CLOSE",
            size_hint_x=1
        )
        close_btn.bind(on_release=lambda x: modal.dismiss())

        card.add_widget(paystack_btn)
        card.add_widget(paypal_btn)
        card.add_widget(close_btn)

        modal.add_widget(card)
        modal.open()

    def open_paystack_setup_form(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        from kivymd.uix.boxlayout import MDBoxLayout

        layout = MDBoxLayout(
            orientation="vertical",
            spacing="15dp",
            padding="10dp",
            size_hint_y=None
        )
        layout.bind(minimum_height=layout.setter("height"))

        bank_code_input = MDTextField(hint_text="Bank Code (e.g. 470010)")
        account_number_input = MDTextField(hint_text="Account Number")
        account_name_input = MDTextField(hint_text="Business/Account Name")

        layout.add_widget(bank_code_input)
        layout.add_widget(account_number_input)
        layout.add_widget(account_name_input)

        self.dialog = MDDialog(
            title="Paystack Bank Details",
            type="custom",
            content_cls=layout,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(
                    text="SAVE",
                    on_release=lambda x: self.submit_paystack_setup(
                        bank_code_input.text,
                        account_number_input.text,
                        account_name_input.text
                    )
                ),
            ],
        )
        self.dialog.open()

    def submit_paystack_setup(self, bank_code, account_number, account_name):
        from app.utils.network import NetworkClient

        bank_code = bank_code.strip()
        account_number = account_number.strip()
        account_name = account_name.strip()

        if not bank_code or not account_number or not account_name:
            toast("All fields are required")
            return

        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")

        if not token:
            toast("Please login again")
            return

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "bank_code": bank_code,
            "bank_account_number": account_number,
            "bank_account_name": account_name
        }

        NetworkClient.post(
            f"{API_URL}/auth/setup-subaccount",
            json=payload,
            headers=headers,
            callback=self.on_payout_setup_saved
        )

    def open_paypal_setup_form(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        from kivymd.uix.boxlayout import MDBoxLayout

        layout = MDBoxLayout(
            orientation="vertical",
            spacing="15dp",
            padding="10dp",
            size_hint_y=None
        )
        layout.bind(minimum_height=layout.setter("height"))

        email_input = MDTextField(hint_text="PayPal Email Address")
        layout.add_widget(email_input)

        self.dialog = MDDialog(
            title="PayPal Payout Email",
            type="custom",
            content_cls=layout,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(
                    text="SAVE",
                    on_release=lambda x: self.submit_paypal_setup(email_input.text)
                ),
            ],
        )
        self.dialog.open()

    def submit_paypal_setup(self, email):
        from app.utils.network import NetworkClient

        email = email.strip()

        if not email:
            toast("Email is required")
            return

        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")

        if not token:
            toast("Please login again")
            return

        headers = {"Authorization": f"Bearer {token}"}
        payload = {"paypal_email": email}

        NetworkClient.post(
            f"{API_URL}/auth/setup-paypal-payee",
            json=payload,
            headers=headers,
            callback=self.on_payout_setup_saved
        )

    def on_payout_setup_saved(self, response, error=None):
        def ui(dt):
            if error or response is None or response.status_code not in (200, 201):
                msg = response.text if response is not None else "Network error"
                toast(f"Failed to save: {msg}")
                return
            toast("Payout details saved successfully")
            if hasattr(self, "dialog") and self.dialog:
                self.dialog.dismiss()
        Clock.schedule_once(ui)

    def open_paystack(self):
        self._get_jobs_for_payment(
            lambda jobs: self._pick_job_dialog(jobs, lambda job: self._fetch_approved_applications(
                job["id"],
                lambda apps: self._pick_application_dialog(apps, lambda app: self._initiate_payment(app, "paystack"))
            ))
        )

    def open_paypal(self):
        self._get_jobs_for_payment(
            lambda jobs: self._pick_job_dialog(jobs, lambda job: self._fetch_approved_applications(
                job["id"],
                lambda apps: self._pick_application_dialog(apps, lambda app: self._initiate_payment(app, "paypal"))
            ))
        )

    def check_payment_status(self):
        toast("Payment status check coming soon")



    def load_jobs(self, *args):

        if self.ids and hasattr(self.ids, "jobs_list"):
            self.ids.jobs_list.clear_widgets()
           # clear UI immediately
        

        # get token safely
        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")

        if not token:
            toast("Please login again")
            self.manager.current = "login"
            return

        # headers
        headers = {
            "Authorization": f"Bearer {token}",
            "ngrok-skip-browser-warning": "true"
        }

        toast("Loading jobs...")

        # async request (NO blocking)
        

        NetworkClient.get(
            f"{API_URL}/jobs/",
            headers=headers,
            callback=self.on_jobs_loaded
        )

    

    def open_truck_pack(self, job, *args):
        applications = job.get("applications", [])
        packs = [a for a in applications if a.get("truck_pack_url")]

        if not packs:
            toast("No truck pack found")
            return

        if len(packs) == 1:
            self._open_pdf_url(packs[0]["truck_pack_url"])
            return

        self._pick_truck_pack_dialog(packs)

    def _open_pdf_url(self, pdf_url):
        # Fix backend bug
        pdf_url = pdf_url.replace(
            "uploads/truck_packs/uploads/truck_packs/",
            "uploads/truck_packs/"
        )
        # Make full URL
        if not pdf_url.startswith("http"):
            pdf_url = f"{API_URL}/{pdf_url.lstrip('/')}"
        print("Opening:", pdf_url)
        webbrowser.open(pdf_url)

    def _pick_truck_pack_dialog(self, packs):
        """Show a list of truck packs for this job; tap one to open it."""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog

        layout = MDBoxLayout(orientation="vertical", spacing="10dp", size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        for a in packs:
            label = f"Application #{a.get('application_id')}"
            location = a.get("location")
            if location:
                label += f" \u2014 {location}"

            btn = MDFlatButton(
                text=label,
                size_hint_y=None,
                height="40dp"
            )
            btn.bind(
                on_release=lambda x, url=a["truck_pack_url"]: (
                    self.dialog.dismiss(),
                    self._open_pdf_url(url)
                )
            )
            layout.add_widget(btn)

        self.dialog = MDDialog(
            title="Select a truck pack to view",
            type="custom",
            content_cls=layout,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss())],
        )
        self.dialog.open()

    def view_truck_pack_pdf(self, application_id):
        """Fetch truck pack PDF URL from backend and open in browser"""
        token = MDApp.get_running_app().current_user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        try:
            r = requests.get(f"{API_URL}/jobs/applications/{application_id}/truck-pack", headers=headers)
            if r.status_code == 200:
                pdf_url = r.json().get("truck_pack_url")
                if pdf_url:
                    import webbrowser
                    webbrowser.open(pdf_url)
                else:
                    toast("No truck pack found")
            else:
                toast(f"Error {r.status_code}: Could not load truck pack")
        except Exception as e:
            print("Truck pack error:", e)
            toast("Server error")

    # ---------------- MONITORING APPLICANTS ----------------
    def load_applicants(self):
        print("Loading applicants...")

        try:
            self.ids.jobs_list.clear_widgets()

            token = MDApp.get_running_app().current_user["token"]
            headers = {"Authorization": f"Bearer {token}"}

            r = requests.get(f"{API_URL}/jobs/monitoring", headers=headers, timeout=5)

            if r.status_code == 200:
                data = r.json()
                print("DATA:", data)

                for application in data:
                    app_id = application.get("application_id") or application.get("id")

                    item = TwoLineAvatarIconListItem(
                        text=f"Owner: {application.get('truck_owner','Unknown')}",
                        secondary_text=f"Job: {application.get('job_title','Untitled')}",
                    )

                    item.add_widget(
                        IconRightWidget(
                            icon="file-eye",
                            on_release=lambda x, a_id=app_id: self.show_slips_history(a_id)
                        )
                    )

                    self.ids.jobs_list.add_widget(item)

            else:
                print("Monitoring error:", r.text)

        except Exception as e:
            print("Applicants Error:", e)

    # ---------------- VIEW / APPROVE APPLICATIONS ----------------
    def view_applications_popup(self, job_id):
        """Fetch applications for a job and show them in a dialog with Approve buttons."""
        app = MDApp.get_running_app()
        token = app.current_user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        def handle_response(response, error=None):
            def update_ui(dt):
                if error or response is None or response.status_code != 200:
                    toast("Could not load applications")
                    return
                applications = response.json()
                self._show_applications_dialog(job_id, applications)
            Clock.schedule_once(update_ui)

        NetworkClient.get(f"{API_URL}/jobs/{job_id}/applications", headers=headers, callback=handle_response)

    def _show_applications_dialog(self, job_id, applications):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        from kivymd.uix.label import MDLabel

        layout = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, padding="10dp")
        layout.bind(minimum_height=layout.setter("height"))

        if not applications:
            layout.add_widget(MDLabel(text="No applications yet", size_hint_y=None, height="40dp"))
        else:
            for a in applications:
                row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="48dp", spacing="10dp")
                status = str(a.get("status", "")).lower()
                label_text = f"{a.get('truck_owner_username', 'Unknown')} \u2014 {status.upper()}"
                row.add_widget(MDLabel(text=label_text, size_hint_x=0.7))

                if status == "pending":
                    approve_btn = MDRaisedButton(text="APPROVE", size_hint_x=0.3)
                    approve_btn.bind(
                        on_release=lambda x, app_id=a.get("application_id"): self._approve_application(app_id, job_id)
                    )
                    row.add_widget(approve_btn)
                else:
                    row.add_widget(MDLabel(text="", size_hint_x=0.3))

                layout.add_widget(row)

        self.dialog = MDDialog(
            title="Applications",
            type="custom",
            content_cls=layout,
            buttons=[MDFlatButton(text="CLOSE", on_release=lambda x: self.dialog.dismiss())],
        )
        self.dialog.open()

    def _approve_application(self, application_id, job_id):
        app = MDApp.get_running_app()
        token = app.current_user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        try:
            r = requests.patch(
                f"{API_URL}/jobs/applications/{application_id}/approve",
                headers=headers
            )
            if r.status_code == 200:
                toast("Application approved")
                self.dialog.dismiss()
                self.view_applications_popup(job_id)
            else:
                toast(f"Error: {r.status_code}")
        except Exception as e:
            print("Approve error:", e)
            toast("Server error")

    # ---------------- ASSIGN ORDER ----------------
    def assign_order_popup(self, application_id):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.toast import toast

        # ----------------- LAYOUT -----------------
        content = MDBoxLayout(
            orientation="vertical",
            spacing="15dp",
            padding="20dp",
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter("height"))

        # ----------------- TITLE / HEADER -----------------
        content.add_widget(
           MDLabel(
               text="Enter order details below",
               halign="center",
               theme_text_color="Secondary",
               size_hint_y=None,
               height="20dp"
            )
        )

        # ----------------- ORDER INPUT -----------------
        order_input = MDTextField(
            hint_text="Order Number",
            helper_text="Required",
            helper_text_mode="on_focus",
            mode="rectangle",
            size_hint_y=None,
            height="50dp",
            icon_right="barcode"
        )
        content.add_widget(order_input)

        # ----------------- LOCATION INPUT -----------------
        location_input = MDTextField(
            hint_text="Delivery Location",
            helper_text="Required",
            helper_text_mode="on_focus",
            mode="rectangle",
            size_hint_y=None,
            height="50dp",
            icon_right="map-marker"
        )
        content.add_widget(location_input)

        # ----------------- VALIDATION -----------------
        def validate_and_send(x):
            order = order_input.text.strip()
            location = location_input.text.strip()

            if not order or not location:
                toast("Please fill in all fields")
                return

            self.send_order_details(application_id, order, location)
            self.dialog.dismiss()

       # ----------------- DIALOG -----------------
        self.dialog = MDDialog(
            title="Assign Order",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="ASSIGN",
                    on_release=validate_and_send
                ),
            ],
        )

        self.dialog.open()
    def send_order_details(self, application_id, order_number, location):
        self.dialog.dismiss()

        app = MDApp.get_running_app()
        token = app.current_user.get("token") if app.current_user else None

        print("CURRENT USER:", app.current_user)
        print("TOKEN:", token)

        if not token:
            toast("Session expired, please login again")
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "ngrok-skip-browser-warning": "true"
        }

        payload = {
            "order_number": order_number,
            "location": location
        }

        print("AUTH HEADER:", headers)
        print("PAYLOAD:", payload)

        try:
            r = requests.patch(
                f"{API_URL}/jobs/applications/{application_id}/assign-order",
                json=payload,
                headers=headers,
                timeout=8
            )

            print("RESPONSE:", r.status_code, r.text)

            if r.status_code == 200:
                toast("Order assigned successfully")
                self.load_jobs()
            else:
                toast("Failed to assign order")

        except Exception as e:
            print("Error assigning order:", e)
            toast("Server error")

    def view_job_popup(self, job, *args):
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.label import MDLabel
        from kivy.uix.boxlayout import BoxLayout
        import webbrowser

        if not isinstance(job, dict):
            return

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Job Info
        layout.add_widget(MDLabel(text=f"Title: {job.get('title', 'N/A')}", size_hint_y=None, height="30dp"))
        layout.add_widget(MDLabel(text=f"Description: {job.get('description', 'N/A')}", size_hint_y=None, height="60dp"))

        # PDF Logic
        pdf_url = job.get("latest_truck_pack_url") or job.get("truck_pack_url")

        if pdf_url:
               # 1. Clean up duplicate paths
            pdf_url = pdf_url.replace("uploads/truck_packs/uploads/truck_packs/", "uploads/truck_packs/")
            
             # 2. Ensure it's a full URL (Add your API base if it's a relative path)
            if not pdf_url.startswith("http"):
                 # Replace 'API_URL' with your actual base domain if needed
                base_domain = API_URL.split('/api')[0] # Strips the /api/v1 part
                pdf_url = f"{base_domain}/{pdf_url.lstrip('/')}"

            # 3. Create the button with a clean helper call
            pdf_btn = MDFlatButton(
                text="OPEN TRUCK PACK PDF",
                theme_text_color="Custom",
                    ext_color=(0, 0, 1, 1),
                )
                 # Pass pdf_url as a default argument to the lambda to "freeze" it
            pdf_btn.bind(on_release=lambda x, u=pdf_url: webbrowser.open(u))
            layout.add_widget(pdf_btn)
        else:
            layout.add_widget(MDLabel(text="No truck pack uploaded", size_hint_y=None, height="30dp"))

        if hasattr(self, "dialog") and self.dialog:
            self.dialog.dismiss()

        self.dialog = MDDialog(
            title="Job Details",
            type="custom",
            content_cls=layout,
            buttons=[MDFlatButton(text="CLOSE", on_release=lambda x: self.dialog.dismiss())],
        )
        self.dialog.open()

    def show_slips_history(self, application_id):
        print(f"📦 Fetching slips for application {application_id}")

        try:
            token = MDApp.get_running_app().current_user["token"]
            headers = {"Authorization": f"Bearer {token}"}

            r = requests.get(
                f"{API_URL}/jobs/applications/{application_id}/slips",
                headers=headers,
                timeout=5
            )

            if r.status_code != 200:
                print("SLIPS ERROR:", r.text)
                toast(f"Error {r.status_code}")
                return

            slips = r.json()

            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.scrollview import ScrollView
            from kivymd.uix.button import MDFlatButton
            from kivymd.uix.label import MDLabel

            # -------- SCROLLABLE CONTENT --------
            scroll = ScrollView(size_hint=(1, None), height="300dp")
            layout = BoxLayout(
                orientation="vertical",
                spacing=10,
                padding=10,
                size_hint_y=None
            )
            layout.bind(minimum_height=layout.setter("height"))

            if not slips:
               layout.add_widget(MDLabel(text="No slips uploaded"))
            else:
                for slip in slips:
                    file_url = slip.get("file_url")

                    btn = MDFlatButton(
                        text=f"View Slip {slip['id']}",
                        on_release=lambda x, url=file_url: webbrowser.open(url)
                    )
                    layout.add_widget(btn)

            scroll.add_widget(layout)

            # -------- DIALOG --------
            self.dialog = MDDialog(
                title="Delivery Slips",
                type="custom",
                content_cls=scroll,
                buttons=[
                    MDFlatButton(
                         text="CLOSE",
                        on_release=lambda x: self.dialog.dismiss()
                    )
                ]
            )

            self.dialog.open()

        except Exception as e:
            print("SLIPS EXCEPTION:", e)
            toast("Failed to load slips")

    from kivy.clock import Clock

    def on_jobs_loaded(self, response, error=None):
        def update_ui(dt):
            if error:
                print("Network error:", error)
                toast("Network error")
                return

            if response is None or response.status_code != 200:
                print("Bad response:", response)
                toast("Failed to load jobs")
                return

            try:
                self.ids.jobs_list.clear_widgets()
                jobs = response.json()

                for job in jobs:
                    self._add_contractor_job_card(job)

            except Exception as e:
                print("UI error:", e)
                toast("Error displaying jobs")

        Clock.schedule_once(update_ui)

    def _add_contractor_job_card(self, job):
        from kivymd.uix.card import MDCard
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton
        from kivymd.uix.label import MDLabel
        from kivy.uix.scrollview import ScrollView
        from functools import partial

        title = job.get("title", "Untitled")
        description = job.get("description", "") or "No description"
        status_val = str(job.get("status", "pending")).lower().strip()
        is_active = (status_val == "pending")
        applicants = int(job.get("applicant_count") or 0)
        limit = int(job.get("target_limit") or 0)
        display_status = "OPEN" if is_active else "CLOSED"
        status_color = (0.2, 0.85, 0.4, 1) if is_active else (0.9, 0.3, 0.3, 1)

        def wrap_label(label):
            label.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
            label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
            return label

        
        card = MDCard(
            orientation="vertical",
            padding="14dp",
            spacing="8dp",
            size_hint=(1, None),
            elevation=3,
            radius=[16],
            md_bg_color=(0.13, 0.13, 0.13, 1)
        )

        # Let the card grow vertically with its content
        card.bind(minimum_height=card.setter("height"))

        # =========================================================
        # TITLE
        # =========================================================
        title_label = wrap_label(MDLabel(
            text=title,
            font_style="H6",
            bold=True,
            size_hint=(1, None),
        ))
        card.add_widget(title_label)

         # =========================================================
        # STATUS + APPLICANTS
        # =========================================================
        status_row = MDBoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height="28dp",
            spacing="8dp"
        )

        status_chip = MDLabel(
            text=display_status,
            size_hint=(None, None),
            size=("85dp", "24dp"),
            halign="left",
            valign="middle",
            theme_text_color="Custom",
            text_color=status_color,
            font_size="12sp",
            bold=True,
        )

        applicants_label = MDLabel(
            text=f"{applicants}/{limit} Applicants",
            theme_text_color="Secondary",
            font_size="12sp",
            size_hint=(1, None),
            height="24dp",
            halign="right",
            valign="middle"
        )

        status_row.add_widget(status_chip)
        status_row.add_widget(applicants_label)

        card.add_widget(status_row)

        # =========================================================
        # DIVIDER
        # =========================================================
        card.add_widget(MDBoxLayout(
            size_hint=(1, None),
            height="1dp",
            md_bg_color=(1, 1, 1, 0.08)
        ))

        # =========================================================
        # DESCRIPTION
        # =========================================================
        desc_label = wrap_label(MDLabel(
             text=description,
            theme_text_color="Secondary",
            size_hint=(1, None),
        ))

        card.add_widget(desc_label)

        # =========================================================
        # ACTION ICONS - HORIZONTAL SCROLL
        # =========================================================
        action_scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint=(1, None),
            height="58dp",
            bar_width="0dp",
            scroll_type=["content"]
        )

        action_row = MDBoxLayout(
            orientation="horizontal",
            spacing="18dp",
            padding=("4dp", "4dp"),
            size_hint=(None, None),
            height="50dp"
        )

        action_row.bind(minimum_width=action_row.setter("width"))

        # ---- STATUS ----
        status_btn = MDIconButton(
            icon="lock-open-outline" if is_active else "lock",
            theme_icon_color="Custom",
            icon_color=status_color,
            size_hint=(None, None),
            size=("48dp", "48dp")
        )

        status_btn.bind(
            on_release=lambda inst, j=job, s=status_val:
            self.toggle_job(j, s)
        )

        action_row.add_widget(status_btn)

        # ---- ASSIGN ORDER ----
        applications = job.get("applications", [])

        if applications:
            app_id = applications[0].get("application_id")

            assign_icon = MDIconButton(
                icon="map-marker-plus",
                theme_icon_color="Custom",
                icon_color=(0.3, 0.7, 1, 1),
                size_hint=(None, None),
                size=("48dp", "48dp")
            )

            assign_icon.bind(
                on_release=lambda inst, app_id=app_id:
                self.assign_order_popup(app_id)
            )

            action_row.add_widget(assign_icon)
        # ---- VIEW APPLICATIONS ----
        view_apps_icon = MDIconButton(
            icon="account-multiple-outline",
            theme_icon_color="Custom",
            icon_color=(1, 0.7, 0.2, 1),
            size_hint=(None, None),
            size=("48dp", "48dp")
        )
        view_apps_icon.bind(
            on_release=lambda inst, jid=job.get("id"):
            self.view_applications_popup(jid)
        )
        action_row.add_widget(view_apps_icon)

        action_scroll.add_widget(action_row)
        card.add_widget(action_scroll)

        # =========================================================
        # SOCIAL ACTIONS - HORIZONTAL SCROLL
        # =========================================================
        social_scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint=(1, None),
            height="52dp",
            bar_width="0dp",
            scroll_type=["content"]
        )

        social_row = MDBoxLayout(
            orientation="horizontal",
            spacing="6dp",
            padding=("4dp", "2dp"),
            size_hint=(None, None),
            height="48dp"
        )

        social_row.bind(minimum_width=social_row.setter("width"))

        # ---------------------------------------------------------
        # LIKE
        # ---------------------------------------------------------
        like_icon = MDIconButton(
            icon="thumb-up-outline",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 0.7),
            size_hint=(None, None),
            size=("44dp", "44dp")
        )

        like_count_label = MDLabel(
            text="0",
            theme_text_color="Secondary",
            size_hint=(None, None),
            size=("35dp", "44dp"),
            halign="left",
            valign="middle"
        )
 
        # ---------------------------------------------------------
        # COMMENTS
        # ---------------------------------------------------------
        comment_icon = MDIconButton(
            icon="comment-outline",
            theme_icon_color="Custom",
            icon_color=(1, 1, 1, 0.7),
            size_hint=(None, None),
            size=("44dp", "44dp")
        )

        comment_count_label = MDLabel(
            text="0",
            theme_text_color="Secondary",
            size_hint=(None, None),
            size=("35dp", "44dp"),
            halign="left",
            valign="middle"
        )

        job_id_for_social = job.get("id")

        # ---------------------------------------------------------
        # LIKE ACTION
        # ---------------------------------------------------------
        like_icon.bind(
            on_release=lambda inst,
            jid=job_id_for_social,
            lbl=like_count_label,
            icon=like_icon:
            self.toggle_like(jid, icon, lbl)
        )

        # ---------------------------------------------------------
        # COMMENT ACTION
        # ---------------------------------------------------------
        comment_icon.bind(
            on_release=lambda inst,
            jid=job_id_for_social,
            t=title:
            self.open_comments(jid, t)
        )

        social_row.add_widget(like_icon)
        social_row.add_widget(like_count_label)
        social_row.add_widget(comment_icon)
        social_row.add_widget(comment_count_label)

        social_scroll.add_widget(social_row)
        card.add_widget(social_scroll)

        # =========================================================
        # LOAD SOCIAL DATA
        # =========================================================
        self._fetch_job_social(
            job_id_for_social,
            like_icon,
            like_count_label,
            comment_count_label
        )

        # =========================================================
        # CARD TOUCH
        # =========================================================
        card.bind(
            on_release=partial(
                self._contractor_card_touch,
                job
            )
        )

        self.ids.jobs_list.add_widget(card)



    def _contractor_card_touch(self, job, *args):
        self.open_truck_pack(job)

    def _get_auth_headers(self):
        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _fetch_job_social(self, job_id, like_icon, like_count_label, comment_count_label):
        try:
            r = requests.get(f"{API_URL}/jobs/{job_id}/likes", headers=self._get_auth_headers())
            if r.status_code == 200:
                data = r.json()
                like_count_label.text = str(data.get("like_count", 0))
                liked = data.get("liked_by_me", False)
                like_icon.icon = "thumb-up" if liked else "thumb-up-outline"
                like_icon.icon_color = (0.2, 0.6, 1, 1) if liked else (1, 1, 1, 0.7)
        except Exception as e:
            print("LIKE FETCH ERROR:", e)
        try:
            r = requests.get(f"{API_URL}/jobs/{job_id}/comments", headers=self._get_auth_headers())
            if r.status_code == 200:
                comment_count_label.text = str(len(r.json()))
        except Exception as e:
            print("COMMENT FETCH ERROR:", e)

    def toggle_like(self, job_id, like_icon, like_count_label):
        try:
            r = requests.post(f"{API_URL}/jobs/{job_id}/likes/toggle", headers=self._get_auth_headers())
            if r.status_code == 200:
                data = r.json()
                like_count_label.text = str(data.get("like_count", 0))
                liked = data.get("liked_by_me", False)
                like_icon.icon = "thumb-up" if liked else "thumb-up-outline"
                like_icon.icon_color = (0.2, 0.6, 1, 1) if liked else (1, 1, 1, 0.7)
            else:
                toast("Failed to update like")
        except Exception as e:
            print("LIKE TOGGLE ERROR:", e)
            toast("Server error")


    def open_comments(self, job_id, job_title):
        try:
            r = requests.get(
                f"{API_URL}/jobs/{job_id}/comments",
                headers=self._get_auth_headers()
            )

            comments = r.json() if r.status_code == 200 else []

        except Exception as e:
            print("COMMENTS LOAD ERROR:", e)
            comments = []
            toast("Could not load comments")

        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.label import MDLabel
        from kivymd.uix.textfield import MDTextField
        from kivy.uix.scrollview import ScrollView

       # =========================================================
        # COMMENT LIST
        # =========================================================
        list_layout = MDBoxLayout(
            orientation="vertical",
            spacing="10dp",
            padding=("5dp", "5dp"),
            size_hint_y=None
        )

        list_layout.bind(
            minimum_height=list_layout.setter("height")
        )

        # =========================================================
        # NO COMMENTS
        # =========================================================
        if not comments:

            empty_label = MDLabel(
                text="No comments yet - be the first!",
                theme_text_color="Secondary",
                halign="center",
                valign="middle",
                size_hint_y=None,
                height="40dp"
            )

            list_layout.add_widget(empty_label)

        # =========================================================
        # COMMENTS
        # =========================================================
        else:

            for c in comments:

                row = MDBoxLayout(
                    orientation="vertical",
                    spacing="3dp",
                    padding=("4dp", "4dp"),
                    size_hint_y=None
                )

                row.bind(
                    minimum_height=row.setter("height")
                )

                # -------------------------------
                # USER
                # -------------------------------
                header = MDLabel(
                    text=f"{c.get('username', 'Unknown')} "
                         f"({c.get('role', '')})",
                    bold=True,
                    font_size="13sp",
                    theme_text_color="Custom",
                    text_color=(0.3, 0.7, 1, 1),
                    size_hint_y=None,
                    height="22dp"
                )

                row.add_widget(header)

                # -------------------------------
                # COMMENT TEXT
                # -------------------------------
                body_label = MDLabel(
                    text=c.get("content", ""),
                    theme_text_color="Primary",
                    size_hint_y=None,
                    halign="left",
                    valign="top"
                )

                # Make text wrap according to available width
                body_label.bind(
                    width=lambda inst, value:
                    setattr(inst, "text_size", (value, None))
                )

                body_label.bind(
                    texture_size=lambda inst, value:
                    setattr(inst, "height", value[1])
                )

                row.add_widget(body_label)

                list_layout.add_widget(row)

        # =========================================================
        # SCROLLABLE COMMENTS (reacts to window/screen size changes)
        # =========================================================
        from kivy.core.window import Window
        from kivy.metrics import dp

        def _calc_scroll_height():
            return min(Window.height * 0.45, dp(320))

        scroll = ScrollView(
            size_hint=(1, None),
            height=_calc_scroll_height(),
            do_scroll_y=True,
            do_scroll_x=False,
            bar_width=dp(3)
        )

        def _on_window_resize(instance, value):
            scroll.height = _calc_scroll_height()

        Window.bind(size=_on_window_resize)

        scroll.add_widget(list_layout)

        # =========================================================
        # COMMENT INPUT
        # =========================================================
        input_field = MDTextField(
            hint_text="Write a comment...",
            mode="rectangle",
            multiline=False,
            size_hint_y=None,
            height="52dp"
        )

        # =========================================================
        # MAIN DIALOG CONTENT
        # =========================================================
        container = MDBoxLayout(
            orientation="vertical",
            spacing="10dp",
            padding=("4dp", "4dp"),
            size_hint_y=None
        )

        container.bind(
            minimum_height=container.setter("height")
        )

        container.add_widget(scroll)
        container.add_widget(input_field)

        # =========================================================
        # POST COMMENT
        # =========================================================
        def post_comment(*args):

            text = input_field.text.strip()

            if not text:
                toast("Write a comment first")
                return

            try:

                r = requests.post(
                    f"{API_URL}/jobs/{job_id}/comments",
                    json={"content": text},
                    headers=self._get_auth_headers()
                )

                if r.status_code == 200:

                    self.dialog.dismiss()

                    # Reload comments
                    self.open_comments(
                        job_id,
                        job_title
                    )

                else:
                    toast("Failed to post comment")

            except Exception as e:

                print("POST COMMENT ERROR:", e)
                toast("Server error")

        # =========================================================
        # DIALOG
        # =========================================================
        self.dialog = MDDialog(
            title=f"Comments - {job_title}",
            type="custom",
            content_cls=container,
            size_hint_x=0.92,
            buttons=[
                MDFlatButton(
                    text="POST",
                    on_release=post_comment
                ),

                MDFlatButton(
                    text="CLOSE",
                    on_release=lambda x:
                    self.dialog.dismiss()
                )
            ]
        )

        def _cleanup_resize_binding(*args):
            Window.unbind(size=_on_window_resize)

        self.dialog.bind(on_dismiss=_cleanup_resize_binding)
        self.dialog.open()


    from kivy.clock import Clock
    from kivymd.toast import toast
    from kivymd.app import MDApp
    from app.utils.network import NetworkClient


    def toggle_job(self, job, current_status):
        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")

        if not token:
            toast("Please login again")
            return

        # ✅ FIX: use backend-valid statuses
        if current_status == "pending":
             new_status = "completed"   # CLOSE job
        else:
            new_status = "pending"     # REOPEN job

        headers = {
            "Authorization": f"Bearer {token}",
            "ngrok-skip-browser-warning": "true"
        }

        payload = {
             "status": new_status
        }

        # Optional UX feedback
        toast("Updating job...")

        # 🔥 ASYNC PATCH REQUEST
        NetworkClient.patch(
            f"{API_URL}/jobs/{job['id']}/status",
            json=payload,
            headers=headers,
            callback=self.on_job_toggled
        )

    def on_job_toggled(self, response, error=None):

        def update_ui(dt):
            if error:
                print("Toggle error:", error)
                toast("Network error")
                return

            if response is None or response.status_code != 200:
                print("Toggle failed:", response.text if response else None)
                toast("Failed to update job")
                return

            toast("Job updated successfully")

            # 🔄 Refresh jobs list
            self.load_jobs()

        Clock.schedule_once(update_ui)

from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage

from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import AsyncImage
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivy.metrics import dp

from kivymd.toast import toast
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog


from plyer import filechooser
from functools import partial
import webbrowser
import requests




class TruckOwnerHome(MDScreen):
    _seen_orders = {}

    def on_pre_enter(self, *args):
        Clock.schedule_once(self.load_jobs, 0.2)
        self.job_refresh_event = Clock.schedule_interval(lambda dt: self.load_jobs(), 1200)

    def on_leave(self, *args):
        if hasattr(self, "job_refresh_event"):
            self.job_refresh_event.cancel()

    # -----------------------------
    # BANK DETAILS
    # -----------------------------
    def open_bank_details(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        from kivymd.uix.boxlayout import MDBoxLayout

        from kivy.uix.scrollview import ScrollView
        from kivy.metrics import dp

        content = MDBoxLayout(
            orientation="vertical",
            spacing="15dp",
            padding="10dp",
            size_hint_y=None
        )
        content.bind(minimum_height=content.setter("height"))

        bank_code_input = MDTextField(hint_text="Bank Code (e.g. 058)")
        account_number_input = MDTextField(hint_text="Account Number")
        account_name_input = MDTextField(hint_text="Account Holder Name")

        content.add_widget(bank_code_input)
        content.add_widget(account_number_input)
        content.add_widget(account_name_input)

        scroll = ScrollView(
            size_hint=(1, None),
            height=dp(250)   # 👈 IMPORTANT: limits height for mobile
        )
        scroll.add_widget(content)

        self.dialog = MDDialog(
            title="Bank Details",
            type="custom",
            content_cls=scroll,   # 👈 USE SCROLL HERE
            size_hint=(0.9, None),  # 👈 responsive width
            height=dp(350),        # 👈 controlled height
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(
                    text="SAVE",
                    on_release=lambda x: self.submit_bank_details(
                        bank_code_input.text,
                        account_number_input.text,
                        account_name_input.text
                    )
                ),
            ],
        )
        self.dialog.open()

    def submit_bank_details(self, bank_code, account_number, account_name):
        from app.utils.network import NetworkClient

        bank_code = bank_code.strip()
        account_number = account_number.strip()
        account_name = account_name.strip()

        if not bank_code or not account_number or not account_name:
            toast("All fields are required")
            return

        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")

        if not token:
            toast("Please login again")
            return

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "bank_code": bank_code,
            "bank_account_number": account_number,
            "bank_account_name": account_name
        }

        NetworkClient.put(
            f"{API_URL}/auth/bank-details",
            json=payload,
            headers=headers,
            callback=self.on_bank_details_saved
        )

    def on_bank_details_saved(self, response, error=None):
        def ui(dt):
            if error or response is None or response.status_code != 200:
                toast("Failed to save bank details")
                return
            toast("Bank details saved successfully")
            if hasattr(self, "dialog") and self.dialog:
                self.dialog.dismiss()
        Clock.schedule_once(ui)

    # -----------------------------
    # LOAD JOBS
    # -----------------------------
    def load_jobs(self, *args):
        from app.utils.network import NetworkClient

        self.ids.jobs_list.clear_widgets()

        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")

        if not token:
            toast("Not logged in")
            return

        headers = {"Authorization": f"Bearer {token}"}

        toast("Loading jobs...")

        NetworkClient.get(
            f"{API_URL}/jobs/available",
            headers=headers,
            callback=self.on_jobs_loaded
        )

    def _load_my_apps(self, jobs):
        from app.utils.network import NetworkClient

        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")

        headers = {"Authorization": f"Bearer {token}"}

        NetworkClient.get(
            f"{API_URL}/jobs/my-applications",
            headers=headers,
            callback=lambda res, error=None: self.on_apps_loaded(res, error, jobs)
        )
    
    def on_apps_loaded(self, response, error, jobs):
        from datetime import datetime
        from app.utils.network import NetworkClient

        def ui(dt):
            job_to_app = {}
            if response and response.status_code == 200:
                my_apps = response.json()
                for item in my_apps:
                    job_id = item.get("job_id")
                    app_id = item.get("id")
                    if job_id and app_id:
                        job_to_app[job_id] = app_id

            for job in jobs:
                job_id = job.get("id")
                job["application_id"] = job_to_app.get(job_id)
                job["title"] = job.get("title") or "Untitled"
                job["description"] = job.get("description") or "No description"
                job["location"] = job.get("location") or "N/A"
                job["order_number"] = job.get("order_number") or "N/A"
                order_num = job["order_number"]
                job_id_key = job.get("id")
                previous_order = self._seen_orders.get(job_id_key)
                if order_num != "N/A" and previous_order != order_num:
                    toast(f"Order assigned: {order_num} for {job.get('title', 'a job')}")
                self._seen_orders[job_id_key] = order_num
                job["status"] = (job.get("status") or "pending").lower()
                job["applicant_count"] = job.get("applicant_count") or 0
                job["target_limit"] = job.get("target_limit") or 0

                def fmt(v):
                    try:
                        return datetime.fromisoformat(v).strftime("%Y-%m-%d %H:%M")
                    except:
                        return "Unknown"

                job["created_at"] = fmt(job.get("created_at"))
                job["payment_status"] = "N/A"

            self._load_my_payments(jobs)

        Clock.schedule_once(ui)

    def _load_my_payments(self, jobs):
        from app.utils.network import NetworkClient

        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")
        headers = {"Authorization": f"Bearer {token}"}

        NetworkClient.get(
            f"{API_URL}/payments/my-payments",
            headers=headers,
            callback=lambda res, error=None: self.on_payments_loaded(res, error, jobs)
        )

    def on_payments_loaded(self, response, error, jobs):
        def ui(dt):
            job_to_payment = {}

            if response and response.status_code == 200:
                payments = response.json()
                for p in payments:
                    job_to_payment[p.get("job_id")] = p.get("status", "pending")

            for job in jobs:
                job_id = job.get("id")
                job["payment_status"] = job_to_payment.get(job_id, "N/A")
                self._add_job_card(job)

            toast("Jobs loaded")

        Clock.schedule_once(ui)


    
        # -----------------------------
        # JOB CARD
    # -----------------------------
    def _add_job_card(self, job):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton
        from kivymd.uix.label import MDLabel
        from kivymd.uix.card import MDCard
        from kivy.uix.scrollview import ScrollView
        from functools import partial

        card = MDCard(
            orientation="vertical",
            padding="12dp",
            spacing="10dp",
            size_hint_y=None,
            elevation=3,
            radius=[15]
        )

        # ANDROID SAFE HEIGHT
        card.bind(minimum_height=card.setter("height"))

        # ---------------- TITLE ----------------
        card.add_widget(MDLabel(
            text=job["title"],
            font_style="H6",
            size_hint_y=None,
            height="30dp"
        ))

        # ---------------- CORE INFO ----------------
        card.add_widget(MDLabel(
            text=f"Order #: {job['order_number']}",
            size_hint_y=None,
            height="25dp"
        ))

        card.add_widget(MDLabel(
            text=f"Location: {job['location']}",
            size_hint_y=None,
            height="25dp"
        ))

        card.add_widget(MDLabel(
            text=f"Created: {job['created_at']}",
            size_hint_y=None,
            height="25dp"
        ))

        card.add_widget(MDLabel(
            text=f"Applicants: {job['applicant_count']}/{job['target_limit']}",
            size_hint_y=None,
            height="25dp"
        ))

        card.add_widget(MDLabel(
            text=f"Status: {job['status']}",
            size_hint_y=None,
            height="25dp"
        ))

        card.add_widget(MDLabel(
            text=f"Payment: {job.get('payment_status', 'N/A').title()}",
            size_hint_y=None,
            height="25dp"
        ))

        # ---------------- DESCRIPTION ----------------
        desc = MDLabel(
            text=job["description"],
             size_hint_y=None,
        )
        desc.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        desc.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        card.add_widget(desc)

        # ---------------- BUTTONS (FIXED UI) ----------------

        btn_layout = MDBoxLayout(
            orientation="horizontal",
            spacing="20dp",
            padding="5dp",
            size_hint_x=None,   # IMPORTANT for scroll
            height="80dp"
        )
        btn_layout.bind(minimum_width=btn_layout.setter("width"))

        # helper for icon + text
        def action_button(icon, text, callback):
            box = MDBoxLayout(
                orientation="vertical",
                size_hint=(None, None),
                size=("70dp", "70dp"),
                spacing="2dp"
            )

            btn = MDIconButton(
                icon=icon,
                pos_hint={"center_x": 0.5},
                theme_icon_color="Custom",
                icon_color=(0.1, 0.5, 1, 1)
            )
            btn.bind(on_release=callback)

            label = MDLabel(
                text=text,
                halign="center",
                font_style="Caption",
                size_hint_y=None,
                height="20dp"
            )

            box.add_widget(btn)
            box.add_widget(label)

            return box

        # ALWAYS SHOW
        btn_layout.add_widget(
            action_button("truck", "Pack", partial(self.choose_truck_pack, job))
        )

        # ONLY IF APPLIED
        if job.get("application_id"):
            btn_layout.add_widget(
                action_button("file-upload", "Slip", partial(self.choose_slip_file, job["application_id"]))
            )

            btn_layout.add_widget(
                action_button("file-eye", "View", partial(self.show_slips_history, job["application_id"]))
            )

        # ---------------- LIKE + COMMENTS ----------------
        def dynamic_action(icon, initial_text):
            box = MDBoxLayout(
                orientation="vertical",
                size_hint=(None, None),
                size=("70dp", "70dp"),
                spacing="2dp"
            )
            btn = MDIconButton(
                icon=icon,
                pos_hint={"center_x": 0.5},
                theme_icon_color="Custom",
                icon_color=(0.1, 0.5, 1, 1)
            )
            label = MDLabel(
                text=initial_text,
                halign="center",
                font_style="Caption",
                size_hint_y=None,
                height="20dp"
            )
            box.add_widget(btn)
            box.add_widget(label)
            return box, btn, label

        job_id_for_social = job.get("id")
        like_box, like_icon, like_label = dynamic_action("thumb-up-outline", "Like")
        comment_box, comment_icon, comment_label = dynamic_action("comment-outline", "Comments")
        like_icon.bind(on_release=lambda inst, jid=job_id_for_social, lbl=like_label, icon=like_icon: self.toggle_like(jid, icon, lbl))
        comment_icon.bind(on_release=lambda inst, jid=job_id_for_social, t=job.get("title", "Job"): self.open_comments(jid, t))
        btn_layout.add_widget(like_box)
        btn_layout.add_widget(comment_box)
        self._fetch_job_social(job_id_for_social, like_icon, like_label, comment_label)

        # SCROLL WRAPPER (prevents squeezing on small phones)
        scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint_y=None,
            height="85dp"
        )

        scroll.add_widget(btn_layout)
        card.add_widget(scroll)

        # CLICK EVENT
        card.bind(on_release=partial(self.view_job_popup, job))
  
        self.ids.jobs_list.add_widget(card)

    def _get_auth_headers(self):
        app = MDApp.get_running_app()
        token = getattr(app, "current_user", {}).get("token")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _fetch_job_social(self, job_id, like_icon, like_label, comment_label):
        try:
            r = requests.get(f"{API_URL}/jobs/{job_id}/likes", headers=self._get_auth_headers())
            if r.status_code == 200:
                data = r.json()
                like_label.text = f"Like ({data.get('like_count', 0)})"
                liked = data.get("liked_by_me", False)
                like_icon.icon = "thumb-up" if liked else "thumb-up-outline"
                like_icon.icon_color = (0.2, 0.6, 1, 1) if liked else (0.1, 0.5, 1, 1)
        except Exception as e:
            print("LIKE FETCH ERROR:", e)
        try:
            r = requests.get(f"{API_URL}/jobs/{job_id}/comments", headers=self._get_auth_headers())
            if r.status_code == 200:
                comment_label.text = f"Comments ({len(r.json())})"
        except Exception as e:
            print("COMMENT FETCH ERROR:", e)

    def toggle_like(self, job_id, like_icon, like_label):
        try:
            r = requests.post(f"{API_URL}/jobs/{job_id}/likes/toggle", headers=self._get_auth_headers())
            if r.status_code == 200:
                data = r.json()
                like_label.text = f"Like ({data.get('like_count', 0)})"
                liked = data.get("liked_by_me", False)
                like_icon.icon = "thumb-up" if liked else "thumb-up-outline"
                like_icon.icon_color = (0.2, 0.6, 1, 1) if liked else (0.1, 0.5, 1, 1)
            else:
                toast("Failed to update like")
        except Exception as e:
            print("LIKE TOGGLE ERROR:", e)
            toast("Server error")

    def open_comments(self, job_id, job_title):
        try:
            r = requests.get(f"{API_URL}/jobs/{job_id}/comments", headers=self._get_auth_headers())
            comments = r.json() if r.status_code == 200 else []
        except Exception as e:
            print("COMMENTS LOAD ERROR:", e)
            comments = []
            toast("Could not load comments")

        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField

        from kivy.core.window import Window
        from kivy.metrics import dp

        def _calc_scroll_height():
            return min(Window.height * 0.45, dp(320))

        scroll_c = ScrollView(size_hint=(1, None), height=_calc_scroll_height())

        def _on_window_resize(instance, value):
            scroll_c.height = _calc_scroll_height()

        Window.bind(size=_on_window_resize)

        list_layout = MDBoxLayout(orientation="vertical", spacing="10dp", size_hint_y=None, padding="5dp")
        list_layout.bind(minimum_height=list_layout.setter("height"))

        if not comments:
            list_layout.add_widget(MDLabel(
                text="No comments yet - be the first!",
                theme_text_color="Secondary",
                size_hint_y=None,
                height="30dp"
            ))
        else:
            for c in comments:
                row = MDBoxLayout(orientation="vertical", size_hint_y=None, spacing="2dp")
                row.bind(minimum_height=row.setter("height"))
                header = f"{c.get('username', 'Unknown')} ({c.get('role', '')})"
                row.add_widget(MDLabel(text=header, bold=True, font_size="13sp", size_hint_y=None, height="20dp"))
                body_label = MDLabel(text=c.get("content", ""), size_hint_y=None)
                body_label.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
                body_label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
                row.add_widget(body_label)
                list_layout.add_widget(row)

        scroll_c.add_widget(list_layout)

        input_field = MDTextField(hint_text="Write a comment...", multiline=False)

        container = MDBoxLayout(orientation="vertical", spacing="10dp", size_hint_y=None)
        container.bind(minimum_height=container.setter("height"))
        container.add_widget(scroll_c)
        container.add_widget(input_field)

        def post_comment(*args):
            text = input_field.text.strip()
            if not text:
                return
            try:
                r = requests.post(
                    f"{API_URL}/jobs/{job_id}/comments",
                    json={"content": text},
                    headers=self._get_auth_headers()
                )
                if r.status_code == 200:
                    self.dialog.dismiss()
                    self.open_comments(job_id, job_title)
                else:
                    toast("Failed to post comment")
            except Exception as e:
                print("POST COMMENT ERROR:", e)
                toast("Server error")

        self.dialog = MDDialog(
            title=f"Comments - {job_title}",
            type="custom",
            content_cls=container,
            size_hint_x=0.92,
            buttons=[
                MDFlatButton(text="POST", on_release=post_comment),
                MDFlatButton(text="CLOSE", on_release=lambda x: self.dialog.dismiss()),
            ],
        )

        def _cleanup_resize_binding(*args):
            Window.unbind(size=_on_window_resize)

        self.dialog.bind(on_dismiss=_cleanup_resize_binding)
        self.dialog.open()
    
    # -----------------------------
        # TRUCK PACK UPLOAD
    # -----------------------------
    def choose_truck_pack(self, job, *args):
        pick_document(lambda path: self.upload_truck_pack(job, [path] if path else None))

    def upload_truck_pack(self, job, selection):
        from app.utils.network import NetworkClient

        if not selection or not selection[0]:
            toast("No file selected")
            return

        token = MDApp.get_running_app().current_user.get("token")

        headers = {
            "Authorization": f"Bearer {token}"
        }

        toast("Uploading...")

        file_path = selection[0]

        NetworkClient.post(
            f"{API_URL}/jobs/apply-with-truck-pack",
            data={  # ✅ MUST be data, NOT json
                "job_id": str(job["id"])
            },
            files={  # ✅ correct
                "file": open(file_path, "rb")
            },
            headers=headers,
            callback=self.on_upload_done
       )
    # -----------------------------
    # SLIP UPLOAD
    # -----------------------------
    def choose_slip_file(self, application_id, *args):
        pick_document(lambda path: self.upload_slip(application_id, [path] if path else None))

    def upload_slip(self, application_id, selection):
        from kivymd.app import MDApp
        from app.utils.network import NetworkClient
        from kivymd.toast import toast

        if not selection or not selection[0]:
            toast("No file selected")
            return

        token = MDApp.get_running_app().current_user.get("token")
        headers = {"Authorization": f"Bearer {token}"}

        file_path = selection[0]
        filename = file_path.split("/")[-1]

        toast("Uploading...")

        files = {
            "file": (filename, open(file_path, "rb"), "application/octet-stream")
        }

        NetworkClient.post(
            url=f"{API_URL}/jobs/applications/{application_id}/upload-slip",
            files=files,
            headers=headers,
            callback=self.on_upload_done
        )

    # -----------------------------
    # JOB POPUP
    # -----------------------------
    def view_job_popup(self, job, *args):
        layout = MDBoxLayout(orientation="vertical", spacing="10dp", padding="10dp", size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        def wrapped_label(text):
            lbl = MDLabel(text=text, size_hint_y=None)
            lbl.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
            lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
            return lbl

        layout.add_widget(wrapped_label(f"Title: {job.get('title')}"))
        layout.add_widget(wrapped_label(f"Description: {job.get('description')}"))
        layout.add_widget(wrapped_label(f"Order #: {job.get('order_number')}"))
        layout.add_widget(wrapped_label(f"Location: {job.get('location')}"))
        location_text = job.get("location") or ""
        if location_text and location_text != "N/A":
            maps_btn = MDFlatButton(
                text="OPEN IN MAPS",
                on_release=lambda x, loc=location_text: self.open_location_in_maps(loc)
            )
            layout.add_widget(maps_btn)
        layout.add_widget(wrapped_label(f"Created: {job.get('created_at')}"))


        self.dialog = MDDialog(
            title="Job Details",
            type="custom",
            content_cls=layout,
            buttons=[MDFlatButton(text="CLOSE", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def open_location_in_maps(self, location_text):
        import webbrowser
        import urllib.parse
        query = urllib.parse.quote(location_text)
        url = f"https://www.google.com/maps/search/?api=1&query={query}"
        webbrowser.open(url)
    
    def show_slips_history(self, application_id, *args):
        from app.utils.network import NetworkClient
        from kivymd.app import MDApp

    # 🔒 HARD GUARD (prevents ALL duplicates)
        if getattr(self, "_slips_loading", False):
            print("⚠️ Ignored duplicate slips request")
            return

        self._slips_loading = True

        try:
            token = MDApp.get_running_app().current_user.get("token")
            headers = {"Authorization": f"Bearer {token}"}

            NetworkClient.get(
                f"{API_URL}/jobs/applications/{application_id}/slips",
                headers=headers,
                callback=self.on_slips_loaded
            )

        except Exception as e:
            self._slips_loading = False
            print("❌ Slips request error:", e)
   


    def on_slips_loaded(self, response, error=None):
        from kivy.clock import Clock

    # 🔓 unlock flag
        self._slips_loading = False

        def ui(dt):
            try:
                if error:
                    self._handle_slips_ui(None, error)
                    return

                if not response:
                    self._handle_slips_ui(None, "Empty response")
                    return

                # ✅ FIX: convert Response → JSON
                if hasattr(response, "json"):
                    data = response.json()
                else:
                    data = response  # already parsed

                print("✅ PARSED SLIPS DATA:", data)

                self._handle_slips_ui(data, None)

            except Exception as e:
                print("❌ JSON PARSE ERROR:", e)
                self._handle_slips_ui(None, str(e))

        Clock.schedule_once(ui, 0)

    def _handle_slips_ui(self, response, error):
        import threading
        import os
        import json
        from kivy.uix.scrollview import ScrollView
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        if error:
            toast("Failed to load slips")
            return

        if not response:
            toast("No slips found")
            return

        # ✅ ensure response is JSON (NOT bytes)
        if isinstance(response, bytes):
            response = json.loads(response.decode("utf-8"))
        elif isinstance(response, str):
            response = json.loads(response)

        # ✅ normalize to list
        if isinstance(response, dict):
            slips_data = response.get("slips") or response.get("data") or []
        else:
            slips_data = response

        if not isinstance(slips_data, list):
            print("❌ Invalid slips format:", slips_data)
            return

        print("✅ SLIPS COUNT:", len(slips_data))

        if not slips_data:
            toast("No slips uploaded yet")
            return

        # ---------------- DIALOG CONTENT ----------------
        scroll = ScrollView(size_hint=(1, None), height="350dp")

        self.slips_content = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=10,
            padding=10
        )
        self.slips_content.bind(minimum_height=self.slips_content.setter("height"))

        scroll.add_widget(self.slips_content)

        if hasattr(self, "dialog") and self.dialog:
            self.dialog.dismiss()

        self.dialog = MDDialog(
            title="Delivery Slips",
            type="custom",
            content_cls=scroll,
            buttons=[
                MDFlatButton(text="CLOSE", on_release=lambda x: self.dialog.dismiss())
            ],
        )
        self.dialog.open()

        # temp folder
        temp_dir = os.path.join(os.getcwd(), "temp_slips")
        os.makedirs(temp_dir, exist_ok=True)

        print("STARTING WORKER THREAD")

        threading.Thread(
            target=self._download_slips_worker,
            args=(slips_data, temp_dir),
            daemon=True
        ).start()

    def _download_slips_worker(self, slips, temp_dir):
        import requests
        import os
        from kivy.clock import Clock

        print("WORKER STARTED WITH:", len(slips))

        for i, slip in enumerate(slips):
            try:
                if not isinstance(slip, dict):
                    print("❌ Invalid slip:", slip)
                    continue

                url = slip.get("file_url")
                if not url:
                    continue

                print("⬇️ DOWNLOADING:", url)

                r = requests.get(url, timeout=15)

                print("STATUS:", r.status_code, "SIZE:", len(r.content))

                if r.status_code != 200 or len(r.content) < 100:
                    print("❌ Skipping invalid image")
                    continue

                file_path = os.path.join(temp_dir, f"slip_{i}.jpg")

                with open(file_path, "wb") as f:
                    f.write(r.content)

                print("✅ SAVED:", file_path)

                Clock.schedule_once(
                    lambda dt, p=file_path: self._add_image(p),
                    0
                )

            except Exception as e:
                print("WORKER ERROR:", e)


    def _add_image(self, path):
        from kivy.metrics import dp
        from kivymd.uix.card import MDCard
        from kivymd.uix.fitimage import FitImage
        import os

        print("🖼️ ADDING IMAGE:", path)

        if not os.path.exists(path):
            print("❌ FILE NOT FOUND:", path)
            return

        card = MDCard(
            size_hint=(1, None),
            height=dp(250),
            radius=[12],
            elevation=3
        )

        image = FitImage(source=path)

        card.add_widget(image)

        self.slips_content.add_widget(card)
        self.slips_content.height = self.slips_content.minimum_height


    def on_jobs_loaded(self, response, error=None):

        def ui(dt):
            if error:
                print("Jobs error:", error)
                toast("Network error")
                return

            if not response or response.status_code != 200:
                print("Jobs failed:", response.text if response else None)
                toast("Failed to load jobs")
                return

            try:
                self.ids.jobs_list.clear_widgets()
                jobs = response.json()
                self._load_my_apps(jobs)

            except Exception as e:
                print("UI error:", e)
                toast("Data error")

        Clock.schedule_once(ui)

    def on_upload_done(self, response, error=None):
        from kivy.clock import Clock
        from kivymd.toast import toast

        def ui(dt):
            if error:
                print("❌ Upload error:", error)
                toast("Upload failed")
            else:
                print("✅ Upload success")
                toast("Upload successful")

        Clock.schedule_once(ui)


class JobApplicationsScreen(MDScreen):
    def on_enter(self):
        self.ids.applications_list.clear_widgets()
        toast("Applications loaded")

class UploadSlipFeedbackScreen(MDScreen):
    slip_path = ObjectProperty()
    current_job_id = 1  # Ensure this is set when navigating to this screen

    def choose_file(self):
        filechooser.open_file(
            on_selection=lambda x: setattr(self.slip_path, "text", x[0] if x else "")
        )

    def upload_slip(self):

        file_path = self.slip_path.text

        if not file_path:
            toast("Please select a file")
            return

        url = f"{API_URL}/jobs/applications/{self.current_job_id}/upload-slip"

        try:
            with open(file_path, "rb") as f:

                files = {"file": (file_path.split("/")[-1], f, "image/jpeg")}

                r = requests.post(url, files=files)

            if r.status_code == 200:
                toast("Slip uploaded successfully")
                self.slip_path.text = ""

            else:
                print(r.text)
                toast("Upload failed")

        except Exception as e:
            print(e)
            toast("Server error")

    def submit_feedback(self):
        rating = self.ids.rating.text
        comment = self.ids.comment.text

        if not rating.isdigit() or not (1 <= int(rating) <= 5):
            toast("Rating must be 1–5")
            return

        # Send feedback to backend
        try:
            payload = {"job_id": self.current_job_id, "rating": int(rating), "comment": comment}
            r = requests.post(f"{API_URL}/feedback/", json=payload)
            
            if r.status_code in (200, 201):
                print(f"FEEDBACK SUCCESS: {r.json()}")
                toast("Feedback submitted")
                self.ids.rating.text = ""
                self.ids.comment.text = ""
            else:
                print(f"FEEDBACK ERROR: {r.text}")
                toast("Failed to submit feedback")
        except:
            toast("Network Error") 

            


class MyApp(MDApp):
    current_user = None

    def build(self):
        self.theme_cls.primary_palette = "LightBlue"
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)
    def init_ads(self):
        try:
            from kivmob import KivMob, TestIds
            self.ads = KivMob(TestIds.APP)
            self.ads.new_banner(TestIds.BANNER, top_pos=False)
            self.ads.request_banner()
            self.ads.show_banner()
        except Exception as e:
            print("AD INIT ERROR:", e)


    def on_start(self):
        print("APP STARTED")
        if platform == "android":
            try:
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ])
            except Exception as e:
                print("PERMISSION REQUEST ERROR:", e)
        if store.exists("auth"):
            store.delete("auth")

        self.root.current = "splash"  # ALWAYS start safe screen
        Clock.schedule_once(lambda dt: self.init_ads(), 2)

        if store.exists("auth"):
            data = store.get("auth")

            self.current_user = {
                "token": data.get("token"),
                "id": data.get("id"),
                "role": data.get("role")
            }

            print("SESSION RESTORED:", self.current_user)

            role = self.current_user.get("role")

            Clock.schedule_once(lambda dt: self._route(role), 1)

        else:
            print("NO SESSION")
            self.current_user = None
            Clock.schedule_once(lambda dt: self._go_login(), 0.5)

    def _go_login(self):
        if self.root:
            self.root.current = "login"

    def _route(self, role):
        if not self.root:
            return

        if role == "truck_owner":
            self.root.current = "truck_owner"

        elif role == "main_contractor":
            self.root.current = "contractor_home"

        else:
            self.root.current = "login"

    def logout(self):
        store.delete("auth")
        self.current_user = None

        if self.root:
            self.root.current = "login"


# ---------------- IMPORTANT ENTRY POINT ----------------
if __name__ == "__main__":
    MyApp().run()

