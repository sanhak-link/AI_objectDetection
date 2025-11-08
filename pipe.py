import cv2
import os

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
