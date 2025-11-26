import os
import time
from datetime import datetime
from collections import defaultdict, deque

import cv2
import requests
from ultralytics import YOLO

# 🔹 추가: 실시간 스트림용 Flask + 스레드
from flask import Flask, Response
import threading

# ====== Flask 앱 / 전역 프레임 버퍼 ======
app = Flask(__name__)

latest_frame = None
latest_frame_lock = threading.Lock()


def generate_mjpeg():
    """
    latest_frame에 저장된 '라벨 없는 원본 프레임'을
    MJPEG 형식으로 계속 내보내는 제너레이터
    """
    global latest_frame
    while True:
        with latest_frame_lock:
            frame = None if latest_frame is None else latest_frame.copy()

        if frame is None:
            time.sleep(0.05)
            continue

        ret, jpeg = cv2.imencode(".jpg", frame)
        if not ret:
            continue
        data = jpeg.tobytes()

        # MJPEG 포맷
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
        )
        time.sleep(0.05)  # 너무 과도하게 보내지 않도록 약간 딜레이


@app.route("/live")
def live_stream():
    return Response(
        generate_mjpeg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


def start_flask_server():
    # 로컬에서만 쓸 거라 0.0.0.0/5001 고정
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)


# ====== 환경 설정 ======
BACKEND_BASE = os.getenv("BACKEND_URL", "http://localhost:8080")

# YOLO 모델 경로
MODEL_PATH = (
    "C:\\Users\\ktg02\\CBNU\\3_2\\sanhak\\bodyCam\\object_detection\\SmartShield_results\\v3_merged_knife_gun_100epochs\\weights\\best.pt"
)

# 사용할 카메라 인덱스 (0: 기본 내장)
CAM_INDEX = 1

CAMERA_ID   = "live_demo_cam"
DATE_PREFIX = datetime.now().strftime("%Y%m%d")

# 라이브 클립 설정: 이전 10초 + 이후 3초
CLIP_PRE_SEC   = 10.0
CLIP_POST_SEC  = 3.0
BUFFER_MAX_SEC = 15.0    # ring buffer 보관 최대 길이

# 클립 인코딩용 FPS (스트림 FPS 대신 고정값 사용)
CLIP_FPS = 15.0

# ====== 위험도 판단 설정값 ======
CLASS_WEIGHTS = {
    "gun":         50,
    "knife":       35,
    "blood_stain": 30,
    "fighting":    25,
}

LEVEL_THRESHOLDS = {
    "MEDIUM": 40.0,
    "HIGH":   70.0,
}

HISTORY_SECONDS   = 3.0
COMBO_WINDOW_SEC  = 2.0
AREA_THRESHOLDS   = [
    (0.05, 20),
    (0.02, 10),
    (0.01,  5),
]
CENTER_BONUS      = 10
PERSISTENCE_BONUS = [
    (3, 10),
    (6, 20),
    (10, 30),
]
COMBO_RULES       = [
    # (["fighting", "blood_stain"], 25),
]
HYSTERESIS_DELTA  = 5.0


# ====== 유틸 ======
def now_event_id() -> str:
    return f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def make_s3_key(event_id: str, camera_id: str, cls_: str, level: str) -> str:
    return f"{DATE_PREFIX}/{camera_id}/clips/{event_id}_{cls_}_{level}.mp4"


# ====== S3 업로드 / 완료 보고 ======
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
        "detected_class": detected_class,
        "danger_level": danger_level,
        "file_url": file_url,
        "meta": meta or {},
    }
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    return r.json() if r.text else {"status": "ok"}


# ====== 위험도 계산용 헬퍼 ======
def yolo_to_detections(results, frame, model_names):
    H, W = frame.shape[:2]
    dets = []
    boxes = results[0].boxes
    if boxes is None:
        return dets

    for box in boxes:
        cls_id = int(box.cls[0])
        conf   = float(box.conf[0])
        name   = model_names[cls_id]

        xyxy = box.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = xyxy
        w, h = x2 - x1, y2 - y1
        area_ratio = (w * h) / (W * H + 1e-6)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

        dets.append({
            "cls": name,
            "conf": conf,
            "bbox": (float(x1), float(y1), float(x2), float(y2)),
            "area_ratio": float(area_ratio),
            "center": (float(cx / W), float(cy / H)),
        })
    return dets


def is_center_region(cx_norm: float, cy_norm: float) -> bool:
    return 0.3 <= cx_norm <= 0.7 and 0.3 <= cy_norm <= 0.7


def update_history(history, frame_idx: int, timestamp: float, detections):
    snapshot = {
        "frame_idx": frame_idx,
        "timestamp": timestamp,
        "detections": detections,
    }
    history["frames"].append(snapshot)

    cutoff = timestamp - HISTORY_SECONDS
    while history["frames"] and history["frames"][0]["timestamp"] < cutoff:
        history["frames"].popleft()

    return history


