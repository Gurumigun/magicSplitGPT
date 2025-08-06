"""
네이버 증권 데이터 수집기
"""

import time
import os
import base64
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import json

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from loguru import logger

from .config import Config


@dataclass
class StockData:
    """주식 데이터 구조체"""
    stock_code: str
    stock_name: str
    current_price: str
    price_change: str
    change_rate: str
    volume: str
    market_cap: str
    investment_opinion: Dict[str, any]
    news_data: List[Dict[str, str]]
    discussion_data: List[Dict[str, str]]
    related_themes: List[str]
    chart_screenshots: Dict[str, str]  # 차트 종류별 스크린샷 경로
    financial_data: Dict[str, any]
    technical_indicators: Dict[str, any]
    collected_at: str


class StockDataCollector:
    """네이버 증권 데이터 수집 클래스"""
    
    def __init__(self, config: Config):
        """
        데이터 수집기 초기화
        
        Args:
            config: 설정 객체
        """
        self.config = config
        self.driver: Optional[uc.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.base_screenshot_dir = Path(config.screenshot.save_path)
        self.current_stock_screenshot_dir = None
        
        # 기본 스크린샷 디렉토리 생성
        self.base_screenshot_dir.mkdir(exist_ok=True)
    
    def _setup_driver(self) -> None:
        """Chrome 드라이버 설정"""
        try:
            import os
            
            # Chrome 사용자 프로필 디렉토리 설정 (보조지표 저장용)
            user_data_dir = os.path.expanduser("~/magicSplitGPT_chrome_profile")
            os.makedirs(user_data_dir, exist_ok=True)
            
            # undetected-chromedriver에 사용자 프로필 옵션 추가
            chrome_options = uc.ChromeOptions()
            chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
            chrome_options.add_argument('--profile-directory=Default')
            
            if self.config.webdriver.headless:
                chrome_options.add_argument("--headless")
            
            # 기본 옵션 설정
            chrome_options.add_argument(f"--window-size={self.config.webdriver.window_size}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument('--disable-web-security')  # iframe 접근용
            chrome_options.add_argument('--allow-running-insecure-content')  # iframe 접근용
            
            # undetected-chromedriver로 드라이버 생성
            try:
                self.driver = uc.Chrome(options=chrome_options)
                logger.info(f"Chrome 사용자 프로필 설정 완료: {user_data_dir}")
            except Exception as e:
                logger.warning(f"옵션과 함께 드라이버 생성 실패, 기본 설정으로 재시도: {e}")
                # 기본 설정으로 재시도
                self.driver = uc.Chrome()
            
            # 대기 시간 설정
            self.driver.implicitly_wait(self.config.webdriver.implicit_wait)
            self.wait = WebDriverWait(self.driver, self.config.webdriver.wait_timeout)
            
            logger.info("Chrome 드라이버 설정 완료")
            
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
    
    def _setup_stock_screenshot_folder(self, stock_code: str) -> None:
        """
        주식별 스크린샷 폴더 생성
        
        Args:
            stock_code: 주식 코드
        """
        # 현재 시간으로 폴더명 생성 (YYMMDDHHmm 형식)
        timestamp = datetime.now().strftime("%y%m%d%H%M")
        folder_name = f"{stock_code}_{timestamp}"
        
        # 주식별 폴더 경로 설정
        self.current_stock_screenshot_dir = self.base_screenshot_dir / folder_name
        
        # 폴더 생성
        self.current_stock_screenshot_dir.mkdir(exist_ok=True)
        logger.info(f"주식별 스크린샷 폴더 생성: {self.current_stock_screenshot_dir}")
    
    def _take_full_page_screenshot_cdp(self, filepath: str) -> bool:
        """
        Chrome DevTools Protocol을 사용해서 전체 페이지 스크린샷 캡처
        
        Args:
            filepath: 저장할 파일 경로
            
        Returns:
            스크린샷 성공 여부
        """
        try:
            # 페이지 레이아웃 메트릭 가져오기
            page_rect = self.driver.execute_cdp_cmd('Page.getLayoutMetrics', {})
            
            # 스크린샷 설정
            screenshot_config = {
                'captureBeyondViewport': True,
                'fromSurface': True,
                'clip': {
                    'width': page_rect['contentSize']['width'],
                    'height': page_rect['contentSize']['height'],
                    'x': 0,
                    'y': 0,
                    'scale': 1
                }
            }
            
            # 스크린샷 캡처
            base_64_png = self.driver.execute_cdp_cmd('Page.captureScreenshot', screenshot_config)
            
            # 이미지 파일로 저장
            with open(filepath, "wb") as fh:
                fh.write(base64.urlsafe_b64decode(base_64_png['data']))
            
            logger.info(f"CDP 전체 페이지 스크린샷 저장 완료: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"CDP 스크린샷 실패: {e}")
            return False
    
    def _navigate_to_stock(self, stock_code: str) -> bool:
        """
        특정 주식 페이지로 이동
        
        Args:
            stock_code: 주식 코드 (예: 005930)
            
        Returns:
            이동 성공 여부
        """
        try:
            stock_url = self.config.get_stock_url(stock_code)
            logger.info(f"주식 페이지 이동: {stock_url}")
            
            self.driver.get(stock_url)
            
            # 페이지 로딩 대기 - 여러 선택자로 시도
            selectors_to_try = [
                (By.CLASS_NAME, "chart_area"),
                (By.ID, "chart"),
                (By.CLASS_NAME, "graph_wrap"),
                (By.CLASS_NAME, "today"),
                (By.TAG_NAME, "body")  # 최후의 수단
            ]
            
            loaded = False
            for by, selector in selectors_to_try:
                try:
                    self.wait.until(EC.presence_of_element_located((by, selector)))
                    logger.info(f"페이지 로딩 완료: {selector} 선택자로 확인")
                    loaded = True
                    break
                except TimeoutException:
                    logger.debug(f"선택자 {selector} 로딩 실패, 다음 시도")
                    continue
            
            if not loaded:
                logger.warning("모든 선택자 로딩 실패, 기본 대기 시간으로 진행")
            
            time.sleep(self.config.naver_finance.delay_between_requests)
            return True
            
        except TimeoutException:
            logger.error(f"주식 페이지 로딩 타임아웃: {stock_code}")
            return False
        except Exception as e:
            logger.error(f"주식 페이지 이동 실패: {e}")
            return False
    
    def _get_basic_info(self) -> Dict[str, str]:
        """기본 주식 정보 수집 - Playwright 분석 결과 기반"""
        basic_info = {}
        
        try:
            # 종목명 - .wrap_company h2 a
            stock_name_elem = self.driver.find_element(By.CSS_SELECTOR, ".wrap_company h2 a")
            basic_info["stock_name"] = stock_name_elem.text.strip()
            
            # 종목코드 - .wrap_company .description .code
            stock_code_elem = self.driver.find_element(By.CSS_SELECTOR, ".wrap_company .description .code")
            basic_info["stock_code"] = stock_code_elem.text.strip()
            
            # 현재가 - .today .no_today em 안의 span들을 조합
            current_price_elem = self.driver.find_element(By.CSS_SELECTOR, ".today .no_today em")
            basic_info["current_price"] = current_price_elem.text.strip().replace(',', '')
            
            # 전일대비 - .today .no_exday em (첫 번째)
            price_change_elements = self.driver.find_elements(By.CSS_SELECTOR, ".today .no_exday em")
            if len(price_change_elements) >= 2:
                price_change = price_change_elements[0].text.strip().replace(',', '')
                change_rate = price_change_elements[1].text.strip()
                basic_info["price_change"] = price_change
                basic_info["change_rate"] = change_rate
            
            # 기업개요 - .summary_info p 텍스트
            try:
                # 기업개요 팝업을 열기 위해 클릭 (숨겨진 정보)
                summary_elem = self.driver.find_element(By.CSS_SELECTOR, ".summary a")
                self.driver.execute_script("arguments[0].click();", summary_elem)
                time.sleep(1)
                
                company_desc_elements = self.driver.find_elements(By.CSS_SELECTOR, ".summary_info p")
                company_description = []
                for elem in company_desc_elements:
                    text = elem.text.strip()
                    if text and not text.startswith('출처'):
                        company_description.append(text)
                
                basic_info["company_description"] = " ".join(company_description)
                
                # 팝업 닫기
                close_btn = self.driver.find_element(By.CSS_SELECTOR, ".summary_lyr .btn_area_top a")
                self.driver.execute_script("arguments[0].click();", close_btn)
                
            except Exception as desc_error:
                logger.debug(f"기업개요 수집 실패: {desc_error}")
                basic_info["company_description"] = "정보 없음"
            
            logger.info(f"기본 정보 수집 완료: {basic_info['stock_name']} ({basic_info['stock_code']})")
            
        except Exception as e:
            logger.error(f"기본 정보 수집 실패: {e}")
            # 최소한의 정보라도 수집 시도
            try:
                basic_info["stock_name"] = self.driver.title.split(':')[0].strip() if ':' in self.driver.title else "정보 없음"
            except:
                basic_info["stock_name"] = "정보 없음"
            
        return basic_info
    
    def _get_investment_opinion(self) -> Dict[str, any]:
        """투자 의견 정보 수집"""
        investment_data = {}
        
        try:
            # 투자의견 탭으로 이동
            opinion_tab = self.driver.find_element(By.XPATH, "//a[contains(text(),'투자의견')]")
            opinion_tab.click()
            time.sleep(2)
            
            # 투자의견 데이터 수집
            opinion_table = self.driver.find_element(By.CLASS_NAME, "type_1")
            rows = opinion_table.find_elements(By.TAG_NAME, "tr")
            
            opinions = []
            for row in rows[1:6]:  # 최근 5개만
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 4:
                    opinion = {
                        "date": cells[0].text,
                        "company": cells[1].text,
                        "opinion": cells[2].text,
                        "target_price": cells[3].text
                    }
                    opinions.append(opinion)
            
            investment_data["opinions"] = opinions
            logger.info(f"투자의견 {len(opinions)}개 수집 완료")
            
        except Exception as e:
            logger.error(f"투자의견 수집 실패: {e}")
            investment_data["opinions"] = []
            
        return investment_data
    
    def _get_news_data(self) -> List[Dict[str, str]]:
        """뉴스 및 공시 정보 수집"""
        news_data = []
        
        try:
            # 뉴스 탭으로 이동
            news_tab = self.driver.find_element(By.XPATH, "//a[contains(text(),'뉴스')]")
            news_tab.click()
            time.sleep(2)
            
            # 뉴스 데이터 수집
            news_list = self.driver.find_elements(By.CLASS_NAME, "tb_cont")
            
            for news_item in news_list[:10]:  # 최근 10개만
                try:
                    title_elem = news_item.find_element(By.TAG_NAME, "a")
                    title = title_elem.get_attribute("title") or title_elem.text
                    
                    date_elem = news_item.find_element(By.CLASS_NAME, "date")
                    date = date_elem.text
                    
                    source_elem = news_item.find_element(By.CLASS_NAME, "press")
                    source = source_elem.text
                    
                    news_data.append({
                        "title": title,
                        "date": date,
                        "source": source
                    })
                    
                except Exception as news_error:
                    logger.debug(f"개별 뉴스 수집 실패: {news_error}")
                    continue
            
            logger.info(f"뉴스 {len(news_data)}개 수집 완료")
            
        except Exception as e:
            logger.error(f"뉴스 데이터 수집 실패: {e}")
            
        return news_data
    
    def _get_discussion_data(self) -> List[Dict[str, str]]:
        """토론실 정보 수집"""
        discussion_data = []
        
        try:
            # 토론실 탭으로 이동
            discussion_tab = self.driver.find_element(By.XPATH, "//a[contains(text(),'토론실')]")
            discussion_tab.click()
            time.sleep(2)
            
            # 토론실 데이터 수집
            discussion_list = self.driver.find_elements(By.CLASS_NAME, "tb_cont")
            
            for discussion_item in discussion_list[:10]:  # 최근 10개만
                try:
                    title_elem = discussion_item.find_element(By.TAG_NAME, "a")
                    title = title_elem.text
                    
                    author_elem = discussion_item.find_element(By.CLASS_NAME, "p11")
                    author = author_elem.text
                    
                    date_elem = discussion_item.find_element(By.CLASS_NAME, "num")
                    date = date_elem.text
                    
                    discussion_data.append({
                        "title": title,
                        "author": author,
                        "date": date
                    })
                    
                except Exception as discussion_error:
                    logger.debug(f"개별 토론 수집 실패: {discussion_error}")
                    continue
            
            logger.info(f"토론실 {len(discussion_data)}개 수집 완료")
            
        except Exception as e:
            logger.error(f"토론실 데이터 수집 실패: {e}")
            
        return discussion_data
    
    def _get_related_themes(self) -> List[str]:
        """관련 테마 정보 수집"""
        themes = []
        
        try:
            # 테마 정보 섹션 찾기
            theme_section = self.driver.find_element(By.CLASS_NAME, "group_theme")
            theme_links = theme_section.find_elements(By.TAG_NAME, "a")
            
            for theme_link in theme_links:
                theme_text = theme_link.text.strip()
                if theme_text and theme_text not in themes:
                    themes.append(theme_text)
            
            logger.info(f"관련 테마 {len(themes)}개 수집 완료")
            
        except Exception as e:
            logger.error(f"관련 테마 수집 실패: {e}")
            
        return themes
    
    def _capture_charts(self, stock_code: str) -> Dict[str, str]:
        """차트 스크린샷 캡처 - 실제 페이지 구조 기반"""
        chart_paths = {}
        
        try:
            # 메인 차트 캡처 (현재 표시된 차트)
            try:
                # 차트 영역 찾기 - 실제 페이지의 #chart 또는 .chart 선택자 사용
                chart_selectors = ["#chart", ".chart", ".chart_area", ".graph_image"]
                chart_element = None
                
                for selector in chart_selectors:
                    try:
                        chart_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except NoSuchElementException:
                        continue
                
                if chart_element:
                    # 스크린샷 파일명 생성
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{stock_code}_main_chart_{timestamp}.{self.config.screenshot.format}"
                    filepath = self.screenshot_dir / filename
                    
                    # 엘리먼트 스크린샷
                    chart_element.screenshot(str(filepath))
                    chart_paths["main_chart"] = str(filepath)
                    logger.info(f"메인 차트 캡처 완료: {filename}")
                else:
                    logger.warning("차트 영역을 찾을 수 없음")
                    
            except Exception as chart_error:
                logger.error(f"메인 차트 캡처 실패: {chart_error}")
            
            # 전체 페이지 스크린샷도 캡처 (백업용)
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                full_filename = f"{stock_code}_full_page_{timestamp}.{self.config.screenshot.format}"
                full_filepath = self.screenshot_dir / full_filename
                
                self.driver.save_screenshot(str(full_filepath))
                chart_paths["full_page"] = str(full_filepath)
                logger.info(f"전체 페이지 캡처 완료: {full_filename}")
                
            except Exception as full_error:
                logger.error(f"전체 페이지 캡처 실패: {full_error}")
            
            # 불필요한 개별 스크린샷 제거 (price_info, summary_info)
            # 메인 차트와 전체 페이지만 유지
                    
        except Exception as e:
            logger.error(f"차트 캡처 실패: {e}")
            
        return chart_paths
    
    def _get_financial_data(self) -> Dict[str, any]:
        """재무제표 정보 수집"""
        financial_data = {}
        
        try:
            # 재무제표 탭으로 이동
            finance_tab = self.driver.find_element(By.XPATH, "//a[contains(text(),'재무제표')]")
            finance_tab.click()
            time.sleep(2)
            
            # 주요 재무 지표 수집
            finance_table = self.driver.find_element(By.CLASS_NAME, "tb_type1_ifrs")
            rows = finance_table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    label = cells[0].text.strip()
                    value = cells[1].text.strip() if len(cells) > 1 else "N/A"
                    
                    if label:
                        financial_data[label] = value
            
            logger.info(f"재무제표 데이터 수집 완료: {len(financial_data)}개 항목")
            
        except Exception as e:
            logger.error(f"재무제표 수집 실패: {e}")
            
        return financial_data
    
    def collect_stock_data(self, stock_code: str) -> Optional[StockData]:
        """
        특정 주식의 모든 데이터 수집
        
        Args:
            stock_code: 주식 코드
            
        Returns:
            수집된 주식 데이터 또는 None
        """
        try:
            logger.info(f"주식 데이터 수집 시작: {stock_code}")
            
            # 주식별 스크린샷 폴더 생성
            self._setup_stock_screenshot_folder(stock_code)
            
            # 드라이버 설정
            self._setup_driver()
            
            # 주식 페이지로 이동
            if not self._navigate_to_stock(stock_code):
                return None
            
            # 1. 기본 종목 페이지에서 기본 정보 수집
            basic_info = self._get_basic_info()
            
            # 2. 종목분석 페이지 (coinfo.naver) - 스크롤링 캡처
            analysis_screenshots = self._capture_company_analysis(stock_code)
            
            # 3. 뉴스공시 페이지 (news.naver) 
            news_data = self._get_news_announcements(stock_code)
            
            # 4. 투자자별 매매동향 페이지 (frgn.naver)
            investor_trends = self._get_investor_trends(stock_code)
            
            # 5. 전문 차트 페이지 (fchart.naver) - 다양한 차트 및 지표
            advanced_charts = self._capture_advanced_charts(stock_code)
            
            # StockData 객체 생성
            stock_data = StockData(
                stock_code=stock_code,
                stock_name=basic_info.get("stock_name", ""),
                current_price=basic_info.get("current_price", ""),
                price_change=basic_info.get("price_change", ""),
                change_rate=basic_info.get("change_rate", ""),
                volume=basic_info.get("volume", ""),
                market_cap=basic_info.get("market_cap", ""),
                investment_opinion=basic_info.get("company_description", ""),
                news_data=news_data,
                discussion_data=investor_trends,  # 매매동향을 토론 데이터에 저장
                related_themes=[],
                chart_screenshots={
                    **analysis_screenshots,
                    **advanced_charts
                },
                financial_data={},
                technical_indicators={},
                collected_at=datetime.now().isoformat()
            )
            
            logger.info(f"전문 주식 데이터 수집 완료: {stock_code} ({basic_info.get('stock_name', '')}) - 종목분석, 뉴스, 매매동향, 고급차트 포함")
            return stock_data
            
        except Exception as e:
            logger.error(f"주식 데이터 수집 실패: {e}")
            # 오류 발생 시에만 드라이버 종료
            self._close_driver()
            return None
    
    def close_driver_if_needed(self) -> None:
        """
        필요한 경우 드라이버를 수동으로 종료
        AI 업로드 완료 후 호출할 수 있음
        """
        self._close_driver()
    
    def _capture_company_analysis(self, stock_code: str) -> Dict[str, str]:
        """종목분석 페이지 iframe 내용 캡처 (coinfo.naver)"""
        analysis_screenshots = {}
        
        try:
            # 종목분석 페이지로 이동
            analysis_url = f"https://finance.naver.com/item/coinfo.naver?code={stock_code}"
            logger.info(f"종목분석 페이지 이동: {analysis_url}")
            self.driver.get(analysis_url)
            time.sleep(5)
            
            # iframe 찾아서 전환
            try:
                iframe_xpath = "/html/body/div[3]/div[2]/div[2]/div[1]/div[3]/iframe"
                iframe = self.driver.find_element(By.XPATH, iframe_xpath)
                self.driver.switch_to.frame(iframe)
                logger.info("종목분석 iframe으로 전환 완료")
                
                # iframe 내부 전체 높이 계산
                iframe_height = self.driver.execute_script("return Math.max("
                    "document.body.scrollHeight, document.body.offsetHeight, "
                    "document.documentElement.clientHeight, document.documentElement.scrollHeight, "
                    "document.documentElement.offsetHeight);")
                
                # 메인 창으로 돌아가서 iframe 크기 조정 후 캡처
                self.driver.switch_to.default_content()
                
                # iframe 스타일 조정으로 전체 내용 표시
                self.driver.execute_script(f"""
                    var iframe = document.evaluate('{iframe_xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (iframe) {{
                        iframe.style.height = '{iframe_height}px';
                        iframe.style.width = '100%';
                        iframe.style.border = 'none';
                        iframe.style.overflow = 'visible';
                    }}
                """)
                time.sleep(3)
                
                # Chrome DevTools Protocol로 전체 페이지 스크린샷 캡처
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{stock_code}_company_analysis_cdp_full_{timestamp}.{self.config.screenshot.format}"
                filepath = self.current_stock_screenshot_dir / filename
                
                success = self._take_full_page_screenshot_cdp(str(filepath))
                if success:
                    analysis_screenshots["cdp_screenshot"] = str(filepath)
                    logger.info(f"종목분석 CDP 전체 캡처 완료: {filename}")
                else:
                    # CDP 실패 시 기존 방식으로 폴백
                    self.driver.save_screenshot(str(filepath))
                    analysis_screenshots["fallback_screenshot"] = str(filepath)
                    logger.info(f"종목분석 폴백 스크린샷 완료: {filename}")
                
            except Exception as iframe_error:
                logger.error(f"iframe 캡처 실패: {iframe_error}")
                # 일반 페이지 캡처로 폴백
                total_height = self.driver.execute_script("return document.body.scrollHeight")
                original_size = self.driver.get_window_size()
                self.driver.set_window_size(1920, total_height)
                time.sleep(2)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{stock_code}_company_analysis_fallback_{timestamp}.{self.config.screenshot.format}"
                filepath = self.current_stock_screenshot_dir / filename
                self.driver.save_screenshot(str(filepath))
                
                self.driver.set_window_size(original_size['width'], original_size['height'])
                analysis_screenshots["fallback_screenshot"] = str(filepath)
                logger.info(f"종목분석 일반 페이지 캡처 완료: {filename}")
            
        except Exception as e:
            logger.error(f"종목분석 페이지 캡처 실패: {e}")
            
        return analysis_screenshots
    
    def _get_news_announcements(self, stock_code: str) -> List[Dict[str, str]]:
        """뉴스공시 페이지 데이터 수집 (news.naver)"""
        news_data = []
        
        try:
            # 뉴스공시 페이지로 이동
            news_url = f"https://finance.naver.com/item/news.naver?code={stock_code}"
            logger.info(f"뉴스공시 페이지 이동: {news_url}")
            self.driver.get(news_url)
            time.sleep(3)
            
            # Chrome DevTools Protocol로 전체 페이지 스크린샷 캡처
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{stock_code}_news_cdp_full_{timestamp}.{self.config.screenshot.format}"
            filepath = self.current_stock_screenshot_dir / filename
            
            success = self._take_full_page_screenshot_cdp(str(filepath))
            if not success:
                # CDP 실패 시 기존 방식으로 폴백
                logger.warning("뉴스 페이지 CDP 스크린샷 실패, 기존 방식으로 폴백")
                self.driver.save_screenshot(str(filepath))
                logger.info(f"뉴스 페이지 폴백 스크린샷 완료: {filename}")
            else:
                logger.info(f"뉴스 페이지 CDP 전체 캡처 완료: {filename}")
            
            # 뉴스 리스트 수집
            news_items = self.driver.find_elements(By.CSS_SELECTOR, ".tb_cont, .newsList li")
            
            for idx, news_item in enumerate(news_items[:20]):  # 최대 20개
                try:
                    # 뉴스 제목
                    title_elem = news_item.find_element(By.CSS_SELECTOR, "a")
                    title = title_elem.get_attribute("title") or title_elem.text.strip()
                    
                    # 날짜
                    date_elem = news_item.find_element(By.CSS_SELECTOR, ".date, .wdate")
                    date = date_elem.text.strip()
                    
                    # 언론사
                    source_elem = news_item.find_element(By.CSS_SELECTOR, ".press, .info_policy")
                    source = source_elem.text.strip()
                    
                    news_data.append({
                        "title": title,
                        "date": date,
                        "source": source,
                        "index": idx + 1
                    })
                    
                except Exception as news_error:
                    logger.debug(f"개별 뉴스 수집 실패 (#{idx}): {news_error}")
                    continue
                    
            logger.info(f"뉴스공시 데이터 수집 완료: {len(news_data)}개")
            
        except Exception as e:
            logger.error(f"뉴스공시 페이지 수집 실패: {e}")
            
        return news_data
    
    def _get_investor_trends(self, stock_code: str) -> List[Dict[str, str]]:
        """투자자별 매매동향 페이지 전체 한 장 이미지로 캡처 (frgn.naver)"""
        investor_data = []
        
        try:
            # 투자자별 매매동향 페이지로 이동
            investor_url = f"https://finance.naver.com/item/frgn.naver?code={stock_code}"
            logger.info(f"투자자별 매매동향 페이지 이동: {investor_url}")
            self.driver.get(investor_url)
            time.sleep(3)
            
            # Chrome DevTools Protocol로 전체 페이지 스크린샷 캡처
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{stock_code}_investor_trends_cdp_full_{timestamp}.{self.config.screenshot.format}"
            filepath = self.current_stock_screenshot_dir / filename
            
            success = self._take_full_page_screenshot_cdp(str(filepath))
            if not success:
                # CDP 실패 시 기존 방식으로 폴백
                logger.warning("투자자별 매매동향 페이지 CDP 스크린샷 실패, 기존 방식으로 폴백")
                self.driver.save_screenshot(str(filepath))
                logger.info(f"투자자별 매매동향 페이지 폴백 스크린샷 완료: {filename}")
            else:
                logger.info(f"투자자별 매매동향 페이지 CDP 전체 캡처 완료: {filename}")
            
            # 투자자별 매매 데이터 테이블 수집
            try:
                table = self.driver.find_element(By.CSS_SELECTOR, ".type2, .tb_cont")
                rows = table.find_elements(By.TAG_NAME, "tr")[1:11]  # 헤더 제외 최대 10개
                
                for idx, row in enumerate(rows):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 6:
                        investor_data.append({
                            "date": cells[0].text.strip(),
                            "foreign_buy": cells[1].text.strip(),
                            "foreign_sell": cells[2].text.strip(),
                            "institution_buy": cells[3].text.strip(),
                            "institution_sell": cells[4].text.strip(),
                            "individual_volume": cells[5].text.strip(),
                            "index": idx + 1
                        })
                        
            except Exception as table_error:
                logger.debug(f"투자자별 매매동향 테이블 수집 실패: {table_error}")
                
            logger.info(f"투자자별 매매동향 수집 완료: {len(investor_data)}개")
            
        except Exception as e:
            logger.error(f"투자자별 매매동향 페이지 수집 실패: {e}")
            
        return investor_data
    
    def _capture_advanced_charts(self, stock_code: str) -> Dict[str, str]:
        """전문 차트 페이지 전체 한 장 이미지로 캡처 (fchart.naver)"""
        chart_screenshots = {}
        
        try:
            # 전문 차트 페이지로 이동
            chart_url = f"https://finance.naver.com/item/fchart.naver?code={stock_code}"
            logger.info(f"전문 차트 페이지 이동: {chart_url}")
            self.driver.get(chart_url)
            time.sleep(10)  # 차트 로딩 대기
            
            # 차트 지표 설정 (MACD, RSI, Stochastic)
            try:
                # 1. 지표 메뉴 클릭
                indicator_menu = self.driver.find_element(By.XPATH, '//*[@id="content"]/div[3]/cq-context/div[1]/div[1]/div/div[2]/cq-menu/span')
                self.driver.execute_script("arguments[0].click();", indicator_menu)
                time.sleep(1)
                
                # 2. MACD 추가
                macd_elem = self.driver.find_element(By.XPATH, '//*[@id="content"]/div[3]/cq-context/div[1]/div[1]/div/div[2]/cq-menu/cq-menu-dropdown/cq-scroll/cq-studies/cq-studies-content/cq-item[9]/cq-label')
                self.driver.execute_script("arguments[0].click();", macd_elem)
                time.sleep(1)
                
                # 3. RSI 추가
                rsi_elem = self.driver.find_element(By.XPATH, '//*[@id="content"]/div[3]/cq-context/div[1]/div[1]/div/div[2]/cq-menu/cq-menu-dropdown/cq-scroll/cq-studies/cq-studies-content/cq-item[12]')
                self.driver.execute_script("arguments[0].click();", rsi_elem)
                time.sleep(1)
                
                # 4. Stochastic 추가
                stoch_elem = self.driver.find_element(By.XPATH, '//*[@id="content"]/div[3]/cq-context/div[1]/div[1]/div/div[2]/cq-menu/cq-menu-dropdown/cq-scroll/cq-studies/cq-studies-content/cq-item[15]')
                self.driver.execute_script("arguments[0].click();", stoch_elem)
                time.sleep(2)
                
                logger.info("차트 지표 설정 완료: MACD, RSI, Stochastic")
                
            except Exception as indicator_error:
                logger.warning(f"차트 지표 설정 실패 (계속 진행): {indicator_error}")
            
            # 차트 종류별 개별 캡처 (월/주/일/1시간봉)
            chart_types = [
                ("month", "month", "월봉"),
                ("week", "week", "주봉"),
                ("day", "day", "일봉")
            ]
            
            for chart_type, css_class, korean_name in chart_types:
                try:
                    # JavaScript로 차트 타입 클릭
                    click_script = f"""
                    const targetDiv = document.querySelector('div.{css_class}:not(.selected)');
                    if (targetDiv) {{
                        const rect = targetDiv.getBoundingClientRect();
                        const eventOptions = {{
                            bubbles: true,
                            cancelable: true,
                            view: window,
                            pointerId: 1,
                            button: 0,
                            clientX: rect.left + rect.width / 2,
                            clientY: rect.top + rect.height / 2,
                            isPrimary: true
                        }};
                        targetDiv.dispatchEvent(new PointerEvent('pointerdown', eventOptions));
                        targetDiv.dispatchEvent(new PointerEvent('pointerup', eventOptions));
                        return true;
                    }} else {{
                        return false;
                    }}
                    """
                    
                    result = self.driver.execute_script(click_script)
                    if result:
                        logger.info(f"{korean_name} 차트 클릭 성공")
                        time.sleep(5)  # 차트 변경 대기
                    else:
                        logger.warning(f"{korean_name} 차트 요소를 찾을 수 없음")
                        continue
                    
                    # 차트 영역만 캡처 (기존 방식 유지)
                    try:
                        chart_area = self.driver.find_element(By.CSS_SELECTOR, "cq-context, .chart_area, #chart")
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{stock_code}_chart_{chart_type}_{timestamp}.{self.config.screenshot.format}"
                        filepath = self.current_stock_screenshot_dir / filename
                        
                        chart_area.screenshot(str(filepath))
                        chart_screenshots[f"chart_{chart_type}"] = str(filepath)
                        logger.info(f"{korean_name} 차트 캡처 완료: {filename}")
                        
                    except Exception as area_error:
                        # 전체 페이지 캡처로 폴백
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{stock_code}_chart_{chart_type}_full_{timestamp}.{self.config.screenshot.format}"
                        filepath = self.current_stock_screenshot_dir / filename
                        
                        self.driver.save_screenshot(str(filepath))
                        chart_screenshots[f"chart_{chart_type}_full"] = str(filepath)
                        logger.info(f"{korean_name} 차트 전체 페이지 캡처 완료: {filename}")
                    
                except Exception as chart_error:
                    logger.error(f"{korean_name} 차트 캡처 실패: {chart_error}")
                    continue
            
            # 1시간봉 차트 캡처
            try:
                # JavaScript로 1시간봉 클릭
                hour_click_script = """
                const targetItem = document.querySelector('cq-item[interval="60"]');
                if (targetItem) {
                    const rect = targetItem.getBoundingClientRect();
                    const eventOptions = {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        pointerId: 1,
                        button: 0,
                        clientX: rect.left + rect.width / 2,
                        clientY: rect.top + rect.height / 2,
                        isPrimary: true
                    };
                    targetItem.dispatchEvent(new PointerEvent('pointerdown', eventOptions));
                    targetItem.dispatchEvent(new PointerEvent('pointerup', eventOptions));
                    return true;
                } else {
                    return false;
                }
                """
                
                result = self.driver.execute_script(hour_click_script)
                if result:
                    logger.info("1시간봉 차트 클릭 성공")
                    time.sleep(5)  # 차트 변경 대기
                else:
                    logger.warning("1시간봉 차트 요소를 찾을 수 없음")
                    raise Exception("1시간봉 요소 찾기 실패")
                
                # 1시간봉 차트 대기시간 증가 후 캡처 (기존 방식 유지)
                time.sleep(3)  # 추가 대기시간 (총 8초)
                
                try:
                    chart_area = self.driver.find_element(By.CSS_SELECTOR, "cq-context, .chart_area, #chart")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{stock_code}_chart_1hour_{timestamp}.{self.config.screenshot.format}"
                    filepath = self.current_stock_screenshot_dir / filename
                    
                    chart_area.screenshot(str(filepath))
                    chart_screenshots["chart_1hour"] = str(filepath)
                    logger.info(f"1시간봉 차트 캡처 완료: {filename}")
                    
                except Exception as area_error:
                    # 전체 페이지 캡처로 폴백
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{stock_code}_chart_1hour_full_{timestamp}.{self.config.screenshot.format}"
                    filepath = self.current_stock_screenshot_dir / filename
                    
                    self.driver.save_screenshot(str(filepath))
                    chart_screenshots["chart_1hour_full"] = str(filepath)
                    logger.info(f"1시간봉 차트 전체 페이지 캡처 완료: {filename}")
                
            except Exception as hour_error:
                logger.error(f"1시간봉 차트 캡처 실패: {hour_error}")
            
            logger.info(f"전문 차트 캡처 완료: {len(chart_screenshots)}개 스크린샷")
            logger.info("보조지표 설정이 Chrome 사용자 프로필에 저장됩니다.")
            
        except Exception as e:
            logger.error(f"전문 차트 페이지 캡처 실패: {e}")
            
        return chart_screenshots
    
    def save_data_to_json(self, stock_data: StockData, filepath: Optional[str] = None) -> str:
        """
        수집된 데이터를 JSON 파일로 저장
        
        Args:
            stock_data: 저장할 주식 데이터
            filepath: 저장할 파일 경로 (None이면 자동 생성)
            
        Returns:
            저장된 파일 경로
        """
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{stock_data.stock_code}_{timestamp}.json"
            filepath = self.screenshot_dir.parent / "data" / filename
            filepath.parent.mkdir(exist_ok=True)
        
        try:
            # dataclass를 dict로 변환
            data_dict = {
                "stock_code": stock_data.stock_code,
                "stock_name": stock_data.stock_name,
                "current_price": stock_data.current_price,
                "price_change": stock_data.price_change,
                "change_rate": stock_data.change_rate,
                "volume": stock_data.volume,
                "market_cap": stock_data.market_cap,
                "investment_opinion": stock_data.investment_opinion,
                "news_data": stock_data.news_data,
                "discussion_data": stock_data.discussion_data,
                "related_themes": stock_data.related_themes,
                "chart_screenshots": stock_data.chart_screenshots,
                "financial_data": stock_data.financial_data,
                "technical_indicators": stock_data.technical_indicators,
                "collected_at": stock_data.collected_at
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"데이터 JSON 저장 완료: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"JSON 저장 실패: {e}")
            raise