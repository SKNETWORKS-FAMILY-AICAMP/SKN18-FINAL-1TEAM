##############################################################
#  Serve - 서울시 전체 원룸/투룸 매물 크롤러 (자치구/읍면동 단위)
#  - 지도 위 동 라벨 클릭 ❌ (매물 안 뜸)
#  - 위치 팝업(서울특별시 > 구 > 동 > "지도에서 검색") 기반 ✅
##############################################################
import os
import csv
import json
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


##############################################################
# 0. 유틸: 이미지 저장 & 스크롤
##############################################################
def download_images(image_urls, save_dir, prefix):
    """상세 페이지에서 수집한 이미지 URL들을 로컬에 저장"""
    if not image_urls:
        return
    os.makedirs(save_dir, exist_ok=True)

    for idx, url in enumerate(image_urls):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            filename = f"{save_dir}/{prefix}_{idx+1}.jpg"
            with open(filename, "wb") as f:
                f.write(resp.content)
        except Exception as e:
            print("[이미지 다운로드 실패]", url, e)


def scroll_detail(page):
    """상세 페이지 끝까지 스크롤 (lazy-load 대비)"""
    # 여러 번 스크롤해서 모든 콘텐츠 로드
    for _ in range(3):
        # 천천히 스크롤 다운
        page.evaluate("""
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            });
        """)
        time.sleep(1.0)
    
    # 다시 맨 위로
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)
    
    # 한 번 더 끝까지 스크롤
    last_height = -1
    max_attempts = 5
    attempts = 0
    
    while attempts < max_attempts:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.8)
        new_height = page.evaluate("document.body.scrollHeight")
        
        if new_height == last_height:
            break
        
        last_height = new_height
        attempts += 1
    
    # 최종적으로 맨 위로 돌아가기
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)


##############################################################
# 1. 상세 페이지 파싱
##############################################################
def parse_detail(soup: BeautifulSoup) -> dict:
    """상세 페이지 HTML(BeautifulSoup)에서 필요한 정보 추출"""
    data = {}

    def pick(selector):
        el = soup.select_one(selector)
        return el.text.strip() if el else None

    # 기본 정보
    data["설명"] = pick("p.detail-explain")
    data["가격"] = pick("p.detail-price")
    data["서브정보"] = pick("p.t-detail-sub-desc")

    # 이미지 URL
    imgs = soup.select("div.swiper-slide img")
    data["이미지"] = [img["src"] for img in imgs if img.get("src") and "http" in img.get("src")]

    # 상세 정보 (ul.t-press-sale-info)
    상세정보 = {}
    for li in soup.select("ul.t-press-sale-info li"):
        strong = li.select_one("strong")
        p = li.select_one("p")
        if strong and p:
            key = strong.text.strip()
            value = p.text.strip()
            상세정보[key] = value
    data["상세정보"] = 상세정보
    
    # 관리비 상세 (팝업 내용)
    관리비상세 = {}
    popup = soup.select_one("div.mnex-detail-popup")
    if popup:
        for tr in popup.select("table tr"):
            tds = tr.select("td")
            if len(tds) >= 2:
                key = tds[0].text.strip()
                value = tds[1].text.strip()
                관리비상세[key] = value
    data["관리비상세"] = 관리비상세

    # 생활시설
    생활시설 = []
    for group in soup.select("div.t-detail-cont-group"):
        tit = group.select_one("div.detail-tit")
        if tit and "생활시설" in tit.text:
            for li in group.select("ul.t-detail-cont-icons li"):
                desc = li.select_one("span.icon-desc")
                if desc:
                    생활시설.append(desc.text.strip())
    data["생활시설"] = 생활시설

    # 보안시설
    보안시설 = []
    for group in soup.select("div.t-detail-cont-group"):
        tit = group.select_one("div.detail-tit")
        if tit and "보안시설" in tit.text:
            for li in group.select("ul.t-detail-cont-icons li"):
                desc = li.select_one("span.icon-desc")
                if desc:
                    보안시설.append(desc.text.strip())
    data["보안시설"] = 보안시설

    # 기타시설
    기타시설 = []
    for group in soup.select("div.t-detail-cont-group"):
        tit = group.select_one("div.detail-tit")
        if tit and "기타시설" in tit.text:
            for li in group.select("ul.t-detail-cont-icons li"):
                desc = li.select_one("span.icon-desc")
                if desc:
                    기타시설.append(desc.text.strip())
    data["기타시설"] = 기타시설

    # 비용 정보
    비용정보 = {}
    for group in soup.select("div.t-detail-cont-group"):
        tit = group.select_one("div.detail-tit")
        if tit and "비용" in tit.text:
            for tr in group.select("table tr"):
                tds = tr.select("td")
                if len(tds) >= 2:
                    key = tds[0].text.strip()
                    value = tds[1].text.strip()
                    비용정보[key] = value
    data["비용정보"] = 비용정보


    # 광고주 정보
    광고주 = {}
    advertiser = soup.select_one("div.t-detail-advertiser")
    if advertiser:
        # 중개사명
        strong = advertiser.select_one("div.advertiser-desc strong")
        if strong:
            광고주["중개사명"] = strong.text.strip()
        
        # 나머지 정보들
        desc_p = advertiser.select("div.advertiser-desc p")
        for p in desc_p:
            text = p.text.strip()
            if text.startswith("대표"):
                광고주["대표"] = text.replace("대표", "").strip()
            elif text.startswith("개설등록번호"):
                광고주["개설등록번호"] = text.replace("개설등록번호", "").strip()
            elif "특별시" in text or "광역시" in text or "도" in text:
                광고주["주소"] = text
            elif text.startswith("http"):
                광고주["홈페이지"] = text
        
        # 전화번호들
        전화번호 = []
        phone_btns = advertiser.select("button.btn-phone span.v-btn__content")
        for btn in phone_btns:
            phone = btn.text.strip()
            if phone:
                전화번호.append(phone)
        if 전화번호:
            광고주["전화번호"] = 전화번호
        
        # 프로필 이미지
        img = advertiser.select_one("div.advertiser-thumb img")
        if img and img.get("src"):
            광고주["프로필이미지"] = img["src"]
    
    data["광고주"] = 광고주

    return data


