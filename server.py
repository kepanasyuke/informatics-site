# -*- coding: utf-8 -*-
"""Простой локальный веб-сервер для сайта D:\informatika-site.

Запуск:  python server.py [порт]
Открыть: http://localhost:8000
"""
import http.server, socketserver, os, sys

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    handler = http.server.SimpleHTTPRequestHandler
    # тихая простая конфигурация
    with socketserver.TCPServer(("", port), handler) as httpd:
        print("Локальный сервер запущен в:", base)
        print("Откройте в браузере: http://localhost:%d" % port)
        print("Для остановки нажмите Ctrl+C")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nСервер остановлен.")

if __name__ == "__main__":
    main()