def decide_level_with_hysteresis(score: float, prev_level: str) -> str:
    high_th   = LEVEL_THRESHOLDS["HIGH"]
    medium_th = LEVEL_THRESHOLDS["MEDIUM"]

    if prev_level == "HIGH":
        if score >= high_th - HYSTERESIS_DELTA:
            return "HIGH"
    if prev_level == "MEDIUM":
        if score >= high_th:
            return "HIGH"
        if score >= medium_th - HYSTERESIS_DELTA:
            return "MEDIUM"

    if score >= high_th:
        return "HIGH"
    if score >= medium_th:
        return "MEDIUM"
    return "LOW"


def assess_risk(history):
    frames = history["frames"]
    if not frames:
        return {
            "level": "LOW",
            "score": 0.0,
            "main_class": "unknown",
            "reasons": ["no_detection"],
            "history": history,
        }

    current = frames[-1]
    now_ts  = current["timestamp"]
    dets    = current["detections"]

    total_score = 0.0
    reasons = []
    class_scores = defaultdict(float)

    # 1) 현재 프레임 기준
    for d in dets:
        cls = d["cls"]
        conf = d["conf"]
        area = d["area_ratio"]
        cx, cy = d["center"]

        base = CLASS_WEIGHTS.get(cls, 0)
        if base > 0:
            total_score += base
            class_scores[cls] += base
            reasons.append(f"base_class_{cls}+{base}")

        conf_score = conf * 30.0
        total_score += conf_score
        class_scores[cls] += conf_score
        reasons.append(f"conf_{cls}_{conf:.2f}+{int(conf_score)}")

        for threshold, bonus in AREA_THRESHOLDS:
            if area >= threshold:
                total_score += bonus
                class_scores[cls] += bonus
                reasons.append(f"area_{cls}_{area:.3f}>={threshold}+{bonus}")
                break

        if is_center_region(cx, cy):
            total_score += CENTER_BONUS
            class_scores[cls] += CENTER_BONUS
            reasons.append(f"center_{cls}+{CENTER_BONUS}")

    # 2) 최근 HISTORY_SECONDS 동안의 지속성
    cls_frame_count = defaultdict(int)
    for snap in frames:
        appeared = set(d["cls"] for d in snap["detections"])
        for cls in appeared:
            cls_frame_count[cls] += 1

    for cls, cnt in cls_frame_count.items():
        for threshold, bonus in PERSISTENCE_BONUS:
            if cnt >= threshold:
                total_score += bonus
                class_scores[cls] += bonus
                reasons.append(f"persistence_{cls}_{cnt}frames+{bonus}")
                break

    # 3) 동시 출현(콤보)
    combo_cutoff = now_ts - COMBO_WINDOW_SEC
    recent_snaps = [s for s in frames if s["timestamp"] >= combo_cutoff]

    recent_classes = set()
    for snap in recent_snaps:
        for d in snap["detections"]:
            recent_classes.add(d["cls"])

    for combo_classes, bonus in COMBO_RULES:
        if all(c in recent_classes for c in combo_classes):
            total_score += bonus
            reasons.append(f"combo_{'+'.join(combo_classes)}+{bonus}")

    # 4) 대표 클래스
    if class_scores:
        main_class = max(class_scores.items(), key=lambda kv: kv[1])[0]
    else:
        main_class = "unknown"

    # 5) 레벨 결정
    prev_level = history["last_level"]
    level = decide_level_with_hysteresis(total_score, prev_level)

    history["last_level"] = level
    history["last_score"] = total_score
    if level == "HIGH":
        history["last_high_timestamp"] = now_ts

    return {
        "level": level,
        "score": total_score,
        "main_class": main_class,
        "reasons": reasons,
        "history": history,
    }