##############################################################
# 2. 우측 매물 리스트 → 상세 페이지 크롤링
##############################################################
def crawl_dong_from_map(page, sido, sigu, dong):
    """현재 화면(특정 동)에 대해 오른쪽 매물 리스트를 돌며 상세 크롤링"""
    results = []

    try:
        # 매물 리스트 컨테이너 대기
        try:
            page.wait_for_selector("ul.t-sale-list", timeout=10000)
            time.sleep(1.5)
        except:
            print(f"[매물없음] {sigu} {dong} - 매물 리스트를 찾을 수 없음")
            return results
        
        # 매물 아이템 찾기 (ul.t-sale-list 안의 li)
        items = page.query_selector_all("ul.t-sale-list li")
        
        print(f"[INFO] {sido} {sigu} {dong} 매물 수: {len(items)}")
        
        if len(items) == 0:
            print(f"[매물없음] {sigu} {dong} - 등록된 매물이 없습니다")
            return results

        for idx in range(len(items)):
            try:
                print(f"[{sigu} {dong}] 매물 {idx+1}/{len(items)} 상세 진입 중…")

                # 매번 새로 가져오기 (stale element 방지)
                # 뒤로가기 후 리스트가 사라졌을 수 있으니 확인
                try:
                    page.wait_for_selector("ul.t-sale-list", timeout=5000)
                except:
                    print(f"[WARNING] 매물 리스트가 사라짐, 건너뜀")
                    break
                
                items = page.query_selector_all("ul.t-sale-list li")
                
                if idx >= len(items):
                    print(f"[WARNING] 매물 인덱스 초과, 종료")
                    break

                # li 안의 button.t-list-btn 클릭
                btn = items[idx].query_selector("button.t-list-btn")
                if not btn:
                    print(f"[WARNING] 매물 {idx+1} 버튼을 찾을 수 없음")
                    continue
                
                # 버튼이 보이는지 확인
                if not btn.is_visible():
                    print(f"[WARNING] 매물 {idx+1} 버튼이 보이지 않음")
                    continue
                
                # Playwright의 Locator로 변환해서 스크롤
                btn_locator = page.locator(f"ul.t-sale-list li:nth-child({idx+1}) button.t-list-btn")
                btn_locator.scroll_into_view_if_needed()
                time.sleep(0.5)
                btn_locator.click()
                time.sleep(3.0)

                # 상세 페이지로 이동했는지 확인
                try:
                    page.wait_for_selector(".detail-explain, .detail-price", timeout=5000)
                except:
                    print(f"[WARNING] 매물 {idx+1} 상세 페이지 로드 실패")
                    continue

                scroll_detail(page)

                soup = BeautifulSoup(page.content(), "html.parser")
                info = parse_detail(soup)
                info["sido"] = sido
                info["sigu"] = sigu
                info["dong"] = dong
                
                # 디버깅: 수집된 정보 출력
                print(f"    ✓ 매물 {idx+1} 정보 수집 완료")
                print(f"      - 제목: {info.get('title', 'N/A')}")
                print(f"      - 가격: {info.get('price', 'N/A')}")
                print(f"      - 이미지 수: {len(info.get('images', []))}")
                
                results.append(info)

                # 이미지 저장 (옵션)
                if info.get("images"):
                    title_safe = (info.get("title") or "no_title").replace("/", "_").replace("\\", "_")
                    save_dir = f"images/{sido}/{sigu}/{dong}/{title_safe}"
                    download_images(info["images"], save_dir, title_safe)

                # 뒤로가기 → 다시 리스트 화면
                page.go_back(wait_until="domcontentloaded")
                time.sleep(2.0)
                
                # 리스트가 다시 나타날 때까지 대기
                try:
                    page.wait_for_selector("ul.t-sale-list", timeout=5000)
                except:
                    print(f"[WARNING] 뒤로가기 후 매물 리스트 복구 실패")
                    break
                
            except Exception as e:
                print(f"[ERROR] 매물 {idx+1} 크롤링 실패: {e}")
                try:
                    # 상세 페이지에 있으면 뒤로가기
                    if page.query_selector(".detail-explain"):
                        page.go_back()
                        time.sleep(2.0)
                except:
                    pass
                continue

    except Exception as e:
        print(f"[ERROR] {sigu} {dong} 크롤링 실패: {e}")

    return results


