from flask import request, jsonify, make_response
from src.configs.db import supabase
import bcrypt
import os
import jwt
import base64
# from datetime import timezone
from src.pipelines.face_pipeline import get_face_embedding , predict_attendance ,model_data 
from src.pipelines.voice_pipeline import get_voice_embedding , process_bulk_audio
import base64
import numpy as np
import cv2
from datetime import datetime ,timedelta, timezone

SECRET_KEY = os.getenv("SECRET_KEY")
COOKIE_MAX_AGE = 60 * 60 * 24 *1000  # 1000 days


def register():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        required_fields = ["username", "name", "password", "role"]

        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"{field} is required"
                }), 400

        existing_user = supabase.table("users") \
            .select("*") \
            .eq("username", data["username"]) \
            .execute()

        if existing_user.data:
            return jsonify({
                "success": False,
                "message": "User already exists"
            }), 409

        hashed_pw = bcrypt.hashpw(
            data["password"].encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        user = {
            "username": data["username"],
            "name": data["name"],
            "password": hashed_pw,
            "role": data["role"]
        }

        res = supabase.table("users").insert(user).execute()

        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "data": res.data
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


def login():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data"}), 400

        res = supabase.table("users") \
            .select("*") \
            .eq("username", data["username"]) \
            .execute()

        if not res.data:
            return jsonify({"success": False, "message": "User not found"}), 404

        user = res.data[0]

        if not bcrypt.checkpw(
            data["password"].encode("utf-8"),
            user["password"].encode("utf-8")
        ):
            return jsonify({"success": False, "message": "Invalid password"}), 401

        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=COOKIE_MAX_AGE
        )

        token = jwt.encode({
            "user_id": user["user_id"],
            "role": user["role"],
            "username": user["username"],
            "name": user["name"],
            "exp": expires_at
        }, SECRET_KEY, algorithm="HS256")

        return jsonify({"success": True, "message": "Login successful", "token": token , "role": user["role"]})

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": str(e)}), 500


