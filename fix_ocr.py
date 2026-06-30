import os

def fix_app_ocr():
    path = "app_ocr.py"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    in_gui_len_gov = False
    
    for line in lines:
        if line.strip() == "from playwright.async_api import async_playwright":
            continue
        
        if line.startswith("async def gui_len_gov"):
            in_gui_len_gov = True
            
        if in_gui_len_gov and line.startswith("def "):
            in_gui_len_gov = False
            
        if in_gui_len_gov:
            # We will just comment out the whole function
            new_lines.append("# " + line)
        else:
            new_lines.append(line)
            
    # Need to also comment out `ham_tra_cuu_chinh` which might use `gui_len_gov`
    # Actually let's just do a string replacement for the import. Since they don't call it, it won't crash at runtime if we just remove the import (Wait, `async_playwright` is used inside `gui_len_gov`. So if we remove the import, `gui_len_gov` will have a NameError when CALLED. But since it's NOT called, it's fine!).
    
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    fix_app_ocr()
