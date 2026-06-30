# Dùng image Python chính thức
FROM python:3.10-slim

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV (ddddocr)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Cài thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào
COPY . .

# Mở port
EXPOSE 8000

# Lệnh chạy
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
