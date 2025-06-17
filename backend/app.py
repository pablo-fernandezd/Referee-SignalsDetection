from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os
from models.inference import detect_referee, detect_signal
import cv2
import numpy as np
from datetime import datetime
import hashlib

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your_very_secret_key_here' # **IMPORTANT: Change this to a strong, random key in production**

# Configuración de rutas
UPLOAD_FOLDER = os.path.join('static', 'uploads')
CROPS_FOLDER = os.path.join('static', 'referee_crops')
SIGNALS_FOLDER = os.path.join('static', 'signals')

# Nuevas carpetas para datos de entrenamiento etiquetados
REFEREE_TRAINING_DATA_FOLDER = os.path.join('data', 'referee_training_data')
SIGNAL_TRAINING_DATA_FOLDER = os.path.join('data', 'signal_training_data')

# Path for the image hash registry
IMAGE_HASH_REGISTRY = os.path.join('data', 'image_hashes.txt')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CROPS_FOLDER, exist_ok=True)
os.makedirs(SIGNALS_FOLDER, exist_ok=True)
os.makedirs(REFEREE_TRAINING_DATA_FOLDER, exist_ok=True)
os.makedirs(SIGNAL_TRAINING_DATA_FOLDER, exist_ok=True)

# Ensure the hash registry file exists
if not os.path.exists(IMAGE_HASH_REGISTRY):
    with open(IMAGE_HASH_REGISTRY, 'w') as f:
        pass # Create an empty file if it doesn't exist

# Helper functions for hash management
def calculate_image_hash(image_path):
    """Calculates the MD5 hash of an image file."""
    with open(image_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def is_hash_registered(image_hash):
    """Checks if an image hash is already registered."""
    with open(IMAGE_HASH_REGISTRY, 'r') as f:
        return image_hash in f.read()

def register_hash(image_hash):
    """Registers a new image hash."""
    with open(IMAGE_HASH_REGISTRY, 'a') as f:
        f.write(image_hash + '\n')

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Recibe una imagen y la guarda temporalmente para procesar."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    filename = file.filename
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)
    # Detectar árbitro y guardar crop temporal
    crop_filename = f"temp_crop_{filename}" # Temporal crop
    crop_path = os.path.join(CROPS_FOLDER, crop_filename)
    result = detect_referee(upload_path, crop_save_path=crop_path)
    if result['detected']:
        # Store original filename for later use in manual_crop if needed
        session['original_filename'] = filename # Use Flask session to pass original filename
        return jsonify({'filename': filename, 'crop_filename': crop_filename, 'crop_url': f'/api/crop/{crop_filename}', 'bbox': result['bbox']})
    else:
        session['original_filename'] = filename # Still store for manual crop
        return jsonify({'error': 'No referee detected', 'filename': filename}), 404

@app.route('/api/crop/<filename>', methods=['GET'])
def get_crop(filename):
    """Devuelve el crop generado por el modelo de árbitro."""
    return send_from_directory(CROPS_FOLDER, filename)

