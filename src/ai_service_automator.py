"""
AI 서비스 자동화 모듈
ChatGPT, Claude, Gemini에 자동으로 프롬프트와 이미지 업로드
"""

import time
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from loguru import logger

from .config import Config
from .stock_data_collector import StockData


@dataclass
class AIServiceResult:
    """AI 서비스 업로드 결과"""
    service_name: str
    success: bool
    message: str
    upload_time: str
    response_url: Optional[str] = None


class AIServiceAutomator:
    """AI 서비스 자동화 클래스"""
    
    def __init__(self, config: Config):
        """
        AI 서비스 자동화 초기화
        
        Args:
            config: 설정 객체
        """
        self.config = config
        self.driver: Optional[uc.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        
        # AI 서비스 URL 매핑
        self.service_urls = {
            "chatgpt": self.config.ai_services.chatgpt["url"],
            "claude": self.config.ai_services.claude["url"], 
            "gemini": self.config.ai_services.gemini["url"]
        }
        
        # 서비스 활성화 상태
        self.enabled_services = {
            "chatgpt": self.config.ai_services.chatgpt["enabled"],
            "claude": self.config.ai_services.claude["enabled"],
            "gemini": self.config.ai_services.gemini["enabled"]
        }
    
    def _setup_driver(self) -> None:
        """Chrome 드라이버 설정"""
        try:
            chrome_options = Options()
            
            # 기본 옵션 설정 (headless는 AI 서비스에서 문제가 될 수 있으므로 False)
            chrome_options.add_argument(f"--window-size={self.config.webdriver.window_size}")
            chrome_options.add_argument(f"--user-agent={self.config.webdriver.user_agent}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 파일 다운로드 및 업로드 허용
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-web-security")
            
            # undetected-chromedriver로 드라이버 생성
            self.driver = uc.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 대기 시간 설정
            self.driver.implicitly_wait(self.config.webdriver.implicit_wait)
            self.wait = WebDriverWait(self.driver, self.config.webdriver.wait_timeout)
            
            logger.info("AI 서비스용 Chrome 드라이버 설정 완료")
            
        except Exception as e:
            logger.error(f"드라이버 설정 실패: {e}")
            raise
    
    def _close_driver(self) -> None:
        """드라이버 종료"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome 드라이버 종료")
            except Exception as e:
                logger.error(f"드라이버 종료 실패: {e}")
    
    def _upload_to_chatgpt(self, prompt: str, image_paths: List[str]) -> AIServiceResult:
        """ChatGPT에 프롬프트와 이미지 업로드"""
        try:
            logger.info("ChatGPT 업로드 시작")
            
            # ChatGPT 페이지로 이동
            self.driver.get(self.service_urls["chatgpt"])
            time.sleep(3)
            
            # 로그인 확인 (간단한 체크)
            try:
                # 텍스트 입력 영역 찾기
                text_area = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//textarea[@data-id='root']"))
                )
            except TimeoutException:
                logger.warning("ChatGPT 로그인이 필요합니다. 수동 로그인 후 진행하세요.")
                input("ChatGPT에 로그인한 후 Enter를 눌러주세요...")
                text_area = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//textarea[@data-id='root']"))
                )
            
            # 이미지 업로드 (있는 경우)
            if image_paths:
                try:
                    # 파일 업로드 버튼 찾기
                    upload_button = self.driver.find_element(By.XPATH, "//input[@type='file']")
                    
                    # 여러 이미지 업로드
                    for image_path in image_paths:
                        if os.path.exists(image_path):
                            upload_button.send_keys(image_path)
                            time.sleep(2)
                            logger.info(f"이미지 업로드 완료: {os.path.basename(image_path)}")
                        else:
                            logger.warning(f"이미지 파일을 찾을 수 없습니다: {image_path}")
                    
                    time.sleep(3)  # 이미지 처리 대기
                    
                except Exception as e:
                    logger.warning(f"이미지 업로드 실패, 텍스트만 전송: {e}")
            
            # 프롬프트 입력
            text_area.clear()
            text_area.send_keys(prompt)
            time.sleep(1)
            
            # 전송 버튼 클릭
            send_button = self.driver.find_element(By.XPATH, "//button[@data-testid='send-button']")
            send_button.click()
            
            logger.info("ChatGPT 업로드 완료")
            return AIServiceResult(
                service_name="ChatGPT",
                success=True,
                message="업로드 성공",
                upload_time=datetime.now().isoformat(),
                response_url=self.driver.current_url
            )
            
        except Exception as e:
            logger.error(f"ChatGPT 업로드 실패: {e}")
            return AIServiceResult(
                service_name="ChatGPT",
                success=False,
                message=f"업로드 실패: {str(e)}",
                upload_time=datetime.now().isoformat()
            )
    
    def _upload_to_claude(self, prompt: str, image_paths: List[str]) -> AIServiceResult:
        """Claude에 프롬프트와 이미지 업로드"""
        try:
            logger.info("Claude 업로드 시작")
            
            # Claude 페이지로 이동
            self.driver.get(self.service_urls["claude"])
            time.sleep(3)
            
            # 로그인 확인
            try:
                # 텍스트 입력 영역 찾기
                text_area = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@contenteditable='true']"))
                )
            except TimeoutException:
                logger.warning("Claude 로그인이 필요합니다. 수동 로그인 후 진행하세요.")
                input("Claude에 로그인한 후 Enter를 눌러주세요...")
                text_area = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@contenteditable='true']"))
                )
            
            # 이미지 업로드 (있는 경우)
            if image_paths:
                try:
                    # 첨부 버튼 찾기
                    attach_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Attach')]")
                    
                    for image_path in image_paths:
                        if os.path.exists(image_path):
                            # 파일 입력 요소 찾기
                            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                            file_input.send_keys(image_path)
                            time.sleep(2)
                            logger.info(f"이미지 업로드 완료: {os.path.basename(image_path)}")
                        else:
                            logger.warning(f"이미지 파일을 찾을 수 없습니다: {image_path}")
                    
                    time.sleep(3)  # 이미지 처리 대기
                    
                except Exception as e:
                    logger.warning(f"이미지 업로드 실패, 텍스트만 전송: {e}")
            
            # 프롬프트 입력
            text_area.clear()
            text_area.send_keys(prompt)
            time.sleep(1)
            
            # 전송 (Enter 키)
            text_area.send_keys(Keys.ENTER)
            
            logger.info("Claude 업로드 완료")
            return AIServiceResult(
                service_name="Claude",
                success=True,
                message="업로드 성공",
                upload_time=datetime.now().isoformat(),
                response_url=self.driver.current_url
            )
            
        except Exception as e:
            logger.error(f"Claude 업로드 실패: {e}")
            return AIServiceResult(
                service_name="Claude",
                success=False,
                message=f"업로드 실패: {str(e)}",
                upload_time=datetime.now().isoformat()
            )
    
    def _upload_to_gemini(self, prompt: str, image_paths: List[str]) -> AIServiceResult:
        """Gemini에 프롬프트와 이미지 업로드"""
        try:
            logger.info("Gemini 업로드 시작")
            
            # Gemini 페이지로 이동
            self.driver.get(self.service_urls["gemini"])
            time.sleep(3)
            
            # 로그인 확인
            try:
                # 텍스트 입력 영역 찾기
                text_area = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//textarea"))
                )
            except TimeoutException:
                logger.warning("Gemini 로그인이 필요합니다. 수동 로그인 후 진행하세요.")
                input("Gemini에 로그인한 후 Enter를 눌러주세요...")
                text_area = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//textarea"))
                )
            
            # 이미지 업로드 (있는 경우)
            if image_paths:
                try:
                    # 이미지 업로드 버튼 찾기
                    upload_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Upload')]")
                    
                    for image_path in image_paths:
                        if os.path.exists(image_path):
                            upload_button.click()
                            time.sleep(1)
                            
                            # 파일 선택
                            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                            file_input.send_keys(image_path)
                            time.sleep(2)
                            logger.info(f"이미지 업로드 완료: {os.path.basename(image_path)}")
                        else:
                            logger.warning(f"이미지 파일을 찾을 수 없습니다: {image_path}")
                    
                    time.sleep(3)  # 이미지 처리 대기
                    
                except Exception as e:
                    logger.warning(f"이미지 업로드 실패, 텍스트만 전송: {e}")
            
            # 프롬프트 입력
            text_area.clear()
            text_area.send_keys(prompt)
            time.sleep(1)
            
            # 전송 버튼 클릭
            send_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send')]")
            send_button.click()
            
            logger.info("Gemini 업로드 완료")
            return AIServiceResult(
                service_name="Gemini",
                success=True,
                message="업로드 성공",
                upload_time=datetime.now().isoformat(),
                response_url=self.driver.current_url
            )
            
        except Exception as e:
            logger.error(f"Gemini 업로드 실패: {e}")
            return AIServiceResult(
                service_name="Gemini",
                success=False,
                message=f"업로드 실패: {str(e)}",
                upload_time=datetime.now().isoformat()
            )
    
    def upload_to_ai_services(
        self, 
        prompt: str, 
        image_paths: Optional[List[str]] = None,
        services: Optional[List[str]] = None
    ) -> List[AIServiceResult]:
        """
        선택된 AI 서비스들에 프롬프트와 이미지 업로드
        
        Args:
            prompt: 업로드할 프롬프트
            image_paths: 업로드할 이미지 파일 경로 리스트
            services: 업로드할 서비스 리스트 (None이면 활성화된 모든 서비스)
            
        Returns:
            각 서비스별 업로드 결과
        """
        if image_paths is None:
            image_paths = []
        
        if services is None:
            services = [service for service, enabled in self.enabled_services.items() if enabled]
        
        results = []
        
        try:
            # 드라이버 설정
            self._setup_driver()
            
            for service in services:
                if service not in self.service_urls:
                    logger.warning(f"지원하지 않는 서비스: {service}")
                    continue
                
                if not self.enabled_services.get(service, False):
                    logger.info(f"비활성화된 서비스 건너뜀: {service}")
                    continue
                
                logger.info(f"{service} 업로드 시작")
                
                try:
                    if service == "chatgpt":
                        result = self._upload_to_chatgpt(prompt, image_paths)
                    elif service == "claude":
                        result = self._upload_to_claude(prompt, image_paths)
                    elif service == "gemini":
                        result = self._upload_to_gemini(prompt, image_paths)
                    else:
                        result = AIServiceResult(
                            service_name=service,
                            success=False,
                            message="지원하지 않는 서비스",
                            upload_time=datetime.now().isoformat()
                        )
                    
                    results.append(result)
                    
                    if result.success:
                        logger.info(f"{service} 업로드 성공")
                    else:
                        logger.error(f"{service} 업로드 실패: {result.message}")
                    
                    # 서비스 간 대기 시간
                    time.sleep(3)
                    
                except Exception as e:
                    logger.error(f"{service} 업로드 중 오류: {e}")
                    results.append(AIServiceResult(
                        service_name=service,
                        success=False,
                        message=f"업로드 중 오류: {str(e)}",
                        upload_time=datetime.now().isoformat()
                    ))
            
            logger.info(f"AI 서비스 업로드 완료: {len([r for r in results if r.success])}/{len(results)} 성공")
            
        except Exception as e:
            logger.error(f"AI 서비스 업로드 전체 실패: {e}")
            
        finally:
            self._close_driver()
        
        return results
    
    def prepare_stock_data_for_upload(
        self, 
        stock_data: StockData, 
        prompt_template: str
    ) -> Tuple[str, List[str]]:
        """
        주식 데이터를 AI 서비스 업로드용으로 준비
        
        Args:
            stock_data: 주식 데이터
            prompt_template: 프롬프트 템플릿
            
        Returns:
            (최종 프롬프트, 이미지 경로 리스트)
        """
        # 프롬프트에 주식 정보 추가
        stock_info = f"""
📊 주식 정보
• 종목명: {stock_data.stock_name} ({stock_data.stock_code})
• 현재가: {stock_data.current_price}
• 등락: {stock_data.price_change} ({stock_data.change_rate})
• 거래량: {stock_data.volume}

📈 최근 뉴스 (상위 3개):
"""
        
        # 주요 뉴스 추가
        for i, news in enumerate(stock_data.news_data[:3], 1):
            stock_info += f"{i}. {news['title']} ({news['date']})\n"
        
        # 관련 테마 추가
        if stock_data.related_themes:
            stock_info += f"\n🏷️ 관련 테마: {', '.join(stock_data.related_themes[:5])}\n"
        
        # 최종 프롬프트 구성
        final_prompt = f"{stock_info}\n\n{prompt_template}"
        
        # 이미지 경로 수집
        image_paths = []
        for chart_type, path in stock_data.chart_screenshots.items():
            if os.path.exists(path):
                image_paths.append(path)
        
        return final_prompt, image_paths
    
    def wait_for_user_action(self) -> str:
        """
        사용자 액션 대기 (재검색 또는 종료)
        
        Returns:
            사용자 선택 ('continue', 'exit')
        """
        print("\n" + "="*60)
        print("🤖 AI 서비스 업로드가 완료되었습니다!")
        print("각 AI 서비스에서 응답을 확인하고 다음 행동을 선택해주세요.")
        print("="*60)
        
        while True:
            print("\n다음 중 선택하세요:")
            print("1. 다른 종목 검색 (Enter 또는 1)")
            print("2. 프로그램 종료 (q 또는 2)")
            
            user_input = input("\n선택: ").strip().lower()
            
            if user_input in ['', '1', 'continue', 'c']:
                return 'continue'
            elif user_input in ['q', '2', 'exit', 'quit']:
                return 'exit'
            else:
                print("잘못된 입력입니다. 다시 선택해주세요.")
    
    def get_upload_summary(self, results: List[AIServiceResult]) -> str:
        """
        업로드 결과 요약 생성
        
        Args:
            results: 업로드 결과 리스트
            
        Returns:
            업로드 결과 요약 문자열
        """
        if not results:
            return "업로드 결과가 없습니다."
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        summary = f"\n📊 업로드 결과 요약:\n"
        summary += f"• 전체: {len(results)}개 서비스\n"
        summary += f"• 성공: {len(successful)}개\n"
        summary += f"• 실패: {len(failed)}개\n\n"
        
        if successful:
            summary += "✅ 성공한 서비스:\n"
            for result in successful:
                summary += f"  - {result.service_name}: {result.message}\n"
        
        if failed:
            summary += "\n❌ 실패한 서비스:\n"
            for result in failed:
                summary += f"  - {result.service_name}: {result.message}\n"
        
        return summary