##############################################################
# 3. 왼쪽 패널 위치 선택 (서울특별시 / 자치구 / 동 선택)
##############################################################
def wait_for_left_panel(page):
    """왼쪽 지역 선택 패널이 로드될 때까지 대기"""
    try:
        page.wait_for_selector(".navi-city", timeout=10000)
        time.sleep(1.0)
    except:
        print("[WARNING] 왼쪽 패널 로드 대기 실패, 계속 진행")
        time.sleep(2.0)


def click_navi_button(page):
    """지역 선택 네비게이션 버튼 클릭"""
    try:
        navi_btn = page.locator(".navi-city").first
        navi_btn.click()
        print("[LOG] 지역 선택 버튼 클릭 완료")
        time.sleep(2.0)
    except Exception as e:
        print(f"[ERROR] 지역 선택 버튼 클릭 실패: {e}")


def click_seoul(page):
    """왼쪽 패널에서 '서울특별시' 선택"""
    try:
        seoul_label = page.locator("label:has-text('서울특별시')").first
        seoul_label.scroll_into_view_if_needed()
        time.sleep(0.5)
        seoul_label.click()
        print("[LOG] 서울특별시 선택 완료")
        time.sleep(2.0)
    except Exception as e:
        print(f"[ERROR] 서울특별시 클릭 실패: {e}")


def get_gu_list(page):
    """
    왼쪽 패널에서 서울 자치구 목록 가져오기
    """
    wait_for_left_panel(page)
    click_navi_button(page)
    click_seoul(page)
    
    # 자치구 목록 가져오기
    gu_names = []
    try:
        # v-label--clickable 클래스를 가진 label 찾기
        labels = page.locator("label.v-label--clickable").all()
        print(f"[DEBUG] 찾은 label 수: {len(labels)}")
        
        for label in labels:
            try:
                text = label.inner_text().strip()
                # 자치구 이름 필터링 (끝에 '구'가 있는 것만)
                if text and text.endswith("구") and len(text) <= 10:
                    gu_names.append(text)
            except:
                continue
        
        # 중복 제거
        gu_names = list(dict.fromkeys(gu_names))
        print(f"[LOG] 총 {len(gu_names)}개 자치구 발견")
        
    except Exception as e:
        print(f"[ERROR] 자치구 목록 가져오기 실패: {e}")
    
    return gu_names


