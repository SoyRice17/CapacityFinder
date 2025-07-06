#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gui import MainWindow
import sys
import os
import re
import json
import logging
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from PyQt5.QtWidgets import QApplication

# 로그 설정 함수
def setup_logging():
    """로그 설정을 초기화합니다."""
    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로그 파일명 (날짜 포함)
    log_filename = os.path.join(log_dir, f"capacity_finder_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 로그 포맷 설정 (파일명, 함수명, 라인 번호 포함)
    log_format = "%(asctime)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s"
    
    # 로그 설정 - 모든 레벨 출력 (DEBUG 포함)
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),  # 파일 출력
            logging.StreamHandler()  # 콘솔 출력
        ]
    )
    
    # 로거 반환
    return logging.getLogger(__name__)

# 로그 설정 초기화
logger = setup_logging()

# 다른 파일에서도 사용할 수 있도록 로그 설정 함수 제공
def get_logger(module_name):
    """다른 모듈에서 로거를 가져올 때 사용"""
    return logging.getLogger(module_name)

class IntelligentCurationSystem:
    """지능형 큐레이션 시스템 - 레이팅 데이터와 파일 점수를 결합한 판단 시스템"""
    
    def __init__(self, ratings_file="user_ratings.json"):
        self.ratings_file = ratings_file
        self.ratings_data = self.load_ratings()
        self.keyword_weights = self.load_keyword_weights()
        logger.info("🧠 지능형 큐레이션 시스템 초기화 완료 (다양성 유지 점수 시스템 적용)")
    
    def load_ratings(self):
        """레이팅 데이터 로드"""
        try:
            if os.path.exists(self.ratings_file):
                with open(self.ratings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('ratings', {})
            return {}
        except Exception as e:
            logger.error(f"레이팅 로드 오류: {e}")
            return {}
    
    def load_keyword_weights(self):
        """키워드 가중치를 파일에서 로드하거나 기본값 사용"""
        try:
            # 저장된 키워드 파일 확인
            if os.path.exists('keyword_weights.json'):
                with open('keyword_weights.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    keywords = data.get('keywords', {})
                    if keywords:
                        logger.info(f"키워드 가중치 파일 로드: {len(keywords)}개 키워드")
                        return keywords
        except Exception as e:
            logger.error(f"키워드 가중치 로드 오류: {e}")
        
        # 기본값 사용
        logger.info("기본 키워드 가중치 사용")
        return self.get_default_keyword_weights()
    
    def get_default_keyword_weights(self):
        """기본 키워드 가중치 시스템 구축 - 다양성 유지 버전"""
        return {
            # 긍정적 키워드 (유지 선호) - 적당한 범위로 조정
            'ㅅㅌㅊ': 0.8,         # 1.2 → 0.8
            'ㅆㅅㅌㅊ': 0.9,        # 1.5 → 0.9
            'ㅈㅅㅌㅊ': 0.7,        # 1.0 → 0.7
            'ㅍㅅㅌㅊ': 0.6,        # 0.8 → 0.6
            'GOAT': 0.9,          # 1.5 → 0.9
            '신': 0.8,            # 1.3 → 0.8
            '귀여움': 0.6,         # 1.0 → 0.6
            '올노': 0.5,          # 0.9 → 0.5
            '자위': 0.4,          # 0.7 → 0.4
            
            # 부정적 키워드 (삭제 선호) - 적당한 범위로 조정
            '가지치기필요': -0.8,    # -1.5 → -0.8
            '녹화중지': -0.6,       # -1.0 → -0.6
            '녹화중단': -0.6,       # -1.0 → -0.6
            '추적중지': -0.7,       # -1.2 → -0.7
            '현재': -0.4,          # -0.6 → -0.4
            '애매함': -0.5,         # -0.8 → -0.5
            '계륵': -0.7,          # -1.3 → -0.7
            '정으로보는느낌': -0.6,   # -1.0 → -0.6
            'ㅍㅌㅊ': -0.3,         # -0.5 → -0.3
            
            # 중립 키워드 (다양성 확대)
            '얼굴': 0.1,
            '육덕': 0.2,
            '코스': 0.1,
            '2인': 0.1,
            '3인': 0.1,
            '섹시': 0.3,
            '예쁨': 0.2,
            '몸매': 0.2,
            '상냥': 0.3,
            '츤데레': 0.2,
        }
    
    def calculate_rating_score(self, username):
        """사용자 레이팅 기반 점수 계산 (0.0 ~ 1.0) - 다양성 유지 시스템"""
        if username not in self.ratings_data:
            return 0.4  # 미평가 사용자 기본 점수 (0.2 → 0.4로 상향)
        
        rating_info = self.ratings_data[username]
        base_rating = rating_info.get('rating', 0) / 5.0  # 0.0 ~ 1.0 정규화
        comment = rating_info.get('comment', '').lower()
        
        # 키워드 가중치 적용 (범위 조정)
        keyword_bonus = 0.0
        for keyword, weight in self.keyword_weights.items():
            if keyword in comment:
                keyword_bonus += weight
        
        # 키워드 보너스 제한 조정 (-0.7 ~ +0.7)
        keyword_bonus = max(-0.7, min(0.7, keyword_bonus))
        
        # 기본 점수 계산
        raw_score = base_rating + keyword_bonus
        raw_score = max(0.0, min(1.0, raw_score))
        
        # 다양성 보정 적용 (부드러운 곡선)
        final_score = self._apply_diversity_adjustment(raw_score)
        
        return final_score
    
    def calculate_composite_score(self, username, file_info, user_files):
        """복합 점수 계산: 파일 점수 + 레이팅 점수"""
        # 기본 파일 점수 (0.0 ~ 1.0)
        file_score = self.calculate_file_score_basic(file_info, user_files)
        
        # 레이팅 점수 (0.0 ~ 1.0)
        rating_score = self.calculate_rating_score(username)
        
        # 가중 결합 (파일 점수 60%, 레이팅 점수 40%)
        composite_score = (file_score * 0.6) + (rating_score * 0.4)
        
        return {
            'composite_score': composite_score,
            'file_score': file_score,
            'rating_score': rating_score,
            'username': username
        }
    
    def calculate_file_score_basic(self, file_info, user_files):
        """기본 파일 점수 계산 (다양성 유지 시스템)"""
        file_name = file_info['name']
        file_size = file_info['size']
        
        size_score = 0.0
        rarity_score = 0.0
        date_score = 0.0
        
        try:
            # 파일 크기 점수 (적당한 곡선)
            all_sizes = [f['size'] for f in user_files]
            if all_sizes:
                max_size = max(all_sizes)
                min_size = min(all_sizes)
                if max_size > min_size:
                    normalized_score = (file_size - min_size) / (max_size - min_size)
                    # 1.5제곱으로 적당한 곡선 유지
                    size_score = normalized_score ** 1.5  # 너무 극단적이지 않게
                else:
                    size_score = 0.6  # 크기 차이 없으면 중상 점수
            
            # 희귀성 점수 (기본값 상향)
            rarity_score = 0.5  # 기본값 (0.3 → 0.5로 상향)
            
            # 날짜 점수 (기본값 상향)
            date_score = 0.4  # 기본값 (0.2 → 0.4로 상향)
            
        except Exception as e:
            logger.error(f"파일 점수 계산 오류: {file_name}, 에러: {e}")
            return 0.3  # 오류 시 기본값을 적당하게 (0.1 → 0.3)
        
        # 가중 평균 계산
        raw_score = (size_score * 0.6 + rarity_score * 0.25 + date_score * 0.15)
        
        # 다양성 보정 적용
        final_score = self._apply_diversity_adjustment(raw_score)
        
        return final_score
    
    def _apply_diversity_adjustment(self, score):
        """다양성 유지 보정 함수 - 부드러운 곡선으로 0.01~0.99 범위에서 고르게 분포"""
        import math
        
        # 시그모이드 곡선 적용으로 부드러운 분포 생성
        # 입력 범위 [0,1]을 [-6,6] 범위로 변환
        x = (score - 0.5) * 12  # -6 ~ +6 범위
        
        # 시그모이드 함수: 1 / (1 + e^(-x))
        sigmoid = 1.0 / (1.0 + math.exp(-x))
        
        # 0.01 ~ 0.99 범위로 스케일링
        adjusted = 0.01 + (sigmoid * 0.98)
        
        # 추가 미세 조정: 중간값 주변에서 더 넓은 분포
        if 0.3 <= score <= 0.7:
            # 중간 영역에서 약간의 랜덤성 추가 (파일명 해시 기반)
            hash_factor = (hash(str(score)) % 100) / 1000.0  # -0.05 ~ +0.05
            adjusted += hash_factor - 0.05
        
        return max(0.01, min(0.99, adjusted))
    
    def get_deletion_priority_list(self, capacity_finder):
        """삭제 우선순위 리스트 생성"""
        priority_list = []
        
        for username, user_data in capacity_finder.dic_files.items():
            files_with_scores = []
            
            for file_info in user_data['files']:
                score_data = self.calculate_composite_score(username, file_info, user_data['files'])
                files_with_scores.append({
                    'name': file_info['name'],
                    'size': file_info['size'],
                    'composite_score': score_data['composite_score'],
                    'file_score': score_data['file_score'],
                    'rating_score': score_data['rating_score'],
                    'username': username
                })
            
            # 점수 낮은 순 정렬 (삭제 우선순위)
            files_with_scores.sort(key=lambda x: x['composite_score'])
            
            priority_list.extend(files_with_scores)
        
        return priority_list
    
    def get_auto_deletion_suggestions(self, capacity_finder, target_savings_gb=10):
        """자동 삭제 추천 (목표 절약 용량 기준) - 다양성 유지 기준"""
        priority_list = self.get_deletion_priority_list(capacity_finder)
        target_savings_mb = target_savings_gb * 1024
        
        suggestions = []
        current_savings = 0
        
        for file_data in priority_list:
            if current_savings >= target_savings_mb:
                break
            
            # 삭제 기준: 복합 점수 0.25 이하 (적당한 기준)
            if file_data['composite_score'] <= 0.25:
                suggestions.append(file_data)
                current_savings += file_data['size']
        
        return {
            'suggested_files': suggestions,
            'total_savings_gb': current_savings / 1024,
            'files_count': len(suggestions),
            'criteria': 'composite_score <= 0.25'
        }
    
    def get_user_cleanup_analysis(self, username):
        """특정 사용자의 정리 분석"""
        if username not in self.ratings_data:
            return None
        
        rating_info = self.ratings_data[username]
        rating = rating_info.get('rating', 0)
        comment = rating_info.get('comment', '')
        
        # 정리 전략 결정
        if rating <= 2:
            strategy = "대부분 삭제 권장"
            keep_ratio = 0.1  # 10%만 유지
        elif rating == 3:
            strategy = "선별적 삭제"
            keep_ratio = 0.3  # 30% 유지
        elif rating >= 4:
            strategy = "보존 우선"
            keep_ratio = 0.7  # 70% 유지
        else:
            strategy = "기본 정리"
            keep_ratio = 0.5  # 50% 유지
        
        # 키워드 기반 조정
        if '가지치기필요' in comment:
            keep_ratio *= 0.5  # 더 많이 삭제
        elif '녹화중지' in comment:
            keep_ratio *= 0.3  # 대부분 삭제
        elif 'ㅅㅌㅊ' in comment or 'GOAT' in comment:
            keep_ratio = min(keep_ratio * 1.5, 0.9)  # 더 많이 보존
        
        return {
            'username': username,
            'rating': rating,
            'strategy': strategy,
            'keep_ratio': keep_ratio,
            'comment': comment
        }

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

class PathHistory:
    """경로 기록을 관리하는 클래스"""
    def __init__(self, config_file="path_history.json"):
        self.config_file = config_file
        self.history = self.load_history()
    
    def load_history(self):
        """JSON 파일에서 경로 기록을 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"경로 기록 로드됨: {len(data.get('paths', []))}개 경로")
                    return data
            else:
                logger.info("경로 기록 파일이 없음, 새로 생성")
                return {"paths": [], "last_updated": None}
        except Exception as e:
            logger.error(f"경로 기록 로드 오류: {e}")
            return {"paths": [], "last_updated": None}
    
    def save_history(self):
        """현재 경로 기록을 JSON 파일에 저장"""
        try:
            self.history["last_updated"] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            logger.info(f"경로 기록 저장됨: {self.config_file}")
        except Exception as e:
            logger.error(f"경로 기록 저장 오류: {e}")
    
    def add_path(self, path):
        """새로운 경로를 기록에 추가"""
        if not path or not os.path.exists(path):
            return False
        
        # 절대 경로로 변환
        abs_path = os.path.abspath(path)
        
        # 기존 경로 찾기
        existing_path = None
        for item in self.history["paths"]:
            if item["path"] == abs_path:
                existing_path = item
                break
        
        if existing_path:
            # 기존 경로 업데이트 (마지막 사용 시간, 사용 횟수 증가)
            existing_path["last_used"] = datetime.now().isoformat()
            existing_path["usage_count"] = existing_path.get("usage_count", 0) + 1
            logger.info(f"기존 경로 업데이트: {abs_path} (사용 횟수: {existing_path['usage_count']})")
        else:
            # 새 경로 추가
            new_path_info = {
                "path": abs_path,
                "display_name": os.path.basename(abs_path) or abs_path,
                "first_used": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "usage_count": 1
            }
            self.history["paths"].append(new_path_info)
            logger.info(f"새 경로 추가: {abs_path}")
        
        # 사용 횟수와 최근 사용 시간 기준으로 정렬
        self.history["paths"].sort(key=lambda x: (x.get("usage_count", 0), x.get("last_used", "")), reverse=True)
        
        # 최대 20개까지만 보관
        if len(self.history["paths"]) > 20:
            self.history["paths"] = self.history["paths"][:20]
        
        self.save_history()
        return True
    
    def get_paths(self):
        """저장된 경로 목록 반환"""
        return self.history.get("paths", [])
    
    def remove_path(self, path):
        """경로를 기록에서 제거"""
        abs_path = os.path.abspath(path)
        self.history["paths"] = [item for item in self.history["paths"] if item["path"] != abs_path]
        self.save_history()
        logger.info(f"경로 제거됨: {abs_path}")

class CapacityFinder:
    def __init__(self):
        self.current_path = None
        self.dic_files = {}  # {username: {'total_size': float, 'files': [{'name': str, 'size': float}]}}
        self.window = None  # GUI 윈도우 참조를 위해 추가
        self.path_history = PathHistory()  # 경로 기록 관리자 추가
        # 날짜 패턴 정의 (2025-06-26T15_09_46+09_00 형식)
        self.date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}[+-]\d{2}_\d{2}')
        
        # === 도구 간 간단한 네비게이션 컨텍스트 ===
        self.navigation_context = {
            'selected_user': None,        # 현재 선택된 사용자
            'source_tool': None,          # 출발점 도구
            'return_callback': None,      # 돌아갈 때 호출할 콜백
        }
        
        # === 지능형 큐레이션 시스템 추가 ===
        self.intelligent_system = IntelligentCurationSystem()
        
        logger.info("CapacityFinder 초기화 완료")
        logger.info("🧠 지능형 큐레이션 시스템 연동 완료 (다양성 유지 점수 분포 시스템)")
        
    def format_file_size(self, size_mb):
        """파일 사이즈를 적절한 단위(MB/GB)로 포맷팅하는 함수"""
        if size_mb >= 1024:  # 1GB 이상
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"
        
    def handle_path_confirmation(self, path):
        """GUI에서 경로가 확인되었을 때 호출되는 함수"""
        import time
        start_time = time.time()
        logger.info(f"경로 확인됨: {path}")
        logger.info(f"📊 경로 로딩 시작: {path}")
        
        self.current_path = path
        
        # 경로를 기록에 추가 (JSON에 자동 저장)
        if self.path_history.add_path(path):
            logger.info(f"경로가 기록에 저장됨: {path}")
        
        # 기존 데이터 초기화
        self.dic_files = {}
        
        # 파일 용량 계산
        logger.debug("파일 목록 및 용량 계산 시작")
        result_dict = self.listing_files()
        files_processed_time = time.time()
        logger.info(f"⏱️ 파일 처리 완료: {files_processed_time - start_time:.2f}초")
        
        if result_dict:
            # GUI 리스트 초기화
            self.window.clear_results()
            
            # 용량 기준으로 내림차순 정렬 (큰 것부터)
            sorted_users = sorted(result_dict.items(), key=lambda x: x[1]['total_size'], reverse=True)
            
            # 전체 파일 통계 계산
            total_files_size = sum(user_data['total_size'] for _, user_data in sorted_users)
            total_files_count = sum(len(user_data['files']) for _, user_data in sorted_users)
            formatted_total_size = self.format_file_size(total_files_size)
            
            logger.info(f"파일 분석 완료 - 총 {len(sorted_users)}명 사용자, 총 용량: {formatted_total_size}, 총 파일: {total_files_count}개")
            
            # 결과를 GUI에 표시 (헤더를 각 열에 맞춰 표시)
            self.window.add_header_with_totals("사용자별 파일 용량 (용량 큰 순)", formatted_total_size, total_files_count)
            for username, user_data in sorted_users:
                total_size = user_data['total_size']
                file_count = len(user_data['files'])
                formatted_size = self.format_file_size(total_size)
                
                # 새로운 트리 구조로 사용자 데이터 추가
                self.window.add_user_data(username, user_data, formatted_size)
                
                logger.debug(f"사용자: {username}, 총 용량: {formatted_size}, 파일 수: {file_count}")
            
            # CapacityFinder 인스턴스를 GUI에 설정하고 모델 정리 버튼 활성화
            self.window.set_capacity_finder(self)
            self.window.update_cleanup_button_state()
            
            # 전체 로딩 완료 시간 측정
            total_time = time.time() - start_time
            logger.info(f"🎯 전체 경로 로딩 완료: {total_time:.2f}초")
            logger.info(f"   📊 파일 처리: {files_processed_time - start_time:.2f}초")
            logger.info(f"   🖥️ GUI 표시: {total_time - (files_processed_time - start_time):.2f}초")
        else:
            logger.warning("처리할 파일이 없습니다.")
            self.window.add_result_to_list("처리할 파일이 없습니다.")
            self.window.update_cleanup_button_state()
            
            # 빈 결과 처리 시간도 측정
            total_time = time.time() - start_time
            logger.info(f"🎯 경로 로딩 완료 (빈 결과): {total_time:.2f}초")
        
    def get_file_size_info(self, file_path, file_name):
        """단일 파일의 크기 정보를 가져오는 함수 (멀티스레딩용)"""
        try:
            if os.path.isfile(file_path):
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                return [file_name, file_size_mb]
            return None
        except Exception as e:
            logger.error(f"파일 크기 가져오기 오류: {file_path}, 에러: {e}")
            return None

    def listing_files_capacity(self) -> list:
        """파일 용량을 계산하는 함수 (멀티스레딩 지원)"""
        list_files = []
        if self.current_path:
            try:
                import time
                start_time = time.time()
                
                # 1. 파일 목록 가져오기
                logger.info("📁 파일 목록 스캔 시작...")
                all_files = os.listdir(self.current_path)
                file_paths = [(os.path.join(self.current_path, file), file) for file in all_files]
                
                scan_time = time.time() - start_time
                logger.info(f"📁 파일 목록 스캔 완료: {len(file_paths)}개 파일 발견 ({scan_time:.2f}초)")
                
                if not file_paths:
                    return []
                
                # 2. 멀티스레딩으로 파일 크기 가져오기
                logger.info("🚀 멀티스레딩 파일 크기 분석 시작...")
                size_start = time.time()
                
                # 네트워크 환경을 고려하여 스레드 수 조정 (너무 많으면 오히려 느려질 수 있음)
                max_workers = min(20, len(file_paths))  # 최대 20개 스레드
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 각 파일의 크기를 병렬로 가져오기
                    future_to_file = {
                        executor.submit(self.get_file_size_info, file_path, file_name): file_name
                        for file_path, file_name in file_paths
                    }
                    
                    completed_count = 0
                    log_interval = max(1, len(file_paths) // 10)  # 10% 간격으로 로그
                    
                    for future in as_completed(future_to_file):
                        file_name = future_to_file[future]
                        try:
                            result = future.result()
                            if result is not None:
                                list_files.append(result)
                            
                            completed_count += 1
                            
                            # 진행 상황 로그 (10% 간격)
                            if completed_count % log_interval == 0 or completed_count == len(file_paths):
                                progress = (completed_count / len(file_paths)) * 100
                                elapsed = time.time() - size_start
                                logger.info(f"⚡ 진행률: {progress:.1f}% ({completed_count}/{len(file_paths)}) - {elapsed:.1f}초")
                        
                        except Exception as e:
                            logger.error(f"파일 크기 가져오기 실패: {file_name}, 에러: {e}")
                
                total_time = time.time() - start_time
                size_time = time.time() - size_start
                
                logger.info(f"✅ 파일 목록 읽기 완료: {len(list_files)}개 파일")
                logger.info(f"   📊 총 소요 시간: {total_time:.2f}초")
                logger.info(f"   📁 파일 스캔: {scan_time:.2f}초")
                logger.info(f"   🚀 크기 분석: {size_time:.2f}초")
                logger.info(f"   ⚡ 속도 향상: {max_workers}개 스레드 사용")
                
                return list_files
                
            except Exception as e:
                logger.error(f"파일 목록 읽기 오류: {e}")
                return []
        else:
            logger.warning("경로가 설정되지 않았습니다.")
            return []
    
    def process_file_name(self, file_info):
        """단일 파일의 이름을 처리하는 함수 (멀티스레딩용)"""
        file_name = file_info[0]
        file_size = file_info[1]
        
        username = self.file_name_handle(file_name)
        if username:
            return {
                'username': username,
                'file_name': file_name,
                'file_size': file_size,
                'success': True
            }
        else:
            return {
                'file_name': file_name,
                'success': False
            }

    def listing_files(self):
        """파일 목록을 가져와서 사용자별로 용량을 계산하는 함수 (멀티스레딩 지원)"""
        import time
        start_time = time.time()
        
        file_list = self.listing_files_capacity()
        
        if not file_list:
            return {}
        
        parsing_start = time.time()
        logger.info(f"🔍 파일명 파싱 시작: {len(file_list)}개 파일")
        
        parsed_count = 0
        failed_files = []
        
        # 파일 수가 많을 때만 멀티스레딩 사용 (적을 때는 오버헤드가 더 클 수 있음)
        if len(file_list) > 100:
            # 멀티스레딩으로 파일명 처리
            max_workers = min(10, len(file_list))  # 파일명 처리는 CPU 작업이라 스레드 수 제한
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self.process_file_name, file_info): file_info
                    for file_info in file_list
                }
                
                completed_count = 0
                log_interval = max(1, len(file_list) // 10)  # 10% 간격으로 로그
                
                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    try:
                        result = future.result()
                        
                        if result['success']:
                            username = result['username']
                            file_name = result['file_name']
                            file_size = result['file_size']
                            
                            # 사용자별 용량 누적
                            if username not in self.dic_files:
                                self.dic_files[username] = {'total_size': 0.0, 'files': []}
                            self.dic_files[username]['total_size'] += file_size
                            self.dic_files[username]['files'].append({'name': file_name, 'size': file_size})
                            parsed_count += 1
                        else:
                            failed_files.append(result['file_name'])
                        
                        completed_count += 1
                        
                        # 진행 상황 로그
                        if completed_count % log_interval == 0 or completed_count == len(file_list):
                            progress = (completed_count / len(file_list)) * 100
                            elapsed = time.time() - parsing_start
                            logger.info(f"🔍 파싱 진행률: {progress:.1f}% ({completed_count}/{len(file_list)}) - {elapsed:.1f}초")
                    
                    except Exception as e:
                        logger.error(f"파일명 처리 실패: {file_info[0]}, 에러: {e}")
                        failed_files.append(file_info[0])
        
        else:
            # 단일스레드로 파일명 처리 (파일 수가 적을 때)
            logger.info("📝 단일스레드 파일명 처리 (파일 수가 적음)")
            for file_info in file_list:
                file_name = file_info[0]
                file_size = file_info[1]
                
                username = self.file_name_handle(file_name)
                if username:
                    # 사용자별 용량 누적
                    if username not in self.dic_files:
                        self.dic_files[username] = {'total_size': 0.0, 'files': []}
                    self.dic_files[username]['total_size'] += file_size
                    self.dic_files[username]['files'].append({'name': file_name, 'size': file_size})
                    parsed_count += 1
                else:
                    failed_files.append(file_name)
        
        parsing_time = time.time() - parsing_start
        total_time = time.time() - start_time
        
        logger.info(f"✅ 파일 분석 완료:")
        logger.info(f"   📁 총 파일: {len(file_list)}개")
        logger.info(f"   👥 인식된 사용자: {len(self.dic_files)}명")
        logger.info(f"   ✅ 성공적으로 파싱: {parsed_count}개")
        logger.info(f"   ❌ 파싱 실패: {len(failed_files)}개")
        logger.info(f"   ⏱️ 파싱 시간: {parsing_time:.3f}초")
        logger.info(f"   ⏱️ 전체 시간: {total_time:.3f}초")
        
        # 실패한 파일들 로그 (너무 많지 않을 때만)
        if failed_files and len(failed_files) <= 10:
            logger.warning(f"파싱 실패한 파일들: {failed_files}")
        elif failed_files:
            logger.warning(f"파싱 실패한 파일 {len(failed_files)}개 (일부): {failed_files[:5]}...")
        
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
                logger.warning(f"날짜 패턴을 찾을 수 없음: {file_name}")
                return None
            
            date_part = date_match.group()
            date_start = date_match.start()
            
            # 날짜 이전 부분 추출
            before_date = name_without_ext[:date_start].rstrip('-')
            
            # '-'로 분리
            parts = before_date.split('-')
            
            if len(parts) < 2:
                logger.warning(f"파일명 구조가 올바르지 않음: {file_name}")
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
                logger.warning(f"알려진 사이트를 찾을 수 없음: {file_name}")
                return None
            
            if not channel_parts:
                logger.warning(f"채널명을 찾을 수 없음: {file_name}")
                return None
            
            # 채널명 결합 (여러 부분이 있을 경우 '-'로 다시 결합)
            channel_name = '-'.join(channel_parts)
            
            logger.debug(f"파일명 처리 완료: {file_name} -> 사이트: {site_part}, 채널: {channel_name}, 날짜: {date_part}")
            return channel_name
                    
        except Exception as e:
            logger.error(f"파일명 처리 중 오류: {file_name}, 에러: {e}")
            return None

    def extract_date_from_filename(self, file_name):
        """파일명에서 날짜 추출"""
        try:
            date_match = self.date_pattern.search(file_name)
            if date_match:
                date_str = date_match.group()
                # 2025-06-26T15_09_46+09_00 -> datetime 변환
                file_date = datetime.fromisoformat(date_str.replace('_', ':'))
                return file_date
        except Exception as e:
            logger.error(f"날짜 추출 오류: {file_name}, 에러: {e}")
        return None

    def select_representative_samples(self, files):
        """더 대표성 있는 샘플 선택"""
        if len(files) <= 5:
            return files  # 파일 적으면 다 보여주기
        
        samples = []
        
        # 파일들을 날짜순으로 정렬
        files_with_dates = []
        for file_info in files:
            file_date = self.extract_date_from_filename(file_info['name'])
            if file_date:
                files_with_dates.append({'file': file_info, 'date': file_date})
        
        if not files_with_dates:
            return files[:5]  # 날짜 추출 실패시 첫 5개
        
        files_with_dates.sort(key=lambda x: x['date'])
        sorted_files = [item['file'] for item in files_with_dates]
        
        # 1. 가장 최근 파일
        samples.append(sorted_files[-1])
        
        # 2. 가장 큰 파일  
        largest_file = max(files, key=lambda x: x['size'])
        if largest_file not in samples:
            samples.append(largest_file)
        
        # 3. 시간대별 분산 샘플 (처음/중간)
        if len(sorted_files) > 2:
            # 첫 기록
            if sorted_files[0] not in samples:
                samples.append(sorted_files[0])
            # 중간
            middle_file = sorted_files[len(sorted_files)//2]
            if middle_file not in samples:
                samples.append(middle_file)
        
        # 4. 남은 자리에 다른 파일들
        for file_info in files:
            if file_info not in samples and len(samples) < 5:
                samples.append(file_info)
        
        return samples[:5]  # 최대 5개

    def create_decision_list(self):
        """결정하기 쉬운 형태로 정리"""
        if not self.dic_files:
            logger.warning("분석할 데이터가 없습니다.")
            return []
        
        # 용량 큰 순으로 정렬
        sorted_models = sorted(
            self.dic_files.items(), 
            key=lambda x: x[1]['total_size'], 
            reverse=True
        )
        
        decision_list = []
        for username, data in sorted_models:
            # 대표 파일들 선택
            sample_files = self.select_representative_samples(data['files'])
            
            decision_list.append({
                'username': username,
                'total_size': data['total_size'],
                'file_count': len(data['files']),
                'sample_files': sample_files,
                'potential_savings': data['total_size']  # 삭제시 절약 용량
            })
        
        return decision_list

    def compare_user_sites(self, username):
        """특정 사용자의 사이트별 파일 비교 및 중복 제거 추천
        
        Args:
            username: 비교할 사용자명
            
        Returns:
            dict: {
                'files_to_delete': [{'name': str, 'size': float, 'site': str, 'date': str}],
                'total_savings': float,
                'username': str,
                'comparison_results': [dict]  # 비교 결과 상세
            }
        """
        if username not in self.dic_files:
            return None
        
        user_files = self.dic_files[username]['files']
        
        # 파일들을 사이트별, 날짜별로 그룹화
        date_site_groups = {}  # {date: {site: [files]}}
        
        for file_info in user_files:
            file_name = file_info['name']
            file_size = file_info['size']
            
            # 파일명에서 사이트와 날짜 추출
            site, date_str = self.extract_site_and_date(file_name)
            if not site or not date_str:
                continue
            
            if date_str not in date_site_groups:
                date_site_groups[date_str] = {}
            
            if site not in date_site_groups[date_str]:
                date_site_groups[date_str][site] = []
            
            date_site_groups[date_str][site].append({
                'name': file_name,
                'size': file_size,
                'site': site,
                'date': date_str
            })
        
        # 같은 날짜에 여러 사이트가 있는 경우 용량 비교
        files_to_delete = []
        comparison_results = []
        total_savings = 0
        
        for date_str, sites in date_site_groups.items():
            if len(sites) <= 1:
                continue  # 사이트가 하나뿐이면 비교할 필요 없음
            
            # 사이트별 총 용량 계산
            site_totals = {}
            for site, files in sites.items():
                site_totals[site] = sum(f['size'] for f in files)
            
            # 가장 큰 용량의 사이트 찾기
            max_site = max(site_totals.items(), key=lambda x: x[1])
            max_site_name = max_site[0]
            max_size = max_site[1]
            
            # 다른 사이트들의 파일을 삭제 대상으로 추가
            comparison_result = {
                'date': date_str,
                'sites': {},
                'keep_site': max_site_name,
                'delete_sites': []
            }
            
            for site, files in sites.items():
                site_total = site_totals[site]
                comparison_result['sites'][site] = {
                    'files': files,
                    'total_size': site_total,
                    'file_count': len(files)
                }
                
                if site != max_site_name:
                    # 작은 용량의 사이트 파일들을 삭제 대상에 추가
                    for file_info in files:
                        files_to_delete.append(file_info)
                        total_savings += file_info['size']
                    comparison_result['delete_sites'].append(site)
            
            comparison_results.append(comparison_result)
        
        return {
            'files_to_delete': files_to_delete,
            'total_savings': total_savings,
            'username': username,
            'comparison_results': comparison_results
        }
    
    def extract_site_and_date(self, file_name):
        """파일명에서 사이트와 날짜를 추출
        
        Args:
            file_name: 파일명
            
        Returns:
            tuple: (site, date_str) 또는 (None, None)
        """
        if not file_name:
            return None, None
            
        try:
            # 확장자 제거
            name_without_ext = file_name.split('.')[0] if '.' in file_name else file_name
            
            # 날짜 패턴 찾기
            date_match = self.date_pattern.search(name_without_ext)
            if not date_match:
                return None, None
            
            date_part = date_match.group()
            date_start = date_match.start()
            
            # 날짜 이전 부분 추출
            before_date = name_without_ext[:date_start].rstrip('-')
            
            # '-'로 분리
            parts = before_date.split('-')
            
            if len(parts) < 2:
                return None, None
            
            # 사이트 찾기
            for part in parts:
                if SiteType.is_valid_site(part):
                    # 날짜에서 시간 부분만 추출해서 날짜로 변환 (2025-06-26 형식)
                    date_only = date_part.split('T')[0] if 'T' in date_part else date_part
                    return part, date_only
            
            return None, None
                    
        except Exception as e:
            logger.error(f"사이트/날짜 추출 중 오류: {file_name}, 에러: {e}")
            return None, None

    def get_available_users(self):
        """분석된 사용자 목록 반환"""
        if not self.dic_files:
            return []
        return list(self.dic_files.keys())

    def calculate_file_score(self, file_info, user_files):
        """파일의 메타데이터 기반 점수 계산
        
        Args:
            file_info: 개별 파일 정보
            user_files: 해당 사용자의 전체 파일 목록
            
        Returns:
            float: 0.0 ~ 1.0 사이의 점수
        """
        file_name = file_info['name']
        file_size = file_info['size']
        
        # 기본 점수 구성 요소들
        size_score = 0.0
        rarity_score = 0.0
        date_score = 0.0
        
        try:
            # 1. 파일 크기 점수 (60% 가중치) - 증가
            all_sizes = [f['size'] for f in user_files]
            if all_sizes:
                max_size = max(all_sizes)
                min_size = min(all_sizes)
                if max_size > min_size:
                    # 크기 점수를 더 관대하게 계산 (상위 30% 이상이면 0.8+ 점수)
                    normalized_score = (file_size - min_size) / (max_size - min_size)
                    # 제곱근 적용해서 중간값들도 더 높은 점수 받도록
                    size_score = min(normalized_score ** 0.5, 1.0)
                else:
                    size_score = 1.0
            
            # 2. 희귀성 점수 (25% 가중치) - 증가
            file_date = self.extract_date_from_filename(file_name)
            if file_date:
                # 같은 날짜의 파일 수가 적을수록 희귀함
                same_date_count = 0
                for f in user_files:
                    f_date = self.extract_date_from_filename(f['name'])
                    if f_date and f_date.date() == file_date.date():
                        same_date_count += 1
                
                if same_date_count <= 1:
                    rarity_score = 1.0
                elif same_date_count <= 2:
                    rarity_score = 0.9
                elif same_date_count <= 3:
                    rarity_score = 0.8
                elif same_date_count <= 5:
                    rarity_score = 0.7
                else:
                    rarity_score = 0.5
            else:
                # 날짜를 추출할 수 없는 파일은 중간 점수
                rarity_score = 0.6
            
            # 3. 날짜 점수 (15% 가중치) - 증가, 최근일수록 높은 점수
            if file_date:
                all_dates = []
                for f in user_files:
                    f_date = self.extract_date_from_filename(f['name'])
                    if f_date:
                        all_dates.append(f_date)
                
                if all_dates:
                    all_dates.sort()
                    oldest = all_dates[0]
                    newest = all_dates[-1]
                    
                    if newest > oldest:
                        total_days = (newest - oldest).days
                        file_days = (file_date - oldest).days
                        date_score = file_days / total_days if total_days > 0 else 1.0
                    else:
                        date_score = 1.0
                else:
                    date_score = 0.8
            else:
                # 날짜를 추출할 수 없는 파일은 중간 점수
                date_score = 0.5
        
        except Exception as e:
            logger.error(f"점수 계산 오류: {file_name}, 에러: {e}")
            return 0.6  # 기본값을 0.6으로 상향
        
        # 가중 평균 계산 (시간 점수 제거, 다른 요소들 가중치 증가)
        final_score = (size_score * 0.6 + rarity_score * 0.25 + date_score * 0.15)
        
        # 추가 보너스: 매우 큰 파일에게 보너스 점수
        if all_sizes:
            size_percentile = (file_size - min(all_sizes)) / (max(all_sizes) - min(all_sizes)) if max(all_sizes) > min(all_sizes) else 1.0
            if size_percentile >= 0.9:  # 상위 10% 크기
                final_score = min(final_score + 0.1, 1.0)
            elif size_percentile >= 0.8:  # 상위 20% 크기
                final_score = min(final_score + 0.05, 1.0)
        
        return min(max(final_score, 0.0), 1.0)  # 0.0 ~ 1.0 사이로 클램핑

    def get_user_files_with_scores(self, username):
        """특정 사용자의 파일들을 점수와 함께 반환
        
        Args:
            username: 사용자명
            
        Returns:
            list: [{'name': str, 'size': float, 'score': float, 'rank': int}, ...]
        """
        if username not in self.dic_files:
            return []
        
        user_files = self.dic_files[username]['files']
        
        # 각 파일에 점수 추가
        files_with_scores = []
        for file_info in user_files:
            score = self.calculate_file_score(file_info, user_files)
            files_with_scores.append({
                'name': file_info['name'],
                'size': file_info['size'],
                'score': score,
                'rank': 0  # 나중에 설정
            })
        
        # 점수 기준으로 정렬 (높은 점수부터)
        files_with_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # 순위 설정
        for i, file_info in enumerate(files_with_scores):
            file_info['rank'] = i + 1
        
        return files_with_scores

    def get_selection_candidates(self, username, top_n=50):
        """선별 후보 파일들 반환 (상위 N개) - 지능형 복합점수 시스템 적용
        
        Args:
            username: 사용자명
            top_n: 후보로 선택할 파일 수
            
        Returns:
            dict: {
                'candidates': list,  # 선별 후보 파일들
                'excluded': list,    # 자동 제외된 파일들
                'total_files': int,  # 전체 파일 수
                'username': str
            }
        """
        if username not in self.dic_files:
            return None
        
        user_data = self.dic_files[username]
        files = user_data['files']
        
        # 지능형 복합 점수를 사용한 파일 분석
        files_with_scores = []
        for file_info in files:
            # 지능형 시스템의 복합 점수 계산 (파일점수 + 레이팅점수)
            score_data = self.intelligent_system.calculate_composite_score(username, file_info, files)
            files_with_scores.append({
                'name': file_info['name'],
                'size': file_info['size'],
                'score': score_data['composite_score'],  # 복합 점수 사용
                'file_score': score_data['file_score'],
                'rating_score': score_data['rating_score'],
                'rank': 0  # 나중에 설정
            })
        
        # 복합 점수 기준으로 정렬 (높은 점수부터)
        files_with_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # 순위 설정
        for i, file_info in enumerate(files_with_scores):
            file_info['rank'] = i + 1
        
        total_files = len(files_with_scores)
        
        # 상위 N개를 후보로 선택
        top_n = min(top_n, total_files)
        candidates = files_with_scores[:top_n]
        excluded = files_with_scores[top_n:]
        
        logger.info(f"🎯 선별 후보 생성: {username} - 총 {total_files}개 중 상위 {top_n}개 선택 (지능형 복합점수 적용)")
        
        return {
            'candidates': candidates,
            'excluded': excluded,
            'total_files': total_files,
            'username': username
        }
    
    # === 지능형 큐레이션 시스템 통합 메서드들 ===
    
    def get_intelligent_deletion_analysis(self, target_savings_gb=10):
        """지능형 삭제 분석 - 레이팅 기반 자동 추천"""
        logger.info(f"🧠 지능형 삭제 분석 시작 (목표: {target_savings_gb}GB 절약)")
        
        # 자동 삭제 추천
        suggestions = self.intelligent_system.get_auto_deletion_suggestions(self, target_savings_gb)
        
        # 사용자별 정리 전략 분석
        user_strategies = {}
        for username in self.dic_files.keys():
            strategy = self.intelligent_system.get_user_cleanup_analysis(username)
            if strategy:
                user_strategies[username] = strategy
        
        # 통계 계산
        total_files = sum(len(data['files']) for data in self.dic_files.values())
        suggested_count = suggestions['files_count']
        suggested_savings = suggestions['total_savings_gb']
        
        analysis_result = {
            'suggestions': suggestions,
            'user_strategies': user_strategies,
            'statistics': {
                'total_files': total_files,
                'suggested_files': suggested_count,
                'suggested_savings_gb': suggested_savings,
                'efficiency_ratio': suggested_count / total_files if total_files > 0 else 0
            }
        }
        
        logger.info(f"✅ 분석 완료: {suggested_count}개 파일, {suggested_savings:.2f}GB 절약 가능")
        return analysis_result
    
    def get_user_intelligence_report(self, username):
        """특정 사용자의 지능형 분석 리포트"""
        if username not in self.dic_files:
            return None
        
        user_data = self.dic_files[username]
        files = user_data['files']
        
        # 각 파일의 복합 점수 계산
        scored_files = []
        for file_info in files:
            score_data = self.intelligent_system.calculate_composite_score(username, file_info, files)
            scored_files.append({
                'name': file_info['name'],
                'size': file_info['size'],
                'composite_score': score_data['composite_score'],
                'file_score': score_data['file_score'],
                'rating_score': score_data['rating_score']
            })
        
        # 점수별 정렬
        scored_files.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # 통계 계산 (다양성 유지 기준)
        high_quality = [f for f in scored_files if f['composite_score'] >= 0.7]   # 0.8 → 0.7
        medium_quality = [f for f in scored_files if 0.3 <= f['composite_score'] < 0.7]  # 0.2~0.8 → 0.3~0.7
        low_quality = [f for f in scored_files if f['composite_score'] < 0.3]     # 0.2 → 0.3
        
        # 사용자 정리 전략
        cleanup_strategy = self.intelligent_system.get_user_cleanup_analysis(username)
        
        return {
            'username': username,
            'files': scored_files,
            'quality_breakdown': {
                'high_quality': len(high_quality),
                'medium_quality': len(medium_quality),
                'low_quality': len(low_quality)
            },
            'cleanup_strategy': cleanup_strategy,
            'total_size': user_data['total_size'],
            'file_count': len(files)
        }
    
    def get_priority_deletion_list(self, count_limit=100, balanced_mode=False):
        """우선순위 기반 삭제 리스트 (전체 분석)
        
        Args:
            count_limit: 표시할 파일 수
            balanced_mode: 균등 분배 모드 (각 사용자별로 골고루 선택)
        """
        logger.info(f"🎯 우선순위 삭제 리스트 생성 (상위 {count_limit}개, 균등모드: {balanced_mode})")
        
        priority_list = self.intelligent_system.get_deletion_priority_list(self)
        
        if balanced_mode:
            # 균등 분배 모드: 각 사용자별로 골고루 선택
            top_priorities = self._get_balanced_priority_list(priority_list, count_limit)
        else:
            # 기본 모드: 점수 낮은 순으로 상위 N개
            top_priorities = priority_list[:count_limit]
        
        # 사용자별 통계
        user_stats = {}
        for file_data in top_priorities:
            username = file_data['username']
            if username not in user_stats:
                user_stats[username] = {'count': 0, 'size': 0}
            user_stats[username]['count'] += 1
            user_stats[username]['size'] += file_data['size']
        
        total_savings = sum(f['size'] for f in top_priorities)
        
        return {
            'priority_files': top_priorities,
            'user_breakdown': user_stats,
            'total_savings_gb': total_savings / 1024,
            'file_count': len(top_priorities),
            'balanced_mode': balanced_mode
        }
    
    def _get_balanced_priority_list(self, priority_list, count_limit):
        """균등 분배 방식으로 우선순위 리스트 생성"""
        # 사용자별로 파일 그룹화
        user_files = {}
        for file_data in priority_list:
            username = file_data['username']
            if username not in user_files:
                user_files[username] = []
            user_files[username].append(file_data)
        
        total_users = len(user_files)
        if total_users == 0:
            return []
        
        # 사용자별 기본 할당량 계산
        base_per_user = max(1, count_limit // total_users)  # 최소 1개씩
        remaining = count_limit - (base_per_user * total_users)
        
        balanced_list = []
        user_counts = {}
        
        # 1단계: 각 사용자별로 기본 할당량만큼 선택
        for username, files in user_files.items():
            selected_count = min(base_per_user, len(files))
            balanced_list.extend(files[:selected_count])
            user_counts[username] = selected_count
        
        # 2단계: 남은 슬롯을 파일이 많은 사용자 순으로 배분
        if remaining > 0:
            # 사용자별 남은 파일 수 계산
            remaining_files = []
            for username, files in user_files.items():
                used_count = user_counts[username]
                if used_count < len(files):
                    # (남은 파일 수, 사용자명, 파일 리스트)
                    remaining_files.append((len(files) - used_count, username, files[used_count:]))
            
            # 남은 파일이 많은 사용자 순으로 정렬
            remaining_files.sort(key=lambda x: x[0], reverse=True)
            
            # 남은 슬롯 배분
            for remaining_count, username, files in remaining_files:
                if remaining <= 0:
                    break
                
                additional = min(remaining, remaining_count, 10)  # 한 사용자당 최대 10개 추가
                balanced_list.extend(files[:additional])
                remaining -= additional
        
        # 최종적으로 점수순으로 정렬
        balanced_list.sort(key=lambda x: x['composite_score'])
        
        logger.info(f"균등 분배 완료: {len(balanced_list)}개 파일, {len(user_counts)}명 사용자")
        
        return balanced_list[:count_limit]
    
    def execute_intelligent_cleanup(self, analysis_result, confirm_callback=None):
        """지능형 정리 실행"""
        suggested_files = analysis_result['suggestions']['suggested_files']
        
        if not suggested_files:
            logger.warning("삭제할 파일이 없습니다.")
            return False
        
        # 확인 콜백이 있으면 호출
        if confirm_callback:
            if not confirm_callback(suggested_files):
                logger.info("사용자가 지능형 정리를 취소했습니다.")
                return False
        
        # 파일 삭제 실행
        deleted_files = []
        deleted_size = 0
        
        for file_data in suggested_files:
            file_path = os.path.join(self.current_path, file_data['name'])
            
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files.append(file_data)
                    deleted_size += file_data['size']
                    logger.debug(f"삭제 완료: {file_data['name']}")
                else:
                    logger.warning(f"파일을 찾을 수 없음: {file_path}")
            except Exception as e:
                logger.error(f"파일 삭제 오류: {file_path}, 에러: {e}")
        
        # 삭제 결과 통계
        deleted_size_gb = deleted_size / 1024
        logger.info(f"🎯 지능형 정리 완료: {len(deleted_files)}개 파일, {deleted_size_gb:.2f}GB 절약")
        
        return {
            'deleted_files': deleted_files,
            'deleted_count': len(deleted_files),
            'deleted_size_gb': deleted_size_gb,
            'success': True
        }

def main():
    """메인 함수에서 GUI 애플리케이션을 실행합니다."""
    app = QApplication(sys.argv)
    
    # CapacityFinder 인스턴스 생성
    finder = CapacityFinder()
    
    # GUI 생성 시 콜백 함수와 경로 기록 전달
    finder.window = MainWindow(
        on_path_confirmed=finder.handle_path_confirmation,
        path_history=finder.path_history
    )
    finder.window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
