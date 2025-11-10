# 동영상 분석 + 위험도 판단
# LOW / MEDIUM / HIGH
# 탐지된 위험 물품의 등장 프레임이 길수록 위험도 UP

#YOLOv8 탐지 → 프레임별 cls, conf, bbox 수집
#track_memory 에 최근 5 프레임 기록 (연속성 체크)
#각 프레임마다 calculate_danger() 로 위험도 점수 산출
#위험도 HIGH 판정 시 즉시 트리거 (clip_triggered = True)
#트리거 발생 시점에서 10초 전 프레임 위치 기록 → 다음 Step 3에서 클립 추출 및 업로드


import os
import time
import json
from datetime import datetime
from collections import defaultdict, deque

import cv2
import requests
from ultralytics import YOLO

# ====== 환경 설정 ======
# Spring Boot 서버 주소 
BACKEND_BASE = os.getenv("BACKEND_URL", "http://localhost:8080")  # Spring Boot 서버


#################### 각자 로컬 환경에 맞게 수정 ####################
# YOLOv8 .pt 경로 (각자 로컬의 best.pt 파일 경로로 수정)
MODEL_PATH   = "C:\\Users\\ktg02\\CBNU\\3_2\\sanhak\\bodyCam\\object_detection\\SmartShield_results\\v3_merged_knife_gun_100epochs\\weights\\best.pt"
# 분석할 동영상 경로 (각자 로컬 환경에 맞게 수정)
VIDEO_PATH   = "C:\\Users\\ktg02\\CBNU\\3_2\\sanhak\\bodyCam\\object_detection\\contents\\video\\test1-2.mp4"
########################################################################


CAMERA_ID    = "demo01"                                  # 데모용 카메라 ID(임시)
DATE_PREFIX  = datetime.now().strftime("%Y%m%d")         # S3 키 prefix용(년/월/일)

# ====== 유틸 ======
def now_event_id() -> str:
    return f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def make_s3_key(event_id: str, camera_id: str, cls_: str, level: str) -> str:
    # {YYYYMMDD}/{camera}/clips/{event_id}_{class}_{level}.mp4
    return f"{DATE_PREFIX}/{camera_id}/clips/{event_id}_{cls_}_{level}.mp4"

