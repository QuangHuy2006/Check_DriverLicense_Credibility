import asyncio
import httpx
from bs4 import BeautifulSoup
import re

async def test_csgt():
    url = "https://gplx.csgt.bocongan.gov.vn/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        # Step 1: Load main page
        print("Fetching main page...")
        resp = await client.get(url, headers=headers)
        print("Main page status:", resp.status_code)
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find security token
        sec_token_input = soup.find('input', {'name': 'securityToken'})
        if sec_token_input:
            sec_token = sec_token_input.get('value')
            print("Found securityToken:", sec_token)
        else:
            print("securityToken not found")
            return
            
        # Find captcha URL
        captcha_img = soup.select_one(".img-cap-mobile img")
        if captcha_img:
            captcha_src = captcha_img.get('src')
            print("Found captcha src:", captcha_src)
            # Try fetching captcha
            captcha_resp = await client.get("https://gplx.csgt.bocongan.gov.vn" + captcha_src, headers=headers)
            print("Captcha status:", captcha_resp.status_code)
            if captcha_resp.status_code == 200:
                print("Captcha loaded successfully. Size:", len(captcha_resp.content))
        else:
            print("Captcha image not found")
        
        print("Cookies:", client.cookies)

if __name__ == "__main__":
    asyncio.run(test_csgt())
