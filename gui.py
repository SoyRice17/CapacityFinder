import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QLineEdit, 
                             QPushButton, QLabel, QMessageBox, QComboBox, QSplitter,
                             QDialog)
from path_dialog import PathSelectionDialog
from decision_dialog import ModelDecisionDialog
from user_site_comparison_dialog import UserSiteComparisonDialog
from accurate_selection_dialog import AccurateSelectionDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

class MainWindow(QMainWindow):
    def __init__(self, on_path_confirmed=None, path_history=None):
        super().__init__()
        self.on_path_confirmed = on_path_confirmed  # 콜백 함수 저장
        self.path_history = path_history  # 경로 기록 관리자
        self.current_path = None  # 현재 경로 저장을 위해 추가
        self.capacity_finder = None  # CapacityFinder 인스턴스 참조 저장
        # 정렬을 위한 사용자 데이터 저장
        self.users_data = {}  # {username: {user_data: dict, formatted_size: str}}
        self.current_sort_column = 1  # 기본값: 크기로 정렬 (0: 이름, 1: 크기, 2: 파일 수)
        self.current_sort_order = Qt.DescendingOrder  # 기본값: 내림차순
        
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
        
        # 정렬 기능 활성화
        self.tree_widget.setSortingEnabled(False)  # 기본 정렬은 비활성화하고 커스텀 정렬 사용
        
        # 헤더 클릭 이벤트 연결
        header = self.tree_widget.header()
        header.sectionClicked.connect(self.on_header_clicked)
        header.setSectionsClickable(True)
        
        # 더블클릭 이벤트 연결
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree_widget, 4)

        # 현재 경로 표시 라벨
        self.path_label = QLabel("현재 경로: 설정되지 않음")
        self.path_label.setStyleSheet("QLabel { padding: 10px; background-color: #2c3e50; color: #ffffff; border: 2px solid #34495e; border-radius: 5px; font-weight: bold; }")
        layout.addWidget(self.path_label)

        # 경로 선택 버튼 레이아웃
        path_button_layout = QHBoxLayout()
        path_button_layout.setContentsMargins(10, 5, 10, 5)
        
        # 메인 경로 선택 버튼
        self.select_path_button = QPushButton("📁 경로 선택 및 관리")
        self.select_path_button.clicked.connect(self.open_path_dialog)
        self.select_path_button.setMinimumHeight(40)
        self.select_path_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        
        # 빠른 재탐색 버튼 (현재 경로가 있을 때만 활성화)
        self.quick_rescan_button = QPushButton("🔄 현재 경로 재탐색")
        self.quick_rescan_button.clicked.connect(self.quick_rescan)
        self.quick_rescan_button.setMinimumHeight(40)
        self.quick_rescan_button.setEnabled(False)
        self.quick_rescan_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover:enabled {
                background-color: #229954;
            }
            QPushButton:pressed:enabled {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        # 모델 정리 버튼 추가
        self.model_cleanup_button = QPushButton("🗑️ 기존 정리도우미")
        self.model_cleanup_button.clicked.connect(self.open_model_decision_dialog)
        self.model_cleanup_button.setMinimumHeight(40)
        self.model_cleanup_button.setEnabled(False)
        self.model_cleanup_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover:enabled {
                background-color: #c0392b;
            }
            QPushButton:pressed:enabled {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        # 특정 유저 사이트 비교 버튼 추가
        self.user_site_comparison_button = QPushButton("⚖️ 유저 사이트 비교")
        self.user_site_comparison_button.clicked.connect(self.open_user_site_comparison_dialog)
        self.user_site_comparison_button.setMinimumHeight(40)
        self.user_site_comparison_button.setEnabled(False)
        self.user_site_comparison_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover:enabled {
                background-color: #8e44ad;
            }
            QPushButton:pressed:enabled {
                background-color: #7d3c98;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        # 정확한 선별도우미 버튼 추가
        self.accurate_selection_button = QPushButton("🎯 정확한 선별도우미")
        self.accurate_selection_button.clicked.connect(self.open_accurate_selection_dialog)
        self.accurate_selection_button.setMinimumHeight(40)
        self.accurate_selection_button.setEnabled(False)
        self.accurate_selection_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover:enabled {
                background-color: #e67e22;
            }
            QPushButton:pressed:enabled {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        path_button_layout.addWidget(self.select_path_button, 3)
        path_button_layout.addWidget(self.quick_rescan_button, 1)
        path_button_layout.addWidget(self.model_cleanup_button, 1)
        path_button_layout.addWidget(self.user_site_comparison_button, 1)
        path_button_layout.addWidget(self.accurate_selection_button, 1)
        
        layout.addLayout(path_button_layout, 1)

    def open_path_dialog(self):
        """경로 선택 다이얼로그 열기"""
        dialog = PathSelectionDialog(self.path_history, self)
        
        if dialog.exec_() == PathSelectionDialog.Accepted:
            selected_path = dialog.get_selected_path()
            if selected_path:
                self.process_selected_path(selected_path)
    
    def quick_rescan(self):
        """현재 경로 빠른 재탐색"""
        if self.current_path and self.on_path_confirmed:
            self.on_path_confirmed(self.current_path)
    
    def process_selected_path(self, path):
        """선택된 경로 처리"""
        self.current_path = path
        self.path_label.setText(f"현재 경로: {path}")
        
        # 빠른 재탐색 버튼 활성화
        self.quick_rescan_button.setEnabled(True)
        
        # 메인 클래스로 값 전달 (콜백 함수 호출)
        if self.on_path_confirmed:
            self.on_path_confirmed(path)

    def set_capacity_finder(self, capacity_finder):
        """CapacityFinder 인스턴스 설정"""
        self.capacity_finder = capacity_finder
        # 데이터가 있을 때만 모델 정리 버튼 활성화
        if capacity_finder and capacity_finder.dic_files:
            self.model_cleanup_button.setEnabled(True)

    def update_cleanup_button_state(self):
        """모델 정리 버튼들 상태 업데이트"""
        if self.capacity_finder and self.capacity_finder.dic_files:
            self.model_cleanup_button.setEnabled(True)
            self.user_site_comparison_button.setEnabled(True)
            self.accurate_selection_button.setEnabled(True)
        else:
            self.model_cleanup_button.setEnabled(False)
            self.user_site_comparison_button.setEnabled(False)
            self.accurate_selection_button.setEnabled(False)

    def open_model_decision_dialog(self):
        """모델 결정 다이얼로그 열기"""
        if not self.capacity_finder or not self.capacity_finder.dic_files:
            QMessageBox.warning(self, "데이터 없음", "먼저 경로를 선택하고 파일을 분석해주세요.")
            return
        
        # 결정 리스트 생성
        decision_data = self.capacity_finder.create_decision_list()
        
        if not decision_data:
            QMessageBox.information(self, "데이터 없음", "분석할 모델 데이터가 없습니다.")
            return
        
        # 팝업 다이얼로그 열기
        dialog = ModelDecisionDialog(decision_data, self.current_path, self)
        if dialog.exec_() == QDialog.Accepted:
            decisions, total_savings = dialog.get_decisions()
            self.process_deletion_decisions(decisions, total_savings)

    def open_user_site_comparison_dialog(self):
        """특정 유저 사이트 비교 다이얼로그 열기"""
        if not self.capacity_finder or not self.capacity_finder.dic_files:
            QMessageBox.warning(self, "데이터 없음", "먼저 경로를 선택하고 파일을 분석해주세요.")
            return
        
        # 유저 사이트 비교 다이얼로그 열기
        dialog = UserSiteComparisonDialog(self.capacity_finder, self.current_path, self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self.process_site_comparison_result(result)

    def open_accurate_selection_dialog(self):
        """정확한 선별도우미 다이얼로그 열기"""
        if not self.capacity_finder or not self.capacity_finder.dic_files:
            QMessageBox.warning(self, "데이터 없음", "먼저 경로를 선택하고 파일을 분석해주세요.")
            return
        
        # 정확한 선별 다이얼로그 열기
        dialog = AccurateSelectionDialog(self.capacity_finder, self.current_path, self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self.process_accurate_selection_result(result)

    def process_site_comparison_result(self, result):
        """사이트 비교 결과 처리"""
        if not result.get('files_to_delete'):
            QMessageBox.information(self, "결과", "삭제할 파일이 없습니다.")
            return
        
        files_to_delete = result['files_to_delete']
        total_savings = result['total_savings']
        username = result['username']
        
        # 확인 메시지
        msg = f"사용자 '{username}'의 중복 파일 {len(files_to_delete)}개를 삭제하시겠습니까?\n"
        msg += f"절약될 용량: {self.format_file_size(total_savings)}\n\n"
        msg += "삭제할 파일들:\n"
        for file_info in files_to_delete[:5]:  # 처음 5개만 표시
            msg += f"- {file_info['name']} ({self.format_file_size(file_info['size'])})\n"
        if len(files_to_delete) > 5:
            msg += f"... 외 {len(files_to_delete) - 5}개\n"
        
        reply = QMessageBox.question(
            self, "삭제 확인", msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.execute_site_comparison_deletions(files_to_delete, total_savings, username)

    def execute_site_comparison_deletions(self, files_to_delete, total_savings, username):
        """사이트 비교 결과에 따른 파일 삭제 실행"""
        if not self.current_path:
            QMessageBox.warning(self, "오류", "현재 경로가 설정되지 않았습니다.")
            return
        
        deleted_count = 0
        failed_count = 0
        
        for file_info in files_to_delete:
            file_path = os.path.join(self.current_path, file_info['name'])
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"삭제됨: {file_info['name']}")
                else:
                    failed_count += 1
                    print(f"파일 없음: {file_info['name']}")
            except Exception as e:
                failed_count += 1
                print(f"삭제 실패: {file_info['name']}, 오류: {e}")
        
        # 결과 메시지
        result_msg = f"사용자 '{username}' 파일 정리 완료!\n\n"
        result_msg += f"삭제된 파일: {deleted_count}개\n"
        if failed_count > 0:
            result_msg += f"삭제 실패: {failed_count}개\n"
        result_msg += f"절약된 용량: {self.format_file_size(total_savings)}"
        
        QMessageBox.information(self, "삭제 완료", result_msg)
        
        # 현재 경로 재탐색
        if self.on_path_confirmed:
            self.on_path_confirmed(self.current_path)

    def process_accurate_selection_result(self, result):
        """정확한 선별 결과 처리"""
        if not result.get('files_to_delete'):
            QMessageBox.information(self, "결과", "삭제할 파일이 없습니다.")
            return
        
        files_to_delete = result['files_to_delete']
        files_to_keep = result['files_to_keep']
        total_savings = result['total_savings']
        username = result['username']
        
        # 확인 메시지
        msg = f"사용자 '{username}'의 선별되지 않은 파일 {len(files_to_delete)}개를 삭제하시겠습니까?\n"
        msg += f"유지할 파일: {len(files_to_keep)}개\n"
        msg += f"절약될 용량: {self.format_file_size(total_savings)}\n\n"
        msg += "삭제할 파일들 (처음 5개):\n"
        for file_info in files_to_delete[:5]:
            msg += f"- {file_info['name']} ({self.format_file_size(file_info['size'])})\n"
        if len(files_to_delete) > 5:
            msg += f"... 외 {len(files_to_delete) - 5}개\n"
        
        reply = QMessageBox.question(
            self, "선별 삭제 확인", msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.execute_accurate_selection_deletions(files_to_delete, total_savings, username)

    def execute_accurate_selection_deletions(self, files_to_delete, total_savings, username):
        """정확한 선별 결과에 따른 파일 삭제 실행"""
        if not self.current_path:
            QMessageBox.warning(self, "오류", "현재 경로가 설정되지 않았습니다.")
            return
        
        deleted_count = 0
        failed_count = 0
        
        for file_info in files_to_delete:
            file_path = os.path.join(self.current_path, file_info['name'])
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"삭제됨: {file_info['name']}")
                else:
                    failed_count += 1
                    print(f"파일 없음: {file_info['name']}")
            except Exception as e:
                failed_count += 1
                print(f"삭제 실패: {file_info['name']}, 오류: {e}")
        
        # 결과 메시지
        result_msg = f"사용자 '{username}' 정확한 선별 완료!\n\n"
        result_msg += f"삭제된 파일: {deleted_count}개\n"
        if failed_count > 0:
            result_msg += f"삭제 실패: {failed_count}개\n"
        result_msg += f"절약된 용량: {self.format_file_size(total_savings)}"
        
        QMessageBox.information(self, "선별 완료", result_msg)
        
        # 현재 경로 재탐색
        if self.on_path_confirmed:
            self.on_path_confirmed(self.current_path)

    def process_deletion_decisions(self, decisions, total_savings):
        """삭제 결정 처리"""
        delete_models = [username for username, decision in decisions.items() if decision == 'delete']
        
        if not delete_models:
            QMessageBox.information(self, "완료", "삭제할 모델이 선택되지 않았습니다.")
            return
        
        # 최종 확인
        msg = QMessageBox()
        msg.setWindowTitle("최종 확인")
        msg.setText(f"""
정말로 다음 모델들의 모든 파일을 삭제하시겠습니까?

삭제할 모델: {len(delete_models)}개
절약될 용량: {self.format_file_size(total_savings)}

⚠️ 이 작업은 되돌릴 수 없습니다!

삭제할 모델들:
{chr(10).join(delete_models)}
        """)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setIcon(QMessageBox.Warning)
        
        if msg.exec_() == QMessageBox.Yes:
            self.execute_file_deletions(delete_models, total_savings)

    def execute_file_deletions(self, delete_models, total_savings):
        """실제 파일 삭제 실행"""
        if not self.current_path or not self.capacity_finder:
            return
        
        deleted_count = 0
        error_count = 0
        
        try:
            for username in delete_models:
                if username in self.capacity_finder.dic_files:
                    user_files = self.capacity_finder.dic_files[username]['files']
                    
                    for file_info in user_files:
                        file_path = os.path.join(self.current_path, file_info['name'])
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                deleted_count += 1
                                print(f"삭제됨: {file_path}")
                            else:
                                print(f"파일 없음: {file_path}")
                        except Exception as e:
                            error_count += 1
                            print(f"삭제 오류: {file_path}, 에러: {e}")
            
            # 결과 메시지
            result_msg = f"""
🗑️ 파일 삭제 완료!

삭제된 파일: {deleted_count}개
오류 발생: {error_count}개
절약된 용량: {self.format_file_size(total_savings)}

경로를 다시 스캔하시겠습니까?
            """
            
            msg = QMessageBox()
            msg.setWindowTitle("삭제 완료")
            msg.setText(result_msg)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)
            
            if msg.exec_() == QMessageBox.Yes:
                # 재스캔 실행
                self.quick_rescan()
                
        except Exception as e:
            QMessageBox.critical(self, "삭제 오류", f"파일 삭제 중 오류가 발생했습니다:\n{str(e)}")

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
        # 사용자 데이터 저장 (정렬을 위해)
        size_mb = user_data['total_size']  # MB 단위 숫자값
        self.users_data[username] = {
            'user_data': {
                'name': username,
                'size': size_mb,
                'files': user_data['files']
            },
            'formatted_size': formatted_size
        }
        
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
        
        # 파일 목록을 크기순(내림차순)으로 정렬 - 첫 로딩시 기본 정렬
        sorted_files = sorted(user_data['files'], key=lambda x: x['size'], reverse=True)
        
        # 파일 목록을 하위 아이템으로 추가 (GB/MB 단위로 표시)
        for file_info in sorted_files:
            file_item = QTreeWidgetItem(user_item)
            file_item.setText(0, file_info['name'])
            file_item.setText(1, self.format_file_size(file_info['size']))  # GB/MB 단위로 표시
            file_item.setText(2, "")
        
        # 기본적으로 접혀있도록 설정
        user_item.setExpanded(False)
        
        self.tree_widget.addTopLevelItem(user_item)

    def clear_results(self):
        """트리 위젯의 모든 결과를 지우는 함수"""
        self.tree_widget.clear()
        self.users_data = {}  # 저장된 사용자 데이터도 초기화

    def on_header_clicked(self, logicalIndex):
        """헤더 클릭 시 정렬 기능"""
        # 같은 컬럼을 클릭하면 정렬 순서 토글, 다른 컬럼이면 내림차순부터 시작
        if self.current_sort_column == logicalIndex:
            self.current_sort_order = Qt.AscendingOrder if self.current_sort_order == Qt.DescendingOrder else Qt.DescendingOrder
        else:
            self.current_sort_column = logicalIndex
            self.current_sort_order = Qt.DescendingOrder  # 새 컬럼은 항상 내림차순부터
        
        # 정렬 표시기 설정
        self.tree_widget.header().setSortIndicator(self.current_sort_column, self.current_sort_order)
        
        # 데이터 정렬 및 표시
        self.sort_users_data()

    def sort_users_data(self):
        """사용자 데이터를 정렬하는 함수"""
        if not self.users_data:
            return
            
        # 정렬 키에 따라 데이터 정렬
        sorted_items = sorted(self.users_data.items(), 
                            key=lambda x: self.get_sort_key(x[0], x[1]), 
                            reverse=(self.current_sort_order == Qt.DescendingOrder))
        
        # 트리 위젯 초기화
        self.tree_widget.clear()
        
        # 헤더 다시 추가
        header_item = QTreeWidgetItem(self.tree_widget)
        header_item.setText(0, "=== 사용자별 파일 용량 ===")
        header_item.setBackground(0, QColor(211, 211, 211))  # lightGray
        font = header_item.font(0)
        font.setBold(True)
        header_item.setFont(0, font)
        self.tree_widget.addTopLevelItem(header_item)
        
        # 정렬된 데이터로 다시 표시 (중복 저장 방지를 위해 직접 아이템 생성)
        for username, data in sorted_items:
            user_data = data['user_data']
            formatted_size = data['formatted_size']
            
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
            
            # 파일 목록 정렬 (헤더 정렬 기준에 따라)
            sorted_files = self.sort_files(user_data['files'])
            
            # 파일 목록을 하위 아이템으로 추가
            for file_info in sorted_files:
                file_item = QTreeWidgetItem(user_item)
                file_item.setText(0, file_info['name'])
                file_item.setText(1, self.format_file_size(file_info['size']))  # GB/MB 단위로 표시
                file_item.setText(2, "")
            
            # 기본적으로 접혀있도록 설정
            user_item.setExpanded(False)
            
            self.tree_widget.addTopLevelItem(user_item)

    def sort_files(self, files):
        """파일 목록을 정렬하는 함수"""
        if self.current_sort_column == 0:  # 파일명으로 정렬
            return sorted(files, key=lambda x: x['name'].lower(), 
                         reverse=(self.current_sort_order == Qt.DescendingOrder))
        elif self.current_sort_column == 1:  # 파일 크기로 정렬
            return sorted(files, key=lambda x: x['size'], 
                         reverse=(self.current_sort_order == Qt.DescendingOrder))
        else:  # 파일 수 컬럼이거나 기타의 경우 기본 순서 유지
            return files

    def get_sort_key(self, username, data):
        """정렬 키를 반환하는 함수"""
        if self.current_sort_column == 0:  # 사용자명
            return username.lower()
        elif self.current_sort_column == 1:  # 크기
            return data['user_data']['size']
        elif self.current_sort_column == 2:  # 파일 수
            return len(data['user_data']['files'])
        return ""

    def format_file_size(self, size_mb):
        """파일 사이즈를 적절한 단위(MB/GB)로 포맷팅하는 함수"""
        if size_mb >= 1024:  # 1GB 이상
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"
