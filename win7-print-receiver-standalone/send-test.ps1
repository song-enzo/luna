$url = "http://127.0.0.1:9876/print"
$token = "luna-win7-print"

$pairs = @{
    token = $token
    job_id = "TEST-001"
    order_id = "ORD-TEST-001"
    customer_code = "CUST-A238"
    customer_name = "TEST CUSTOMER"
    address_code = "ADDR-08"
    style_code = "ART-SCUBA001"
    style_name = "SCUBA TEST LABEL"
    fabric = "Scuba"
    composition = "92% Polyester / 8% Spandex"
    color = "Black"
    size = "M"
    qty = "1"
    wash_label = "固定水洗标内容"
    header_text = "LUNA ATELIER"
    note = "standalone receiver simulation test"
}

$items = @()
foreach ($key in $pairs.Keys) {
    $items += ([System.Uri]::EscapeDataString($key) + "=" + [System.Uri]::EscapeDataString($pairs[$key]))
}
$body = $items -join "&"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)

$client = New-Object System.Net.WebClient
$client.Headers.Add("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
$client.Headers.Add("X-Luna-Print-Token", $token)
$resultBytes = $client.UploadData($url, "POST", $bytes)
[System.Text.Encoding]::UTF8.GetString($resultBytes)
