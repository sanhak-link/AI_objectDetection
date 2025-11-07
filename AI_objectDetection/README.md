# 🛡️ SmartShield Object Detection

**SmartShield**는 위험 상황 감지를 위한 **객체 탐지(Object Detection) AI 프로젝트**입니다.
본 저장소는 모델 학습, 성능 평가, 그리고 최종 배포용 가중치(`.pt`) 파일을 포함합니다.

---

## 📘 프로젝트 개요

* **목표**: CCTV 또는 바디캠 영상에서 칼, 총 등의 위험 물체를 실시간으로 탐지
* **기술 스택**:

  * **AI 모델**: YOLO 계열(Object Detection 기반)
  * **Framework**: PyTorch
  * **Dataset**: Custom dataset (위험 물체 중심)
  * **Language**: Python
* **결과물**:

  * 학습된 모델 가중치 파일(`.pt`)
  * 학습 및 추론 스크립트 (`train.py`, `detect.py`, 등)
  * 시각화 및 성능 평가 결과(`runs/`, `results/` 폴더)

---

## 🧠 주요 기능

* 사용자 지정 객체(칼, 총 등) 탐지 모델 학습
* 실시간 영상 스트림에서 위험 객체 감지
* 학습 로그 및 성능 평가 결과 자동 저장
* YOLO 기반의 학습 환경 제공

---

## 📝 Commit Convention(규칙)

| Type    | 의미          | 예시                                  |
| ------- | ----------- | ----------------------------------- |
| `feat:` | 새로운 기능 개발   | `feat: add YOLOv8 training script`  |
| `fix:`  | 기존 코드 수정    | `fix: correct dataset path error`   |
| `del:`  | 기존 코드 일부 삭제 | `del: remove unused config options` |

**Commit 메시지 형식:**

```
feat: (내용)
```

---

## 🚀 향후 계획

* [ ] 인공지능 학습 성능 강화
* [ ] 총기류, 사람, 피, 범죄 가능성 판단
* [ ] openCV 연결 후 동영상에서 객체 탐지
* [ ] 실시간 영상에서 객체 탐지