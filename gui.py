import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit, QPushButton, QLabel

class MainWindow(QMainWindow):
    def __init__(self, on_path_confirmed=None):
        super().__init__()
        self.on_path_confirmed = on_path_confirmed  # 콜백 함수 저장
        self.setWindowTitle("경로 입력기")
        self.setGeometry(100, 100, 800, 600)

        # 메인 위젯과 레이아웃 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 리스트 위젯 (4/5 크기)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 4)

        # 현재 경로 표시 라벨
        self.path_label = QLabel("현재 경로: 설정되지 않음")
        self.path_label.setStyleSheet("QLabel { padding: 10px; background-color: #2c3e50; color: #ffffff; border: 2px solid #34495e; border-radius: 5px; font-weight: bold; }")
        layout.addWidget(self.path_label)

        # 입력창과 버튼을 위한 수평 레이아웃
        input_layout = QHBoxLayout()
        
        # 텍스트 입력창
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("경로를 입력하세요...")
        input_layout.addWidget(self.path_input, 4)

        # 확인 버튼
        self.confirm_button = QPushButton("확인")
        self.confirm_button.clicked.connect(self.on_confirm_clicked)
        input_layout.addWidget(self.confirm_button, 1)

        # 수평 레이아웃을 메인 레이아웃에 추가
        layout.addLayout(input_layout, 1)

    def on_confirm_clicked(self):
        """확인 버튼 클릭 시 호출되는 함수"""
        path_text = self.path_input.text().strip()
        if path_text:
            self.path_label.setText(f"현재 경로: {path_text}")
            self.path_input.clear()
            
            # 메인 클래스로 값 전달 (콜백 함수 호출)
            if self.on_path_confirmed:
                self.on_path_confirmed(path_text)
        else:
            self.path_label.setText("현재 경로: 설정되지 않음")

    def add_result_to_list(self, result_text):
        """메인에서 호출해서 리스트에 결과를 추가하는 함수"""
        self.list_widget.addItem(result_text)
