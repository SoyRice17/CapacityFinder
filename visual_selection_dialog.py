import sys
import os
import json
import math
import time
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QScrollArea, QWidget,
                             QMessageBox, QTextEdit, QSplitter, QSpinBox, 
                             QCheckBox, QProgressBar, QGroupBox, QGridLayout,
                             QSlider, QFrame, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot, QSize
from PyQt5.QtGui import QFont, QColor, QPixmap, QPainter, QPen, QBrush
import subprocess

# FFmpeg 관리자 import
from ffmpeg_manager import FFmpegManager

class ThumbnailExtractorThread(QThread):
    """썸네일 추출을 백그라운드에서 처리하는 스레드"""
    thumbnail_ready = pyqtSignal(str, QPixmap)  # 파일명, 썸네일
    
    def __init__(self, file_list, thumbnail_size=(2048, 925)):
        super().__init__()
        self.file_list = file_list
        self.thumbnail_size = thumbnail_size
        self.current_path = ""
        self.stop_requested = False  # 중단 요청 플래그
        
        # FFmpeg 매니저 초기화
        self.ffmpeg_manager = FFmpegManager()
        self.ffmpeg_path, self.ffprobe_path = self.ffmpeg_manager.get_ffmpeg_paths()
        
    def request_stop(self):
        """썸네일 추출 중단 요청"""
        print("🛑 썸네일 추출 중단 요청됨")
        self.stop_requested = True
    
    def set_path(self, path):
        self.current_path = path
    
    def run(self):
        """고성능 썸네일 배치 추출 🚀"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        print(f"🎬 배치 썸네일 추출 시작: {len(self.file_list)}개 파일")
        start_time = time.time()
        
        # 중단 요청 확인
        if self.stop_requested:
            print("🛑 시작 전 중단 요청으로 작업 취소")
            return
        
        # 네트워크 드라이브 확인 및 적응적 스레드 수 결정
        first_file_path = os.path.join(self.current_path, self.file_list[0]['name']) if self.file_list else ""
        is_network_path = first_file_path.startswith('\\\\') or first_file_path.startswith('//')
        
        if is_network_path:
            max_workers = 1  # 네트워크 드라이브는 순차 처리
            print("🌐 네트워크 드라이브 감지 - 순차 썸네일 생성 모드")
        else:
            max_workers = min(3, len(self.file_list))  # 로컬은 최대 3개 동시 처리
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 썸네일 추출 작업 제출
            future_to_file = {}
            for file_info in self.file_list:
                # 중단 요청 확인 (작업 제출 단계)
                if self.stop_requested:
                    print(f"🛑 작업 제출 중 중단 요청됨. 제출된 작업: {len(future_to_file)}개")
                    break
                    
                file_name = file_info['name'] 
                file_path = os.path.join(self.current_path, file_name)
                
                if os.path.exists(file_path):
                    future = executor.submit(self.extract_thumbnail, file_path)
                    future_to_file[future] = file_name
            
            # 제출된 작업이 없으면 종료
            if not future_to_file:
                print("🛑 제출된 작업이 없거나 중단 요청으로 종료")
                return
            
            print(f"📋 총 {len(future_to_file)}개 작업 제출됨. 진행 상황 모니터링...")
            
            # 결과 수집 및 발신
            completed_count = 0
            for future in as_completed(future_to_file, timeout=300):
                try:
                    # 중단 요청 확인 (결과 처리 단계)
                    if self.stop_requested:
                        print(f"🛑 결과 처리 중 중단 요청됨. 완료된 작업: {completed_count}/{len(future_to_file)}")
                        # 남은 작업들을 취소하려 시도 (이미 실행 중인 것은 취소 안됨)
                        for remaining_future in future_to_file:
                            if not remaining_future.done():
                                remaining_future.cancel()
                        break
                    
                    file_name = future_to_file[future]
                    thumbnail = future.result()
                    completed_count += 1
                    
                    if thumbnail:
                        self.thumbnail_ready.emit(file_name, thumbnail)
                        print(f"✅ [{completed_count}/{len(future_to_file)}] {file_name} 완료")
                    else:
                        print(f"❌ [{completed_count}/{len(future_to_file)}] {file_name} 실패")
                        
                except Exception as e:
                    file_name = future_to_file[future]
                    completed_count += 1
                    print(f"💥 [{completed_count}/{len(future_to_file)}] {file_name} 예외: {e}")
        
        elapsed_time = time.time() - start_time
        if self.stop_requested:
            print(f"🛑 썸네일 추출 중단됨: {completed_count}개 완료, {elapsed_time:.1f}초 소요")
        else:
            print(f"🎯 배치 추출 완료: {len(self.file_list)}개 파일, {elapsed_time:.1f}초 소요")
            print(f"   ⚡ 평균 속도: {len(self.file_list)/elapsed_time:.1f}개/초")
    


    def detect_hardware_acceleration(self):
        """하드웨어 가속 지원 여부 감지"""
        if not hasattr(self, '_hw_accel'):
            self._hw_accel = None
            try:
                # GPU 가속 지원 확인 (하이브리드 시스템에서는 항상 로컬 처리)
                result = subprocess.run([self.ffmpeg_path, '-hide_banner', '-encoders'], 
                                      capture_output=True, text=True, timeout=5)
                if 'h264_nvenc' in result.stdout:
                    self._hw_accel = 'nvenc'
                    print("🚀 NVIDIA GPU 가속 감지!")
                elif 'h264_qsv' in result.stdout:
                    self._hw_accel = 'qsv'
                    print("🚀 Intel QSV 가속 감지!")
                elif 'h264_amf' in result.stdout:
                    self._hw_accel = 'amf'
                    print("🚀 AMD AMF 가속 감지!")
                else:
                    print("⚡ CPU 모드 (하드웨어 가속 없음)")
            except:
                print("⚡ CPU 모드 (가속 감지 실패)")
        return self._hw_accel

    def get_thumbnail_cache_path(self, video_path):
        """썸네일 캐시 경로 생성"""
        try:
            # 현재 폴더의 상위 폴더 경로
            current_dir = os.path.dirname(video_path)
            parent_dir = os.path.dirname(current_dir)
            
            # 영상 제목 (확장자 제외)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            
            # 메타데이터 경로 구성
            metadata_dir = os.path.join(parent_dir, "metadata", video_name)
            thumbnail_path = os.path.join(metadata_dir, "image_grid_large.jpg")
            
            return metadata_dir, thumbnail_path
            
        except Exception as e:
            print(f"썸네일 캐시 경로 생성 실패: {e}")
            return None, None

    def load_cached_thumbnail(self, video_path):
        """캐시된 썸네일 로드"""
        try:
            metadata_dir, thumbnail_path = self.get_thumbnail_cache_path(video_path)
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                print(f"📁 캐시된 썸네일 발견: {os.path.basename(thumbnail_path)}")
                
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    # 썸네일 크기로 리사이즈
                    scaled_pixmap = pixmap.scaled(
                        self.thumbnail_size[0], self.thumbnail_size[1],
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    print(f"✅ 캐시된 썸네일 로드 성공")
                    return scaled_pixmap
                else:
                    print(f"❌ 캐시된 썸네일 파일 손상")
            else:
                print(f"📂 캐시된 썸네일 없음, 새로 생성 필요")
                    
        except Exception as e:
            print(f"캐시된 썸네일 로드 실패: {e}")
        
        return None

    def save_thumbnail_cache(self, video_path, thumbnail_pixmap):
        """썸네일을 캐시로 저장"""
        try:
            metadata_dir, thumbnail_path = self.get_thumbnail_cache_path(video_path)
            
            if not metadata_dir or not thumbnail_path:
                return False
            
            # 메타데이터 폴더 생성
            os.makedirs(metadata_dir, exist_ok=True)
            
            # 썸네일 저장
            success = thumbnail_pixmap.save(thumbnail_path, "JPEG", 95)  # 95% 품질
            
            if success:
                print(f"💾 썸네일 캐시 저장 완료: {os.path.basename(thumbnail_path)}")
                return True
            else:
                print(f"❌ 썸네일 캐시 저장 실패")
                return False
                
        except Exception as e:
            print(f"썸네일 캐시 저장 실패: {e}")
            return False

    def get_smart_frame_timestamps(self, video_path, duration, target_count=20):
        """스마트 프레임 선택 - 액션 위주 씬 변화 감지"""
        try:
            print(f"🎯 스마트 프레임 분석 시작: {os.path.basename(video_path)}")
            
            # 네트워크 드라이브 확인 및 타임아웃 조정
            is_network_path = video_path.startswith('\\\\') or video_path.startswith('//')
            timeout_duration = 120 if is_network_path else 30  # 네트워크는 2분, 로컬은 30초
            
            if is_network_path:
                print("🌐 네트워크 드라이브 - 분석 타임아웃 연장 (2분)")
            
            # 씬 변화 감지를 위한 FFmpeg 명령 (네트워크 최적화)
            cmd = [
                self.ffmpeg_path,
                '-probesize', '50M',  # 네트워크용 프로브 크기 증가
                '-analyzeduration', '30M',  # 분석 시간 증가
                '-i', video_path,
                '-vf', 'select=gt(scene\\,0.25),showinfo',  # 25% 이상 씬 변화
                '-vsync', 'vfr',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_duration)
            
            # showinfo에서 타임스탬프 추출
            scene_times = []
            for line in result.stderr.split('\n'):
                if 'pts_time:' in line:
                    try:
                        pts_time = float(line.split('pts_time:')[1].split()[0])
                        if 0 < pts_time < duration:
                            scene_times.append(pts_time)
                    except:
                        continue
            
            if len(scene_times) >= target_count:
                # 씬 변화가 충분하면 균등하게 선택
                step = len(scene_times) // target_count
                selected_times = [scene_times[i * step] for i in range(target_count)]
                print(f"✅ 씬 변화 기반 {len(selected_times)}개 프레임 선택")
                return selected_times
            else:
                # 씬 변화가 부족하면 하이브리드 방식
                print(f"⚠️ 씬 변화 부족 ({len(scene_times)}개), 하이브리드 모드")
                smart_times = scene_times.copy()
                
                # 부족한 만큼 균등 분할로 채우기
                remaining = target_count - len(smart_times)
                if remaining > 0:
                    for i in range(remaining):
                        time_point = duration * (i + 1) / (remaining + 1)
                        # 기존 씬 변화와 겹치지 않도록
                        if not any(abs(time_point - t) < 5 for t in smart_times):
                            smart_times.append(time_point)
                
                return sorted(smart_times[:target_count])
                
        except Exception as e:
            print(f"⚠️ 스마트 분석 실패: {e}, 균등 분할 모드로 전환")
            
            # 네트워크 드라이브에서는 간단한 균등 분할 사용
            is_network_path = video_path.startswith('\\\\') or video_path.startswith('//')
            if is_network_path:
                print("🌐 네트워크 최적화: 간단 균등 분할 적용")
                timestamps = []
                for i in range(target_count):
                    progress = (i + 1) / (target_count + 1)  # 시작/끝 제외
                    time_point = duration * progress
                    timestamps.append(time_point)
                print(f"📊 네트워크 균등 분할: {len(timestamps)}개 프레임")
                return timestamps
            
        # 실패시 개선된 균등 분할 (액션 위주)
        # 시작/끝 10% 제외하고 액션이 많은 중간 부분에 집중
        start_offset = duration * 0.1
        end_offset = duration * 0.9
        effective_duration = end_offset - start_offset
        
        timestamps = []
        for i in range(target_count):
            # 중간 부분에 더 집중된 분포
            progress = i / (target_count - 1) if target_count > 1 else 0.5
            # 시그모이드 함수로 중간에 집중
            weighted_progress = 1 / (1 + math.exp(-6 * (progress - 0.5)))
            time_point = start_offset + effective_duration * weighted_progress
            timestamps.append(time_point)
            
        print(f"📊 액션 집중 균등 분할: {len(timestamps)}개 프레임")
        return timestamps

    def extract_frame_parallel(self, video_path, timestamp, frame_id, hw_accel):
        """개별 프레임을 병렬로 추출 (하이브리드 시스템 최적화)"""
        try:
            # 하드웨어 가속 설정 (하이브리드 시스템에서는 모든 처리가 로컬)
            hw_params = []
            if hw_accel:
                if hw_accel == 'nvenc':
                    hw_params = ['-hwaccel', 'cuda']
                elif hw_accel == 'qsv':
                    hw_params = ['-hwaccel', 'qsv']
                elif hw_accel == 'amf':
                    hw_params = ['-hwaccel', 'd3d11va']
            
            # 하이브리드 시스템: 모든 파일이 로컬에서 처리됨 (메모리 파이프 방식)
            cmd = [
                self.ffmpeg_path,
                '-hide_banner', '-loglevel', 'error',
                '-threads', '1',
                '-probesize', '32M',
                '-analyzeduration', '10M',
                *hw_params,
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '3',
                '-s', '400x220',
                '-f', 'image2pipe',
                '-vcodec', 'mjpeg',
                '-pred', '1',
                'pipe:1'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                pixmap = QPixmap()
                if pixmap.loadFromData(result.stdout):
                    return (frame_id, pixmap)
            else:
                # 실패 원인 디버깅
                if result.returncode != 0:
                    print(f"   ❌ FFmpeg 오류 (코드 {result.returncode}): {result.stderr.decode('utf-8', errors='ignore')[:200]}")
                elif not result.stdout:
                    print(f"   ❌ 파이프 출력 데이터 없음")
            
            return (frame_id, None)
            
        except subprocess.TimeoutExpired:
            print(f"프레임 {frame_id} ({timestamp:.1f}s) 타임아웃 (10초)")
            return (frame_id, None)
        except Exception as e:
            print(f"프레임 {frame_id} ({timestamp:.1f}s) 추출 실패: {e}")
            return (frame_id, None)

    def get_file_size_mb(self, file_path):
        """파일 크기를 MB 단위로 반환"""
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            return size_mb
        except:
            return 0

    def copy_to_temp_local(self, video_path):
        """네트워크 파일을 로컬 임시 폴더로 복사"""
        try:
            import tempfile
            import shutil
            
            temp_dir = tempfile.gettempdir()
            file_name = os.path.basename(video_path)
            temp_path = os.path.join(temp_dir, f"cf_temp_{os.getpid()}_{file_name}")
            
            print(f"📋 로컬 임시 복사: {file_name}")
            start_time = time.time()
            
            shutil.copy2(video_path, temp_path)
            
            elapsed = time.time() - start_time
            size_mb = self.get_file_size_mb(temp_path)
            speed = size_mb / elapsed if elapsed > 0 else 0
            
            print(f"✅ 복사 완료: {size_mb:.1f}MB, {elapsed:.1f}초, {speed:.1f}MB/s")
            return temp_path
            
        except Exception as e:
            print(f"❌ 임시 복사 실패: {e}")
            return None

    def extract_segments_for_thumbnails(self, video_path, timestamps):
        """큰 파일에서 타임스탬프 주변 세그먼트들만 추출"""
        try:
            import tempfile
            
            temp_dir = tempfile.gettempdir()
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            segment_paths = []
            
            print(f"🔪 부분 추출 모드: {len(timestamps)}개 세그먼트")
            
            # 각 타임스탬프별로 3초 세그먼트 추출
            for i, timestamp in enumerate(timestamps):
                segment_path = os.path.join(temp_dir, f"cf_seg_{os.getpid()}_{base_name}_{i}.mp4")
                
                # 시작 시간 (1초 여유)
                start_time = max(0, timestamp - 1)
                
                cmd = [
                    self.ffmpeg_path,
                    '-hide_banner', '-loglevel', 'error',
                    '-ss', str(start_time),
                    '-i', video_path,
                    '-t', '3',  # 3초간
                    '-c', 'copy',  # 재인코딩 없이 복사 (빠름)
                    '-avoid_negative_ts', 'make_zero',
                    '-y',
                    segment_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(segment_path):
                    segment_paths.append((i, segment_path, 1.0))  # (인덱스, 경로, 상대시간)
                    print(f"✅ 세그먼트 {i+1}/20 추출 완료")
                else:
                    print(f"❌ 세그먼트 {i+1}/20 추출 실패")
                    segment_paths.append((i, None, 1.0))
            
            return segment_paths
            
        except Exception as e:
            print(f"❌ 세그먼트 추출 실패: {e}")
            return []

    def extract_thumbnail(self, video_path):
        """하이브리드 스마트 썸네일 추출 시스템 🚀"""
        # 중단 요청 확인
        if self.stop_requested:
            print(f"🛑 썸네일 추출 중단: {os.path.basename(video_path)}")
            return self.create_placeholder_thumbnail()
            
        # FFmpeg가 비활성화되었거나 없으면 플레이스홀더 반환
        if not self.ffmpeg_path or not self.ffprobe_path:
            return self.create_placeholder_thumbnail()
        
        # 캐시된 썸네일 우선 시도
        cached_thumbnail = self.load_cached_thumbnail(video_path)
        if cached_thumbnail:
            return cached_thumbnail
        
        try:
            import math
            import time
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            # 파일 크기 및 네트워크 드라이브 확인
            file_size_mb = self.get_file_size_mb(video_path)
            is_network_path = video_path.startswith('\\\\') or video_path.startswith('//')
            
            # 영상 길이 확인
            duration = self.get_simple_duration(video_path)
            if duration <= 0:
                print(f"영상 길이 확인 실패, 기본값 사용: {video_path}")
                duration = 1200
            
            print(f"🎬 하이브리드 썸네일 추출: {os.path.basename(video_path)}")
            print(f"   📊 파일 크기: {file_size_mb:.1f}MB, 네트워크: {is_network_path}")
            
            # 하이브리드 전략 결정
            size_threshold_mb = 500  # 500MB 기준
            temp_file_path = None
            segment_paths = []
            
            if is_network_path and file_size_mb > size_threshold_mb:
                # 큰 네트워크 파일: 부분 추출 방식
                print(f"🔪 큰 파일 부분 추출 모드 ({file_size_mb:.1f}MB > {size_threshold_mb}MB)")
                
                # 스마트 프레임 타임스탬프 생성 (단순화)
                timestamps = []
                for i in range(20):
                    progress = (i + 1) / 21  # 5%, 10%, 15%, ..., 95%
                    time_point = duration * progress
                    timestamps.append(time_point)
                
                # 세그먼트 추출
                segment_paths = self.extract_segments_for_thumbnails(video_path, timestamps)
                processing_mode = "segments"
                
            elif is_network_path and file_size_mb <= size_threshold_mb:
                # 작은 네트워크 파일: 전체 임시 복사
                print(f"📋 작은 파일 임시 복사 모드 ({file_size_mb:.1f}MB ≤ {size_threshold_mb}MB)")
                temp_file_path = self.copy_to_temp_local(video_path)
                if temp_file_path:
                    video_path = temp_file_path  # 로컬 파일로 대체
                processing_mode = "local_copy"
                
            else:
                # 로컬 파일: 기존 방식
                print(f"⚡ 로컬 파일 직접 처리 모드")
                processing_mode = "direct"
            
                         # 하드웨어 가속 감지
            hw_accel = self.detect_hardware_acceleration()
            
            if processing_mode == "segments":
                # 세그먼트별 썸네일 생성
                frame_pixmaps = []
                for i, segment_info in enumerate(segment_paths):
                    frame_id, segment_path, relative_time = segment_info
                    
                    if segment_path and os.path.exists(segment_path):
                        try:
                            # 세그먼트에서 프레임 추출 (로컬 고속)
                            pixmap = self.extract_frame_from_segment(segment_path, relative_time, hw_accel)
                            frame_pixmaps.append(pixmap)
                        except Exception as e:
                            print(f"❌ 세그먼트 {i+1} 처리 실패: {e}")
                            frame_pixmaps.append(None)
                        finally:
                            # 세그먼트 파일 정리
                            try:
                                os.unlink(segment_path)
                            except:
                                pass
                    else:
                        frame_pixmaps.append(None)
                
            else:
                # 기존 방식 (로컬 또는 임시 복사된 파일)
                timestamps = self.get_smart_frame_timestamps(video_path, duration, 20)
                
                print(f"   📊 해상도: 400x220, 품질: 고품질, 가속: {hw_accel or 'CPU'}")
                
                # 병렬 프레임 추출
                max_workers = 1 if (is_network_path and processing_mode != "local_copy") else 5
                
                frame_results = {}
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_frame = {
                        executor.submit(self.extract_frame_parallel, video_path, ts, i, hw_accel): i
                        for i, ts in enumerate(timestamps)
                    }
                    
                    for future in as_completed(future_to_frame, timeout=60):
                        try:
                            frame_id, pixmap = future.result()
                            frame_results[frame_id] = pixmap
                            if pixmap:
                                print(f"✅ 프레임 {frame_id+1}/20 완료")
                            else:
                                print(f"❌ 프레임 {frame_id+1}/20 실패")
                        except Exception as e:
                            frame_id = future_to_frame[future]
                            print(f"❌ 프레임 {frame_id+1}/20 예외: {e}")
                            frame_results[frame_id] = None
                
                frame_pixmaps = [frame_results.get(i) for i in range(20)]
            
            # 임시 파일 정리
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    print(f"🗑️ 임시 파일 정리 완료")
                except:
                    pass
            
            # 결과 확인
            valid_count = sum(1 for p in frame_pixmaps if p is not None)
            print(f"🎯 추출 완료: {valid_count}/20개 프레임 성공 ({processing_mode} 모드)")
            
            # 고품질 5x4 그리드 썸네일 생성
            generated_thumbnail = self.create_5x4_grid_thumbnail(frame_pixmaps)
            
            # 생성된 썸네일을 캐시로 저장
            if generated_thumbnail and not generated_thumbnail.isNull():
                self.save_thumbnail_cache(video_path, generated_thumbnail)
            
            return generated_thumbnail
                
        except Exception as e:
            print(f"💥 하이브리드 썸네일 추출 실패: {video_path}, 오류: {e}")
            import traceback
            traceback.print_exc()
            
            # 임시 파일 정리 (예외 상황에서도)
            if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
        return self.create_placeholder_thumbnail()

    def extract_frame_from_segment(self, segment_path, relative_time, hw_accel):
        """로컬 세그먼트에서 고속 프레임 추출"""
        try:
            # 하드웨어 가속 설정 (로컬 파일이므로 활성화)
            hw_params = []
            if hw_accel:
                if hw_accel == 'nvenc':
                    hw_params = ['-hwaccel', 'cuda']
                elif hw_accel == 'qsv':
                    hw_params = ['-hwaccel', 'qsv']
                elif hw_accel == 'amf':
                    hw_params = ['-hwaccel', 'd3d11va']
            
            # 로컬 세그먼트에서 메모리 파이프 방식으로 고속 추출
            cmd = [
                self.ffmpeg_path,
                '-hide_banner', '-loglevel', 'error',
                *hw_params,
                '-ss', str(relative_time),
                '-i', segment_path,
                '-vframes', '1',
                '-q:v', '3',
                '-s', '400x220',
                '-f', 'image2pipe',
                '-vcodec', 'mjpeg',
                'pipe:1'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
            if result.returncode == 0 and result.stdout:
                pixmap = QPixmap()
                if pixmap.loadFromData(result.stdout):
                    return pixmap
                    
            return None
            
        except Exception as e:
            print(f"세그먼트 프레임 추출 실패: {e}")
            return None
    
    def get_simple_duration(self, video_path):
        """영상 길이 간단히 확인 (초 단위) - 네트워크 드라이브 최적화"""
        try:
            cmd = [
                self.ffprobe_path, '-v', 'quiet', 
                '-print_format', 'compact',
                '-show_entries', 'format=duration',
                video_path
            ]
            
            # 네트워크 드라이브용 긴 타임아웃
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                # format|duration=123.456 형태에서 숫자 추출
                for line in result.stdout.strip().split('\n'):
                    if 'duration=' in line:
                        duration_str = line.split('duration=')[1].split('|')[0]
                        duration = float(duration_str)
                        print(f"영상 길이: {duration:.1f}초 ({duration/60:.1f}분)")
                        return duration
            
        except Exception as e:
            print(f"간단 영상 길이 확인 실패: {video_path}, 오류: {e}")
            
        return 0
    
    def create_5x4_grid_thumbnail(self, frame_pixmaps):
        """사용 가능한 프레임들로 5x4 격자 배치 (적응형)"""
        try:
            # 5x4 격자 설정
            grid_cols = 5
            grid_rows = 4
            frame_width = self.thumbnail_size[0] // grid_cols
            frame_height = self.thumbnail_size[1] // grid_rows
            
            # 최종 이미지 생성
            final_pixmap = QPixmap(self.thumbnail_size[0], self.thumbnail_size[1])
            final_pixmap.fill(QColor(35, 35, 35))  # 어두운 배경
            
            painter = QPainter(final_pixmap)
            
            # 실제 성공한 프레임 수에 따라 퍼센트 계산
            valid_frames = [p for p in frame_pixmaps if p is not None and not p.isNull()]
            total_valid = len(valid_frames)
            
            print(f"유효한 프레임 수: {total_valid}/{len(frame_pixmaps)}")
            
            # 20개 그리드 셀에 배치
            valid_index = 0
            for i in range(20):  # 5x4 = 20개
                row = i // grid_cols
                col = i % grid_cols
                    
                x = col * frame_width
                y = row * frame_height
                
                # 경계선을 위한 여백
                margin = 1
                inner_width = frame_width - (margin * 2)
                inner_height = frame_height - (margin * 2)
                
                # 실제 프레임이 있으면 표시
                if i < len(frame_pixmaps) and frame_pixmaps[i] and not frame_pixmaps[i].isNull():
                    # 실제 프레임 표시
                    scaled_frame = frame_pixmaps[i].scaled(
                        inner_width, inner_height,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    
                    # 중앙 배치
                    center_x = x + margin + (inner_width - scaled_frame.width()) // 2
                    center_y = y + margin + (inner_height - scaled_frame.height()) // 2
                    
                    painter.drawPixmap(center_x, center_y, scaled_frame)
                    
                    # 프레임 순서 표시 (퍼센트 대신)
                    painter.setPen(QPen(QColor(255, 255, 255, 200)))
                    font = painter.font()
                    font.setPixelSize(8)
                    font.setBold(True)
                    painter.setFont(font)
                    painter.drawText(x + 2, y + 10, f"#{i+1}")
                    
                else:
                    # 플레이스홀더 표시
                    painter.fillRect(x + margin, y + margin, inner_width, inner_height, QColor(55, 55, 55))
                    painter.setPen(QPen(QColor(120, 120, 120)))
                    painter.drawText(x + margin, y + margin, inner_width, inner_height, Qt.AlignCenter, "?")
                
                # 격자 경계선
                painter.setPen(QPen(QColor(70, 70, 70), 1))
                painter.drawRect(x, y, frame_width, frame_height)
            
            painter.end()
            
            # 최소 1개 프레임이라도 있으면 성공
            if total_valid > 0:
                print(f"썸네일 그리드 생성 완료 ({total_valid}개 프레임)")
                return final_pixmap
            else:
                print("유효한 프레임이 없어 플레이스홀더 반환")
                return self.create_placeholder_thumbnail()
            
        except Exception as e:
            print(f"5x4 격자 썸네일 생성 실패: {e}")
            return self.create_placeholder_thumbnail()

    def create_simple_grid_thumbnail(self, frame_pixmaps):
        """4개 프레임을 2x2 격자로 빠르게 배치 (호환성 유지)"""
        try:
            # 2x2 격자 설정
            grid_size = 2
            frame_width = self.thumbnail_size[0] // grid_size
            frame_height = self.thumbnail_size[1] // grid_size
            
            # 최종 이미지 생성
            final_pixmap = QPixmap(self.thumbnail_size[0], self.thumbnail_size[1])
            final_pixmap.fill(QColor(40, 40, 40))  # 어두운 배경
            
            painter = QPainter(final_pixmap)
            
            # 2x2 격자에 프레임 배치
            positions = [(0, 0), (1, 0), (0, 1), (1, 1)]  # (col, row)
            
            for i, (col, row) in enumerate(positions):
                if i >= len(frame_pixmaps):
                    break
                    
                x = col * frame_width
                y = row * frame_height
                
                # 경계선을 위한 여백
                margin = 1
                inner_width = frame_width - (margin * 2)
                inner_height = frame_height - (margin * 2)
                
                if frame_pixmaps[i] and not frame_pixmaps[i].isNull():
                    # 실제 프레임 표시
                    scaled_frame = frame_pixmaps[i].scaled(
                        inner_width, inner_height,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    
                    # 중앙 배치
                    center_x = x + margin + (inner_width - scaled_frame.width()) // 2
                    center_y = y + margin + (inner_height - scaled_frame.height()) // 2
                    
                    painter.drawPixmap(center_x, center_y, scaled_frame)
                else:
                    # 플레이스홀더 표시
                    painter.fillRect(x + margin, y + margin, inner_width, inner_height, QColor(60, 60, 60))
                    painter.setPen(QPen(QColor(120, 120, 120)))
                    painter.drawText(x + margin, y + margin, inner_width, inner_height, Qt.AlignCenter, "?")
                
                # 격자 경계선
                painter.setPen(QPen(QColor(80, 80, 80), 1))
                painter.drawRect(x, y, frame_width, frame_height)
            
            painter.end()
            return final_pixmap
            
        except Exception as e:
            print(f"간단 격자 썸네일 생성 실패: {e}")
            return self.create_placeholder_thumbnail()
    
    def create_placeholder_thumbnail(self):
        """플레이스홀더 썸네일 생성"""
        pixmap = QPixmap(self.thumbnail_size[0], self.thumbnail_size[1])
        pixmap.fill(QColor(64, 64, 64))
        
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(128, 128, 128), 2))
        painter.drawRect(10, 10, self.thumbnail_size[0]-20, self.thumbnail_size[1]-20)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "미리보기\n없음")
        painter.end()
        
        return pixmap

class VideoThumbnailWidget(QWidget):
    """개별 비디오 썸네일 위젯"""
    selection_changed = pyqtSignal(str, bool)  # 파일명, 선택상태
    preview_requested = pyqtSignal(str)  # 미리보기 요청
    
    def __init__(self, file_info, formatted_size, file_path=None):
        super().__init__()
        self.file_info = file_info
        self.file_name = file_info['name']
        self.file_size = file_info['size']
        self.formatted_size = formatted_size
        self.file_path = file_path  # 전체 파일 경로
        self.is_selected = False
        self.thumbnail_pixmap = None
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.request_preview)
        
        self.setFixedSize(180, 160)
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # 썸네일 영역
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(160, 120)
        self.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setText("로딩중...")
        layout.addWidget(self.thumbnail_label)
        
        # 메타데이터 오버레이
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # 체크박스
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self.on_selection_changed)
        info_layout.addWidget(self.checkbox)
        
        # 파일 정보
        info_text = f"{self.formatted_size}"
        self.info_label = QLabel(info_text)
        self.info_label.setStyleSheet("font-size: 10px; color: #666;")
        info_layout.addWidget(self.info_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # 파일명 (짧게 표시)
        display_name = self.file_name
        if len(display_name) > 20:
            display_name = display_name[:17] + "..."
        
        self.name_label = QLabel(display_name)
        self.name_label.setStyleSheet("font-size: 9px; font-weight: bold;")
        self.name_label.setToolTip(self.file_name)  # 전체 이름은 툴팁으로
        layout.addWidget(self.name_label)
        
    def set_thumbnail(self, pixmap):
        """썸네일 설정"""
        self.thumbnail_pixmap = pixmap
        self.thumbnail_label.setPixmap(pixmap)
        self.thumbnail_label.setText("")
        
    def on_selection_changed(self, state):
        """선택 상태 변경"""
        self.is_selected = (state == Qt.Checked)
        self.update_style()
        self.selection_changed.emit(self.file_name, self.is_selected)
        
    def update_style(self):
        """선택 상태에 따른 스타일 업데이트"""
        if self.is_selected:
            self.setStyleSheet("""
                VideoThumbnailWidget {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 5px;
                }
            """)
        else:
            self.setStyleSheet("""
                VideoThumbnailWidget {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }
                VideoThumbnailWidget:hover {
                    background-color: #f5f5f5;
                    border: 1px solid #999;
                }
            """)
    
    def enterEvent(self, event):
        """마우스 진입시 미리보기 타이머 시작"""
        super().enterEvent(event)
        self.hover_timer.start(1000)  # 1초 후 미리보기
        
    def leaveEvent(self, event):
        """마우스 떠날시 타이머 취소"""
        super().leaveEvent(event)
        self.hover_timer.stop()
        
    def request_preview(self):
        """미리보기 요청"""
        self.preview_requested.emit(self.file_name)
        
    def set_selected(self, selected):
        """외부에서 선택 상태 설정"""
        self.checkbox.setChecked(selected)
    
    def mouseDoubleClickEvent(self, event):
        """더블클릭시 영상 파일 열기"""
        if event.button() == Qt.LeftButton and self.file_path:
            try:
                # Windows에서 기본 프로그램으로 파일 열기
                import os
                os.startfile(self.file_path)
                    
            except Exception as e:
                print(f"영상 파일 열기 실패: {self.file_name}, 오류: {e}")
                # 실패 시 메시지박스 표시
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "파일 열기 실패", 
                                  f"영상 파일을 열 수 없습니다.\n\n파일: {self.file_name}\n오류: {str(e)}")
        
        super().mouseDoubleClickEvent(event)

class VisualSelectionDialog(QDialog):
    def __init__(self, capacity_finder, current_path, parent=None):
        super().__init__(parent)
        self.capacity_finder = capacity_finder
        self.current_path = current_path
        self.selection_result = None
        self.current_files = []
        self.thumbnail_widgets = {}  # {파일명: 위젯}
        self.selected_files = set()
        self.thumbnail_extractor = None
        
        # FFmpeg 매니저 초기화
        self.ffmpeg_manager = FFmpegManager()
        
        self.setWindowTitle("비주얼 영상 선별 도우미")
        self.setGeometry(100, 100, 1200, 800)
        self.setModal(True)
        
        # FFmpeg 체크를 지연시켜서 UI가 먼저 표시되도록
        QTimer.singleShot(100, self.check_ffmpeg_on_startup)
        
        self.init_ui()
        self.load_users()
        
    def check_ffmpeg_on_startup(self):
        """시작시 FFmpeg 체크 및 필요시 다운로드 프롬프트"""
        if self.ffmpeg_manager.needs_installation():
            self.ffmpeg_manager.check_and_prompt_if_needed(self)
            # FFmpeg 상태가 변경되었을 수 있으므로 UI 업데이트
            self.update_ffmpeg_status()
    
    def update_ffmpeg_status(self):
        """FFmpeg 상태 UI 업데이트"""
        if hasattr(self, 'ffmpeg_status_label'):
            if self.ffmpeg_manager.is_ffmpeg_disabled():
                self.ffmpeg_status_label.setText("🚫 FFmpeg 비활성화")
                self.ffmpeg_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            else:
                ffmpeg_path, ffprobe_path = self.ffmpeg_manager.get_ffmpeg_paths()
                if ffmpeg_path and ffprobe_path:
                    self.ffmpeg_status_label.setText("✅ FFmpeg 사용 가능")
                    self.ffmpeg_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                else:
                    self.ffmpeg_status_label.setText("❌ FFmpeg 없음")
                    self.ffmpeg_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        # 로드 버튼 상태 업데이트
        if hasattr(self, 'load_button'):
            has_users = self.user_combo.count() > 0 and self.user_combo.currentText() != "사용 가능한 사용자 없음"
            self.load_button.setEnabled(has_users)
        
        # 재설치 버튼 표시/숨김
        if hasattr(self, 'reinstall_ffmpeg_btn'):
            # FFmpeg가 비활성화되었거나 없을 때만 재설치 버튼 표시
            show_button = (self.ffmpeg_manager.is_ffmpeg_disabled() or 
                          not all(self.ffmpeg_manager.get_ffmpeg_paths()))
            self.reinstall_ffmpeg_btn.setVisible(show_button)
    
    def reinstall_ffmpeg(self):
        """FFmpeg 재설치"""
        # 비활성화 상태라면 먼저 활성화
        if self.ffmpeg_manager.is_ffmpeg_disabled():
            self.ffmpeg_manager.enable_ffmpeg()
        
        # 다운로드 시도
        success = self.ffmpeg_manager.download_ffmpeg(self)
        
        # 상태 업데이트
        self.update_ffmpeg_status()
        
        if success:
            QMessageBox.information(self, "재설치 완료", 
                                  "FFmpeg가 성공적으로 재설치되었습니다!\n비주얼 선별 기능을 사용할 수 있습니다.")
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 상단 컨트롤 패널
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # 메인 분할기
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # 썸네일 그리드 영역
        thumbnail_area = self.create_thumbnail_area()
        main_splitter.addWidget(thumbnail_area)
        
        # 실시간 대시보드
        dashboard = self.create_dashboard()
        main_splitter.addWidget(dashboard)
        
        # 비율 설정 (썸네일:대시보드 = 3:1)
        main_splitter.setSizes([900, 300])
        
        # 하단 실행 버튼들
        button_layout = self.create_action_buttons()
        layout.addLayout(button_layout)
        
    def create_control_panel(self):
        """상단 컨트롤 패널 생성"""
        panel = QGroupBox("필터 및 컨트롤")
        panel.setMaximumHeight(60)  # 높이 제한
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)  # 패딩 줄이기
        
        # 사용자 선택
        layout.addWidget(QLabel("사용자:"))
        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(150)
        self.user_combo.setMaximumHeight(25)
        self.user_combo.currentTextChanged.connect(self.on_user_changed)
        layout.addWidget(self.user_combo)
        
        # 크기 필터
        layout.addWidget(QLabel("최소 크기:"))
        self.size_filter_spin = QSpinBox()
        self.size_filter_spin.setRange(0, 10000)
        self.size_filter_spin.setValue(0)
        self.size_filter_spin.setSuffix(" MB")
        self.size_filter_spin.setMaximumHeight(25)
        self.size_filter_spin.valueChanged.connect(self.apply_filters)
        layout.addWidget(self.size_filter_spin)
        
        # 로드 버튼
        self.load_button = QPushButton("📁 파일 로드")
        self.load_button.clicked.connect(self.load_files)
        self.load_button.setEnabled(False)
        self.load_button.setMaximumHeight(25)
        layout.addWidget(self.load_button)
        
        # 빠른 선택
        layout.addWidget(QLabel("|"))
        self.select_all_btn = QPushButton("전체 선택")
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        self.select_all_btn.setMaximumHeight(25)
        layout.addWidget(self.select_all_btn)
        
        self.clear_all_btn = QPushButton("전체 해제")
        self.clear_all_btn.clicked.connect(self.clear_all)
        self.clear_all_btn.setEnabled(False)
        self.clear_all_btn.setMaximumHeight(25)
        layout.addWidget(self.clear_all_btn)
        
        # FFmpeg 상태 표시
        layout.addWidget(QLabel("|"))
        self.ffmpeg_status_label = QLabel("FFmpeg 확인 중...")
        self.ffmpeg_status_label.setMaximumHeight(25)
        layout.addWidget(self.ffmpeg_status_label)
        
        # FFmpeg 재설치 버튼
        self.reinstall_ffmpeg_btn = QPushButton("🔄 FFmpeg 재설치")
        self.reinstall_ffmpeg_btn.clicked.connect(self.reinstall_ffmpeg)
        self.reinstall_ffmpeg_btn.setMaximumHeight(25)
        self.reinstall_ffmpeg_btn.setVisible(False)  # 기본적으로 숨김
        layout.addWidget(self.reinstall_ffmpeg_btn)
        
        layout.addStretch()
        
        # 초기 FFmpeg 상태 업데이트
        QTimer.singleShot(200, self.update_ffmpeg_status)
        
        return panel
        
    def create_thumbnail_area(self):
        """썸네일 그리드 영역 생성"""
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 썸네일 컨테이너
        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QGridLayout(self.thumbnail_container)
        self.thumbnail_layout.setSpacing(10)
        
        scroll_area.setWidget(self.thumbnail_container)
        return scroll_area
        
    def create_dashboard(self):
        """실시간 대시보드 생성"""
        dashboard = QGroupBox("실시간 통계")
        layout = QVBoxLayout(dashboard)
        
        # 진행률
        self.progress_label = QLabel("진행률: 0/0 (0%)")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 통계 정보
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        
        # 미리보기 영역
        preview_group = QGroupBox("빠른 미리보기")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("파일 위에 마우스를 올려보세요")
        self.preview_label.setFixedSize(240, 180)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9;")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        self.preview_info_label = QLabel("")
        self.preview_info_label.setStyleSheet("font-size: 11px; color: #666;")
        preview_layout.addWidget(self.preview_info_label)
        
        layout.addWidget(preview_group)
        layout.addStretch()
        
        return dashboard
        
    def create_action_buttons(self):
        """하단 실행 버튼들 생성"""
        layout = QHBoxLayout()
        
        self.execute_button = QPushButton("선별 실행 (선택된 것만 유지)")
        self.execute_button.clicked.connect(self.accept)
        self.execute_button.setEnabled(False)
        self.execute_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover:enabled {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        layout.addStretch()
        layout.addWidget(self.execute_button)
        layout.addWidget(cancel_button)
        
        return layout
        
    def load_users(self):
        """사용자 목록 로드"""
        if not self.capacity_finder:
            return
            
        users = self.capacity_finder.get_available_users()
        self.user_combo.clear()
        
        if users:
            self.user_combo.addItems(sorted(users))
            self.load_button.setEnabled(True)
        else:
            self.user_combo.addItem("사용 가능한 사용자 없음")
            self.load_button.setEnabled(False)
    
    def on_user_changed(self):
        """사용자 선택 변경시"""
        self.clear_thumbnails()
        self.update_stats()
        
    def load_files(self):
        """선택된 사용자의 파일 로드"""
        username = self.user_combo.currentText()
        if not username or username == "사용 가능한 사용자 없음":
            return
        
        if username not in self.capacity_finder.dic_files:
            QMessageBox.warning(self, "오류", f"사용자 '{username}'의 데이터를 찾을 수 없습니다.")
            return
        
        # 파일 리스트 가져오기
        user_data = self.capacity_finder.dic_files[username]
        self.current_files = user_data['files'].copy()
        
        # 필터 적용
        self.apply_filters()
        
    def apply_filters(self):
        """필터 적용"""
        if not self.current_files:
            return
            
        # 크기 필터
        min_size = self.size_filter_spin.value()
        filtered_files = [f for f in self.current_files if f['size'] >= min_size]
        
        # 썸네일 생성
        self.create_thumbnails(filtered_files)
        
    def create_thumbnails(self, files):
        """썸네일 위젯들 생성"""
        self.clear_thumbnails()
        
        if not files:
            return
            
        # 썸네일 위젯 생성
        for i, file_info in enumerate(files):
            formatted_size = self.format_file_size(file_info['size'])
            file_path = os.path.join(self.current_path, file_info['name'])
            widget = VideoThumbnailWidget(file_info, formatted_size, file_path)
            
            # 신호 연결
            widget.selection_changed.connect(self.on_selection_changed)
            widget.preview_requested.connect(self.show_preview)
            
            # 그리드에 배치 (5열)
            row = i // 5
            col = i % 5
            self.thumbnail_layout.addWidget(widget, row, col)
            
            self.thumbnail_widgets[file_info['name']] = widget
        
        # 썸네일 추출 시작
        self.start_thumbnail_extraction(files)
        
        # 버튼 활성화
        self.select_all_btn.setEnabled(True)
        self.clear_all_btn.setEnabled(True)
        self.execute_button.setEnabled(True)
        
        self.update_stats()
        
    def start_thumbnail_extraction(self, files):
        """백그라운드 썸네일 추출 시작"""
        # 기존 스레드가 실행 중이면 먼저 중단
        if self.thumbnail_extractor and self.thumbnail_extractor.isRunning():
            print("🔄 기존 썸네일 추출 작업 중단 후 새 작업 시작...")
            self.stop_thumbnail_extraction()
        
        # 새 스레드 생성 및 시작
        self.thumbnail_extractor = ThumbnailExtractorThread(files)
        self.thumbnail_extractor.set_path(self.current_path)
        self.thumbnail_extractor.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.thumbnail_extractor.start()
        
        print(f"🎬 새 썸네일 추출 작업 시작: {len(files)}개 파일")
        
    @pyqtSlot(str, QPixmap)
    def on_thumbnail_ready(self, file_name, thumbnail):
        """썸네일이 준비되었을 때"""
        if file_name in self.thumbnail_widgets:
            self.thumbnail_widgets[file_name].set_thumbnail(thumbnail)
            
    def clear_thumbnails(self):
        """모든 썸네일 제거"""
        for widget in self.thumbnail_widgets.values():
            widget.deleteLater()
        self.thumbnail_widgets.clear()
        self.selected_files.clear()
        
        # 썸네일 추출 중단
        if self.thumbnail_extractor and self.thumbnail_extractor.isRunning():
            self.thumbnail_extractor.quit()
            self.thumbnail_extractor.wait()
            
    def on_selection_changed(self, file_name, is_selected):
        """선택 상태 변경 처리"""
        if is_selected:
            self.selected_files.add(file_name)
        else:
            self.selected_files.discard(file_name)
            
        self.update_stats()
        
    def show_preview(self, file_name):
        """빠른 미리보기 표시"""
        if file_name in self.thumbnail_widgets:
            widget = self.thumbnail_widgets[file_name]
            file_info = widget.file_info
            
            # 썸네일을 미리보기에 표시
            if widget.thumbnail_pixmap:
                scaled_pixmap = widget.thumbnail_pixmap.scaled(240, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText(f"미리보기\n{file_name}")
                
            # 파일 정보 표시
            info_text = f"파일: {file_name}\n"
            info_text += f"크기: {self.format_file_size(file_info['size'])}"
            self.preview_info_label.setText(info_text)
            
    def select_all(self):
        """모든 파일 선택"""
        for widget in self.thumbnail_widgets.values():
            widget.set_selected(True)
            
    def clear_all(self):
        """모든 선택 해제"""
        for widget in self.thumbnail_widgets.values():
            widget.set_selected(False)
            
    def update_stats(self):
        """통계 업데이트"""
        total_files = len(self.thumbnail_widgets)
        selected_count = len(self.selected_files)
        
        # 진행률 업데이트
        if total_files > 0:
            progress = (selected_count / total_files) * 100
            self.progress_bar.setValue(int(progress))
            self.progress_label.setText(f"선택: {selected_count}/{total_files} ({progress:.1f}%)")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("선택: 0/0 (0%)")
            
        # 통계 텍스트 업데이트
        if self.thumbnail_widgets:
            selected_size = 0
            total_size = 0
            
            for file_name, widget in self.thumbnail_widgets.items():
                file_size = widget.file_info['size']
                total_size += file_size
                
                if file_name in self.selected_files:
                    selected_size += file_size
                    
            unselected_size = total_size - selected_size
            unselected_count = total_files - selected_count
            
            stats = f"📊 비주얼 선별 통계\n\n"
            stats += f"📁 전체 파일: {total_files}개\n"
            stats += f"💾 전체 용량: {self.format_file_size(total_size)}\n\n"
            
            stats += f"✅ 선택된 파일: {selected_count}개\n"
            stats += f"💾 유지할 용량: {self.format_file_size(selected_size)}\n\n"
            
            stats += f"🗑️ 삭제 예정: {unselected_count}개\n"
            stats += f"💽 절약될 용량: {self.format_file_size(unselected_size)}\n\n"
            
            if total_size > 0:
                efficiency = (unselected_size / total_size) * 100
                stats += f"📈 공간 효율성: {efficiency:.1f}% 절약"
                
            self.stats_text.setPlainText(stats)
        else:
            self.stats_text.setPlainText("파일을 로드해주세요.")
            
    def format_file_size(self, size_mb):
        """파일 사이즈 포맷팅"""
        if size_mb >= 1024:  # 1GB 이상
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"
            
    def get_result(self):
        """선별 결과 반환"""
        if not self.thumbnail_widgets:
            return None
            
        files_to_keep = []
        files_to_delete = []
        
        for file_name, widget in self.thumbnail_widgets.items():
            file_info = widget.file_info
            
            if file_name in self.selected_files:
                files_to_keep.append(file_info)
            else:
                files_to_delete.append(file_info)
                
        total_savings = sum(f['size'] for f in files_to_delete)
        
        self.selection_result = {
            'files_to_keep': files_to_keep,
            'files_to_delete': files_to_delete,
            'total_savings': total_savings,
            'username': self.user_combo.currentText()
        }
        
        return self.selection_result
    
    def stop_thumbnail_extraction(self):
        """썸네일 추출 작업 안전하게 중단"""
        if self.thumbnail_extractor and self.thumbnail_extractor.isRunning():
            print("🛑 썸네일 추출 스레드 중단 시작...")
            
            # 중단 요청
            self.thumbnail_extractor.request_stop()
            
            # 최대 5초 대기 후 강제 종료
            if not self.thumbnail_extractor.wait(5000):  # 5초 대기
                print("⚠️ 스레드가 5초 내에 종료되지 않아 강제 종료")
                self.thumbnail_extractor.terminate()
                self.thumbnail_extractor.wait(1000)  # 추가 1초 대기
            else:
                print("✅ 썸네일 추출 스레드 정상 종료됨")
    
    def closeEvent(self, event):
        """창 닫기 이벤트 처리 - 썸네일 추출 작업 정리"""
        print("🚪 비주얼 선별 창 닫기 요청됨")
        
        # 썸네일 추출 작업이 진행 중이면 중단
        if self.thumbnail_extractor and self.thumbnail_extractor.isRunning():
            print("🛑 진행 중인 썸네일 추출 작업을 안전하게 중단합니다...")
            
            # 사용자에게 알림
            from PyQt5.QtWidgets import QMessageBox, QPushButton
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("작업 중단 중...")
            msg_box.setText("진행 중인 썸네일 추출 작업을 안전하게 중단하고 있습니다.")
            msg_box.setInformativeText("현재 처리 중인 파일들을 완료한 후 종료됩니다.")
            msg_box.setStandardButtons(QMessageBox.NoButton)
            
            # 강제 종료 버튼 추가
            force_button = msg_box.addButton("즉시 강제 종료", QMessageBox.DestructiveRole)
            
            # 메시지 박스를 모달이 아닌 방식으로 표시
            msg_box.setModal(False)
            msg_box.show()
            
            # 백그라운드에서 중단 처리
            self.stop_thumbnail_extraction()
            
            # 메시지 박스 닫기
            msg_box.close()
        
        # 부모 클래스의 closeEvent 호출
        super().closeEvent(event)
        print("✅ 비주얼 선별 창 완전히 종료됨") 