def get_dong_list(page, gu_name, is_first=False):
    """
    특정 자치구 선택 후 읍면동 목록 가져오기
    """
    # 첫 번째 자치구가 아니면 목록 다시 열기
    if not is_first:
        try:
            click_navi_button(page)
            click_seoul(page)
        except Exception as e:
            print(f"[WARNING] 자치구 목록 다시 열기 실패: {e}")
    
    # 자치구 클릭 (정확한 텍스트 매칭)
    try:
        # XPath로 정확한 텍스트 매칭
        gu_label = page.locator(f"xpath=//label[text()='{gu_name}']").first
        gu_label.click()
        print(f"[LOG] {gu_name} 선택 완료")
        time.sleep(2.0)
    except Exception as e:
        print(f"[ERROR] {gu_name} 클릭 실패: {e}")
        return []
    
    # 읍면동 목록 가져오기
    dong_names = []
    try:
        labels = page.locator("label.v-label--clickable").all()
        
        for label in labels:
            try:
                text = label.inner_text().strip()
                # 동 이름 필터링 (끝에 '동'이 있고, 자치구 이름이 아닌 것)
                if text and text.endswith("동") and len(text) <= 10 and text != gu_name:
                    dong_names.append(text)
            except:
                continue
        
        # 중복 제거
        dong_names = list(dict.fromkeys(dong_names))
        
        # "동", "남동", "북동" 같은 너무 짧은 이름 제거
        dong_names = [d for d in dong_names if len(d) >= 3]
        
        print(f"[LOG] {gu_name}에서 총 {len(dong_names)}개 동 발견")
        
    except Exception as e:
        print(f"[ERROR] 읍면동 목록 가져오기 실패: {e}")
    
    return dong_names


def select_dong(page, dong_name):
    """
    동을 선택하여 오른쪽에 매물 리스트 표시
    (이미 동 목록이 열려있는 상태에서 호출)
    """
    try:
        # XPath로 정확한 텍스트 매칭 (부분 매칭 방지)
        dong_label = page.locator(f"xpath=//label[text()='{dong_name}']").first
        dong_label.click()
        print(f"[LOG] {dong_name} 선택 완료")
        time.sleep(2.0)  # 매물 리스트 로딩 대기
    except Exception as e:
        print(f"[ERROR] {dong_name} 클릭 실패: {e}")


