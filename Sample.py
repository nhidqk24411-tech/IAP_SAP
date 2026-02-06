import requests
import json
import time


def trigger_n8n_webhook():
    """Hàm gọi webhook n8n"""
    url = "http://localhost:5678/webhook-test/smr119966"

    print("🚀 Đang kích hoạt workflow n8n...")
    print(f"📡 URL: {url}")
    print("-" * 50)

    try:
        # Dữ liệu gửi đi
        payload = {
            "triggered_by": "python_script",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Hello from Python!"
        }

        # Gửi POST request
        print("📤 Đang gửi request...")
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"✅ Thành công!")
        print(f"📊 Status Code: {response.status_code}")
        print(f"⏱️ Thời gian: {response.elapsed.total_seconds():.2f} giây")
        print("\n📥 Response:")

        # Hiển thị response
        try:
            # Thử parse JSON
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            # Nếu không phải JSON, hiển thị text
            print(response.text[:500])  # Giới hạn 500 ký tự

    except requests.exceptions.ConnectionError:
        print("❌ Lỗi kết nối!")
        print("Hãy chắc chắn rằng:")
        print("1. n8n đang chạy (localhost:5678)")
        print("2. Webhook 'smr119966' tồn tại")
        print("3. Workflow đang active")
    except requests.exceptions.Timeout:
        print("❌ Timeout! n8n không phản hồi")
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")


if __name__ == "__main__":
    trigger_n8n_webhook()