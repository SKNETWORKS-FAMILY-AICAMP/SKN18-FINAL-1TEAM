import asyncio
import numpy as np
import urllib.parse
from playwright.async_api import async_playwright
import json
import os
import sys
from global_land_mask import globe
import time

# ======================================================
# 1. [설정] 서울 전역 좌표 및 5개 그룹 정의
# ======================================================
ZOOM_LEVEL = 16
LAT_STEP = 0.015
LNG_STEP = 0.015

TARGET_ZONES = {
    # --- 1그룹: 강남권 ---
    "강남구": {"lat_min": 37.470, "lat_max": 37.535, "lng_min": 127.010, "lng_max": 127.080},
    "서초구": {"lat_min": 37.440, "lat_max": 37.520, "lng_min": 126.990, "lng_max": 127.050},
    "송파구": {"lat_min": 37.470, "lat_max": 37.530, "lng_min": 127.070, "lng_max": 127.150},
    "강동구": {"lat_min": 37.520, "lat_max": 37.580, "lng_min": 127.110, "lng_max": 127.190},

    # --- 2그룹: 서남권 ---
    "관악구": {"lat_min": 37.455, "lat_max": 37.490, "lng_min": 126.900, "lng_max": 126.970},
    "동작구": {"lat_min": 37.475, "lat_max": 37.515, "lng_min": 126.905, "lng_max": 126.985},
    "영등포구": {"lat_min": 37.490, "lat_max": 37.555, "lng_min": 126.880, "lng_max": 126.950},
    "구로구": {"lat_min": 37.460, "lat_max": 37.510, "lng_min": 126.810, "lng_max": 126.900},
    "금천구": {"lat_min": 37.430, "lat_max": 37.485, "lng_min": 126.870, "lng_max": 126.915},

    # --- 3그룹: 서북권 ---
    "강서구": {"lat_min": 37.530, "lat_max": 37.570, "lng_min": 126.820, "lng_max": 126.880},
    "양천구": {"lat_min": 37.505, "lat_max": 37.555, "lng_min": 126.820, "lng_max": 126.890},
    "마포구": {"lat_min": 37.535, "lat_max": 37.575, "lng_min": 126.880, "lng_max": 126.960},
    "서대문구": {"lat_min": 37.550, "lat_max": 37.600, "lng_min": 126.900, "lng_max": 126.970},
    "은평구": {"lat_min": 37.570, "lat_max": 37.650, "lng_min": 126.880, "lng_max": 126.950},

    # --- 4그룹: 도심 & 성동광진 ---
    "종로구": {"lat_min": 37.560, "lat_max": 37.630, "lng_min": 126.950, "lng_max": 127.020},
    "중구":   {"lat_min": 37.540, "lat_max": 37.570, "lng_min": 126.960, "lng_max": 127.020},
    "용산구": {"lat_min": 37.510, "lat_max": 37.555, "lng_min": 126.940, "lng_max": 127.015},
    "성동구": {"lat_min": 37.530, "lat_max": 37.575, "lng_min": 127.010, "lng_max": 127.070},
    "광진구": {"lat_min": 37.525, "lat_max": 37.575, "lng_min": 127.050, "lng_max": 127.120},

    # --- 5그룹: 동북권 ---
    "동대문구": {"lat_min": 37.560, "lat_max": 37.610, "lng_min": 127.020, "lng_max": 127.080},
    "중랑구": {"lat_min": 37.570, "lat_max": 37.630, "lng_min": 127.070, "lng_max": 127.120},
    "성북구": {"lat_min": 37.575, "lat_max": 37.620, "lng_min": 127.000, "lng_max": 127.070},
    "강북구": {"lat_min": 37.610, "lat_max": 37.690, "lng_min": 127.000, "lng_max": 127.050},
    "도봉구": {"lat_min": 37.640, "lat_max": 37.690, "lng_min": 127.010, "lng_max": 127.060},
    "노원구": {"lat_min": 37.615, "lat_max": 37.670, "lng_min": 127.040, "lng_max": 127.100},
}

