import os
import time
from datetime import datetime
from collections import defaultdict, deque

import cv2
import requests
from ultralytics import YOLO

# ======현재 파이프라인 작업 완료 ======

# ====== 환경 설정 ======
# Spring Boot 서버 주소 
BACKEND_BASE = os.getenv("BACKEND_URL", "http://localhost:8080")  # Spring Boot 서버

#################### 각자 로컬 환경에 맞게 수정 ####################
# YOLOv8 .pt 경로 (각자 로컬의 best.pt 파일 경로로 수정)
MODEL_PATH   = "C:\\Users\\ktg02\\CBNU\\3_2\\sanhak\\bodyCam\\object_detection\\SmartShield_results\\v3_merged_knife_gun_100epochs\\weights\\best.pt"
# 분석할 동영상 경로 (각자 로컬 환경에 맞게 수정)
VIDEO_PATH   = "C:\\Users\\ktg02\\CBNU\\3_2\\sanhak\\bodyCam\\object_detection\\contents\\video\\test1-2.mp4"
#####################################################################

CAMERA_ID    = "demo01"                                  # 데모용 카메라 ID(임시)
DATE_PREFIX  = datetime.now().strftime("%Y%m%d")         # S3 키 prefix용(년/월/일)

# ====== 위험도 판단 설정값 ======

# 클래스별 기본 위험 가중치
CLASS_WEIGHTS = {
    "gun":         50,
    "knife":       35,
    # 2차 스프린트에서 모델 확장 시 사용할 예정
    "blood_stain": 30,
    "fighting":    25,
}

# 위험도 등급 임계값
LEVEL_THRESHOLDS = {
    "MEDIUM": 40.0,
    "HIGH":   70.0,
}

# 히스토리 유지 시간(초) – 이 구간 동안의 지속성을 기준으로 위험도 평가
HISTORY_SECONDS = 3.0

# 동시 출현(콤보) 판단에 사용할 시간창(초)
COMBO_WINDOW_SEC = 2.0

# bbox 면적 비율에 따른 점수
AREA_THRESHOLDS = [
    (0.05, 20),   # 5% 이상 → +20
    (0.02, 10),   # 2~5%   → +10
    (0.01,  5),   # 1~2%   → +5
]

# 화면 중앙 근처일 때 추가 점수
CENTER_BONUS = 10

# 최근 HISTORY_SECONDS 동안 cls가 등장한 프레임 수에 따른 지속성 보너스
PERSISTENCE_BONUS = [
    (3, 10),
    (6, 20),
    (10, 30),
]

# 동시 출현(콤보) 룰 – 필요 시 확장
COMBO_RULES = [
    # (["fighting", "blood_stain"], 25),
    # (["gun", "person"], 15),
]

# 히스테리시스 폭 – 레벨이 바로 떨어지지 않게 하기 위한 여유 구간
HYSTERESIS_DELTA = 5.0


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

    # 영상 크기 축소 (50%) – 속도/용량 절약
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


# ====== 위험도 계산용 헬퍼 ======
def yolo_to_detections(results, frame, model_names):
    """
    YOLO 결과를 SmartShield 공통 Detection 포맷으로 변환
    """
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
            "center": (float(cx / W), float(cy / H)),  # 0~1 정규화
        })
    return dets


def is_center_region(cx_norm: float, cy_norm: float) -> bool:
    """
    정규화된 중심좌표(cx, cy)가 화면 중앙 영역에 가까운지 판단
    예: 0.3 ~ 0.7 범위를 중앙 영역으로 간주
    """
    return 0.3 <= cx_norm <= 0.7 and 0.3 <= cy_norm <= 0.7


