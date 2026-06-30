import os

def main():
    path = "main.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Replace imports
    content = content.replace("from playwright.async_api import async_playwright", "import httpx\nfrom bs4 import BeautifulSoup")

    # 2. Replace verify_gplx_ws logic
    # Find start of the replacement
    start_str = """    await websocket.send_json({"type": "status", "message": "Đang khởi tạo trình duyệt ẩn..."})
    
    async with async_playwright() as p:"""
    
    # Find end of the replacement
    end_str = """    # Đảm bảo đóng websocket (nếu chưa đóng do error block trên)
    try:
        await websocket.close()
    except Exception:
        pass"""

    start_idx = content.find(start_str)
    end_idx = content.find(end_str) + len(end_str)

    if start_idx == -1 or end_idx < len(end_str):
        print("Could not find start or end block!")
        return

    new_logic = """    await websocket.send_json({"type": "status", "message": "Đang kết nối hệ thống CSGT..."})
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
        try:
            # 1. Tải trang chủ để lấy securityToken & Cookies
            resp = await client.get("https://gplx.csgt.bocongan.gov.vn/", headers=headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            sec_token_input = soup.find('input', {'name': 'securityToken'})
            if not sec_token_input:
                await websocket.send_json({"type": "error", "message": "Không thể kết nối với hệ thống CSGT (Thiếu token)."})
                return
            security_token = sec_token_input.get('value')
            
            choose_gplx = "1" if loai_bang == "OLD" else "2"
            
            async def get_and_read_captcha(save_path="captcha_real.png"):
                captcha_img = soup.select_one(".img-cap-mobile img")
                if not captcha_img:
                    return None
                
                # Cập nhật thời gian thực vào captcha src để tránh cache
                import time
                captcha_url = "https://gplx.csgt.bocongan.gov.vn" + captcha_img.get('src')
                if '?' in captcha_url:
                    captcha_url = re.sub(r't=\\d+', f't={int(time.time()*1000)}', captcha_url)
                
                cap_resp = await client.get(captcha_url, headers=headers)
                if cap_resp.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(cap_resp.content)
                    return doc_captcha_ddddocr(save_path)
                return None
                
            async def get_manual_captcha_image():
                captcha_img = soup.select_one(".img-cap-mobile img")
                if not captcha_img:
                    return None
                import time
                captcha_url = "https://gplx.csgt.bocongan.gov.vn" + captcha_img.get('src')
                if '?' in captcha_url:
                    captcha_url = re.sub(r't=\\d+', f't={int(time.time()*1000)}', captcha_url)
                cap_resp = await client.get(captcha_url, headers=headers)
                if cap_resp.status_code == 200:
                    return base64.b64encode(cap_resp.content).decode('utf-8')
                return None

            async def submit_form(cap_code: str):
                payload_data = {
                    "type": "",
                    "fields[formTypeId]": "565f96637f8b9af6558b4567",
                    "fields[chooseGPLX]": str(choose_gplx),
                    "fields[codeGPLX]": str(gplx),
                    "fields[birthDate]": str(dob),
                    "fields[birthDateType2]": "",
                    "captcha_code": str(cap_code).lower().strip(),
                    "securityToken": str(security_token),
                    "submitFormId": "8",
                    "moduleId": "8"
                }
                
                api_url = "https://gplx.csgt.bocongan.gov.vn/api/Project/GPLX/ApiSearchGPLX/sendRequest?site=2005782"
                
                req_headers = headers.copy()
                req_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                req_headers["Accept"] = "application/json, text/plain, */*"
                req_headers["Origin"] = "https://gplx.csgt.bocongan.gov.vn"
                req_headers["Referer"] = "https://gplx.csgt.bocongan.gov.vn/"
                
                res = await client.post(api_url, data=payload_data, headers=req_headers)
                return await parse_response_to_data(res.text)

            # === AUTOMATIC OCR LOOP (MAX 2 TIMES) ===
            auto_attempts = 0
            max_auto = 2
            success_result = None
            
            while auto_attempts < max_auto:
                auto_attempts += 1
                await websocket.send_json({"type": "status", "message": f"Đang tự động đọc Captcha (Lần {auto_attempts}/{max_auto})..."})
                
                cap_code = await get_and_read_captcha()
                
                if not cap_code:
                    await websocket.send_json({"type": "status", "message": "OCR không đọc được, tải captcha mới..."})
                    continue
                    
                await websocket.send_json({"type": "status", "message": f"Thử Captcha: {cap_code}..."})
                result = await submit_form(cap_code)
                
                if result.get("is_captcha_error"):
                    await websocket.send_json({"type": "status", "message": "Sai Captcha tự động."})
                    await asyncio.sleep(1)
                    continue
                else:
                    success_result = result
                    break
            
            # === MANUAL CAPTCHA IF AUTO FAILED ===
            if not success_result:
                await websocket.send_json({"type": "status", "message": "Giải Captcha tự động thất bại. Yêu cầu nhập tay."})
                
                while not success_result:
                    b64_img = await get_manual_captcha_image()
                    if not b64_img:
                        await websocket.send_json({"type": "error", "message": "Không thể tải mã Captcha."})
                        break
                        
                    await websocket.send_json({
                        "type": "require_manual_captcha",
                        "image_base64": b64_img,
                        "message": "Vui lòng nhập mã Captcha bên dưới."
                    })
                    
                    try:
                        user_resp = await websocket.receive_json()
                        manual_cap = user_resp.get("captcha_code", "")
                        
                        await websocket.send_json({"type": "status", "message": "Đang gửi yêu cầu tra cứu..."})
                        result = await submit_form(manual_cap)
                        
                        if result.get("is_captcha_error"):
                            await websocket.send_json({"type": "status", "message": "Bạn đã nhập sai mã Captcha. Thử lại..."})
                            await asyncio.sleep(0.5)
                            continue
                        else:
                            success_result = result
                            break
                            
                    except WebSocketDisconnect:
                        return
            
            # === XỬ LÝ KẾT QUẢ ===
            if success_result:
                status = success_result.get("status")
                if status == "success":
                    db.save_verification(gplx, dob, "success", success_result.get("data"))
                    logger.info(f"[{client_ip}] Xác thực thành công: GPLX={gplx}")
                    await websocket.send_json({
                        "type": "success",
                        "source": "live",
                        "message": "Tra cứu thành công!",
                        "data": success_result.get("data")
                    })
                elif status == "not_found":
                    db.save_verification(gplx, dob, "not_found", None)
                    logger.info(f"[{client_ip}] Không tìm thấy: GPLX={gplx}")
                    await websocket.send_json({
                        "type": "error",
                        "source": "live",
                        "message": "Không tìm thấy thông tin trên hệ thống (Cục CSGT)."
                    })
                else:
                    db.save_verification(gplx, dob, "error", None)
                    logger.error(f"[{client_ip}] Lỗi: GPLX={gplx} - {success_result.get('message', '')}")
                    await websocket.send_json({
                        "type": "error",
                        "source": "live",
                        "message": success_result.get("message", "Lỗi không xác định.")
                    })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            await websocket.send_json({"type": "error", "message": f"Lỗi hệ thống: {str(e)}"})
            
    try:
        await websocket.close()
    except Exception:
        pass"""

    content = content[:start_idx] + new_logic + content[end_idx:]

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Refactored main.py successfully.")

if __name__ == "__main__":
    main()