@app.route('/api/confirm_crop', methods=['POST'])
def confirm_crop():
    """El usuario confirma si el crop es correcto. Si sí, se guarda para entrenamiento futuro."""
    data = request.json
    original_filename = data.get('original_filename') # Get original filename
    crop_filename = data.get('crop_filename')
    bbox = data.get('bbox')

    # Calculate hash of the original uploaded image
    original_img_path = os.path.join(UPLOAD_FOLDER, original_filename)
    if not os.path.exists(original_img_path):
        return jsonify({'error': 'Original image not found for hashing.'}), 404

    original_image_hash = calculate_image_hash(original_img_path)

    if is_hash_registered(original_image_hash):
        print(f"[INFO] Image with hash {original_image_hash} already processed. Skipping saving.")
        # If the image is already processed, we still want to proceed to signal detection
        # We need to return the filename that would have been created if it wasn't a duplicate
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f") # Generate a temporary timestamp just for filename consistency
        temp_dest_filename = f"referee_auto_{original_filename.rsplit('.', 1)[0]}_{timestamp}.png"
        return jsonify({'status': 'ok', 'crop_filename_for_signal': temp_dest_filename, 'message': 'Image already processed.'})

    # Guardar el crop confirmado en la carpeta de entrenamiento de árbitros
    if crop_filename and original_filename and bbox:
        # Move the crop from temp to permanent training folder with a unique timestamp
        src_path = os.path.join(CROPS_FOLDER, crop_filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f") # Add microseconds for higher uniqueness
        dest_filename = f"referee_auto_{original_filename.rsplit('.', 1)[0]}_{timestamp}.png"
        dest_path = os.path.join(REFEREE_TRAINING_DATA_FOLDER, dest_filename)

        try:
            os.rename(src_path, dest_path)
        except FileExistsError:
            print(f"[WARNING] confirm_crop: Destination file already exists: {dest_path}. This should be prevented by hashing.")
            return jsonify({'error': 'File already exists after hashing check. Investigate.'}), 500

        # Save YOLO label for referee (class_id 0 for referee)
        original_img = cv2.imread(original_img_path)
        h, w = original_img.shape[:2]
        x1, y1, x2, y2 = bbox
        x_center = ((x1 + x2) / 2) / w
        y_center = ((y1 + y2) / 2) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        yolo_line = f"0 {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}\n" # Class ID 0 for referee
        label_filename = dest_filename.rsplit('.', 1)[0] + '.txt'
        label_path = os.path.join(REFEREE_TRAINING_DATA_FOLDER, label_filename)
        with open(label_path, 'w') as f:
            f.write(yolo_line)
        
        # Register the hash after successful saving
        register_hash(original_image_hash)

    # Continue to signal detection for this confirmed crop
    return jsonify({'status': 'ok', 'crop_filename_for_signal': dest_filename})

@app.route('/api/referee_crop_image/<filename>', methods=['GET'])
def get_referee_crop_image(filename):
    """Devuelve la imagen del crop del árbitro para visualización."""
    return send_from_directory(REFEREE_TRAINING_DATA_FOLDER, filename)

@app.route('/api/process_signal', methods=['POST'])
def process_signal():
    """Procesa el crop por el modelo de señales y devuelve la predicción."""
    data = request.json
    # Now, crop_filename_for_signal refers to the path in REFEREE_TRAINING_DATA_FOLDER
    crop_filename = data.get('crop_filename_for_signal')
    crop_path = os.path.join(REFEREE_TRAINING_DATA_FOLDER, crop_filename)
    
    # Ensure the image exists before processing
    if not os.path.exists(crop_path):
        return jsonify({'error': f'Image not found: {crop_path}'}), 404

    result = detect_signal(crop_path)
    # Ensure bbox_xywhn is included in the response even if not detected
    return jsonify({
        'predicted_class': result.get('predicted_class'),
        'confidence': result.get('confidence'),
        'bbox_xywhn': result.get('bbox_xywhn')
    })

@app.route('/api/confirm_signal', methods=['POST'])
def confirm_signal():
    """El usuario confirma o corrige la predicción de señal."""
    data = request.json
    crop_filename_for_signal = data.get('crop_filename_for_signal') # This is the referee crop
    selected_class = data.get('selected_class')
    # New: Get the signal_bbox_yolo from the frontend, if available
    signal_bbox_yolo = data.get('signal_bbox_yolo') 

    # Get original filename from session (set during upload)
    original_filename = session.get('original_filename')
    if not original_filename:
        return jsonify({'error': 'Original filename not found in session.'}), 400

    original_img_path = os.path.join(UPLOAD_FOLDER, original_filename)
    if not os.path.exists(original_img_path):
        return jsonify({'error': 'Original image not found for hashing in signal confirmation.'}), 404

    original_image_hash = calculate_image_hash(original_img_path)

    if is_hash_registered(original_image_hash):
        print(f"[INFO] Original image (hash: {original_image_hash}) associated with this signal already processed. Skipping saving signal data.")
        return jsonify({'status': 'ok', 'message': 'Image already processed. Signal data not saved to prevent duplication.'})

    # Load the referee crop (image that was sent to signal detection)
    referee_crop_path = os.path.join(REFEREE_TRAINING_DATA_FOLDER, crop_filename_for_signal)
    referee_crop_img = cv2.imread(referee_crop_path)

    if referee_crop_img is None:
        return jsonify({'error': 'Referee crop image not found for signal confirmation'}), 404

    # Save the referee crop image and its signal label in SIGNAL_TRAINING_DATA_FOLDER
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f") # Add microseconds for higher uniqueness
    signal_dest_filename = f"signal_{crop_filename_for_signal.replace('referee_auto_', '').replace('referee_manual_', '').rsplit('.', 1)[0]}_{timestamp}.png"
    signal_dest_path = os.path.join(SIGNAL_TRAINING_DATA_FOLDER, signal_dest_filename)

    cv2.imwrite(signal_dest_path, referee_crop_img) # Save the referee crop

    # Get the class ID for the selected_class from inference.py's SIGNAL_CLASSES
    from models.inference import SIGNAL_CLASSES # Import SIGNAL_CLASSES from inference module
    class_id_for_yolo = SIGNAL_CLASSES.index(selected_class) if selected_class != 'none' else -1

    if class_id_for_yolo != -1: # Only save label if a valid class was selected
        # Use the provided signal_bbox_yolo if available, otherwise use a default (or handle appropriately)
        if signal_bbox_yolo: # If a specific bounding box was provided for the signal
            x_center, y_center, bw, bh = signal_bbox_yolo
        else: # Fallback to full image if no specific bbox is provided (e.g., for classification-like signals)
            x_center, y_center, bw, bh = 0.5, 0.5, 1.0, 1.0 # Full image bbox
            print("[WARNING] confirm_signal: No signal_bbox_yolo provided. Saving full image bbox for signal label.")

        yolo_line = f"{class_id_for_yolo} {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}\n"
        signal_label_filename = signal_dest_filename.rsplit('.', 1)[0] + '.txt'
        signal_label_path = os.path.join(SIGNAL_TRAINING_DATA_FOLDER, signal_label_filename)
        with open(signal_label_path, 'w') as f:
            f.write(yolo_line)
    
    # Register the hash after successful saving of signal and its label
    register_hash(original_image_hash)

    return jsonify({'status': 'ok'})

@app.route('/api/manual_crop', methods=['POST'])
def manual_crop():
    """
    Recibe la imagen original, las coordenadas del recorte y la clase seleccionada.
    Guarda el crop y la anotación en formato YOLO.
    """
    data = request.json
    original_filename = data.get('filename') # This is the original uploaded filename
    bbox = data.get('bbox', [0, 0, 0, 0])
    class_id = data.get('class_id')

    # Calculate hash of the original uploaded image
    original_img_path = os.path.join(UPLOAD_FOLDER, original_filename)
    if not os.path.exists(original_img_path):
        return jsonify({'error': 'Original image not found for hashing.'}), 404

    original_image_hash = calculate_image_hash(original_img_path)

    if is_hash_registered(original_image_hash):
        print(f"[INFO] Image with hash {original_image_hash} already processed via manual crop. Skipping saving.")
        # If the image is already processed, we still want to proceed to signal detection
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f") # Generate a temporary timestamp just for filename consistency
        temp_manual_crop_filename = f"referee_manual_{original_filename.rsplit('.', 1)[0]}_{timestamp}.png"
        return jsonify({'status': 'ok', 'crop_filename_for_signal': temp_manual_crop_filename, 'message': 'Image already processed.'})

    # Read original image
    img_path = os.path.join(UPLOAD_FOLDER, original_filename)
    img = cv2.imread(img_path)

    # Crop the image
    x1, y1, x2, y2 = bbox
    cropped_img = img[y1:y2, x1:x2]

    # Ensure the manually cropped image is also resized to MODEL_SIZE for signal detection consistency
    from models.inference import MODEL_SIZE # Import MODEL_SIZE from inference module
    if cropped_img.shape[0] > 0 and cropped_img.shape[1] > 0:
        resized_cropped_img = cv2.resize(cropped_img, (MODEL_SIZE, MODEL_SIZE))
    else:
        return jsonify({'error': 'Invalid manual crop dimensions'}), 400

    # Generate a unique filename for the manually cropped referee image
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f") # Add microseconds for higher uniqueness
    manual_crop_filename = f"referee_manual_{original_filename.rsplit('.', 1)[0]}_{timestamp}.png"
    manual_crop_path = os.path.join(REFEREE_TRAINING_DATA_FOLDER, manual_crop_filename)
    cv2.imwrite(manual_crop_path, resized_cropped_img) # Save the resized image

    # Save YOLO label for the manually cropped referee
    if class_id != -1: # Only save label if a class was selected (not 'none')
        h, w = img.shape[:2]
        x_center = ((x1 + x2) / 2) / w
        y_center = ((y1 + y2) / 2) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        yolo_line = f"{class_id} {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}\n"
        label_filename = manual_crop_filename.rsplit('.', 1)[0] + '.txt'
        label_path = os.path.join(REFEREE_TRAINING_DATA_FOLDER, label_filename)
        with open(label_path, 'w') as f:
            f.write(yolo_line)
    
    # Register the hash after successful saving
    register_hash(original_image_hash)

    # Return the path to the newly created manual crop for signal processing
    return jsonify({'status': 'ok', 'crop_filename_for_signal': manual_crop_filename})

if __name__ == '__main__':
    app.run(debug=True) 