# ====== 메인: 라이브 카메라 + 클립 추출 + 라이브 스트림 ======
def run_live_camera_with_clip():
    # 🔹 먼저 Flask 스트리밍 서버를 백그라운드에서 실행
    flask_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_thread.start()

    model = YOLO(MODEL_PATH)
    try:
        import torch
        if torch.cuda.is_available():
            model.to("cuda")
    except Exception:
        pass

    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print(f"Error: {CAM_INDEX}번 카메라를 열 수 없습니다. 인덱스를 변경해보세요.")
        return

    # 해상도 줄여서 부담 감소
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    print(f"[INFO] 카메라 {CAM_INDEX} 연결 성공! 'q'를 누르면 종료합니다.")
    print("[INFO] 라이브 스트림: http://localhost:5001/live")

    frame_idx = 0
    start_time = time.time()

    # 위험도 히스토리
    history = {
        "frames": deque(),
        "last_level": "LOW",
        "last_score": 0.0,
        "last_high_timestamp": None,
    }

    # 프레임 ring buffer: (timestamp_sec, frame)
    frame_buffer = deque()

    # 클립 녹화 상태
    clip_recording  = False
    clip_writer     = None
    clip_event_id   = None
    clip_primary    = None
    clip_start_t    = None
    clip_end_t      = None
    clip_local_path = None

    global latest_frame

    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 수신할 수 없습니다. 연결을 확인하세요.")
            break

        frame_idx += 1
        now = time.time()
        timestamp_sec = now - start_time

        # 🔹 최신 "원본" 프레임을 스트림용 버퍼에 저장
        with latest_frame_lock:
            latest_frame = frame.copy()

        # ring buffer에 현재 프레임 저장
        frame_buffer.append((timestamp_sec, frame.copy()))
        cutoff = timestamp_sec - BUFFER_MAX_SEC
        while frame_buffer and frame_buffer[0][0] < cutoff:
            frame_buffer.popleft()

        # YOLO 추론
        results = model(frame)

        # Detection 포맷 변환
        detections = yolo_to_detections(results, frame, model.names)

        # 위험도 히스토리 갱신
        history = update_history(history, frame_idx, timestamp_sec, detections)

        # 🔹 assess_risk 호출 전에 이전 레벨 저장
        prev_level = history["last_level"]

        # 위험도 평가
        risk_result = assess_risk(history)
        level      = risk_result["level"]
        score      = risk_result["score"]
        main_cls   = risk_result["main_class"]

        print(f"[LIVE FRAME {frame_idx}] t={timestamp_sec:5.1f}s "
              f"level={level}, score={score:6.1f}, main={main_cls}")

        # ====== HIGH "진입" 순간에만 클립 시작 (LOW/MEDIUM → HIGH) ======
        if level == "HIGH" and prev_level != "HIGH" and not clip_recording:
            clip_recording = True
            clip_event_id  = now_event_id()
            clip_primary   = (main_cls or "unknown").lower()
            event_time_sec = timestamp_sec

            clip_start_t = max(0.0, event_time_sec - CLIP_PRE_SEC)
            clip_end_t   = event_time_sec + CLIP_POST_SEC

            os.makedirs("./clips", exist_ok=True)
            level_s = "high"
            clip_local_path = f"./clips/{clip_event_id}_{clip_primary}_{level_s}.mp4"

            print(f"[ALERT] HIGH detected! event_id={clip_event_id}, cls={clip_primary}, "
                  f"time={event_time_sec:.2f}s -> clip {clip_start_t:.2f}~{clip_end_t:.2f}s")

            # VideoWriter 생성
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            clip_writer = cv2.VideoWriter(clip_local_path, fourcc, CLIP_FPS, (w, h))

            # ring buffer에서 과거 프레임들 기록
            for ts, fr in frame_buffer:
                if clip_start_t <= ts <= event_time_sec:
                    clip_writer.write(fr)

        # ====== 클립 녹화 중이면 이후 프레임 계속 기록 ======
        if clip_recording and clip_writer is not None:
            if timestamp_sec <= clip_end_t:
                clip_writer.write(frame)
            else:
                # POST 구간까지 다 채웠으면 클립 종료
                clip_writer.release()
                clip_writer = None
                clip_recording = False

                print(f"[INFO] 클립 저장 완료: {clip_local_path}")

                # S3 업로드 + 이벤트 완료 보고
                try:
                    s3_key = make_s3_key(
                        event_id=clip_event_id,
                        camera_id=CAMERA_ID,
                        cls_=clip_primary,
                        level="high",
                    )
                    ok_upload, file_url = upload_to_s3_with_retry(
                        clip_local_path, s3_key, max_retry=1
                    )
                    if not ok_upload:
                        raise RuntimeError("S3 upload failed")

                    meta = {
                        "mode": "LIVE",
                        "clip_start_sec": clip_start_t,
                        "clip_end_sec": clip_end_t,
                        "s3_key": s3_key,
                        "source": "live_camera",
                        "camera_id": CAMERA_ID,
                    }
                    resp = notify_event_complete(
                        event_id=clip_event_id,
                        camera_id=CAMERA_ID,
                        detected_class=clip_primary,
                        danger_level="HIGH",
                        file_url=file_url,
                        meta=meta,
                    )
                    print("[INFO] event_complete:", resp)
                except Exception as e:
                    print("[ERROR] clip upload/notify failed:", e)

        # 화면에 YOLO 결과 표시 (이건 계속 annotated 사용)
        annotated = results[0].plot()
        cv2.namedWindow("SmartShield Live Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("SmartShield Live Detection", 1280, 720)
        cv2.imshow("SmartShield Live Detection", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Live detection with clip finished.")


if __name__ == "__main__":
    run_live_camera_with_clip()