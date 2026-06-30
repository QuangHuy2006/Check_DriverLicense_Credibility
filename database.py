import os
import json
from datetime import datetime
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print("Lỗi kết nối Supabase:", e)

def init_db():
    pass

def is_gplx_verified(gplx: str) -> bool:
    if not supabase: return False
    try:
        response = supabase.table('verified_users').select('id').eq('gplx', gplx).eq('status', 'success').execute()
        return len(response.data) > 0
    except Exception:
        return False

def get_verified_data(gplx: str):
    """Lấy dữ liệu GPLX đã xác thực và cấu trúc lại cho frontend."""
    if not supabase: return None
    try:
        response = supabase.table('verified_users').select('name, loai_bang, ngay_cap, thoi_han').eq('gplx', gplx).eq('status', 'success').execute()
        if response.data and len(response.data) > 0:
            row = response.data[0]
            # Tạo data ảo cho frontend hiển thị
            return {
                "Họ và tên": row.get('name', ''),
                "Hạng GPLX": row.get('loai_bang', ''),
                "Ngày cấp": row.get('ngay_cap', ''),
                "Ngày hết hạn": row.get('thoi_han', '')
            }
    except Exception:
        pass
    return None

def get_stored_dob(gplx: str):
    if not supabase: return None
    try:
        response = supabase.table('verified_users').select('dob').eq('gplx', gplx).eq('status', 'success').execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get('dob')
    except Exception:
        pass
    return None

def save_verification(gplx: str, dob: str, status: str, data: dict = None):
    """Lưu kết quả xác thực (không lưu cột data thô nữa)."""
    if not supabase: return
    try:
        name = ""
        loai_bang = ""
        ngay_cap = ""
        thoi_han = ""
        
        if data:
            if isinstance(data, dict):
                for k, v in data.items():
                    kl = k.lower()
                    val = str(v).strip() if v else ""
                    if not val: continue
                    if not name and ("tên" in kl or "name" in kl or kl == "ho_va_ten"): name = val
                    if not loai_bang and ("hạng" in kl or "loại" in kl or "class" in kl or kl == "hang_gplx" or kl == "hang"): loai_bang = val
                    if not ngay_cap and ("ngày cấp" in kl or "cấp ngày" in kl or "issue" in kl or "ngaycap" in kl or kl == "ngay_cap"): ngay_cap = val
                    if not thoi_han and ("thời hạn" in kl or "giá trị" in kl or "expir" in kl or "valid" in kl or "hạn" in kl or kl == "ngay_het_han"): thoi_han = val
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            kl = k.lower()
                            val = str(v).strip() if v else ""
                            if not val: continue
                            if not name and ("tên" in kl or "name" in kl or kl == "ho_va_ten"): name = val
                            if not loai_bang and ("hạng" in kl or "loại" in kl or "class" in kl or kl == "hang_gplx" or kl == "hang"): loai_bang = val
                            if not ngay_cap and ("ngày cấp" in kl or "cấp ngày" in kl or "issue" in kl or "ngaycap" in kl or kl == "ngay_cap"): ngay_cap = val
                            if not thoi_han and ("thời hạn" in kl or "giá trị" in kl or "expir" in kl or "valid" in kl or "hạn" in kl or kl == "ngay_het_han"): thoi_han = val

        payload = {
            "gplx": gplx,
            "dob": dob,
            "status": status,
            "name": name,
            "loai_bang": loai_bang,
            "ngay_cap": ngay_cap,
            "thoi_han": thoi_han
            # KHÔNG truyền cột data vào nữa
        }
        
        res = supabase.table('verified_users').select('id').eq('gplx', gplx).execute()
        
        if res.data and len(res.data) > 0:
            supabase.table('verified_users').update(payload).eq('gplx', gplx).execute()
        else:
            supabase.table('verified_users').insert(payload).execute()
    except Exception as e:
        print("Lỗi lưu dữ liệu Supabase:", e)

def get_all_history():
    """Lấy toàn bộ lịch sử."""
    if not supabase: return []
    try:
        response = supabase.table('verified_users').select('gplx, dob, status, created_at, name, loai_bang, ngay_cap, thoi_han').order('created_at', desc=True).execute()
        rows = response.data
        
        result = []
        for r in rows:
            result.append({
                "gplx": r.get('gplx', ''), 
                "dob": r.get('dob', ''), 
                "status": r.get('status', ''), 
                "created_at": r.get('created_at', ''),
                "name": r.get('name', ''),
                "loai_bang": r.get('loai_bang', ''),
                "ngay_cap": r.get('ngay_cap', ''),
                "thoi_han": r.get('thoi_han', '')
            })
        return result
    except Exception as e:
        print("Lỗi lấy lịch sử Supabase:", e)
        return []
