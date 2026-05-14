from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import cv2
import easyocr
import numpy as np
import json
import os
from datetime import datetime
import time
import base64
import re
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

# --- MODELLER ---
model_plate = YOLO("weights/plate_model.pt")  # Plaka tespiti
model_char = YOLO("weights/char_model.pt")    # Karakter tanıma

reader = easyocr.Reader(['en'])

PARKING_FILE = 'data/parking_data.json'
os.makedirs('data', exist_ok=True)

# --- Veri Yönetimi ---
def load_parking_data():
    if not os.path.exists(PARKING_FILE):
        return {}
    try:
        with open(PARKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_parking_data(data):
    with open(PARKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

last_seen_time = {}         # kamera modunda plaka tekrarını önlemek için

# --- Yardımcı Fonksiyonlar ---

def clean_plate_text(text):
    text = text.upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    match = re.match(r"(\d{1,2})([A-Z]{1,3})(\d{2,4})", text)
    if not match:
        return text
    number_part, letter_part, final_number = match.groups()
    letter_part = (letter_part.replace('0','O').replace('1','I').replace('5','S').replace('8','B').replace('6','G'))
    number_part = number_part.replace('O','0').replace('I','1')
    final_number = final_number.replace('O','0').replace('I','1')
    return f"{number_part}{letter_part}{final_number}"

def class_id_to_char(class_id):
    mapping = {
        0:'0',1:'1',2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'8',9:'9',
        10:'A',11:'B',12:'C',13:'D',14:'E',15:'F',16:'G',17:'H',18:'I',
        19:'J',20:'K',21:'L',22:'M',23:'N',24:'O',25:'P',26:'R',27:'S',
        28:'T',29:'U',30:'V',31:'Y',32:'Z'
    }
    return mapping.get(class_id,'')

def warp_plate(plate_img):
    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)

    cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    for cnt in cnts:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)

        if len(approx) == 4:
            pts = approx.reshape(4, 2)
            break
    else:
        return plate_img

    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth-1, 0],
        [maxWidth-1, maxHeight-1],
        [0, maxHeight-1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(plate_img, M, (maxWidth, maxHeight))

    return warped

# --- Ana Görüntü İşleme ---
def process_frame(frame, mode="camera"):
    # Her işlemde dosyadan güncel veriyi oku
    parking_state = load_parking_data()
    
    detections = []
    now_ts = time.time()
    now_iso = datetime.now().isoformat()

    results = model_plate(frame)
    boxes = results[0].boxes.xyxy.tolist()

    for box in boxes:
        x1,y1,x2,y2 = map(int, box[:4])
        pad = 5
        x1,y1 = max(x1-pad,0), max(y1-pad,0)
        x2,y2 = min(x2+pad, frame.shape[1]), min(y2+pad, frame.shape[0])
        plate_crop = frame[y1:y2, x1:x2]
        if plate_crop.size==0: continue
        
        if mode == "camera":
            plate_crop = warp_plate(plate_crop)

        # Karakter tespiti
        char_results = model_char(plate_crop)
        char_boxes = char_results[0].boxes.xyxy.tolist()
        char_preds = char_results[0].boxes.cls.tolist()

        if len(char_boxes)==0:
            ocr_result = reader.readtext(plate_crop, detail=0)
            if not ocr_result: continue
            plate_text_raw = "".join(ocr_result)
        else:
            char_with_pos = sorted(zip(char_preds,char_boxes), key=lambda x:x[1][0])
            plate_text_raw = "".join([class_id_to_char(int(c)) for c,_ in char_with_pos])

        plate_text = clean_plate_text(plate_text_raw)
        if len(plate_text)<5: continue

        # --- FOTOĞRAF MODU ---
        if mode=="photo":
            entry_time = None
            if plate_text in parking_state:
                event="exit"
                entry_time = parking_state.pop(plate_text) # Çıkış yap ve sil
            else:
                event="entry"
                parking_state[plate_text] = now_iso # Giriş yap
                
            save_parking_data(parking_state) # Kaydet

            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
            cv2.putText(frame,plate_text,(x1,y1-10),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,0),2)
            _, buffer = cv2.imencode('.jpg', frame)
            annotated_b64 = base64.b64encode(buffer).decode('utf-8')
            
            det_obj = {
                'box':[x1,y1,x2,y2],
                'plate':plate_text,
                'event':event,
                'annotated_image':f"data:image/jpeg;base64,{annotated_b64}"
            }
            if event == 'exit' and entry_time:
                det_obj['entry_time'] = entry_time
            
            detections.append(det_obj)
            continue

        # --- KAMERA MODU ---
        # 3 saniye içinde tekrar okunmayı engelle
        last_time = last_seen_time.get(plate_text,0)
        if now_ts - last_time < 3:
            continue
        last_seen_time[plate_text] = now_ts

        entry_time = None
        if plate_text in parking_state:
            event="exit"
            entry_time = parking_state.pop(plate_text)
        else:
            event="entry"
            parking_state[plate_text] = now_iso

        save_parking_data(parking_state)

        det_obj = {'plate':plate_text,'event':event}
        if event == 'exit' and entry_time:
            det_obj['entry_time'] = entry_time
            
        detections.append(det_obj)

    return detections

# --- Ücret Tarife ---
def calculate_fee(minutes):
    if minutes<=15: return 0
    elif minutes<=60: return 50
    elif minutes<=180: return 100
    elif minutes<=360: return 200
    elif minutes<=540: return 400
    elif minutes<=720: return 750
    else: return 1000

# --- API ---
@app.route('/api/parked', methods=['GET'])
def get_parked_vehicles():
    # Her istekte dosyadan oku
    return jsonify(load_parking_data())

# --- FOTOĞRAF MODU ---
@app.route('/upload', methods=['POST'])
def upload_image():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error':'Görsel bulunamadı'}),400

    image_b64 = data['image']
    image_data = base64.b64decode(image_b64.split(',')[1])
    np_arr = np.frombuffer(image_data,np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    detections = process_frame(frame, mode="photo")
    if not detections:
        return jsonify({'status':'no_plate','message':'Plaka okunamadı'})

    return jsonify({'status':'ok','detections':detections})

# --- KAMERA MODU ---
@app.route('/camera', methods=['POST'])
def camera_feed():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error':'Görsel bulunamadı'}),400

    image_b64 = data['image']
    image_data = base64.b64decode(image_b64.split(',')[1])
    np_arr = np.frombuffer(image_data,np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    detections = process_frame(frame, mode="camera")
    if not detections:
        return jsonify({'status':'no_plate'})

    last_detection = detections[-1]
    
    response = {
        'status':'ok',
        'plate': last_detection.get('plate'),
        'event': last_detection.get('event'),
        'timestamp': datetime.now().strftime("%H:%M:%S")
    }
    if 'entry_time' in last_detection:
        response['entry_time'] = last_detection['entry_time']

    return jsonify(response)

# --- HTML ---
@app.route('/')
def index():
    return render_template('index.html')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=True,use_reloader=False)