def get_current_user():
    try:
        data = request.get_json()
        token = data.get("token")

        if not token:
            return jsonify({"success": False, "message": "No token"}), 401

        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        user_id = decoded["user_id"]

        res = supabase.table("users") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()

        if not res.data:
            return jsonify({"success": False, "message": "User not found"}), 404

        user = res.data[0]

        return jsonify({
            "success": True,
            "user": {
                "user_id": user["user_id"],
                "name": user["name"],
                "role": user["role"],
                "username": user["username"]
            }
        })

    except jwt.ExpiredSignatureError:
        return jsonify({"success": False, "message": "Token expired"}), 401

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def registerImageAndVioce():
    try:
        # ---------------- GET FILES ----------------
        image_file = request.files.get("image")
        audio_file = request.files.get("audio")
        user_id = request.form.get("user_id")
        
        print("image_file:", image_file)
        print("audio_file:", audio_file)
        print("user_id:", user_id)

        if not image_file:
            return jsonify({"error": "Image missing"}), 400

        # ---------------- IMAGE PROCESS ----------------
        image_bytes = image_file.read()

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        face_embeddings = get_face_embedding(img)

        if len(face_embeddings) == 0:
            return jsonify({"error": "No face detected"}), 400

        face_embedding = face_embeddings[0]
        
        model_data = None

        # save face embedding
        supabase.table("face_embeddings").insert({
            "user_id": user_id,
            "embedding": face_embedding.tolist()
        }).execute()

        # ---------------- AUDIO PROCESS ----------------
        if audio_file:
            audio_bytes = audio_file.read()

            voice_embedding = get_voice_embedding(audio_bytes)

            if voice_embedding:
                supabase.table("voice_embeddings").insert({
                    "user_id": user_id,
                    "embedding": voice_embedding
                }).execute()

        return jsonify({"message": "User registered successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

def add_class():
    try:
        data = request.json

        subject_name = data.get("subject_name",'').strip().upper()
        subject_code = data.get("subject_code")
        subject_section = data.get("subject_section",'').strip().lower()
        teacher_id = data.get("teacher_id")

        if not subject_name or not teacher_id or not subject_code or not subject_section:
            return jsonify({"error": "Missing fields"}), 400

        existing = supabase.table("subjects") \
            .select("*") \
            .eq("subject_code", subject_code) \
            .eq("subject_section", subject_section) \
            .eq("teacher_id", teacher_id) \
            .execute()

        if existing.data:
            return jsonify({
                "error": "This class already exists for this teacher"
            }), 400

        # insert into DB
        res = supabase.table("subjects").insert({
            "subject_name": subject_name,
            "subject_code": subject_code,
            "subject_section": subject_section,
            "teacher_id": teacher_id
        }).execute()

        return jsonify({
            "message": "Class created successfully",
            "data": res.data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
def get_classes(teacher_id):
    try:
        res = supabase.table("subjects") \
            .select("*") \
            .eq("teacher_id", teacher_id) \
            .execute()
        
        return jsonify(res.data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def enroll_student():
    
    try:

        data = request.get_json()

        student_id = data.get("student_id")
        subject_id = data.get("subject_id")

        print(data)

        if not student_id or not subject_id:

            return jsonify({
                "error": "Missing fields"
            }), 400

        # student exists

        student_res = supabase.table("users") \
            .select("*") \
            .eq("user_id", student_id) \
            .eq("role", "student") \
            .execute()

        if not student_res.data:

            return jsonify({
                "error": "Student does not exist"
            }), 400

        # subject exists

        subject_res = supabase.table("subjects") \
            .select("*") \
            .eq("subject_id", subject_id) \
            .execute()

        if not subject_res.data:

            return jsonify({
                "error": "Subject does not exist"
            }), 400

        current_subject = subject_res.data[0]

        current_section = current_subject["subject_section"]

        # duplicate enrollment

        existing = supabase.table("enrollments") \
            .select("*") \
            .eq("student_id", student_id) \
            .eq("subject_id", subject_id) \
            .execute()

        if existing.data:

            return jsonify({
                "error": "Student already enrolled"
            }), 400

        # get student's existing enrollments

        student_enrollments = supabase.table("enrollments") \
            .select("subject_id") \
            .eq("student_id", student_id) \
            .execute()

        enrolled_subject_ids = [
            row["subject_id"]
            for row in student_enrollments.data
        ]

        # section validation

        if enrolled_subject_ids:

            enrolled_subjects = supabase.table("subjects") \
                .select("subject_section") \
                .in_("subject_id", enrolled_subject_ids) \
                .execute()

            # first enrolled section
            print('enrolled_subjects',enrolled_subjects)

            student_section = enrolled_subjects.data[0][
                "subject_section"
            ]

            # section mismatch

            if student_section != current_section:

                return jsonify({
                    "error":
                    f"Student belongs to section {student_section}"
                }), 400

        # insert enrollment

        supabase.table("enrollments").insert({

            "student_id": student_id,
            "subject_id": subject_id

        }).execute()

        return jsonify({
            "message": "Student enrolled successfully"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

def teacher_dashboard(teacher_id):
    
    try:

        subjects_res = supabase.table("subjects") \
            .select("*") \
            .eq("teacher_id", teacher_id) \
            .execute()

        subjects = subjects_res.data

        result = []

        for subject in subjects:

            subject_id = subject["subject_id"]

            # enrollments

            enroll_res = supabase.table("enrollments") \
                .select("student_id") \
                .eq("subject_id", subject_id) \
                .execute()

            student_ids = [
                e["student_id"]
                for e in enroll_res.data
            ]

            # students

            students = []

            if student_ids:

                user_res = supabase.table("users") \
                    .select("user_id, name") \
                    .in_("user_id", student_ids) \
                    .execute()

                students = user_res.data

            # active session check

            session_res = supabase.table(
                "attendance_sessions"
            ).select("*") \
             .eq("subject_id", subject_id) \
             .eq("session_status", "active") \
             .execute()

            # status

            status = "close"

            if session_res.data:
                status = "start"

            # final response

            result.append({

                "subject_id":
                    subject_id,

                "subject_name":
                    subject["subject_name"],

                "subject_code":
                    subject["subject_code"],

                "subject_section":
                    subject["subject_section"],

                "status":
                    status,

                "students":
                    students
            })

        return jsonify(result)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


def mark_attendance():
    
    try:

        subject_id = request.form.get("subject_id")

        image_file = request.files.get("image")

        audio_file = request.files.get("audio")

        if not subject_id:

            return jsonify({
                "error": "Subject ID missing"
            }), 400

        # active session

        active_session = supabase.table(
            "attendance_sessions"
        ).select("*") \
         .eq("subject_id", subject_id) \
         .eq("session_status", "active") \
         .execute()

        if not active_session.data:

            return jsonify({
                "error": "Class is not started"
            }), 400

        session = active_session.data[0]

        session_id = session["session_id"]

        marked_students = []

        # ==================================================
        # FACE ATTENDANCE
        # ==================================================

        if image_file:

            image_bytes = image_file.read()

            nparr = np.frombuffer(
                image_bytes,
                np.uint8
            )

            img = cv2.imdecode(
                nparr,
                cv2.IMREAD_COLOR
            )

            detected_students, _, total_faces = \
                predict_attendance(img)

            print(
                "TOTAL DETECTED FACES:",
                total_faces
            )

            print(
                "DETECTED STUDENTS:",
                detected_students
            )

            if not detected_students:

                return jsonify({
                    "error":
                    "No student recognized"
                }), 400

            # loop all detected students

            for student_id in detected_students.keys():

                # enrollment check

                enrollment = supabase.table(
                    "enrollments"
                ).select("*") \
                 .eq("student_id", student_id) \
                 .eq("subject_id", subject_id) \
                 .execute()

                if not enrollment.data:

                    continue

                # duplicate check

                existing = supabase.table(
                    "attendance_logs"
                ).select("*") \
                 .eq("student_id", student_id) \
                 .eq("session_id", session_id) \
                 .execute()

                if existing.data:

                    continue

                # insert attendance

                supabase.table(
                    "attendance_logs"
                ).insert({

                    "student_id":
                        student_id,

                    "subject_id":
                        subject_id,

                    "session_id":
                        session_id,

                    "attendance_date":
                        datetime.now().date().isoformat(),

                    "check_in_time":
                        datetime.now().isoformat(),

                    "status":
                        "present",

                    "face_confidence":
                        0.95

                }).execute()

                marked_students.append(student_id)

        # ==================================================
        # VOICE ATTENDANCE
        # ==================================================

        elif audio_file:

            audio_bytes = audio_file.read()

            enrollment_res = supabase.table(
                "enrollments"
            ).select("student_id") \
             .eq("subject_id", subject_id) \
             .execute()

            student_ids = [
                x["student_id"]
                for x in enrollment_res.data
            ]

            voice_res = supabase.table(
                "voice_embeddings"
            ).select("*") \
             .in_("user_id", student_ids) \
             .execute()

            candidates_dict = {}

            for row in voice_res.data:

                candidates_dict[
                    row["user_id"]
                ] = np.array(
                    row["embedding"]
                )

            identified = process_bulk_audio(
                audio_bytes,
                candidates_dict
            )

            print("identified:", identified)

            if not identified:

                return jsonify({
                    "error":
                    "No voice recognized"
                }), 400

            # multiple voice attendance

            for student_id, confidence in identified.items():

                existing = supabase.table(
                    "attendance_logs"
                ).select("*") \
                 .eq("student_id", student_id) \
                 .eq("session_id", session_id) \
                 .execute()

                if existing.data:

                    continue

                supabase.table(
                    "attendance_logs"
                ).insert({

                    "student_id":
                        student_id,

                    "subject_id":
                        subject_id,

                    "session_id":
                        session_id,

                    "attendance_date":
                        datetime.now().date().isoformat(),

                    "check_in_time":
                        datetime.now().isoformat(),

                    "status":
                        "present",

                    "voice_confidence":
                        confidence

                }).execute()

                marked_students.append(student_id)

        # ==================================================
        # FINAL RESPONSE
        # ==================================================

        if len(marked_students) == 0:

            return jsonify({
                "error":
                "No attendance marked"
            }), 400

        return jsonify({

            "message":
                "Attendance marked successfully",

            "marked_students":
                marked_students,

            "total_marked":
                len(marked_students)

        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500
        
def student_dashboard(student_id):
    
    try:

        print("student_id:", student_id)

        # enrolled subjects

        enrollments = supabase.table(
            "enrollments"
        ).select("subject_id") \
         .eq("student_id", student_id) \
         .execute()

        subject_ids = [
            row["subject_id"]
            for row in enrollments.data
        ]

        if not subject_ids:

            return jsonify({

                "student_id":
                    student_id,

                "overall_percentage":
                    0,

                "total_subjects":
                    0,

                "total_present":
                    0,

                "total_absent":
                    0,

                "total_classes":
                    0,

                "subjects":
                    []
            })

        # subjects

        subjects_res = supabase.table(
            "subjects"
        ).select("*") \
         .in_("subject_id", subject_ids) \
         .execute()

        subjects = subjects_res.data

        today = datetime.now().date().isoformat()

        dashboard_subjects = []

        overall_present = 0
        overall_absent = 0
        overall_classes = 0

        # loop subjects

        for subject in subjects:

            subject_id = subject["subject_id"]

            # total classes

            total_logs = supabase.table(
                "attendance_logs"
            ).select("*", count="exact") \
             .eq("student_id", student_id) \
             .eq("subject_id", subject_id) \
             .execute()

            total_classes = total_logs.count or 0

            # present count

            present_logs = supabase.table(
                "attendance_logs"
            ).select("*", count="exact") \
             .eq("student_id", student_id) \
             .eq("subject_id", subject_id) \
             .eq("status", "present") \
             .execute()

            present_count = present_logs.count or 0

            # absent count

            absent_logs = supabase.table(
                "attendance_logs"
            ).select("*", count="exact") \
             .eq("student_id", student_id) \
             .eq("subject_id", subject_id) \
             .eq("status", "absent") \
             .execute()

            absent_count = absent_logs.count or 0

            # percentage

            percentage = 0

            if total_classes > 0:

                percentage = (
                    present_count / total_classes
                ) * 100

            # today attendance

            today_log = supabase.table(
                "attendance_logs"
            ).select("*") \
             .eq("student_id", student_id) \
             .eq("subject_id", subject_id) \
             .eq("attendance_date", today) \
             .execute()

            today_status = "not_marked"

            if today_log.data:

                today_status = today_log.data[0][
                    "status"
                ]

            # active class

            active_session = supabase.table(
                "attendance_sessions"
            ).select("*") \
             .eq("subject_id", subject_id) \
             .eq("session_status", "active") \
             .execute()

            class_status = "close"

            if active_session.data:
                class_status = "start"

            # attendance history

            history_res = supabase.table(
                "attendance_logs"
            ).select(
                "attendance_date, status"
            ) \
             .eq("student_id", student_id) \
             .eq("subject_id", subject_id) \
             .order(
                "attendance_date",
                desc=True
             ) \
             .execute()

            attendance_history = history_res.data

            # overall stats

            overall_present += present_count
            overall_absent += absent_count
            overall_classes += total_classes

            # subject data

            dashboard_subjects.append({

                "subject_id":
                    subject_id,

                "subject_name":
                    subject["subject_name"],

                "subject_code":
                    subject["subject_code"],

                "subject_section":
                    subject["subject_section"],

                "total_classes":
                    total_classes,

                "present_classes":
                    present_count,

                "absent_classes":
                    absent_count,

                "attendance_percentage":
                    round(percentage, 2),

                "today_status":
                    today_status,

                "class_status":
                    class_status,

                "attendance_history":
                    attendance_history
            })

        # overall percentage

        overall_percentage = 0

        if overall_classes > 0:

            overall_percentage = (
                overall_present / overall_classes
            ) * 100

        # final response

        return jsonify({

            "student_id":
                student_id,

            "overall_percentage":
                round(overall_percentage, 2),

            "total_subjects":
                len(subjects),

            "total_present":
                overall_present,

            "total_absent":
                overall_absent,

            "total_classes":
                overall_classes,

            "today_date":
                today,

            "subjects":
                dashboard_subjects
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500
        
        
def update_class_status():

    try:

        data = request.get_json()

        subject_id = data.get("subject_id")
        teacher_id = data.get("teacher_id")

        if not subject_id or not teacher_id:

            return jsonify({
                "error": "Missing fields"
            }), 400

        # subject exists check

        subject_res = supabase.table("subjects") \
            .select("*") \
            .eq("subject_id", subject_id) \
            .eq("teacher_id", teacher_id) \
            .execute()

        if not subject_res.data:

            return jsonify({
                "error": "Subject not found"
            }), 400

        # active session check

        active_session = supabase.table(
            "attendance_sessions"
        ).select("*") \
         .eq("subject_id", subject_id) \
         .eq("session_status", "active") \
         .execute()

        # START SESSION

        if not active_session.data:

            session_res = supabase.table(
                "attendance_sessions"
            ).insert({

                "subject_id":
                    subject_id,

                "teacher_id":
                    teacher_id,

                "session_date":
                    datetime.now().date().isoformat(),

                "start_time":
                    datetime.now().isoformat(),

                "session_status":
                    "active"

            }).execute()

            return jsonify({

                "message":
                    "Attendance session started",

                "status":
                    "start",

                "session":
                    session_res.data

            })

        # CLOSE SESSION

        session = active_session.data[0]

        session_id = session["session_id"]

        # close session

        supabase.table("attendance_sessions") \
            .update({

                "session_status":
                    "closed",

                "end_time":
                    datetime.now().isoformat()

            }) \
            .eq("session_id", session_id) \
            .execute()

        # enrolled students

        enrollments = supabase.table(
            "enrollments"
        ).select("student_id") \
         .eq("subject_id", subject_id) \
         .execute()

        enrolled_students = [
            row["student_id"]
            for row in enrollments.data
        ]

        # present students

        present_logs = supabase.table(
            "attendance_logs"
        ).select("student_id") \
         .eq("session_id", session_id) \
         .execute()

        present_students = [
            row["student_id"]
            for row in present_logs.data
        ]

        # absent students

        absent_students = []

        for sid in enrolled_students:

            if sid not in present_students:

                absent_students.append(sid)

        # insert absent

        today = datetime.now().date().isoformat()

        for sid in absent_students:

            supabase.table("attendance_logs") \
                .insert({

                    "student_id":
                        sid,

                    "subject_id":
                        subject_id,

                    "session_id":
                        session_id,

                    "attendance_date":
                        today,

                    "check_in_time":
                        datetime.now().isoformat(),

                    "status":
                        "absent"

                }).execute()

        return jsonify({

            "message":
                "Attendance session closed",

            "status":
                "close",

            "absent_students":
                absent_students

        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500