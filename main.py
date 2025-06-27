#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gui import MainWindow
import sys
import os
import re
from enum import Enum
from PyQt5.QtWidgets import QApplication

class SiteType(Enum):
    """지원하는 성인 플랫폼 목록"""
    CHATURBATE = "chaturbate"
    STRIPCHAT = "stripchat"
    CAMSODA = "camsoda"
    MYFREECAMS = "myfreecams"
    CAM4 = "cam4"
    BONGACAMS = "bongacams"
    LIVEJASMIN = "livejasmin"
    FLIRT4FREE = "flirt4free"
    XHAMSTERLIVE = "xhamsterlive"
    STREAMATE = "streamate"
    CAMGIRLS = "camgirls"
    IMLIVE = "imlive"
    CAMS = "cams"
    JERKMATE = "jerkmate"
    AMATEUR = "amateur"
    
    @classmethod
    def get_all_sites(cls):
        """모든 사이트명을 리스트로 반환"""
        return [site.value for site in cls]
    
    @classmethod
    def is_valid_site(cls, site_name):
        """주어진 문자열이 유효한 사이트명인지 확인"""
        return site_name.lower() in cls.get_all_sites()

class CapacityFinder:
    def __init__(self):
        self.current_path = None
        self.dic_files = {}
        self.window = None  # GUI 윈도우 참조를 위해 추가
        # 날짜 패턴 정의 (2025-06-26T15_09_46+09_00 형식)
        self.date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}[+-]\d{2}_\d{2}')
        
    def format_file_size(self, size_mb):
        """파일 사이즈를 적절한 단위(MB/GB)로 포맷팅하는 함수"""
        if size_mb >= 1024:  # 1GB 이상
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"
        
    def handle_path_confirmation(self, path):
        """GUI에서 경로가 확인되었을 때 호출되는 함수"""
        print(f"메인에서 받은 경로: {path}")
        self.current_path = path
        
        # 기존 데이터 초기화
        self.dic_files = {}
        
        # 파일 용량 계산
        result_dict = self.listing_files()
        
        if result_dict:
            # GUI 리스트 초기화
            self.window.list_widget.clear()
            
            # 용량 기준으로 내림차순 정렬 (큰 것부터)
            sorted_users = sorted(result_dict.items(), key=lambda x: x[1], reverse=True)
            
            # 결과를 GUI에 표시
            self.window.add_result_to_list("=== 사용자별 파일 용량 (용량 큰 순) ===")
            for username, total_size in sorted_users:
                formatted_size = self.format_file_size(total_size)
                result_text = f"{username}: {formatted_size}"
                self.window.add_result_to_list(result_text)
                print(f"사용자: {username}, 총 용량: {formatted_size}")
        else:
            self.window.add_result_to_list("처리할 파일이 없습니다.")
        
    def listing_files_capacity(self) -> list:
        """파일 용량을 계산하는 함수"""
        list_files = []
        if self.current_path:
            try:
                for file in os.listdir(self.current_path):
                    file_path = os.path.join(self.current_path, file)
                    # 파일인지 확인 (디렉토리 제외)
                    if os.path.isfile(file_path):
                        # 리스트에 파일명, 파일크기 저장 MB 단위
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        list_files.append([file, file_size_mb])
                return list_files
            except Exception as e:
                print(f"파일 목록 읽기 오류: {e}")
                return []
        else:
            print("경로가 설정되지 않았습니다.")
            return []
    
    def listing_files(self):
        """파일 목록을 가져와서 사용자별로 용량을 계산하는 함수"""
        file_list = self.listing_files_capacity()
        
        if not file_list:
            return {}
            
        for file_info in file_list:
            file_name = file_info[0]
            file_size = file_info[1]
            
            username = self.file_name_handle(file_name)
            if username:
                # 사용자별 용량 누적
                if username not in self.dic_files:
                    self.dic_files[username] = 0.0
                self.dic_files[username] += file_size
            else:
                print(f"파일명 처리 불가: {file_name}")
        
        return self.dic_files

    def file_name_handle(self, file_name):
        """파일 이름을 처리해서 채널명만 반환하는 함수
        다양한 파일명 구조 지원:
        - 사이트-채널-날짜
        - 채널-사이트-날짜
        - 기타 조합
        예: instagram-john_doe-2025-06-26T15_09_46+09_00.txt -> john_doe 반환
        """
        if not file_name:
            return None
            
        try:
            # 확장자 제거
            name_without_ext = file_name.split('.')[0] if '.' in file_name else file_name
            
            # 날짜 패턴 찾기
            date_match = self.date_pattern.search(name_without_ext)
            if not date_match:
                print(f"날짜 패턴을 찾을 수 없음: {file_name}")
                return None
            
            date_part = date_match.group()
            date_start = date_match.start()
            
            # 날짜 이전 부분 추출
            before_date = name_without_ext[:date_start].rstrip('-')
            
            # '-'로 분리
            parts = before_date.split('-')
            
            if len(parts) < 2:
                print(f"파일명 구조가 올바르지 않음: {file_name}")
                return None
            
            # 사이트 찾기
            site_part = None
            channel_parts = []
            
            for i, part in enumerate(parts):
                if SiteType.is_valid_site(part):
                    site_part = part
                    # 사이트가 아닌 나머지 부분들을 채널명으로 결합
                    channel_parts = parts[:i] + parts[i+1:]
                    break
            
            if not site_part:
                print(f"알려진 사이트를 찾을 수 없음: {file_name}")
                return None
            
            if not channel_parts:
                print(f"채널명을 찾을 수 없음: {file_name}")
                return None
            
            # 채널명 결합 (여러 부분이 있을 경우 '-'로 다시 결합)
            channel_name = '-'.join(channel_parts)
            
            print(f"파일명: {file_name} -> 사이트: {site_part}, 채널: {channel_name}, 날짜: {date_part}")
            return channel_name
                    
        except Exception as e:
            print(f"파일명 처리 중 오류: {file_name}, 에러: {e}")
            return None

def main():
    """메인 함수에서 GUI 애플리케이션을 실행합니다."""
    app = QApplication(sys.argv)
    
    # CapacityFinder 인스턴스 생성
    finder = CapacityFinder()
    
    # GUI 생성 시 콜백 함수 전달
    finder.window = MainWindow(on_path_confirmed=finder.handle_path_confirmation)
    finder.window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
