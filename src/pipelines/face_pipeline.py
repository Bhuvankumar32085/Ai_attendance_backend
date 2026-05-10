import dlib
import numpy as np
import face_recognition_models
from sklearn.svm import SVC
from src.configs.db import supabase

def get_face_embedding(image_np):

    faces = detector(image_np, 1)

    print("TOTAL FACES:", len(faces))

    encodings = []

    for face in faces:

        shape = sp(image_np, face)

        face_descriptor = facerec.compute_face_descriptor(
            image_np,
            shape
        )

        encodings.append(
            np.array(face_descriptor)
        )

    return encodings


# -------------------- GET STUDENTS --------------------

def get_all_students():

    res = supabase.table("users") \
        .select("user_id") \
        .eq("role", "student") \
        .execute()

    return res.data


# -------------------- TRAIN MODEL --------------------

def get_trained_svm_model():

    X = []
    Y = []

    students = get_all_students()

    if not students:
        raise Exception("No students found")

    for student in students:

        user_id = student["user_id"]

        res = supabase.table("face_embeddings") \
            .select("embedding") \
            .eq("user_id", user_id) \
            .execute()

        embeddings = res.data

        for emb in embeddings:

            if emb["embedding"]:

                X.append(
                    np.array(emb["embedding"])
                )

                Y.append(user_id)

    if len(X) == 0:
        raise Exception("No embeddings found")

    # dummy clf for compatibility
    clf = SVC(
        kernel='linear',
        probability=True,
        class_weight='balanced'
    )

    clf.fit(X, Y)

    return {
        "clf": clf,
        "X": X,
        "Y": Y
    }


# -------------------- TRAIN CLASSIFIER (CACHE) --------------------

def train_classifier():

    global model_data

    model_data = get_trained_svm_model()

    return model_data


# -------------------- RESET MODEL --------------------

def reset_model():

    global model_data

    model_data = None


# -------------------- PREDICT ATTENDANCE --------------------

def predict_attendance(class_image_np):

    global model_data

    # always reload latest students
    model_data = train_classifier()

    clf = model_data["clf"]

    X = model_data["X"]

    Y = model_data["Y"]

    print('X :- ', X)

    print('Y :- ', Y)

    encodings = get_face_embedding(class_image_np)

    print('encodings :- ', encodings)

    if len(encodings) == 0:

        return {}, [], 0

    detected_students = {}

    all_students = sorted(list(set(Y)))

    print('all_students :- ', all_students)

    # ---------------- LOOP ALL DETECTED FACES ----------------

    for encoding in encodings:

        best_match_score = 999

        predicted_id = None

        # compare with ALL embeddings
        for i in range(len(X)):

            dist = np.linalg.norm(
                X[i] - encoding
            )

            if dist < best_match_score:

                best_match_score = dist

                predicted_id = Y[i]

        print(
            'predicted_id :- ',
            predicted_id
        )

        print(
            'best_match_score :- ',
            best_match_score
        )

        # ---------------- THRESHOLD ----------------

        threshold = 0.55

        if best_match_score < threshold:

            detected_students[
                predicted_id
            ] = True

    print(
        'detected_students :- ',
        detected_students
    )

    return (
        detected_students,
        all_students,
        len(encodings)
    )