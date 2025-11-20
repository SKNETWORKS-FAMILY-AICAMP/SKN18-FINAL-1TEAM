import asyncio
import numpy as np
import urllib.parse
from playwright.async_api import async_playwright
import json
import os
import sys
from global_land_mask import globe

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
    if not os.path.exists(MASTER_ID_FILE): return set()
    try:
        with open(MASTER_ID_FILE, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except: return set()

def update_and_save_master_ids(new_ids_set):
    if not new_ids_set: return
    try:
        current_file_ids = set()
        if os.path.exists(MASTER_ID_FILE):
            with open(MASTER_ID_FILE, 'r', encoding='utf-8') as f:
                current_file_ids = {line.strip() for line in f if line.strip()}
        merged_ids = current_file_ids.union(new_ids_set)
        with open(MASTER_ID_FILE, 'w', encoding='utf-8') as f:
            for item_id in sorted(list(merged_ids)): f.write(f"{item_id}\n")
        print(f"--- [ID 저장] 통합 {len(merged_ids)}개 저장 완료 (이번 추가: {len(new_ids_set)}개) ---")
    except Exception as e: print(f"--- [ID 저장 오류] {e}")

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
        await page.wait_for_selector(scroll_container, timeout=5000)
        list_cont = page.locator(scroll_container)
        last_cnt = 0
        while True:
            try:
                await list_cont.click(timeout=500); await list_cont.press('PageDown'); await page.wait_for_timeout(300)
            except: pass
            
            cur_top = await list_cont.evaluate("node => node.scrollTop")
            for _ in range(5):
                try: await list_cont.press('PageDown'); await page.wait_for_timeout(200)
                except: break
                
            cur_cnt = await page.locator(item_selector).count()
            if cur_cnt == last_cnt:
                try: await page.wait_for_function(f"document.querySelectorAll('{item_selector}').length > {last_cnt}", timeout=3000); continue
                except: break
            last_cnt = cur_cnt
    except: pass

# ======================================================
# 상세 페이지 스크랩
# ======================================================
async def scrape_detail_page(new_page):
    page_url = new_page.url
    listing_id = page_url.split('/house/')[-1].split('?')[0] if '/house/' in page_url else None
    
    # [수정] 모든 키값을 한글로 변경
    final_data = {
        '중개사_정보': {},         # agent_info -> 중개사_정보 (맨 위로 이동 요청 반영)
        '매물번호': listing_id,    # listing_id
        '매물_URL': page_url,      # url
        '주소_정보': {},           # address_info
        '평면도_URL': [],          # floor_plan_urls
        '거래_정보': {},           # transaction_info
        '매물_정보': {},           # property_info
        '추가_옵션': [],           # additional_options
        '주변_학교': [],           # nearby_schools
        '상세_설명': ""            # detail_description
    }
    
    # 1. 주소
    try:
        addr_sel = ".div-detail-house-address-type > span, span.address"
        await new_page.wait_for_selector(addr_sel, timeout=3000)
        # full_address -> 전체주소
        final_data['주소_정보']['전체주소'] = (await new_page.locator(addr_sel).first.inner_text()).strip()
    except: pass

    # 2. 중개사 (내부 키값도 한글로 변경)
    try:
        sb = new_page.locator(".sidebar-content").first
        if await sb.count() > 0:
            agency_name_selector = ".agency-name"
            if await sb.locator(agency_name_selector).count() > 0:
                final_data['중개사_정보']['중개사명'] = (await sb.locator(agency_name_selector).inner_text()).strip()
            
            txt = await sb.inner_text()
            for line in txt.split('\n'):
                line = line.strip()
                if not line: continue
                if "대표번호" in line: final_data['중개사_정보']['전화번호'] = line.replace("대표번호", "").strip()
                elif "주소" in line: final_data['중개사_정보']['주소'] = line.replace("주소", "").strip()
                elif "등록번호" in line: final_data['중개사_정보']['등록번호'] = line.replace("중개사무소", "").replace("등록번호", "").strip()
                elif "대표자" in line: final_data['중개사_정보']['대표자'] = line.replace("대표자", "").strip()
                elif "대표 " in line and "대표자" not in final_data['중개사_정보']: final_data['중개사_정보']['담당자'] = line.replace("대표", "").strip()

            # 거래완료/등록매물
            stat_items = await sb.locator(".agency-house .item-wrapper").all()
            for item in stat_items:
                try:
                    title_el = item.locator(".agency-house-title")
                    count_el = item.locator(".agency-house-count")
                    if await title_el.count() > 0 and await count_el.count() > 0:
                        title = (await title_el.inner_text()).strip()
                        count = (await count_el.inner_text()).strip()
                        if "거래완료" in title: final_data['중개사_정보']['거래완료'] = count
                        elif "등록매물" in title: final_data['중개사_정보']['등록매물'] = count
                except: pass
    except: pass

    # 3. 평면도
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
    except: pass

    # 4. 상세 정보
    rows = await new_page.locator(".detail-table-row").all()
    for r in rows:
        try:
            k = (await r.locator(".detail-table-th").inner_text()).strip()
            v = (await r.locator(".detail-table-td").inner_text()).strip().replace('\n', ' ')
            if k in ["거래방식", "관리비", "융자금", "입주가능일"]: final_data['거래_정보'][k] = v
            else: final_data['매물_정보'][k] = v
        except: pass

    # 5. 추가옵션
    try:
        options_container = new_page.locator(".detail-option-table dd")
        if await options_container.count() > 0:
            all_options = await options_container.all()
            for opt in all_options:
                text = await opt.inner_text()
                if text.strip():
                    final_data['추가_옵션'].append(text.strip())
    except: pass

    # 6. 주변학교
    try:
        school_header = new_page.locator("h3", has_text="주변학교")
        if await school_header.count() > 0:
            school_section = school_header.locator("xpath=..")
            school_buttons = await school_section.locator("button").all()
            for btn in school_buttons:
                school_name = (await btn.inner_text()).strip()
                if not school_name: continue
                try:
                    await btn.click(); await new_page.wait_for_timeout(100)
                    addr_row = school_section.locator(".detail-table-row", has_text="주소")
                    if await addr_row.count() > 0:
                        full_text = await addr_row.inner_text()
                        address = full_text.replace("주소", "").strip()
                        final_data['주변_학교'].append({"학교명": school_name, "주소": address})
                except: pass
    except: pass

    # 7. 상세설명
    try:
        desc_selector = "#description-text"
        if await new_page.locator(desc_selector).count() > 0:
            desc_text = await new_page.locator(desc_selector).inner_text()
            final_data['상세_설명'] = desc_text.strip()
    except: pass
    
    print("  ->  ... (새 탭) 상세 정보 스크랩 완료.")
    return final_data

async def extract_data_from_list(page, item_selector, all_data, master_set, current_session_ids):
    items = await page.locator(item_selector).all()
    for item in items:
        try:
            hid = await item.get_attribute('data-hidx')
            if hid and hid in master_set: continue 
            
            async with page.context.expect_page() as event:
                await item.click(timeout=3000)
            np = await event.value
            await np.wait_for_load_state('domcontentloaded')
            
            data = await scrape_detail_page(np)
            
            if not data['매물번호'] and hid: data['매물번호'] = hid
            
            if data['매물번호']:
                all_data.append(data)
                master_set.add(data['매물번호']) 
                current_session_ids.add(data['매물번호']) 
            
            await np.close()
            await page.wait_for_timeout(500)
        except: pass

async def setup_filters(page):
    try:
        btn = page.locator("button", has_text="전용면적")
        if await btn.count() == 0: btn = page.locator("button", has_text="평")
        if await btn.count() > 0:
            await btn.first.click(); await page.wait_for_timeout(1000)
            handles = page.locator(".vue-slider-dot-handle")
            if await handles.count() >= 2:
                box = await handles.nth(1).bounding_box()
                if box:
                    await page.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2)
                    await page.mouse.down()
                    await page.mouse.move(box['x']-230, box['y'], steps=10)
                    await page.mouse.up()
                    await page.wait_for_timeout(1000)
    except: pass

