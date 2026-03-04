import os
import numpy as np
import cv2
from flask import Flask, request, render_template, redirect, url_for
from tensorflow.keras.models import load_model # type: ignore
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input # type: ignore
from werkzeug.utils import secure_filename
import base64
import logging
import os as _os

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
# Try common locations for the model file inside the repository
MODEL_PATHS = [
    os.path.join(BASE_DIR, "Blood Cell.h5"),
    os.path.join(BASE_DIR, "project requriments", "Blood Cell.h5"),
    os.path.join(BASE_DIR, "project requriments", "BloodCell.h5"),
]
model = None
for p in MODEL_PATHS:
    if os.path.exists(p):
        try:
            model = load_model(p)
            logging.info(f"Loaded model from {p}")
            break
        except Exception as e:
            logging.exception(f"Failed loading model from {p}: {e}")
if model is None:
    logging.warning("Model not found. Predictions will fail until a valid model path is provided.")

class_labels = ['eosinophil', 'lymphocyte', 'monocyte', 'neutrophil']

def predict_image_class(image_path, model):
    if model is None:
        raise RuntimeError("Model is not loaded")
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_AREA)
    img_preprocessed = preprocess_input(img_resized.reshape((1, 224, 224, 3)).astype('float32'))
    predictions = model.predict(img_preprocessed)
    predicted_class_idx = int(np.argmax(predictions, axis=1)[0])
    predicted_class_label = class_labels[predicted_class_idx]
    return predicted_class_label, img_rgb

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        if file:
            uploads_dir = os.path.join(BASE_DIR, "static")
            os.makedirs(uploads_dir, exist_ok=True)
            filename = secure_filename(file.filename)
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)
            try:
                predicted_class_label, img_rgb = predict_image_class(file_path, model)
            except Exception as e:
                logging.exception("Prediction failed")
                return render_template("home.html", error=str(e))

            _, img_encoded = cv2.imencode('.png', cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
            img_str = base64.b64encode(img_encoded).decode('utf-8')

            return render_template("result.html", class_label=predicted_class_label, img_data=img_str)
    return render_template("home.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