# ====== Presigned URL / 업로드 / 완료 보고 ======
def request_presigned_url(s3_key: str):
    url = f"{BACKEND_BASE}/api/s3/presigned"
    r = requests.post(url, json={"fileName": s3_key}, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data["uploadUrl"], data["fileUrl"]

def upload_to_s3_with_retry(local_path: str, s3_key: str, max_retry: int = 1):
    attempt = 0
    while True:
        upload_url, file_url = request_presigned_url(s3_key)
        with open(local_path, "rb") as f:
            resp = requests.put(upload_url, data=f, timeout=300)
        if resp.status_code in (200, 201):
            return True, file_url
        if resp.status_code in (401, 403) and attempt < max_retry:
            attempt += 1
            time.sleep(1.0)
            continue
        raise RuntimeError(f"Upload failed: {resp.status_code} {resp.text}")

def notify_event_complete(event_id: str, camera_id: str, detected_class: str,
                          danger_level: str, file_url: str, meta: dict | None = None):
    url = f"{BACKEND_BASE}/api/event/complete"
    payload = {
        "event_id": event_id,
        "camera_id": camera_id,
        "detected_class": detected_class,  # "gun"/"knife"/"unknown"
        "danger_level": danger_level,      # "LOW"/"MEDIUM"/"HIGH"
        "file_url": file_url,
        "meta": meta or {}
    }
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    return r.json() if r.text else {"status": "ok"}
# ====== 클립 추출 ======
def save_clip(video_path: str, start_sec: float, end_sec: float | None, out_path: str):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 🔽 영상 크기 축소 (50%)
    scale = 0.5
    new_size = (int(width * scale), int(height * scale))

    start_frame = max(int(start_sec * fps), 0)
    end_frame   = total_frames if end_sec is None else min(int(end_sec * fps), total_frames)
    if end_frame <= start_frame:
        end_frame = min(total_frames, start_frame + int(3 * fps))  # 최소 3초 보장

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(out_path, fourcc, fps, new_size)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    cur = start_frame
    while cur < end_frame:
        ok, frame = cap.read()
        if not ok:
            break
        resized = cv2.resize(frame, new_size)
        out.write(resized)
        cur += 1

    out.release()
    cap.release()

    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError("Clip saving failed")

# ====== 위험도 계산 ======
def assess_risk(results, frame, model_names, memory, frame_idx):
    H, W = frame.shape[:2]
    objs = []
    for box in results[0].boxes:
        cls_id = int(box.cls[0])
        conf   = float(box.conf[0])
        name   = model_names[cls_id]
        xyxy   = box.xyxy[0].cpu().numpy()
        w      = xyxy[2] - xyxy[0]
        h      = xyxy[3] - xyxy[1]
        area_ratio = (w * h) / (W * H + 1e-6)
        memory[name].append((frame_idx, conf, area_ratio))
        continued = len(memory[name])
        objs.append({"cls": name, "conf": conf, "area": area_ratio, "continued": continued})

    score = 0
    main_cls = None
    for o in objs:
        if o["cls"] == "gun":
            score += 40; main_cls = main_cls or "gun"
        elif o["cls"] == "knife":
            score += 25; main_cls = main_cls or "knife"
        score += int(o["conf"] * 40)
        if o["continued"] >= 3:
            score += 10
        if o["area"] > 0.03:
            score += 10

    if score >= 70:
        return "HIGH", (main_cls or "unknown")
    if score >= 40:
        return "MEDIUM", (main_cls or "unknown")
    return "LOW", (main_cls or "unknown")

# ====== 메인 ======
def main():
    model = YOLO(MODEL_PATH)
    try:
        import torch
        if torch.cuda.is_available():
            model.to('cuda')
    except Exception:
        pass

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_idx = 0
    clip_triggered = False
    track_memory = defaultdict(lambda: deque(maxlen=5))

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1

        results = model(frame)
        level, main_cls = assess_risk(results, frame, model.names, track_memory, frame_idx)

        if level == "HIGH" and not clip_triggered:
            clip_triggered = True
            event_time_sec = frame_idx / fps
            clip_start_sec = max(0.0, event_time_sec - 10.0)

            event_id = now_event_id()
            primary  = (main_cls or "unknown").lower()
            level_s  = "high"

            os.makedirs("./clips", exist_ok=True)
            local_clip = f"./clips/{event_id}_{primary}_{level_s}.mp4"

            print(f"[ALERT] HIGH detected: cls={primary}, t={event_time_sec:.2f}s -> clip start {clip_start_sec:.2f}s")

            # 1) 클립 추출 (50% 크기)
            save_clip(VIDEO_PATH, clip_start_sec, None, local_clip)

            # 2) S3 키 생성
            s3_key = make_s3_key(event_id=event_id, camera_id=CAMERA_ID, cls_=primary, level=level_s)

            # 3) Presign → PUT 업로드(300초 제한)
            ok_upload, file_url = upload_to_s3_with_retry(local_clip, s3_key, max_retry=1)
            if not ok_upload:
                raise RuntimeError("S3 upload failed")

            # 4) 완료 보고(백엔드가 DB 저장 + SSE 알림)
            meta = {
                "fps": fps,
                "clip_start_sec": clip_start_sec,
                "clip_end_sec": None,
                "s3_key": s3_key,
                "source": os.path.basename(VIDEO_PATH)
            }
            resp = notify_event_complete(
                event_id=event_id,
                camera_id=CAMERA_ID,
                detected_class=primary,
                danger_level="HIGH",
                file_url=file_url,
                meta=meta
            )
            print("complete:", resp)

        annotated = results[0].plot()
        cv2.namedWindow("SmartShield Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("SmartShield Detection", 1280, 720)
        cv2.imshow("SmartShield Detection", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Done.")

if __name__ == "__main__":
    main()