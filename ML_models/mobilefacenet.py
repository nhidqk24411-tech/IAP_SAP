# FILE: mobilefacenet.py
import cv2
import numpy as np
import torch

# -------------------- utilities --------------------

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

# -------------------- MobileFaceNet Wrapper --------------------
class MobileFaceNetWrapper(torch.nn.Module):
    def __init__(self, model_path: str, device: str = 'cpu'):
        super().__init__()
        self.device = device
        try:
            loaded = torch.load(model_path, map_location=device)
            if isinstance(loaded, torch.nn.Module):
                self.model = loaded.to(device).eval()
            elif isinstance(loaded, dict) and 'model' in loaded:
                 self.model = loaded['model'].to(device).eval()
            else:
                 # Fallback basic load
                 self.model = loaded.to(device).eval()
        except Exception as e:
            print(f"Warning loading MobileFaceNet: {e}")
            raise e

    def forward(self, x: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            out = self.model(x.to(self.device))
            if isinstance(out, torch.Tensor):
                out = out.detach().cpu().numpy()
            return out