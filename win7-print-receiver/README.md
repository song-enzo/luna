# Luna Win7 Print Receiver

This folder is the Win7-side package for BarTender automatic printing.

## Files

- `receiver.py` - HTTP receiver. It listens for `POST /print`, writes `current_job.csv`, and calls BarTender.
- `config.ini` - Default settings. The installer copies it to `C:\LunaPrint\config.ini`.
- `templates\scuba.btw` - BarTender template copied from the provided file.
- `install.bat` - Installs to `C:\LunaPrint`, adds startup entry, opens TCP port `9876`, and starts the receiver.
- `uninstall.bat` - Removes startup entry and firewall rule.
- `test_send.py` - Sends a sample print job to the receiver.

## Install On Win7

1. Install Python 3.8 for Windows 7 to `C:\Python38`.
2. Run `install.bat`.
3. Make sure BarTender is installed at:

   `C:\Program Files (x86)\Seagull\BarTender Suite\bartend.exe`

4. Make sure `scuba.btw` is designed to read:

   `C:\LunaPrint\data\current_job.csv`

## Test

On the Win7 computer:

```bat
C:\Python38\python.exe C:\LunaPrint\test_send.py
```

From another computer on the same network:

```bat
python test_send.py http://WIN7-IP:9876/print luna-win7-print
```

## BarTender Data Fields

The CSV contains one row with these headers:

`job_id, order_id, customer_code, customer_name, address_code, style_code, style_name, fabric, composition, color, size, qty, wash_label, header_text, note`

Bind the dynamic text objects in `scuba.btw` to these CSV fields. Fixed header text, symbols, and wash label graphics should remain in the template.