# ======================================================
# 4. 핵심 실행 로직
# ======================================================
async def run_zone_batch(zone_name):
    master_id_set = load_master_ids()
    current_session_new_ids = set()

    AREA_FILTER_PREFIX = "checkRealSize:999~40||"
    CATEGORIES = [
        {"name": "아파트", "base": "https://www.peterpanz.com/apt", "filt": AREA_FILTER_PREFIX + 'buildingType;["아파트"]', "out": f"{zone_name}_아파트.json"},
        {"name": "원,투룸", "base": "https://www.peterpanz.com/onetworoom", "filt": AREA_FILTER_PREFIX + 'buildingType;["원,투룸"]', "out": f"{zone_name}_원투룸.json"},
        {"name": "빌라,주택", "base": "https://www.peterpanz.com/villa", "filt": AREA_FILTER_PREFIX + 'buildingType;["빌라","주택"]', "out": f"{zone_name}_빌라주택.json"},
        {"name": "오피스텔", "base": "https://www.peterpanz.com/officetel", "filt": AREA_FILTER_PREFIX + 'buildingType;["오피스텔"]', "out": f"{zone_name}_오피스텔.json"},
        {"name": "상가∙사무실∙건물∙공장∙토지", "base": "https://www.peterpanz.com/store", "filt": AREA_FILTER_PREFIX + 'buildingType;["상가","사무실","건물","공장","토지"]', "out": f"{zone_name}_상가.json"}
    ]

    coordinates = generate_coordinate_grid(zone_name)
    if not coordinates: return

    ITEM_SELECTOR = ".a-house"
    current_processing_data = []
    current_processing_filename = ""

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            for cat in CATEGORIES:
                print(f"\n🚀🚀🚀 [{zone_name}] 카테고리: '{cat['name']}' 시작 🚀🚀🚀")
                current_processing_data = []
                current_processing_filename = cat['out']
                
                try:
                    await page.goto(cat['base'], timeout=60000)
                    try:
                        popup = page.get_by_role("button", name="오늘 하루 보지 않기")
                        if await popup.is_visible(): await popup.click()
                    except: pass
                    await page.wait_for_timeout(2000)
                    await setup_filters(page)

                    for i, coord in enumerate(coordinates):
                        lat, lng, zoom = coord['lat'], coord['lng'], coord['zoom']
                        center = urllib.parse.quote(f'{{"y":{lat},"_lat":{lat},"x":{lng},"_lng":{lng}}}')
                        filt = urllib.parse.quote(cat['filt'], safe=':;~')
                        target_url = f"{cat['base']}?zoomLevel={zoom}&center={center}&filter={filt}"
                        
                        print(f"({i+1}/{len(coordinates)}) 이동...")
                        try:
                            await page.goto(target_url, timeout=30000)
                            await page.wait_for_load_state('networkidle'); await page.wait_for_timeout(500)
                            if await page.locator(ITEM_SELECTOR).count() == 0: continue
                            
                            await scroll_to_bottom(page, ITEM_SELECTOR)
                            await extract_data_from_list(page, ITEM_SELECTOR, current_processing_data, master_id_set, current_session_new_ids)
                        except: pass

                except Exception as e:
                    print(f"Error in category loop: {e}")
                
                if current_processing_data:
                    with open(current_processing_filename, 'w', encoding='utf-8') as f:
                        json.dump(current_processing_data, f, ensure_ascii=False, indent=2)
                    print(f"✅ '{current_processing_filename}' 저장 완료.")
                    update_and_save_master_ids(current_session_new_ids)
                    current_session_new_ids.clear()

            await browser.close()
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        print(f"\n\n🚨 --- [{zone_name}] 사용자 중단 발생! 현재 데이터 저장 시도... ---")
        if current_processing_data and current_processing_filename:
            try:
                with open(current_processing_filename, 'w', encoding='utf-8') as f:
                    json.dump(current_processing_data, f, ensure_ascii=False, indent=2)
                print(f"💾 [비상 저장] '{current_processing_filename}'에 {len(current_processing_data)}개 데이터 저장 완료.")
            except Exception as e:
                print(f"❌ [비상 저장 실패] {e}")

    finally:
        update_and_save_master_ids(current_session_new_ids)
        print(f"--- [{zone_name}] 작업 종료 ---")