def update_history(history, frame_idx: int, timestamp: float, detections):
    """
    RiskHistory 업데이트
    history: {
        "frames": deque([...]),
        "last_level": str,
        "last_score": float,
        "last_high_timestamp": float | None
    }
    """
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
    """
    점수와 이전 레벨을 기반으로 위험도 레벨 결정 (히스테리시스 적용)
    """
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
    """
    RiskHistory를 기반으로 현재 프레임의 위험도 평가.
    반환값:
    {
        "level": "LOW"/"MEDIUM"/"HIGH",
        "score": float,
        "main_class": str,
        "reasons": [str, ...],
        "history": updated_history
    }
    """
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

    # ---------- 1) 현재 프레임 기준: 클래스/신뢰도/크기/위치 ----------
    for d in dets:
        cls = d["cls"]
        conf = d["conf"]
        area = d["area_ratio"]
        cx, cy = d["center"]

        # (1) 클래스 기본 가중치
        base = CLASS_WEIGHTS.get(cls, 0)
        if base > 0:
            total_score += base
            class_scores[cls] += base
            reasons.append(f"base_class_{cls}+{base}")

        # (2) confidence
        conf_score = conf * 30.0
        total_score += conf_score
        class_scores[cls] += conf_score
        reasons.append(f"conf_{cls}_{conf:.2f}+{int(conf_score)}")

        # (3) bbox 크기
        for threshold, bonus in AREA_THRESHOLDS:
            if area >= threshold:
                total_score += bonus
                class_scores[cls] += bonus
                reasons.append(f"area_{cls}_{area:.3f}>={threshold}+{bonus}")
                break

        # (4) 화면 중앙 여부
        if is_center_region(cx, cy):
            total_score += CENTER_BONUS
            class_scores[cls] += CENTER_BONUS
            reasons.append(f"center_{cls}+{CENTER_BONUS}")

    # ---------- 2) 최근 HISTORY_SECONDS 동안의 지속성 ----------
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

    # ---------- 3) 동시 출현(콤보) 보너스 ----------
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

    # ---------- 4) 대표 클래스(main_class) 선정 ----------
    if class_scores:
        main_class = max(class_scores.items(), key=lambda kv: kv[1])[0]
    else:
        main_class = "unknown"

    # ---------- 5) 최종 스코어 → 등급 ----------
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

    # 위험도 평가용 히스토리 초기화
    history = {
        "frames": deque(),
        "last_level": "LOW",
        "last_score": 0.0,
        "last_high_timestamp": None,
    }

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        timestamp_sec = frame_idx / fps

        # YOLO 추론
        results = model(frame)

        # Detection 포맷으로 변환
        detections = yolo_to_detections(results, frame, model.names)

        # 히스토리 갱신
        history = update_history(history, frame_idx, timestamp_sec, detections)

        # 위험도 평가
        risk_result = assess_risk(history)
        level      = risk_result["level"]
        score      = risk_result["score"]
        main_cls   = risk_result["main_class"]

        # 디버깅용 로그
        print(f"[FRAME {frame_idx}] level={level}, score={score:.1f}, main={main_cls}")

        # HIGH 최초 발생 시 짧은 클립 추출/업로드 트리거
        if level == "HIGH" and not clip_triggered:
            clip_triggered = True
            event_time_sec = timestamp_sec

            # 🎯 클립 범위: HIGH 발생 10초 전 ~ 3초 후 (총 13초)
            clip_start_sec = max(0.0, event_time_sec - 10.0)
            clip_end_sec   = event_time_sec + 3.0

            event_id = now_event_id()
            primary  = (main_cls or "unknown").lower()
            level_s  = "high"

            os.makedirs("./clips", exist_ok=True)
            local_clip = f"./clips/{event_id}_{primary}_{level_s}.mp4"

            print(f"[ALERT] HIGH detected: cls={primary}, t={event_time_sec:.2f}s "
                  f"-> clip {clip_start_sec:.2f}s ~ {clip_end_sec:.2f}s")

            # 1) 짧은 클립 추출
            save_clip(VIDEO_PATH, clip_start_sec, clip_end_sec, local_clip)

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
                "clip_end_sec": clip_end_sec,
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

        # 시각화
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
