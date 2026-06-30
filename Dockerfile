# Dùng image Python chính thức
FROM python:3.10-slim

# Cài đặt Playwright dependencies
RUN pip install --no-cache-dir playwright
RUN playwright install-deps chromium

WORKDIR /app
COPY requirements.txt .

# Cài thư viện Python và Chromium cho Playwright
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copy toàn bộ code vào
COPY . .

# Mở port
EXPOSE 8000

# Lệnh chạy
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
