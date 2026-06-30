# Luna Win7 Print Receiver Standalone

This package does not require Python, Node.js, or a database. It uses Windows built-in batch, VBScript, PowerShell, and .NET HttpListener.

## Install

Run `install.bat` as Administrator on the Win7 computer.

The installer:

- Copies files to `C:\LunaPrint`
- Copies `scuba.btw` to `C:\LunaPrint\templates\scuba.btw`
- Creates `D:\BarTender_Print\Input`
- Creates `D:\BarTender_Print\Processing`
- Creates `D:\BarTender_Print\Archive`
- Creates `D:\BarTender_Print\Error`
- Copies `template_data.csv` to `D:\BarTender_Print\template_data.csv`
- Copies the template to `D:\BarTender_Print\composition_label.btw`
- Creates startup entry `LunaPrintManager.vbs`
- Opens TCP port `9876`
- Adds HTTP permission for `http://+:9876/`
- Starts the manager window

## How It Works

Website data is received by the local gateway and written as CSV files:

```text
D:\BarTender_Print\Input\luna_*.csv
```

The built-in queue monitor moves files through:

```text
Input -> Processing -> Archive
```

Failed files go to:

```text
D:\BarTender_Print\Error
```

The monitor calls:

```text
C:\Program Files (x86)\Seagull\BarTender Suite\bartend.exe
```

with:

```text
C:\LunaPrint\templates\scuba.btw
```

Use the manager window to select the real label printer and click Save.

## Website Request Format

POST form data to:

```text
http://WIN7-IP:9876/print
```

Header:

```text
X-Luna-Print-Token: luna-win7-print
```

Content type:

```text
application/x-www-form-urlencoded; charset=utf-8
```

Fields:

```text
job_id, order_id, customer_code, customer_name, address_code, art_code, brand, style_code, style_name, fabric, composition, origin, color, size, qty, wash_symbols, wash_label, header_text, note
```
