"""
Face recognition webcam (Python 3.13 compatible)
- Default: SCRFD detector + ArcFace embeddings from insightface (no extra model files required)
- Optional: load your own MobileFaceNet PyTorch checkpoint (.pth) if you insist on MobileFaceNet
- Alignment: similarity transform from 5 landmarks -> crop 112x112
- Preprocess (MobileFaceNet): (x - 127.5) / 128
- Embedding: either insightface embedding (recommended) or MobileFaceNet forward
- Normalize: L2-normalize
- Compare: cosine similarity or L2 distance against embeddings DB
- Session login logic: auto-login on match, count warnings, pause session after max_warnings

Requirements:
- Python 3.13+
- pip install insightface opencv-python numpy torch scikit-learn

Files expected (defaults):
- embeddings.npy : N x D numpy array of saved reference embeddings
- names.json     : list of N names

Usage examples:
# use insightface builtin embeddings (recommended):
python face_recog.py --db_embeddings embeddings.npy --db_names names.json

# use your MobileFaceNet checkpoint (optional):
python face_recog.py --use_mobilefacenet --model_path mobilefacenet.pth --db_embeddings embeddings.npy --db_names names.json

"""

import cv2
import time
import json
import argparse
import numpy as np
import csv
from datetime import datetime
import torch
from pathlib import Path
from typing import Optional

# insightface for SCRFD detector + optional recognition
from insightface.app import FaceAnalysis
from sklearn.metrics.pairwise import cosine_similarity


# -------------------- utilities --------------------

def l2_norm(x, axis=1, eps=1e-10):
    norm = np.linalg.norm(x, axis=axis, keepdims=True)
    return x / np.maximum(norm, eps)


def preprocess_mobilefacenet(img_rgb, size=112):
    """RGB uint8 -> torch float 1x3x112x112"""
    img = cv2.resize(img_rgb, (size, size))
    x = img.astype(np.float32)
    x = (x - 127.5) / 128.0
    x = np.transpose(x, (2, 0, 1))
    x = np.expand_dims(x, 0)
    return torch.from_numpy(x).float()


def get_similarity_transform(src_pts, dst_pts):
    src = np.array(src_pts, dtype=np.float32)
    dst = np.array(dst_pts, dtype=np.float32)
    if src.shape[0] >= 3:
        M, _ = cv2.estimateAffinePartial2D(src, dst)
        return M
    raise ValueError('Need at least 3 points for transform')


def align_face(image_rgb, kps, output_size=112):
    # expect kps: [[lx,ly],[rx,ry],[nx,ny],[lm_x,lm_y],[rm_x,rm_y]]
    dst = np.array([
        [0.35 * output_size, 0.35 * output_size],  # left eye
        [0.65 * output_size, 0.35 * output_size],  # right eye
        [0.50 * output_size, 0.55 * output_size],  # nose
    ], dtype=np.float32)
    src = np.array([kps[0], kps[1], kps[2]], dtype=np.float32)
    M = get_similarity_transform(src, dst)
    warped = cv2.warpAffine(image_rgb, M, (output_size, output_size), flags=cv2.INTER_LINEAR)
    return warped


