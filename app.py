from flask import Flask, render_template, request, redirect, url_for, flash
import random
import string
import os
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from dotenv import load_dotenv
import json

load_dotenv()
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Google Sheets setup
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds_data = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
CREDS = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
# CREDS = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
# CREDS = Credentials.from_service_account_file(creds_data, scopes=SCOPES)
SPREADSHEET_ID = (
    "186jdKDsYUrbIv0B-rFXRCzhiY8veFSPwmvwPbNAGgd4"  # Replace with your Google Sheet ID
)
SHEET_NAME = "PaymentData"  # Replace with your sheet name

# Initialize Google Sheets
client = gspread.authorize(CREDS)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

drive_service = build("drive", "v3", credentials=CREDS)


# Function to generate a unique 6-digit code
def generate_unique_code():
    return "".join(random.choices(string.digits, k=6))


# Function to save data to Google Sheets
def save_to_google_sheet(data):
    sheet.append_row(data)


# Function to upload a file directly to Google Drive from memory
def upload_to_drive(file):
    # Define the metadata for the file
    parent_folder_id = (
        "1E6Kc3T9jIo6u50ydjhHbXOyqDXgE1C9b"  # Replace with your folder ID
    )
    file_metadata = {
        "name": file.filename,  # Use the original file name
        "parents": [parent_folder_id],
    }

    # Read the file directly from memory using io.BytesIO
    file_stream = io.BytesIO(file.read())

    # Upload the file to Google Drive
    media = MediaIoBaseUpload(file_stream, mimetype=file.content_type)
    uploaded_file = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )

    # Get the file ID and generate the file link
    file_id = uploaded_file.get("id")
    file_link = f"https://drive.google.com/uc?id={file_id}"

    return file_link


def check_login(email, code):
    print(email, code)
    all_records = sheet.get_all_records()

    # Normalize input email and code
    email = email.strip().lower()  # Remove spaces and make email lowercase
    code = str(code).strip()  # Ensure code is treated as a string and remove spaces

    for record in all_records:
        # Normalize the stored email and code
        record_email = (
            record["Email"].strip().lower()
        )  # Remove spaces and make lowercase
        record_code = str(
            record["Unique Code"]
        ).strip()  # Ensure it's a string and remove spaces

        # Check if both email and code match
        if record_email == email and record_code == code:
            print("Login successful:", email, code)
            return (
                record["Course"],
                record["Semester"],
            )  # Return the course name if login is successful

    return None  # Return None if no match is found


# Landing page route
@app.route("/", methods=["GET", "POST"])
def landing_page():
    return render_template("landing.html")


@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        # Collect form data
        name = request.form["name"]
        email = request.form["email"]
        whatsapp = request.form["whatsapp"]
        phone = request.form["phone"]
        month = request.form["month"]
        amount = request.form["amount"]
        payment_mode = request.form["payment_mode"]
        course = request.form["course"]
        semester = request.form["semester"]
        centre = request.form["centre"]
        address = request.form["location"]
        payment_image = request.files["payment_image"]

        # Generate a unique code
        unique_code = generate_unique_code()
        print(unique_code, course, semester)
        # Upload the payment image to Google Drive and get the link
        image_link = upload_to_drive(payment_image)

        # Save data to Google Sheets, including the image link
        save_to_google_sheet(
            [
                name,
                email,
                whatsapp,
                phone,
                month,
                amount,
                payment_mode,
                course,
                semester,
                centre,
                address,
                unique_code,
                image_link,
            ]
        )
        # Flash a message with the unique code
        flash(f"Your unique code is: {unique_code}")
        return redirect(url_for("join"))

    return render_template("form.html")


# Route for the login page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        code = request.form["code"]

        course, semester = check_login(email, code)

        if course:
            return redirect(url_for("courses", course=course, semester=semester))
        else:
            flash("Invalid email or unique code.")
            return redirect(url_for("login"))

    return render_template("login.html")


# Route for course materials
@app.route("/course_materials")
def course_materials():
    course = request.args.get("course")
    course_materials = {
        "Course1": ["Lecture 1", "Lecture 2", "Assignment 1"],
        "Course2": ["Lecture A", "Lecture B", "Assignment A"],
    }
    materials = course_materials.get(course, [])
    return render_template("course_materials.html", course=course, materials=materials)


# Fetch live video data from Google Sheet
def get_google_sheet_data(course, semester):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)

    # Create a dictionary mapping course and semester combinations to Google Sheet IDs
    course_sem_key = f"{course}sem{semester}"
    sheet_mapping = {
        "BCasemI": "1RqiDfcv890FOJFPQ2heeLtVg5aa0mVu2vMmIuHX6Yeo",
        "BCasemII": "1jw1VlDgKyEv6IgMYi4cL1-2mvtYA_xjXatPyFg96TPI",
        "BtechsemI": "some_google_sheet_id",
        "BtechsemII": "another_google_sheet_id",
        # Add more course-semester combinations as needed
    }

    # Look up the correct Google Sheet ID for the selected course and semester
    sheet_id = sheet_mapping.get(course_sem_key)
    if not sheet_id:
        raise Exception(
            f"No Google Sheet found for course {course} semester {semester}"
        )

    print(semester, course)
    # Authorize and open the correct Google Sheet
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).sheet1

    # Get all the records in the sheet (as a list of dictionaries)
    data = sheet.get_all_records()
    return data


# Route for live videos
@app.route("/live_videos")
def live_videos():
    course = request.args.get("course")
    semester = request.args.get("semester")
    print(course, semester)
    if not course or not semester:
        flash("Please select both a course and a semester.")
        return redirect(url_for("courses"))

    try:
        # Fetch video data for the selected course and semester from Google Sheet
        video_data = get_google_sheet_data(course, semester)
    except Exception as e:
        flash(f"Error retrieving live video data: {e}")
        video_data = []

    return render_template(
        "live_videos.html", videos=video_data, course=course, semester=semester
    )


# Route for courses
@app.route("/courses")
def courses():
    course = request.args.get("course")
    semester = request.args.get("semester")
    print(course, semester)
    return render_template("courses.html", course=course, semester=semester)


if __name__ == "__main__":
    app.run(debug=True)
