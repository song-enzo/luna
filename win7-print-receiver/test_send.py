from __future__ import print_function

import json
import sys

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen


url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9876/print"
token = sys.argv[2] if len(sys.argv) > 2 else "luna-win7-print"

payload = {
    "job_id": "TEST-001",
    "order_id": "ORD-TEST-001",
    "customer_code": "CUST-A238",
    "customer_name": "TEST CUSTOMER",
    "address_code": "ADDR-08",
    "style_code": "ART-SCUBA001",
    "style_name": "SCUBA TEST LABEL",
    "fabric": "Scuba",
    "composition": "92% Polyester / 8% Spandex",
    "color": "Black",
    "size": "M",
    "qty": "1",
    "wash_label": "固定水洗标内容",
    "header_text": "LUNA ATELIER",
    "note": "receiver simulation test",
}

body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
request = Request(url, data=body, headers={
    "Content-Type": "application/json; charset=utf-8",
    "X-Luna-Print-Token": token,
})

response = urlopen(request, timeout=20)
print(response.read().decode("utf-8"))
