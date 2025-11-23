import cv2

def run_ivcam():
    # 1. 카메라 열기 (0번이 안 되면 1, 2로 변경해보세요)
    # iVCam이 켜져 있고 PC와 연결된 상태여야 합니다.
    cam_index = 1 
    cap = cv2.VideoCapture(cam_index)

    # 카메라가 제대로 열렸는지 확인
    if not cap.isOpened():
        print(f"Error: {cam_index}번 카메라를 열 수 없습니다. 인덱스를 변경해보세요.")
        return

    # iVCam 해상도 설정 (필요시 조절, iVCam 앱 설정과 맞추는 게 좋음)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("카메라 연결 성공! 'q'를 누르면 종료합니다.")

    while True:
        # 프레임 읽기
        ret, frame = cap.read()

        if not ret:
            print("프레임을 수신할 수 없습니다. 연결을 확인하세요.")
            break

        # 화면 출력
        cv2.imshow('iVCam Python Connect', frame)

        # 'q' 키를 누르면 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 자원 해제
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_ivcam()