##############################################################
# 4. 서울 전체(자치구/읍면동) 크롤링
##############################################################
def crawl_seoul_all():
    all_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 데스크탑 뷰 고정
        page.set_viewport_size({"width": 1400, "height": 900})

        # 1) 메인 진입
        page.goto("https://www.serve.co.kr/main", wait_until="networkidle")
        time.sleep(1.5)
        print("[LOG] 메인 진입 완료")

        # 2) 상단 '원룸 원/투룸' 탭 클릭
        page.get_by_role("button", name="원룸 원/투룸").click()
        print("[LOG] 원룸 탭 클릭 완료")
        time.sleep(1.2)

        # 3) 지도 페이지로 이동 ('지도검색' or '매물 찾기' 등)
        try:
            page.locator("span.v-btn__content:has-text('지도검색')").first.click()
        except:
            try:
                page.locator("span.v-btn__content:has-text('매물 찾기')").first.click()
            except:
                page.locator("span.v-btn__content:has-text('지도')").first.click()

        print("[LOG] 지도 페이지 진입 완료")
        time.sleep(3.0)  # 지도 로딩 대기 시간 증가
        
        # 페이지가 완전히 로드될 때까지 대기 (타임아웃 에러 방지)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            print("[WARNING] networkidle 대기 타임아웃, 계속 진행")
        time.sleep(1.0)

        # 4) 서울 자치구 목록 확보
        gu_names = get_gu_list(page)
        print("[LOG] 서울 자치구 목록:", gu_names)

        # 5) 각 자치구 반복 (전체)
        for gu_idx, gu_name in enumerate(gu_names, 1):
            print("\n" + "="*50)
            print(f"[{gu_idx}/{len(gu_names)}] {gu_name}")
            print("="*50)

            gu_data = []  # 이 자치구의 매물만 저장
            
            # 첫 번째 자치구는 이미 목록이 열려있음
            is_first = (gu_idx == 1)
            dong_names = get_dong_list(page, gu_name, is_first)
            print(f"[LOG] {gu_name} 읍면동 목록 ({len(dong_names)}개): {dong_names}")

            # 동 목록이 이미 열려있는 상태에서 각 동 순회 (전체)
            for dong_idx, dong_name in enumerate(dong_names, 1):
                print(f"\n--- [{dong_idx}/{len(dong_names)}] {gu_name} {dong_name} ---")

                # 해당 동 선택 (동 목록이 열려있는 상태)
                select_dong(page, dong_name)

                # 매물 크롤링
                dong_data = crawl_dong_from_map(page, "서울특별시", gu_name, dong_name)
                gu_data.extend(dong_data)
                all_data.extend(dong_data)
                
                print(f"[결과] {gu_name} {dong_name}: {len(dong_data)}개 매물 수집 완료")
                print(f"[누적] 현재까지 총 {len(all_data)}개 매물 수집")
            
            # 자치구별 저장
            print(f"\n[자치구 완료] {gu_name}: 총 {len(gu_data)}개 매물")
            save_gu_results(gu_name, gu_data)
            
            # 매물 리스트 영역 닫기 (다음 구 선택을 위해)
            try:
                # ESC 키로 닫기 시도
                page.keyboard.press("Escape")
                time.sleep(0.5)
                
                # 또는 X 버튼 클릭
                close_btns = page.query_selector_all("button[class*='close'], button[aria-label='close']")
                for btn in close_btns:
                    try:
                        if btn.is_visible():
                            btn.click()
                            break
                    except:
                        continue
                
                print("[LOG] 매물 리스트 영역 닫기 완료")
            except Exception as e:
                print(f"[WARNING] 매물 리스트 닫기 실패: {e}")
            
            time.sleep(2.0)

        browser.close()

    return all_data


##############################################################
# 5. 결과 저장
##############################################################
def save_results(data, filename_prefix="serve_seoul_rooms"):
    """결과를 JSON과 CSV로 저장"""
    os.makedirs("results", exist_ok=True)

    # JSON
    with open(f"results/{filename_prefix}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # CSV 요약
    with open(f"results/{filename_prefix}.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["시도", "자치구", "동", "설명", "가격", "이미지수"])
        for d in data:
            writer.writerow([
                d.get("sido"),
                d.get("sigu"),
                d.get("dong"),
                d.get("설명"),
                d.get("가격"),
                len(d.get("이미지") or []),
            ])
    
    print(f"[저장완료] {filename_prefix}.json, {filename_prefix}.csv")


def save_gu_results(gu_name, gu_data):
    """자치구별로 결과 저장"""
    if not gu_data:
        return
    
    gu_dir = f"results/{gu_name}"
    os.makedirs(gu_dir, exist_ok=True)
    
    # JSON
    with open(f"{gu_dir}/{gu_name}_매물.json", "w", encoding="utf-8") as f:
        json.dump(gu_data, f, ensure_ascii=False, indent=4)
    
    # CSV
    with open(f"{gu_dir}/{gu_name}_매물.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["시도", "자치구", "동", "설명", "가격", "서브정보", "이미지수"])
        for d in gu_data:
            writer.writerow([
                d.get("sido"),
                d.get("sigu"),
                d.get("dong"),
                d.get("설명"),
                d.get("가격"),
                d.get("서브정보"),
                len(d.get("이미지") or []),
            ])
    
    print(f"[저장완료] {gu_name} 폴더에 {len(gu_data)}개 매물 저장")


##############################################################
# 6. 실행부
##############################################################
if __name__ == "__main__":
    data = crawl_seoul_all()
    save_results(data)

    print("\n========================")
    print("  서울시 원룸/투룸 전체 크롤링 완료")
    print("========================")
    print("총 매물:", len(data))