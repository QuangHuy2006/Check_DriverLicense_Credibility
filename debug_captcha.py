import httpx
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}
client = httpx.Client(verify=False)
resp = client.get('https://gplx.csgt.bocongan.gov.vn/', headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

cap_area = soup.select_one('.img-cap-mobile')
if cap_area:
    print('=== img-cap-mobile HTML ===')
    print(cap_area.prettify()[:5000])
else:
    print('img-cap-mobile not found')

print()
all_imgs = soup.select('.img-cap-mobile img')
print(f'Total images in .img-cap-mobile: {len(all_imgs)}')
for idx, img in enumerate(all_imgs):
    src = img.get('src', '')
    style = img.get('style', '')
    w = img.get('width', '')
    h = img.get('height', '')
    print(f'  img[{idx}]: src={src}')
    print(f'    style={style} width={w} height={h}')

# Find all captcha-related elements
cap2 = soup.select('[id*=captcha], [class*=captcha], [id*=Captcha], [class*=Captcha], .BDC_CaptchaImageDiv')
print(f'\nOther captcha elements: {len(cap2)}')
for c in cap2:
    cid = c.get('id', '')
    ccls = c.get('class', '')
    print(f'  tag={c.name} id={cid} class={ccls}')
    # Show inner HTML if small
    inner = str(c)
    if len(inner) < 500:
        print(f'    html={inner}')
