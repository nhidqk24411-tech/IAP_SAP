# FILE: main.py
"""
Face Recognition System Entry Point
- Tích hợp InsightFace (Detector)
- Tích hợp MobileFaceNet (Optional Recognizer)
- Tích hợp FaceEngine (Logic so khớp & quản lý DB)
"""

import cv2
import argparse
import numpy as np
import csv
import time
from datetime import datetime
from pathlib import Path
import torch

# Import các modules "ngầm"
from insightface.app import FaceAnalysis
from face_engine import FaceRecognitionML  # Logic so khớp
import mobilefacenet as mbf  # Logic MobileFaceNet & Align


def main(args):
    # 1. Khởi tạo Logging CSV
    csv_file = 'recognition_log.csv'
    csv_exists = Path(csv_file).exists()
    csv_f = open(csv_file, 'a', newline='', encoding='utf-8')
    csv_writer = csv.writer(csv_f)
    if not csv_exists:
        csv_writer.writerow(['time', 'frame_id', 'name', 'score', 'matched', 'warnings', 'session_active'])

    # 2. Cấu hình thiết bị (CPU/GPU)
    device = 'cuda' if torch.cuda.is_available() and not args.force_cpu else 'cpu'
    print(f'Running on: {device}')

    # 3. Load Detector (InsightFace)
    print('Initializing Face Detector (SCRFD)...')
    # providers: ['CUDAExecutionProvider'] nếu có GPU, hoặc ['CPUExecutionProvider']
    providers = ['CPUExecutionProvider'] if device == 'cpu' else ['CUDAExecutionProvider', 'CPUExecutionProvider']
    app = FaceAnalysis(providers=providers)
    app.prepare(ctx_id=0, det_size=(640, 640))

    # 4. Load Recognizer (MobileFaceNet hoặc InsightFace ArcFace)
    mobile_net = None
    if args.use_mobilefacenet:
        if not Path(args.model_path).exists():
            raise FileNotFoundError(f"MobileFaceNet model not found: {args.model_path}")
        print(f'Loading MobileFaceNet from {args.model_path}...')
        mobile_net = mbf.MobileFaceNetWrapper(args.model_path, device=device)
    else:
        print('Using InsightFace built-in ArcFace embeddings.')

    # 5. Load Database (FaceEngine)
    print('Loading Face Database...')
    try:
        face_engine = FaceRecognitionML(
            db_embeddings_path=args.db_embeddings,
            db_names_path=args.db_names,
            db_ids_path='ids.json'  # File này do retrieve.py tạo ra
        )
    except Exception as e:
        print(f"Error loading database: {e}")
        return

    # 6. Mở Camera
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError('Cannot open camera')

    # Biến quản lý Session
    session_active = True
    warnings_count = 0
    logged_in_user = None
    frame_id = 0
    current_matched = False

    print('\nSYSTEM READY. Press "q" to quit, "r" to reset session.\n')

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # DETECT FACES
        faces = app.get(img_rgb)

        display = frame.copy()
        current_matched = False

        for face in faces:
            frame_id += 1
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]

            # Xử lý Embedding
            emb = None

            # --- Trường hợp 1: Dùng MobileFaceNet ---
            if mobile_net is not None:
                # Cần align và preprocess
                kps = face.kps
                if kps is not None:
                    aligned = mbf.align_face(img_rgb, kps)
                    tensor = mbf.preprocess_mobilefacenet(aligned)
                    emb = mobile_net(tensor).reshape(-1)
                else:
                    continue  # Không có landmarks thì bỏ qua

            # --- Trường hợp 2: Dùng InsightFace có sẵn ---
            else:
                if hasattr(face, 'embedding'):
                    emb = face.embedding
                else:
                    continue

            # MATCHING (Gọi sang face_engine)
            if emb is not None:
                # Gọi hàm match_face từ module face_engine
                match_result = face_engine.match_face(emb, threshold=args.threshold)

                best_match = match_result['best_match']

                # Phân tích kết quả
                if best_match and best_match['matched']:
                    name = best_match['name']
                    score = best_match['similarity']
                    matched = True
                else:
                    # Nếu có best_match nhưng dưới threshold
                    name = best_match['name'] if best_match else "Unknown"
                    score = best_match['similarity'] if best_match else 0.0
                    matched = False

                # Xử lý hiển thị
                color = (0, 255, 0) if matched else (0, 0, 255)
                label = f"{name}" if matched else "UNKNOWN"
                score_text = f"{score:.2f}"

                # LOGIC SESSION
                if session_active:
                    if matched:
                        if logged_in_user is None:
                            logged_in_user = name
                            print(f'[LOGIN] User verified: {name}')
                    else:
                        warnings_count += 1
                        # print(f'Warning #{warnings_count}') # Uncomment nếu muốn spam console
                        if warnings_count >= args.max_warnings:
                            session_active = False
                            print('[SESSION] Paused due to repeated failed attempts')

                current_matched = current_matched or matched

                # Ghi Log CSV
                csv_writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    frame_id, label, score_text, matched, warnings_count, session_active
                ])

                # Vẽ lên màn hình
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display, f'{label} ({score_text})', (x1, max(15, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Hiển thị HUD
        cv2.putText(display, f'Session: {"ACTIVE" if session_active else "PAUSED"}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(display, f'Warnings: {warnings_count}/{args.max_warnings}', (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(display, f'User: {logged_in_user if logged_in_user else "-"}', (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow('Main Face Recognition System', display)

        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord('r'):
            session_active = True
            warnings_count = 0
            logged_in_user = None
            print('[SESSION] Reset manually.')

        # Logic: Tự động thoát khi đã đăng nhập thành công (tùy chọn)
        if logged_in_user is not None and current_matched:
            # time.sleep(1.0) # Delay 1 chút để người dùng thấy khung xanh
            # break # Uncomment dòng này nếu muốn chương trình tự tắt sau khi nhận diện
            pass

    csv_f.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Main Entry Point for Face Recognition")

    # Các tham số cấu hình
    parser.add_argument('--use_mobilefacenet', action='store_true',
                        help='Use external MobileFaceNet model instead of InsightFace')
    parser.add_argument('--model_path', type=str, default='mobilefacenet.pth',
                        help='Path to .pth file if using MobileFaceNet')

    parser.add_argument('--db_embeddings', type=str, default='embeddings.npy')
    parser.add_argument('--db_names', type=str, default='names.json')

    parser.add_argument('--threshold', type=float, default=0.35, help="Similarity threshold")
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--force_cpu', action='store_true')
    parser.add_argument('--max_warnings', type=int, default=50, help="Number of unknown frames before pause")

    args = parser.parse_args()

    # Chế độ vòng lặp (giống code cũ của bạn: đợi 30p sau khi xong session)
    # Nếu chỉ muốn chạy 1 lần rồi tắt, bỏ vòng while bên dưới đi
    while True:
        main(args)
        print("System Standby. Restarting in 3 seconds (Demo mode)...")
        # Code gốc của bạn đợi 1800s, tôi để 3s để dễ test, bạn sửa lại thành 1800 nếu muốn
        time.sleep(3)