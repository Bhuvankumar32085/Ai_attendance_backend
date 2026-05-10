from flask import Blueprint
from src.controllers.auth_controller import register,login,get_current_user,registerImageAndVioce,add_class,get_classes,enroll_student,teacher_dashboard,mark_attendance,student_dashboard,update_class_status

auth_bp = Blueprint("auth", __name__)

auth_bp.route("/register", methods=["POST"])(register)
auth_bp.route("/login", methods=["POST"])(login)
auth_bp.route("/get-curr-user", methods=["POST"])(get_current_user)
auth_bp.route("/register-image-voice", methods=["POST"])(registerImageAndVioce)
auth_bp.route("/add-class", methods=["POST"])(add_class)
auth_bp.route("/mark-attendance", methods=["POST"])(mark_attendance)
auth_bp.route("/get-classes/<teacher_id>", methods=["GET"])(get_classes)
auth_bp.route("/get-student-data/<student_id>", methods=["GET"])(student_dashboard)
auth_bp.route("/teacher-dashboard-data/<teacher_id>", methods=["GET"])(teacher_dashboard)
auth_bp.route("/add-student-in-class", methods=["POST"])(enroll_student)
auth_bp.route("/update-class-status", methods=["PUT"])(update_class_status)