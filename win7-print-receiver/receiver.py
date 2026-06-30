from __future__ import print_function

import csv
import json
import os
import subprocess
import sys
import time

try:
    from ConfigParser import SafeConfigParser
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from configparser import ConfigParser as SafeConfigParser
    from http.server import HTTPServer, BaseHTTPRequestHandler


APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.ini")


DEFAULT_FIELDS = [
    "job_id",
    "order_id",
    "customer_code",
    "customer_name",
    "address_code",
    "style_code",
    "style_name",
    "fabric",
    "composition",
    "color",
    "size",
    "qty",
    "wash_label",
    "header_text",
    "note",
]


def now_text():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def load_config():
    parser = SafeConfigParser()
    if sys.version_info[0] >= 3:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as handle:
            parser.read_file(handle)
    else:
        parser.read(CONFIG_PATH)
    return parser


def cfg(parser, section, key, default=""):
    if parser.has_option(section, key):
        return parser.get(section, key)
    return default


def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path)


def log_message(config, message):
    log_file = cfg(config, "paths", "log_file", os.path.join(APP_DIR, "logs", "receiver.log"))
    ensure_dir(os.path.dirname(log_file))
    with open(log_file, "a") as handle:
        handle.write("[%s] %s\n" % (now_text(), message))


def text_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def write_csv(config, payload):
    data_file = cfg(config, "paths", "data_file", os.path.join(APP_DIR, "data", "current_job.csv"))
    ensure_dir(os.path.dirname(data_file))

    fields_text = cfg(config, "print", "fields", ",".join(DEFAULT_FIELDS))
    fields = [field.strip() for field in fields_text.split(",") if field.strip()]

    try:
        open_args = {"newline": "", "encoding": "utf-8-sig"}
        with open(data_file, "w", **open_args) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            row = {}
            for field in fields:
                row[field] = text_value(payload.get(field, ""))
            writer.writerow(row)
    except TypeError:
        with open(data_file, "wb") as handle:
            handle.write("\xef\xbb\xbf")
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            row = {}
            for field in fields:
                row[field] = text_value(payload.get(field, "")).encode("utf-8")
            writer.writerow(row)

    return data_file


def quote(value):
    return '"' + value.replace('"', '\\"') + '"'


def build_command(config, data_file):
    bartender = cfg(config, "paths", "bartender_exe")
    template = cfg(config, "paths", "template")
    printer = cfg(config, "print", "printer", "")
    copies = cfg(config, "print", "copies", "1")

    if not bartender:
        raise RuntimeError("config.ini missing paths.bartender_exe")
    if not template:
        raise RuntimeError("config.ini missing paths.template")

    parts = [
        quote(bartender),
        "/F=" + quote(template),
        "/D=" + quote(data_file),
        "/C=" + copies,
    ]
    if printer:
        parts.append("/PRN=" + quote(printer))
    parts.extend(["/P", "/X"])
    return " ".join(parts)


def print_job(config, payload):
    data_file = write_csv(config, payload)
    dry_run = cfg(config, "print", "dry_run", "0").strip().lower() in ("1", "true", "yes")
    command = build_command(config, data_file)
    log_message(config, "job %s csv=%s" % (payload.get("job_id", ""), data_file))
    log_message(config, "command %s" % command)

    if dry_run:
        return {"printed": False, "dry_run": True, "csv": data_file, "command": command}

    if not os.path.isfile(cfg(config, "paths", "bartender_exe")):
        raise RuntimeError("BarTender not found: %s" % cfg(config, "paths", "bartender_exe"))
    if not os.path.isfile(cfg(config, "paths", "template")):
        raise RuntimeError("Template not found: %s" % cfg(config, "paths", "template"))

    code = subprocess.call(command, shell=True)
    if code != 0:
        raise RuntimeError("BarTender exited with code %s" % code)
    return {"printed": True, "csv": data_file, "command": command}


class LunaPrintHandler(BaseHTTPRequestHandler):
    server_version = "LunaPrintReceiver/0.1"

    def send_json(self, status, body):
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"ok": True, "time": now_text()})
            return
        self.send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/print":
            self.send_json(404, {"ok": False, "error": "not found"})
            return

        config = load_config()
        expected_token = cfg(config, "receiver", "token", "")
        actual_token = self.headers.get("X-Luna-Print-Token", "")

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": "invalid json: %s" % exc})
            return

        if expected_token and actual_token != expected_token and payload.get("token") != expected_token:
            self.send_json(403, {"ok": False, "error": "bad token"})
            return

        try:
            result = print_job(config, payload)
            self.send_json(200, {"ok": True, "result": result})
        except Exception as exc:
            log_message(config, "error %s" % exc)
            self.send_json(500, {"ok": False, "error": str(exc)})

    def log_message(self, fmt, *args):
        config = load_config()
        log_message(config, fmt % args)


def main():
    config = load_config()
    host = cfg(config, "receiver", "host", "0.0.0.0")
    port = int(cfg(config, "receiver", "port", "9876"))
    log_message(config, "starting receiver on %s:%s" % (host, port))
    server = HTTPServer((host, port), LunaPrintHandler)
    print("Luna print receiver listening on http://%s:%s" % (host, port))
    server.serve_forever()


if __name__ == "__main__":
    main()
