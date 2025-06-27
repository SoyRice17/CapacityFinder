import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QLineEdit, 
                             QPushButton, QLabel, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

class MainWindow(QMainWindow):
    def __init__(self, on_path_confirmed=None):
        super().__init__()
        self.on_path_confirmed = on_path_confirmed  # 콜백 함수 저장
        self.current_path = None  # 현재 경로 저장을 위해 추가
        self.setWindowTitle("Capacity Finder")
        self.setGeometry(100, 100, 1000, 700)

        # 메인 위젯과 레이아웃 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 트리 위젯 (4/5 크기)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["사용자/파일", "크기", "파일 수"])
        self.tree_widget.setColumnWidth(0, 400)
        self.tree_widget.setColumnWidth(1, 150)
        self.tree_widget.setColumnWidth(2, 100)
        # 더블클릭 이벤트 연결
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree_widget, 4)

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
            self.current_path = path_text  # 현재 경로 저장
            self.path_label.setText(f"현재 경로: {path_text}")
            self.path_input.clear()
            
            # 메인 클래스로 값 전달 (콜백 함수 호출)
            if self.on_path_confirmed:
                self.on_path_confirmed(path_text)
        else:
            self.path_label.setText("현재 경로: 설정되지 않음")

    def on_item_double_clicked(self, item, column):
        """트리 아이템 더블클릭 시 호출되는 함수"""
        # 사용자 아이템(부모)인지 파일 아이템(자식)인지 확인
        parent = item.parent()
        
        if parent is not None:  # 파일 아이템인 경우 (부모가 있음)
            file_name = item.text(0)  # 파일명 가져오기
            
            if self.current_path and file_name:
                file_path = os.path.join(self.current_path, file_name)
                
                # 파일이 실제로 존재하는지 확인
                if os.path.exists(file_path):
                    try:
                        # 운영체제별 파일 열기
                        if sys.platform.startswith('win'):  # Windows
                            os.startfile(file_path)
                        elif sys.platform.startswith('darwin'):  # macOS
                            subprocess.call(['open', file_path])
                        else:  # Linux
                            subprocess.call(['xdg-open', file_path])
                            
                        print(f"파일 열기: {file_path}")
                        
                    except Exception as e:
                        # 오류 발생 시 메시지 박스 표시
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Warning)
                        msg.setWindowTitle("파일 열기 오류")
                        msg.setText(f"파일을 열 수 없습니다:\n{str(e)}")
                        msg.exec_()
                        print(f"파일 열기 오류: {e}")
                else:
                    # 파일이 존재하지 않는 경우
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("파일 없음")
                    msg.setText(f"파일을 찾을 수 없습니다:\n{file_path}")
                    msg.exec_()
                    print(f"파일 없음: {file_path}")
            else:
                print("경로가 설정되지 않았거나 파일명이 없습니다.")
        else:
            # 사용자 아이템인 경우 (폴더 확장/축소)
            if item.isExpanded():
                item.setExpanded(False)
            else:
                item.setExpanded(True)

    def add_result_to_list(self, result_text):
        """메인에서 호출해서 리스트에 결과를 추가하는 함수 (기존 호환성 유지)"""
        # 트리 위젯에 헤더 추가
        if result_text.startswith("==="):
            header_item = QTreeWidgetItem(self.tree_widget)
            header_item.setText(0, result_text)
            header_item.setBackground(0, QColor(211, 211, 211))  # lightGray
            # 폰트 굵게 설정
            font = header_item.font(0)
            font.setBold(True)
            header_item.setFont(0, font)
            self.tree_widget.addTopLevelItem(header_item)
        else:
            # 일반 결과는 사용자 정보로 처리
            pass

    def add_user_data(self, username, user_data, formatted_size):
        """사용자 데이터를 트리에 추가하는 함수"""
        # 사용자 아이템 생성
        user_item = QTreeWidgetItem(self.tree_widget)
        user_item.setText(0, username)
        user_item.setText(1, formatted_size)
        user_item.setText(2, str(len(user_data['files'])))
        
        # 사용자 아이템 스타일 설정
        light_blue = QColor(173, 216, 230)  # lightBlue
        user_item.setBackground(0, light_blue)
        user_item.setBackground(1, light_blue)
        user_item.setBackground(2, light_blue)
        
        # 파일 목록을 하위 아이템으로 추가
        for file_info in user_data['files']:
            file_item = QTreeWidgetItem(user_item)
            file_item.setText(0, file_info['name'])
            file_item.setText(1, f"{file_info['size']:.2f} MB")
            file_item.setText(2, "")
        
        # 기본적으로 접혀있도록 설정
        user_item.setExpanded(False)
        
        self.tree_widget.addTopLevelItem(user_item)

    def clear_results(self):
        """트리 위젯의 모든 결과를 지우는 함수"""
        self.tree_widget.clear()
