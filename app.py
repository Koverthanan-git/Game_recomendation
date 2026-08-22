import os
from flask import Flask, request, render_template, jsonify
from PIL import Image
import numpy as np
from tensorflow.keras.models import load_model

app = Flask(__name__)

# Load your pre-trained CNN model
model = load_model('model/product_model.h5')

# Directory to save uploaded images
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Preprocess the image for the model
def prepare_image(image, target_size=(224, 224)):
    image = image.resize(target_size)
    image = np.asarray(image) / 255.0
    image = np.expand_dims(image, axis=0)
    return image

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file:
        # Save the uploaded file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Open and preprocess the image
        image = Image.open(file)
        prepared_image = prepare_image(image)

        # Make prediction
        predictions = model.predict(prepared_image)
        result = np.argmax(predictions, axis=1)
        product_type = "GPU" if result == 0 else "CPU"

        # Render the result page with the image and prediction
        return render_template('result.html', product_type=product_type, image_path=file_path)

if __name__ == '__main__':
    app.run(debug=True)