# ======================================================
# 2. 중복 ID 관리
# ======================================================
MASTER_ID_FILE = 'crawled_ids.txt'

def load_master_ids():
    if not os.path.exists(MASTER_ID_FILE):
        return set()
    try:
        with open(MASTER_ID_FILE, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except:
        return set()

def update_and_save_master_ids(new_ids_set):
    if not new_ids_set:
        return
    try:
        current_file_ids = set()
        if os.path.exists(MASTER_ID_FILE):
            with open(MASTER_ID_FILE, 'r', encoding='utf-8') as f:
                current_file_ids = {line.strip() for line in f if line.strip()}
        merged_ids = current_file_ids.union(new_ids_set)
        with open(MASTER_ID_FILE, 'w', encoding='utf-8') as f:
            for item_id in sorted(list(merged_ids)):
                f.write(f"{item_id}\n")
        print(f"--- [ID 저장] 통합 {len(merged_ids)}개 저장 완료 (이번 추가: {len(new_ids_set)}개) ---")
    except Exception as e:
        print(f"--- [ID 저장 오류] {e}")

# ======================================================
# 2-1. JSON 파일 병합 (크롤링 완료 후 자동 실행)
# ======================================================
def merge_json_by_category():
    """
    카테고리별 JSON 파일 병합 (크롤링 완료 후 자동 실행)
    기능:
    1. 구역별 JSON 파일들을 카테고리별로 병합
    2. 현재 크롤링에서 발견되지 않은 매물(판매 완료) 자동 삭제
    3. 중복 제거 후 통합 파일 저장
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, 'data')

    if not os.path.exists(data_dir):
        print(f"❌ 오류: '{data_dir}' 폴더를 찾을 수 없습니다.")
        return

    category_map = {
        # "아파트": "00_통합_아파트.json",
        # "원투룸": "00_통합_원투룸.json",
        "빌라주택": "00_통합_빌라주택.json",
        # "오피스텔": "00_통합_오피스텔.json"
    }

    all_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
    print(f"\n--- [병합 시작] '{data_dir}' 폴더 내 JSON 파일 {len(all_files)}개 감지됨 ---")

    total_removed = 0

    for keyword, output_filename in category_map.items():
        merged_data = []
        processed_files_count = 0
        target_files = [f for f in all_files if keyword in f and "00_통합" not in f]

        if not target_files:
            continue

        print(f"\n>> 카테고리: '{keyword}' 병합 중... (대상 파일: {len(target_files)}개)")

        current_crawl_ids = set()
        for filename in target_files:
            file_path = os.path.join(data_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        merged_data.extend(data)
                        processed_files_count += 1
                        for item in data:
                            if item.get('매물번호'):
                                current_crawl_ids.add(item.get('매물번호'))
            except Exception as e:
                print(f"  [오류] '{filename}' 읽기 실패: {e}")

        if not merged_data:
            continue

        output_path = os.path.join(data_dir, output_filename)
        removed_count = 0

        if os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                    if isinstance(old_data, list):
                        old_ids = {item.get('매물번호') for item in old_data if item.get('매물번호')}
                        sold_ids = old_ids - current_crawl_ids
                        removed_count = len(sold_ids)
                        total_removed += removed_count
                        if sold_ids:
                            print(f"  🗑️ 판매 완료된 매물 {removed_count}개 삭제됨")
                            sample_ids = list(sold_ids)[:5]
                            print(f"     예시: {sample_ids}{'...' if len(sold_ids) > 5 else ''}")
            except Exception as e:
                print(f"  [경고] 기존 파일 읽기 실패: {e}")

        unique_data = {item.get('매물번호'): item for item in merged_data if item.get('매물번호')}.values()
        final_list = list(unique_data)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 저장 완료: {output_filename}")
            print(f"  📊 현재 매물: {len(final_list)}개 (파일 {processed_files_count}개 병합)")
        except Exception as e:
            print(f"  ❌ 저장 실패: {e}")

    if total_removed > 0:
        print(f"\n🗑️ 총 {total_removed}개의 판매 완료 매물이 정리되었습니다.")
        cleanup_master_ids(data_dir)

    print("\n--- [병합 완료] 모든 작업이 끝났습니다. ---")

def cleanup_master_ids(data_dir: str):
    try:
        valid_ids = set()
        for filename in os.listdir(data_dir):
            if filename.startswith("00_통합") and filename.endswith(".json"):
                file_path = os.path.join(data_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if item.get('매물번호'):
                                valid_ids.add(item.get('매물번호'))

        if valid_ids and os.path.exists(MASTER_ID_FILE):
            with open(MASTER_ID_FILE, 'w', encoding='utf-8') as f:
                for item_id in sorted(list(valid_ids)):
                    f.write(f"{item_id}\n")
            print(f"  📝 crawled_ids.txt 정리 완료 ({len(valid_ids)}개 유지)")
    except Exception as e:
        print(f"  [경고] ID 파일 정리 실패: {e}")

# ======================================================
# 3. 유틸리티 함수들
# ======================================================
def generate_coordinate_grid(zone_name):
    if zone_name not in TARGET_ZONES:
        print(f"Error: '{zone_name}' 구역 정보가 없습니다.")
        return []

    zone = TARGET_ZONES[zone_name]
    coordinates = []
    print(f"--- [좌표 생성] '{zone_name}' (Zoom {ZOOM_LEVEL}) ---")

    lat_points = np.arange(zone["lat_min"], zone["lat_max"], LAT_STEP)
    lng_points = np.arange(zone["lng_min"], zone["lng_max"], LNG_STEP)

    for lat in lat_points:
        for lng in lng_points:
            if globe.is_land(lat, lng):
                coordinates.append({'lat': lat, 'lng': lng, 'zoom': ZOOM_LEVEL})

    print(f"--- [완료] '{zone_name}' 총 {len(coordinates)}개의 격자 좌표 생성 ---")
    return coordinates

async def scroll_to_bottom(page, item_selector):
    scroll_container = ".list__wrapper"
    try:
        if page.is_closed():
            print("  ⚠️ Page is closed, skipping scroll")
            return False

        await page.wait_for_selector(scroll_container, timeout=10000)
        list_cont = page.locator(scroll_container)
        last_cnt = 0
        no_change_count = 0

        while True:
            try:
                if page.is_closed():
                    print("  ⚠️ Page crashed during scroll")
                    return False

                await list_cont.click(timeout=1000)
                await list_cont.press('PageDown')
                await page.wait_for_timeout(500)
            except Exception as e:
                if "Page crashed" in str(e) or "Target closed" in str(e):
                    print(f"  ⚠️ Page crashed detected: {e}")
                    return False

            for _ in range(5):
                try:
                    await list_cont.press('PageDown')
                    await page.wait_for_timeout(300)
                except Exception as e:
                    if "Page crashed" in str(e) or "Target closed" in str(e):
                        return False
                    break

            cur_cnt = await page.locator(item_selector).count()
            if cur_cnt == last_cnt:
                no_change_count += 1
                if no_change_count >= 3:
                    break
                try:
                    await page.wait_for_function(
                        f"document.querySelectorAll('{item_selector}').length > {last_cnt}",
                        timeout=5000
                    )
                    no_change_count = 0
                    continue
                except:
                    break
            else:
                no_change_count = 0
            last_cnt = cur_cnt
        return True
    except Exception as e:
        if "Page crashed" in str(e) or "Target closed" in str(e):
            print(f"  ⚠️ Page crashed in scroll_to_bottom: {e}")
            return False
        return True

# ======================================================
# 상세 페이지 스크랩
# ======================================================
async def scrape_detail_page(new_page):
    page_url = new_page.url
    listing_id = page_url.split('/house/')[-1].split('?')[0] if '/house/' in page_url else None

    final_data = {
        '중개사_정보': {},
        '매물번호': listing_id,
        '매물_URL': page_url,
        '매물_이미지': [],
        '주소_정보': {},
        '평면도_URL': [],
        '거래_정보': {},
        '매물_정보': {},
        '추가_옵션': [],
        '주변_학교': [],
        '상세_설명': ""
    }

    # 1. 매물 이미지
    try:
        img_elements = await new_page.locator(".carousel-inner .item img.photo").all()
        for img in img_elements:
            src = await img.get_attribute("src")
            if src and src not in final_data['매물_이미지']:
                final_data['매물_이미지'].append(src)

        if not final_data['매물_이미지']:
            await new_page.wait_for_selector(".carousel-inner", timeout=2000)
            img_elements = await new_page.locator(".carousel-inner img").all()
            for img in img_elements:
                src = await img.get_attribute("src")
                if src and src not in final_data['매물_이미지']:
                    final_data['매물_이미지'].append(src)
    except:
        pass

    # 2. 주소
    try:
        addr_sel = ".div-detail-house-address-type > span, span.address"
        await new_page.wait_for_selector(addr_sel, timeout=3000)
        final_data['주소_정보']['전체주소'] = (await new_page.locator(addr_sel).first.inner_text()).strip()
    except:
        pass

    # 3. 중개사
    try:
        sb = new_page.locator(".sidebar-content").first
        if await sb.count() > 0:
            agency_name_selector = ".agency-name"
            if await sb.locator(agency_name_selector).count() > 0:
                final_data['중개사_정보']['중개사명'] = (await sb.locator(agency_name_selector).inner_text()).strip()

            txt = await sb.inner_text()
            for line in txt.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if "대표번호" in line:
                    final_data['중개사_정보']['전화번호'] = line.replace("대표번호", "").strip()
                elif "주소" in line:
                    final_data['중개사_정보']['주소'] = line.replace("주소", "").strip()
                elif "등록번호" in line:
                    final_data['중개사_정보']['등록번호'] = line.replace("중개사무소", "").replace("등록번호", "").strip()
                elif "대표자" in line:
                    final_data['중개사_정보']['대표자'] = line.replace("대표자", "").strip()
                elif "대표 " in line and "대표자" not in final_data['중개사_정보']:
                    final_data['중개사_정보']['담당자'] = line.replace("대표", "").strip()

            stat_items = await sb.locator(".agency-house .item-wrapper").all()
            for item in stat_items:
                try:
                    title_el = item.locator(".agency-house-title")
                    count_el = item.locator(".agency-house-count")
                    if await title_el.count() > 0 and await count_el.count() > 0:
                        title = (await title_el.inner_text()).strip()
                        count = (await count_el.inner_text()).strip()
                        if "거래완료" in title:
                            final_data['중개사_정보']['거래완료'] = count
                        elif "등록매물" in title:
                            final_data['중개사_정보']['등록매물'] = count
                except:
                    pass
    except:
        pass

    # 4. 평면도
    try:
        plan_imgs = await new_page.locator("div[id^='aptPlanImage'] img").all()
        for img in plan_imgs:
            src = await img.get_attribute("src")
            if src and src not in final_data['평면도_URL']:
                final_data['평면도_URL'].append(src)
        if not final_data['평면도_URL']:
            fallback_imgs = await new_page.locator(".detail-aptPlanImage img").all()
            for img in fallback_imgs:
                src = await img.get_attribute("src")
                if src and src not in final_data['평면도_URL']:
                    final_data['평면도_URL'].append(src)
    except:
        pass

    # 5. 상세 정보
    rows = await new_page.locator(".detail-table-row").all()
    for r in rows:
        try:
            k = (await r.locator(".detail-table-th").inner_text()).strip()
            v = (await r.locator(".detail-table-td").inner_text()).strip().replace('\n', ' ')
            if k in ["거래방식", "관리비", "융자금", "입주가능일"]:
                final_data['거래_정보'][k] = v
            else:
                final_data['매물_정보'][k] = v
        except:
            pass

    # 6. 추가옵션
    try:
        options_container = new_page.locator(".detail-option-table dd")
        if await options_container.count() > 0:
            all_options = await options_container.all()
            for opt in all_options:
                text = await opt.inner_text()
                if text.strip():
                    final_data['추가_옵션'].append(text.strip())
    except:
        pass

    # 7. 주변학교
    try:
        school_header = new_page.locator("h3", has_text="주변학교")
        if await school_header.count() > 0:
            school_section = school_header.locator("xpath=..")
            school_buttons = await school_section.locator("button").all()
            for btn in school_buttons:
                school_name = (await btn.inner_text()).strip()
                if not school_name:
                    continue
                try:
                    await btn.click()
                    await new_page.wait_for_timeout(100)
                    addr_row = school_section.locator(".detail-table-row", has_text="주소")
                    if await addr_row.count() > 0:
                        full_text = await addr_row.inner_text()
                        address = full_text.replace("주소", "").strip()
                        final_data['주변_학교'].append({"학교명": school_name, "주소": address})
                except:
                    pass
    except:
        pass

    # 8. 상세설명
    try:
        desc_selector = "#description-text"
        if await new_page.locator(desc_selector).count() > 0:
            desc_text = await new_page.locator(desc_selector).inner_text()
            final_data['상세_설명'] = desc_text.strip()
    except:
        pass

    print("  ->  ... (새 탭) 상세 정보 스크랩 완료.")
    return final_data

async def extract_data_from_list(page, item_selector, all_data, master_set, current_session_ids):
    try:
        items = await page.locator(item_selector).all()
    except Exception as e:
        print(f"  ⚠️ Failed to get items: {e}")
        return False

    for item in items:
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries:
            try:
                hid = await item.get_attribute('data-hidx')
                if hid and hid in master_set:
                    break

                async with page.context.expect_page() as event:
                    await item.click(timeout=5000, force=True)
                npg = await event.value
                await npg.wait_for_load_state('domcontentloaded', timeout=30000)
                await npg.wait_for_timeout(300)  # 짧게 안정화

                data = await scrape_detail_page(npg)

                if not data['매물번호'] and hid:
                    data['매물번호'] = hid

                if data['매물번호']:
                    all_data.append(data)
                    master_set.add(data['매물번호'])
                    current_session_ids.add(data['매물번호'])

                await npg.close()
                await page.wait_for_timeout(300)  # 너무 길 필요 없음
                break

            except Exception as e:
                retry_count += 1
                if "Page crashed" in str(e) or "Target closed" in str(e):
                    print(f"  ⚠️ Page crashed while extracting item, retry {retry_count}/{max_retries}")
                    if retry_count > max_retries:
                        return False
                    await page.wait_for_timeout(2000)
                else:
                    if retry_count > max_retries:
                        print(f"  ⚠️ Failed to extract item after {max_retries} retries: {e}")
                    break
    return True

# ======================================================
# 4. 핵심 실행 로직
# ======================================================
async def run_zone_batch(zone_name):
    master_id_set = load_master_ids()
    current_session_new_ids = set()

    AREA_FILTER_PREFIX = "checkRealSize:d~40||"
    CATEGORIES = [
        # {"name": "아파트", "base": "https://www.peterpanz.com/apt", "filt": AREA_FILTER_PREFIX + 'buildingType;["아파트"]', "out": f"{zone_name}_아파트.json"},
        # {"name": "원,투룸", "base": "https://www.peterpanz.com/onetworoom", "filt": AREA_FILTER_PREFIX + 'buildingType;["원,투룸"]', "out": f"{zone_name}_원투룸.json"},
        {"name": "빌라,주택", "base": "https://www.peterpanz.com/villa", "filt": AREA_FILTER_PREFIX + 'buildingType;["빌라","주택"]', "out": f"{zone_name}_빌라주택.json"},
        # {"name": "오피스텔", "base": "https://www.peterpanz.com/officetel", "filt": AREA_FILTER_PREFIX + 'buildingType;["오피스텔"]', "out": f"{zone_name}_오피스텔.json"},
    ]

    coordinates = generate_coordinate_grid(zone_name)
    if not coordinates:
        return

    ITEM_SELECTOR = ".a-house"
    current_processing_data = []
    current_processing_filename = ""

    # 데스크톱 설정 상수
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    VIEWPORT = {"width": 1920, "height": 1080}

    # debug 디렉토리 (/tmp는 ECS에서 안전)
    DEBUG_DIR = os.environ.get("DEBUG_DIR", "/tmp/debug")

    try:
        async with async_playwright() as p:
            is_headless = os.environ.get("HEADLESS_MODE", "True").lower() == "true"

            for cat in CATEGORIES:
                print(f"\n🚀🚀🚀 [{zone_name}] 카테고리: '{cat['name']}' 시작 🚀🚀🚀")
                current_processing_data = []
                current_processing_filename = cat['out']

                # (중요) Automation 감지 완화 옵션 추가
                browser = await p.chromium.launch(
                    headless=is_headless,
                    args=[
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",
                        "--window-size=1920,1080",
                    ],
                )

                # Context 생성 (데스크톱 강제 설정)
                context = await browser.new_context(
                    user_agent=UA,
                    viewport=VIEWPORT,
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                    # 🔥 모바일 감지 방지 (핵심)
                    has_touch=False,
                    is_mobile=False,
                    device_scale_factor=1,
                    extra_http_headers={
                        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Upgrade-Insecure-Requests": "1",
                    },
                )

                # 🔥 데스크톱 쿠키 강제 설정 (피터팬 서버사이드 감지 우회)
                await context.add_cookies([
                    {
                        "name": "device_type",
                        "value": "pc",
                        "domain": ".peterpanz.com",
                        "path": "/",
                    },
                    {
                        "name": "view_type",
                        "value": "desktop",
                        "domain": ".peterpanz.com",
                        "path": "/",
                    },
                ])

                # 🔥 리소스 차단 (메모리/네트워크 부하 감소, 크래시 방지)
                async def block_resources(route):
                    req = route.request
                    if req.resource_type in ("image", "media", "font"):
                        return await route.abort()
                    # 광고/트래커 차단
                    url = req.url.lower()
                    if any(x in url for x in ["doubleclick", "googletagmanager", "google-analytics", "facebook", "tiktok", "kakao.com/sdk"]):
                        return await route.abort()
                    await route.continue_()

                await context.route("**/*", block_resources)
                print(f"  ℹ️ 리소스 차단: 이미지/폰트/광고 비활성화")

                page = await context.new_page()

                # webdriver 제거 + 추가 속성 위장
                await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                """)

                print(f"  ℹ️ 브라우저: 데스크톱 모드 (1920x1080, has_touch=False, 쿠키 설정)")

                try:
                    await page.goto(cat['base'], wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(1000)

                    # 팝업 닫기
                    try:
                        popup = page.get_by_role("button", name="오늘 하루 보지 않기")
                        if await popup.is_visible():
                            await popup.click()
                    except:
                        pass

                    print(f"  ℹ️ 필터: URL 파라미터 사용 (면적: 40~999㎡)")

                    for i, coord in enumerate(coordinates):
                        lat, lng, zoom = coord['lat'], coord['lng'], coord['zoom']
                        center = urllib.parse.quote(f'{{"y":{lat},"_lat":{lat},"x":{lng},"_lng":{lng}}}')

                        # (중요) filter 파라미터 인코딩 safe 확장
                        filt = urllib.parse.quote(cat['filt'], safe=':;~,"[]')
                        target_url = f"{cat['base']}?zoomLevel={zoom}&center={center}&filter={filt}"

                        print(f"({i+1}/{len(coordinates)}) 이동... [현재 수집: {len(current_processing_data)}개]")

                        # 20개 좌표마다 중간 저장 + 페이지 재생성
                        if i > 0 and i % 20 == 0:
                            print(f"  💾 중간 저장 ({len(current_processing_data)}개 데이터)")
                            if current_processing_data:
                                # 절대 경로 사용
                                current_dir = os.path.dirname(os.path.abspath(__file__))
                                data_dir = os.path.join(current_dir, 'data')
                                os.makedirs(data_dir, exist_ok=True)
                                save_path = os.path.join(data_dir, current_processing_filename)
                                with open(save_path, 'w', encoding='utf-8') as f:
                                    json.dump(current_processing_data, f, ensure_ascii=False, indent=2)
                                print(f"  ✅ 저장 위치: {save_path}")

                            print(f"  🔄 페이지 재생성 (메모리 최적화)")
                            await page.close()
                            page = await context.new_page()
                            await page.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
                            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                            """)
                            await page.goto(cat['base'], timeout=90000)
                            await page.wait_for_timeout(2000)

                        coord_retry = 0
                        max_coord_retry = 3

                        while coord_retry <= max_coord_retry:
                            try:
                                if page.is_closed():
                                    print(f"  ⚠️ Page is closed, recreating...")
                                    page = await context.new_page()
                                    await page.add_init_script("""
                                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                                    Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
                                    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                                    """)
                                    await page.goto(cat['base'], timeout=90000)
                                    await page.wait_for_timeout(2000)

                                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                                await page.wait_for_timeout(700)  # 짧게 안정화

                                # remobile 감지 시 HTML 저장 후 재시도/스킵 판단
                                if "remobile" in page.url:
                                    print(f"  ⚠️ remobile 리다이렉트 감지 -> HTML 덤프 후 재시도")
                                    try:
                                        os.makedirs(DEBUG_DIR, exist_ok=True)
                                        html = await page.content()
                                        dump_path = os.path.join(DEBUG_DIR, f"remobile_{zone_name}_{cat['name']}_{i+1}.html")
                                        with open(dump_path, "w", encoding="utf-8") as f:
                                            f.write(html)
                                        print(f"  🧪 remobile html saved: {dump_path}")
                                    except Exception as dump_e:
                                        print(f"  ⚠️ remobile html dump failed: {dump_e}")

                                    coord_retry += 1
                                    if coord_retry > max_coord_retry:
                                        print("  ❌ remobile 지속 -> 좌표 스킵")
                                        break
                                    # 페이지 재생성 후 재시도
                                    await page.close()
                                    page = await context.new_page()
                                    await page.add_init_script("""
                                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                                    Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
                                    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                                    """)
                                    await page.goto(cat['base'], timeout=90000)
                                    await page.wait_for_timeout(2000)
                                    continue

                                print(f"  🔍 URL: {page.url[:80]}...")

                                initial_count = await page.locator(ITEM_SELECTOR).count()
                                print(f"  🔍 초기 매물 개수: {initial_count}")

                                if initial_count == 0:
                                    # 0개면 HTML 덤프(원인 진단용)
                                    try:
                                        os.makedirs(DEBUG_DIR, exist_ok=True)
                                        html = await page.content()
                                        dump_path = os.path.join(DEBUG_DIR, f"zero_{zone_name}_{cat['name']}_{i+1}.html")
                                        with open(dump_path, "w", encoding="utf-8") as f:
                                            f.write(html)
                                        print(f"  🧪 zero html saved: {dump_path}")
                                    except Exception as dump_e:
                                        print(f"  ⚠️ zero html dump failed: {dump_e}")

                                    alt_count = await page.locator(".house-item, .listing-item, [data-hidx]").count()
                                    print(f"  🔍 대체 셀렉터 개수: {alt_count}")
                                    break

                                scroll_success = await scroll_to_bottom(page, ITEM_SELECTOR)
                                if not scroll_success:
                                    raise Exception("Page crashed during scroll")

                                final_count = await page.locator(ITEM_SELECTOR).count()
                                print(f"  🔍 스크롤 후 매물 개수: {final_count}")

                                extract_success = await extract_data_from_list(
                                    page, ITEM_SELECTOR,
                                    current_processing_data, master_id_set, current_session_new_ids
                                )
                                if not extract_success:
                                    raise Exception("Page crashed during extraction")

                                break

                            except Exception as e:
                                coord_retry += 1
                                error_msg = str(e)
                                print(f"  ⚠️ 좌표 {i+1} 오류: {e}")

                                if coord_retry > max_coord_retry:
                                    print(f"  ❌ 좌표 {i+1} 최대 재시도 초과, 건너뜀")
                                    break

                                # 페이지 재생성 후 재시도
                                try:
                                    await page.close()
                                except:
                                    pass
                                page = await context.new_page()
                                await page.add_init_script("""
                                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                                Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
                                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                                """)
                                await page.goto(cat['base'], timeout=90000)
                                await page.wait_for_timeout(2000)

                except Exception as e:
                    print(f"❌ Error in category loop: {e}")

                finally:
                    if current_processing_data:
                        # 절대 경로 사용
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        data_dir = os.path.join(current_dir, 'data')
                        os.makedirs(data_dir, exist_ok=True)
                        save_path = os.path.join(data_dir, current_processing_filename)
                        with open(save_path, 'w', encoding='utf-8') as f:
                            json.dump(current_processing_data, f, ensure_ascii=False, indent=2)
                        print(f"✅ '{current_processing_filename}' 저장 완료 ({len(current_processing_data)}개)")
                        print(f"   📂 저장 위치: {save_path}")
                        update_and_save_master_ids(current_session_new_ids)
                        current_session_new_ids.clear()

                    await context.close()
                    await browser.close()

    except (KeyboardInterrupt, asyncio.CancelledError):
        print(f"\n\n🚨 --- [{zone_name}] 사용자 중단 발생! 현재 데이터 저장 시도... ---")
        if current_processing_data and current_processing_filename:
            try:
                save_path = os.path.join('data', current_processing_filename)
                os.makedirs('data', exist_ok=True)
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(current_processing_data, f, ensure_ascii=False, indent=2)
                print(f"💾 [비상 저장] '{current_processing_filename}'에 {len(current_processing_data)}개 데이터 저장 완료.")
                print(f"   📂 저장 위치: {os.path.abspath(save_path)}")
            except Exception as e:
                print(f"❌ [비상 저장 실패] {e}")

    finally:
        update_and_save_master_ids(current_session_new_ids)
        print(f"--- [{zone_name}] 작업 종료 ---")

# ======================================================
# 5. 실행부
# ======================================================
GROUPS = {
    1: ["강남구", "서초구", "송파구", "강동구"],
    2: ["관악구", "동작구", "영등포구", "구로구", "금천구"],
    3: ["강서구", "양천구", "마포구", "서대문구", "은평구"],
    4: ["종로구", "중구", "용산구", "성동구", "광진구"],
    5: ["동대문구", "중랑구", "성북구", "강북구", "도봉구", "노원구"]
}

def run_group(group_number: int):
    target_zones_list = GROUPS.get(group_number, [])
    if not target_zones_list:
        return

    print(f"========== [그룹 {group_number}] 작업 시작 ==========")
    print(f"대상 구역: {target_zones_list}")

    for zone in target_zones_list:
        asyncio.run(run_zone_batch(zone))

    print(f"========== [그룹 {group_number}] 작업 완료 ==========")

def run_all_sequential():
    """모든 그룹 순차 실행 (ECS 안정성 최적화)"""
    print("=" * 60)
    print("🚀 서울 전역 크롤링 시작 (순차 실행 - ECS 안정 모드)")
    print("=" * 60)
    print()

    for group_num, zones in GROUPS.items():
        print(f"  그룹 {group_num}: {zones}")
    print()

    for group_num in range(1, 6):
        print(f"\n{'='*40}")
        print(f"📍 그룹 {group_num} 시작")
        print(f"{'='*40}")
        run_group(group_num)
        print(f"✅ 그룹 {group_num} 완료\n")

    print()
    print("=" * 60)
    print("🎉 서울 전역 크롤링 완료!")
    print("=" * 60)

    print()
    print("📦 JSON 파일 병합 시작...")
    merge_json_by_category()

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    TOTAL_START_TIME = time.time()

    if len(sys.argv) > 1:
        TERMINAL_NUMBER = int(sys.argv[1])
        if TERMINAL_NUMBER not in GROUPS:
            print(f"❌ 잘못된 터미널 번호입니다: {TERMINAL_NUMBER} (1~5 사이 입력)")
        else:
            run_group(TERMINAL_NUMBER)
    else:
        # 🔥 병렬 대신 순차 실행 (ECS 안정성)
        run_all_sequential()

    TOTAL_END_TIME = time.time()
    elapsed = TOTAL_END_TIME - TOTAL_START_TIME
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)

    print(f"⏱️ 총 소요 시간: {int(hours)}시간 {int(minutes)}분 {int(seconds)}초")