# ======================================================
# 5. 실행부
# ======================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        TERMINAL_NUMBER = int(sys.argv[1])
    else:
        print("⚠️ 터미널 번호를 입력하지 않아 기본값 1로 실행합니다.")
        TERMINAL_NUMBER = 1

    GROUPS = {
        1: ["강남구", "서초구", "송파구", "강동구"],
        2: ["관악구", "동작구", "영등포구", "구로구", "금천구"],
        3: ["강서구", "양천구", "마포구", "서대문구", "은평구"],
        4: ["종로구", "중구", "용산구", "성동구", "광진구"],
        5: ["동대문구", "중랑구", "성북구", "강북구", "도봉구", "노원구"]
    }

    target_zones_list = GROUPS.get(TERMINAL_NUMBER, [])
    
    if not target_zones_list:
        print(f"❌ 잘못된 터미널 번호입니다: {TERMINAL_NUMBER} (1~5 사이 입력)")
    else:
        print(f"========== [터미널 {TERMINAL_NUMBER}] 병렬 작업 시작 ==========")
        print(f"대상 구역: {target_zones_list}")
        
        for zone in target_zones_list:
            asyncio.run(run_zone_batch(zone))
            
        print(f"========== [터미널 {TERMINAL_NUMBER}] 모든 작업 종료 ==========")