# -------------------- MobileFaceNet optional wrapper --------------------
class MobileFaceNetWrapper(torch.nn.Module):
    def __init__(self, model_path: str, device: str = 'cpu'):
        super().__init__()
        self.device = device
        loaded = torch.load(model_path, map_location=device)
        if isinstance(loaded, torch.nn.Module):
            self.model = loaded.to(device).eval()
        elif isinstance(loaded, dict):
            # try load state_dict into user-provided implementation
            try:
                from mobilefacenet_impl import MobileFaceNet
                net = MobileFaceNet()
                net.load_state_dict(loaded)
                self.model = net.to(device).eval()
            except Exception:
                if 'model' in loaded and isinstance(loaded['model'], torch.nn.Module):
                    self.model = loaded['model'].to(device).eval()
                else:
                    raise RuntimeError('Cannot load MobileFaceNet checkpoint. Provide scripted module or state_dict plus \"mobilefacenet_impl.py\"')
        else:
            try:
                self.model = loaded.to(device).eval()
            except Exception as e:
                raise RuntimeError(f'Unsupported model file: {e}')

    def forward(self, x: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            out = self.model(x.to(self.device))
            if isinstance(out, torch.Tensor):
                out = out.detach().cpu().numpy()
            return out


# -------------------- matching helper --------------------

def get_best_match(emb: np.ndarray, db_emb: np.ndarray, names: list, metric: str = 'cosine'):
    # emb: 1D normalized
    if metric == 'cosine':
        sims = db_emb @ emb.reshape(-1,1)
        sims = sims.reshape(-1)
        idx = int(np.argmax(sims))
        return names[idx], float(sims[idx]), idx
    else:
        dists = np.linalg.norm(db_emb - emb, axis=1)
        idx = int(np.argmin(dists))
        return names[idx], float(dists[idx]), idx


# -------------------- main app --------------------

def main(args):
    # CSV logging (B1 - ghi mỗi khung hình)
    csv_file = 'recognition_log.csv'
    csv_exists = Path(csv_file).exists()

    csv_f = open(csv_file, 'a', newline='', encoding='utf-8')
    csv_writer = csv.writer(csv_f)
    if not csv_exists:
        csv_writer.writerow(['time','frame_id','name','score','matched','warnings','session_active'])
    device = 'cuda' if torch.cuda.is_available() and not args.force_cpu else 'cpu'

    print('Preparing detector + recognition (insightface SCRFD + ArcFace) ...')
    # Load detector and recognition by default. insightface will download models on first run.
    # allowed_modules None => detection+recognition
    app = FaceAnalysis(provider=['CPUExecutionProvider'] if device=='cpu' else None)
    app.prepare(ctx_id=0, det_size=(640,640))

    mobile_net: Optional[MobileFaceNetWrapper] = None
    if args.use_mobilefacenet:
        if not Path(args.model_path).exists():
            raise FileNotFoundError(f"MobileFaceNet model not found: {args.model_path}")
        print('Loading MobileFaceNet checkpoint...')
        mobile_net = MobileFaceNetWrapper(args.model_path, device=device)

    print('Loading database embeddings...')
    db_emb = np.load(args.db_embeddings)
    with open(args.db_names, 'r', encoding='utf-8') as f:
        names = json.load(f)
    if db_emb.ndim != 2 or len(names) != db_emb.shape[0]:
        raise ValueError('embeddings.npy must be shape (N,D) and names.json length N')

    # normalize DB
    db_emb = l2_norm(db_emb, axis=1)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError('Cannot open camera')

    session_active = True
    warnings_count = 0
    logged_in_user = None

    print('Start camera. Press q to quit, r to reset session')
    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = app.get(img_rgb)  # returns list of Face objects with bbox, kps, embedding (if model loaded)

        display = frame.copy()

        for face in faces:
            frame_id += 1
            # face.bbox: [x1,y1,x2,y2]
            try:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            except Exception:
                continue

            # landmarks (x,y)
            kps = None
            try:
                kps = np.array(face.kps, dtype=np.float32)
            except Exception:
                kps = None

            if kps is None or kps.shape[0] < 3:
                # fallback crop
                x1c = max(0, x1); y1c = max(0, y1); x2c = min(frame.shape[1], x2); y2c = min(frame.shape[0], y2)
                crop = img_rgb[y1c:y2c, x1c:x2c]
                aligned = cv2.resize(crop, (112,112))
            else:
                aligned = align_face(img_rgb, kps, output_size=112)

            if mobile_net is not None:
                tensor = preprocess_mobilefacenet(aligned)
                emb = mobile_net(tensor).reshape(-1)
                emb = emb / (np.linalg.norm(emb) + 1e-10)
            else:
                # use insightface's own embedding if available
                try:
                    emb = np.array(face.embedding, dtype=np.float32)
                    emb = emb / (np.linalg.norm(emb) + 1e-10)
                except Exception:
                    # If insightface recognition wasn't loaded, compute via app.get with model by re-querying
                    # As a fallback, compute embedding by running app.get on the aligned patch (not ideal but works)
                    temp = app.get(aligned)
                    if len(temp) > 0 and hasattr(temp[0], 'embedding'):
                        emb = np.array(temp[0].embedding, dtype=np.float32)
                        emb = emb / (np.linalg.norm(emb) + 1e-10)
                    else:
                        continue

            # compare
            name, score, idx = get_best_match(emb, db_emb, names, metric=args.metric)
            if args.metric == 'cosine':
                matched = score >= args.threshold
                score_text = f'{score:.3f}'
            else:
                matched = score <= args.threshold
                score_text = f'{score:.3f}'

            color = (0,255,0) if matched else (0,0,255)
            label = name if matched else 'UNKNOWN'

            # session logic
            if session_active:
                if matched:
                    if logged_in_user is None:
                        logged_in_user = name
                        print(f'User {name} logged in')
                else:
                    warnings_count += 1
                    print(f'Warning #{warnings_count}')
                    if warnings_count >= args.max_warnings:
                        session_active = False
                        print('Session paused due to repeated failed attempts')

            # --- CSV LOGGING B1: ghi mỗi frame ---
            csv_writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                frame_id,
                name,
                score,
                matched,
                warnings_count,
                session_active
            ])

            # draw
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display, f'{label} {score_text}', (x1, max(15,y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.putText(display, f'Session: {"ACTIVE" if session_active else "PAUSED"}', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255),2)
        cv2.putText(display, f'Warnings: {warnings_count}', (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255),2)
        cv2.putText(display, f'User: {logged_in_user if logged_in_user else "-"}', (10,90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0),2)

        # show frame first
        cv2.imshow('Face Recognition', display)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord('r'):
            session_active = True
            warnings_count = 0
            logged_in_user = None
            print('Session reset')

        # # auto-exit AFTER showing frame — but DO NOT reset login; just close camera
        if logged_in_user is not None and matched:
            time.sleep(0.3)
            break

        cv2.imshow('Face Recognition', display)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord('r'):
            session_active = True
            warnings_count = 0
            logged_in_user = None
            print('Session reset')

    csv_f.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--use_mobilefacenet', action='store_true', help='Load and use MobileFaceNet model instead of insightface embedding')
    parser.add_argument('--model_path', type=str, default='mobilefacenet.pth')
    parser.add_argument('--db_embeddings', type=str, default='embeddings.npy')
    parser.add_argument('--db_names', type=str, default='names.json')
    parser.add_argument('--threshold', type=float, dest='threshold', default=0.35)
    parser.add_argument('--metric', type=str, default='cosine', choices=['cosine','l2'])
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--force_cpu', action='store_true')
    parser.add_argument('--max_warnings', type=int, default=3)
    args = parser.parse_args()

    while True:
        main(args)
        print("Logged in, waiting 30 minutes before next check...")
        time.sleep(5)
