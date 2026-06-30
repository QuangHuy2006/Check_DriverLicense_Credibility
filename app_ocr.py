import json
import asyncio
import warnings
import cv2
import numpy as np
from playwright.async_api import async_playwright
import os
import time
from datetime import datetime
import ddddocr
import traceback

# Ẩn cảnh báo rác
warnings.filterwarnings("ignore", category=UserWarning)

# === THAM SỐ ===
MAX_RETRIES = 3
DELAY_BETWEEN_RETRIES = 1

print("🔄 Đang khởi tạo ddddocr...")

# === KHỞI TẠO DDDDOCR ===
try:
    ocr = ddddocr.DdddOcr()
    print("✅ ddddocr đã sẵn sàng!")
    print("=" * 60)
except Exception as e:
    print(f"❌ Lỗi khởi tạo ddddocr: {e}")
    print("💡 Cài đặt: pip install ddddocr")
    exit(1)

# === HÀM TIỀN XỬ LÝ ẢNH ===
def preprocess_for_ddddocr(path_anh):
    """Tiền xử lý ảnh cho ddddocr"""
    try:
        anh = cv2.imread(path_anh)
        if anh is None:
            return None
        
        gray = cv2.cvtColor(anh, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Đảo ngược nếu cần
        white_pixels = np.sum(binary == 255)
        black_pixels = np.sum(binary == 0)
        if white_pixels > black_pixels:
            binary = cv2.bitwise_not(binary)
        
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        # Crop
        coords = cv2.findNonZero(cleaned)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            padding = 5
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(cleaned.shape[1] - x, w + 2*padding)
            h = min(cleaned.shape[0] - y, h + 2*padding)
            cleaned = cleaned[y:y+h, x:x+w]
        
        cv2.imwrite("captcha_processed_ddddocr.png", cleaned)
        return cleaned
        
    except Exception as e:
        print(f"⚠️ Lỗi tiền xử lý: {e}")
        return None

# === HÀM ĐỌC CAPTCHA ===
def doc_captcha_ddddocr(path_anh="captcha_real.png"):
    """Đọc captcha với ddddocr"""
    try:
        # Cách 1: Đọc trực tiếp
        with open(path_anh, 'rb') as f:
            image_bytes = f.read()
        captcha_text = ocr.classification(image_bytes)
        
        if captcha_text and 4 <= len(captcha_text) <= 8:
            print(f"   ✅ Đọc trực tiếp: {captcha_text}")
            return captcha_text
        
        # Cách 2: Đọc sau tiền xử lý
        img_processed = preprocess_for_ddddocr(path_anh)
        if img_processed is not None:
            _, img_encoded = cv2.imencode('.png', img_processed)
            img_bytes = img_encoded.tobytes()
            captcha_text2 = ocr.classification(img_bytes)
            if captcha_text2 and 4 <= len(captcha_text2) <= 8:
                print(f"   ✅ Đọc sau xử lý: {captcha_text2}")
                return captcha_text2
        
        return None
            
    except Exception as e:
        print(f"⚠️ Lỗi đọc captcha: {str(e)}")
        return None

# === HÀM GỬI DỮ LIỆU LÊN GOV ===
async def gui_len_gov(gplx_number, dob, gplx_type="PET", captcha_code=""):
    """
    Gửi dữ liệu lên Bộ Công An
    Trả về: (response_data, is_captcha_error)
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="vi-VN"
        )
        page = await context.new_page()
        
        try:
            await page.goto("https://gplx.csgt.bocongan.gov.vn/", wait_until="networkidle")
            security_token = await page.locator("input[name='securityToken']").get_attribute("value")
            
            # Lấy captcha mới
            captcha_selector = ".img-cap-mobile a.captcha-refresh img"
            await page.wait_for_selector(captcha_selector, timeout=5000)
            captcha_element = await page.query_selector(captcha_selector)
            await captcha_element.screenshot(path="captcha_real.png")
            
            # Đọc captcha
            if not captcha_code:
                print("   📸 Đang đọc captcha với ddddocr...")
                captcha_code = doc_captcha_ddddocr("captcha_real.png")
                
                if not captcha_code:
                    print("   ⚠️ ddddocr không đọc được, thử lại...")
                    if os.path.exists("captcha_processed_ddddocr.png"):
                        with open("captcha_processed_ddddocr.png", 'rb') as f:
                            img_bytes = f.read()
                        captcha_code = ocr.classification(img_bytes)
                    
                    if not captcha_code:
                        print("   ❌ Không đọc được captcha tự động!")
                        return {"status": "captcha_error", "message": "Không đọc được captcha"}, True
            
            print(f"   🔐 Mã captcha: {captcha_code}")
            
            # Chuẩn bị payload
            choose_gplx = "2" if gplx_type == "PET" else "1"
            
            payload_data = {
                "type": "",
                "fields[formTypeId]": "565f96637f8b9af6558b4567",
                "fields[chooseGPLX]": str(choose_gplx),
                "fields[codeGPLX]": str(gplx_number),
                "fields[birthDate]": str(dob),
                "fields[birthDateType2]": "",
                "captcha_code": str(captcha_code).lower().strip(),
                "securityToken": str(security_token),
                "submitFormId": "8",
                "moduleId": "8"
            }
            
            # Gửi request
            api_url = "/api/Project/GPLX/ApiSearchGPLX/sendRequest?site=2005782"
            raw_response = await page.evaluate(
                f"""async (formDataObj) => {{
                    const searchParams = new URLSearchParams();
                    for (const key in formDataObj) {{
                        searchParams.append(key, formDataObj[key]);
                    }}
                    
                    const res = await fetch('{api_url}', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'Accept': 'application/json, text/plain, */*'
                        }},
                        body: searchParams.toString()
                    }});
                    return res.text();
                }}""",
                payload_data
            )
            
            # === LOG CHI TIẾT RESPONSE ===
            print(f"\n   📥 RAW RESPONSE:")
            print(f"   {'-' * 50}")
            print(f"   {raw_response[:500]}")  # In 500 ký tự đầu
            print(f"   {'-' * 50}")
            
            # Lưu response vào file để debug
            with open("response_debug.txt", "w", encoding='utf-8') as f:
                f.write(raw_response)
            
            # === XỬ LÝ RESPONSE ===
            if raw_response.strip() == "BotDetect":
                return {"status": "captcha_error", "message": "Sai mã captcha (BotDetect)"}, True
            
            # Thử parse JSON
            try:
                data = json.loads(raw_response)
                print(f"   ✅ Parse JSON thành công")
                
                # === QUAN TRỌNG: ƯU TIÊN HIỂN THỊ DỮ LIỆU ===
                # Nếu có dữ liệu (dù status có thể không phải success)
                if data:
                    # Kiểm tra nếu data là dict
                    if isinstance(data, dict):
                        # Nếu có key 'data' và có giá trị
                        if 'data' in data and data['data']:
                            return {"status": "success", "data": data['data'], "raw": data}, False
                        
                        # Nếu có key 'status' và các key khác
                        if 'status' in data:
                            # Dù status là gì, nếu có dữ liệu thì vẫn hiển thị
                            if len(data) > 1:  # Có thêm keys ngoài status
                                return {"status": "success", "data": data, "raw": data}, False
                        
                        # Kiểm tra message có phải lỗi không
                        msg = data.get('message', '').lower()
                        if 'không tìm thấy' in msg or 'not found' in msg:
                            return {"status": "not_found", "message": msg}, False
                        
                        if 'captcha' in msg or 'mã bảo mật' in msg:
                            return data, True
                        
                        # Nếu có dữ liệu (không rỗng)
                        if data:
                            return {"status": "success", "data": data}, False
                    
                    # Nếu data là list
                    elif isinstance(data, list):
                        if data:
                            return {"status": "success", "data": data}, False
                        else:
                            return {"status": "not_found", "message": "Không tìm thấy dữ liệu"}, False
                    
                    # Các kiểu dữ liệu khác
                    else:
                        return {"status": "success", "data": data}, False
                
                # Data rỗng
                else:
                    return {"status": "not_found", "message": "Không tìm thấy dữ liệu"}, False
                    
            except json.JSONDecodeError as e:
                print(f"   ⚠️ Không phải JSON: {e}")
                
                # Thử tìm kiếm thông tin trong raw_response
                if 'không tìm thấy' in raw_response.lower():
                    return {"status": "not_found", "message": "Không tìm thấy thông tin"}, False
                elif 'thành công' in raw_response.lower():
                    return {"status": "success", "data": raw_response}, False
                else:
                    # Nếu có dữ liệu, vẫn trả về
                    if raw_response and len(raw_response) > 10:
                        return {"status": "success", "data": raw_response}, False
                    else:
                        return {"status": "unknown", "data": raw_response}, False
                
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")
            traceback.print_exc()
            return {"status": "error", "message": f"Lỗi: {str(e)}"}, False
        finally:
            await browser.close()

# === HÀM TRA CỨU CHÍNH ===
async def tra_cuu_gplx():
    """
    Hàm chính: Tự động lặp lại khi sai captcha
    """
    print("\n" + "=" * 60)
    print("🚔 HỆ THỐNG TRA CỨU GPLX - TỰ ĐỘNG HIỂN THỊ DỮ LIỆU")
    print("=" * 60)
    
    # === NHẬP THÔNG TIN ===
    print("\n📝 NHẬP THÔNG TIN TRA CỨU:")
    gplx = input("   Số GPLX: ").replace(" ", "").strip()
    dob = input("   Ngày sinh (dd/mm/yyyy): ").replace(" ", "").strip()
    loai = input("   Loại bằng (1: PET, 2: Giấy cũ) [1]: ").strip()
    
    loai_bang = "OLD" if loai == "2" else "PET"
    
    if not gplx or not dob:
        print("❌ Không được bỏ trống!")
        return
    
    print("\n" + "=" * 60)
    print("📋 THÔNG TIN TRA CỨU:")
    print(f"   - Số GPLX: {gplx}")
    print(f"   - Ngày sinh: {dob}")
    print(f"   - Loại bằng: {'PET' if loai_bang == 'PET' else 'Giấy cũ'}")
    print(f"   - Số lần thử tối đa: {MAX_RETRIES}")
    print("=" * 60)
    
    print("\n🤖 ĐANG TỰ ĐỘNG TRA CỨU...")
    print("   (Sẽ tự động lặp lại khi sai captcha)")
    print("-" * 60)
    
    # === VÒNG LẶP ===
    so_lan_thu = 0
    captcha_fail_count = 0
    
    while so_lan_thu < MAX_RETRIES:
        so_lan_thu += 1
        
        print(f"\n🔄 LẦN THỬ {so_lan_thu}/{MAX_RETRIES}")
        print("   ⏳ Đang lấy captcha mới...")
        
        result, is_captcha_error = await gui_len_gov(gplx, dob, loai_bang)
        
        # === XỬ LÝ KẾT QUẢ ===
        print(f"\n   📊 KẾT QUẢ XỬ LÝ:")
        print(f"   - is_captcha_error: {is_captcha_error}")
        print(f"   - Status: {result.get('status', 'unknown')}")
        
        # === QUAN TRỌNG: KIỂM TRA VÀ HIỂN THỊ DATA NGAY ===
        if result.get('status') == 'success' and result.get('data'):
            print("\n" + "=" * 60)
            print("✅ ✅ ✅ TRA CỨU THÀNH CÔNG! ✅ ✅ ✅")
            print("=" * 60)
            
            data = result['data']
            print("\n📋 THÔNG TIN CHI TIẾT:")
            
            # Hiển thị dữ liệu dạng đẹp
            if isinstance(data, dict):
                # Nếu data có key 'data' lồng bên trong
                if 'data' in data and data['data']:
                    data = data['data']
                
                # In từng field
                for key, value in data.items():
                    if value:
                        print(f"   - {key}: {value}")
                    else:
                        print(f"   - {key}: (trống)")
                        
            elif isinstance(data, list):
                for idx, item in enumerate(data, 1):
                    print(f"\n   📌 Kết quả {idx}:")
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if value:
                                print(f"      - {key}: {value}")
                    else:
                        print(f"      {item}")
            else:
                print(f"   {data}")
            
            print("\n" + "=" * 60)
            print(f"📊 Thống kê: {so_lan_thu} lần thử, {captcha_fail_count} lần sai captcha")
            
            # Lưu kết quả vào file
            with open("ket_qua_tra_cuu.json", "w", encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("💾 Đã lưu kết quả vào ket_qua_tra_cuu.json")
            
            return
        
        # === XỬ LÝ CAPTCHA ERROR ===
        if is_captcha_error:
            captcha_fail_count += 1
            print(f"\n   ❌ Sai CAPTCHA! (Lần {captcha_fail_count})")
            print(f"   ⏳ Đợi {DELAY_BETWEEN_RETRIES}s rồi thử lại...")
            time.sleep(DELAY_BETWEEN_RETRIES)
            continue
        
        # === XỬ LÝ NOT FOUND ===
        if result.get('status') == 'not_found':
            print("\n" + "=" * 60)
            print("📋 KHÔNG TÌM THẤY THÔNG TIN TRONG CSDL!")
            print("=" * 60)
            print("   -> Kiểm tra lại số GPLX và ngày sinh")
            print("   -> Thử loại bằng khác")
            print(f"\n📊 Thống kê: {so_lan_thu} lần thử, {captcha_fail_count} lần sai captcha")
            return
        
        # === XỬ LÝ LỖI KHÁC ===
        if 'message' in result:
            msg = result['message'].lower()
            
            # Phát hiện captcha error qua message
            if 'captcha' in msg or 'mã bảo mật' in msg:
                captcha_fail_count += 1
                print(f"\n   ❌ Sai CAPTCHA! (Lần {captcha_fail_count})")
                print(f"   ⏳ Đợi {DELAY_BETWEEN_RETRIES}s rồi thử lại...")
                time.sleep(DELAY_BETWEEN_RETRIES)
                continue
            
            # Phát hiện not found qua message
            if 'không tìm thấy' in msg or 'not found' in msg:
                print("\n" + "=" * 60)
                print("📋 KHÔNG TÌM THẤY THÔNG TIN TRONG CSDL!")
                print("=" * 60)
                print(f"   Message: {result['message']}")
                print(f"\n📊 Thống kê: {so_lan_thu} lần thử, {captcha_fail_count} lần sai captcha")
                return
            
            # Lỗi khác
            print(f"\n⚠️ LỖI: {result['message']}")
            print(f"   ⏳ Đợi {DELAY_BETWEEN_RETRIES}s rồi thử lại...")
            time.sleep(DELAY_BETWEEN_RETRIES)
            continue
        
        # === UNKNOWN - NHƯNG VẪN HIỂN THỊ DATA NẾU CÓ ===
        if result and result.get('data'):
            print("\n" + "=" * 60)
            print("✅ CÓ DỮ LIỆU TRẢ VỀ (dù status không xác định)")
            print("=" * 60)
            print(f"\n📋 Dữ liệu: {json.dumps(result['data'], ensure_ascii=False, indent=2)}")
            print("\n" + "=" * 60)
            return
        
        # Thử lại
        print("   ⚠️ Kết quả không xác định, thử lại...")
        time.sleep(DELAY_BETWEEN_RETRIES)
    
    # Hết số lần
    print("\n" + "=" * 60)
    print("❌ ĐÃ HẾT SỐ LẦN THỬ!")
    print("=" * 60)
    print(f"\n📊 Thống kê: {so_lan_thu} lần thử, {captcha_fail_count} lần sai captcha")

# === TEST ===
def test_ocr():
    """Test OCR"""
    print("\n🧪 TEST DDDDOCR CAPTCHA")
    print("=" * 50)
    
    if os.path.exists("captcha_real.png"):
        result = doc_captcha_ddddocr("captcha_real.png")
        if result:
            print(f"\n✅ Kết quả: {result}")
        else:
            print("\n❌ Không đọc được captcha!")
    else:
        print("⚠️ Chưa có file captcha_real.png!")

# === MAIN ===
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test-ocr":
        test_ocr()
    else:
        asyncio.run(tra_cuu_gplx())