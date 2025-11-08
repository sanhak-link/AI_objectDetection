import cv2
import os
import requests


#path = 분석 대상 원본 동영상 파일 경로
def save_clip(video_path, start_sec, end_sec, out_path):
    cap = cv2.VideoCapture(video_path) 
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    start_frame = max(int(start_sec * fps), 0)
    end_frame = total_frames if end_sec is None else min(int(end_sec * fps), total_frames)

    # VideoWriter 설정 (mp4v 코덱)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    cur = start_frame
    while cur < end_frame:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        cur += 1

    out.release()
    cap.release()
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError("Clip saving failed")
# 백엔드의 /api/s3/presigned로 파일 키를 보내고, 업로드 URL과 조회 URL을 받는다.
# {YYYYMMDD}/{camera_id}/clips/{event_id}_{class}_{level}.mp4
# 예: 20251108/demo01/clips/evt_20251108_0004_gun_high.mp4


BACKEND_BASE = "http://localhost:8080"

def request_presigned_url(s3_key: str):
    url = f"{BACKEND_BASE}/api/s3/presigned"
    body = {"fileName": s3_key}
    r = requests.post(url, json=body, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data["uploadUrl"], data["fileUrl"]