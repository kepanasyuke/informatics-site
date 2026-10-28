# -*- coding: utf-8 -*-
"""
Серверный модуль регистрации и лимита пользователей курса «Информатика 3–11 + ЕГЭ».

Зачем: ключи и лимит «максимум 3 пользователя» в localStorage клиента легко сбросить.
Этот скрипт даёт НАСТОЯЩИЙ счётчик и генерацию ключей НА СЕРВЕРЕ.

Как работает:
- GET  /api/reg?name=...&email=...  -> если занято мест < MAX_USERS и email новый:
     генерируется уникальный ключ (для этого email), сохраняется в базу (JSON),
     возвращает {ok:true, key:"XXXXX-XXXXX-XXXXX"}
   Иначе: {ok:false, reason:"limit"|"dup", ...}
- GET /api/check?key=XXX -> проверка ключа (ок/нет)
- GET /api/users  -> количество зарегистрированных (для авторской панели)

Запуск (из папки сайта, где лежит этот файл):
    python auth_server.py [порт]
По умолчанию порт 8001, открой http://localhost:8001

⚙ Настройки:
    MAX_USERS=3   — лимит зарегистрированных пользователей
    DB_FILE="users_db.json" — файл базы (создаётся рядом).
"""
import http.server, socketserver, json, os, re, hashlib, secrets, sys

# ------------------- НАСТРОЙКИ -------------------
MAX_USERS = 3            # жёсткий лимит пользователей
DB_FILE = "users_db.json"
CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
# -------------------------------------------------

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"users": {}}
    return {"users": {}}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def make_key(email):
    # детерминированный ключ из email + соль — стабильно, привязано к почте
    h = hashlib.sha256(("inf-course:"+email.lower().strip()).encode("utf-8")).digest()
    key = ""
    for b in range(15):
        key += CHARS[h[b] % len(CHARS)]
    return key[:5] + "-" + key[5:10] + "-" + key[10:15]

def valid_email(e):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', e or ""))

class Handler(http.server.BaseHTTPRequestHandler):
    db = None  # общий, загружается при старте

    def log_message(self, *a):  # тише логи
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        query = {}
        if "?" in self.path:
            for kv in self.path.split("?",1)[1].split("&"):
                if "=" in kv:
                    k,v = kv.split("=",1); query[k]=v
        db = self.db

        if path == "/api/reg":
            name = query.get("name","").strip()
            email = (query.get("email","") or "").lower().strip()
            if not valid_email(email):
                return self._json({"ok":False,"reason":"email"})
            if email in db["users"]:
                return self._json({"ok":False,"reason":"dup","msg":"Эта почта уже зарегистрирована."})
            if len(db["users"]) >= MAX_USERS:
                return self._json({"ok":False,"reason":"limit","msg":"Достигнут лимит мест (%d)." % MAX_USERS})
            key = make_key(email)
            db["users"][email] = {"name":name,"key":key,"date":__import__("time").strftime("%Y-%m-%d")}
            save_db(db)
            return self._json({"ok":True,"key":key,"users":len(db["users"])})

        elif path == "/api/check":
            key = (query.get("key","") or "").strip().upper()
            found = [e for e,u in db["users"].items() if u.get("key")==key]
            return self._json({"ok":bool(found),"email":found[0] if found else None})

        elif path == "/api/users":
            return self._json({"total":len(db["users"]),"max":MAX_USERS,"list":[{"email":e,"name":u.get("name")} for e,u in db["users"].items()]})

        elif path == "/" or path == "/index.html":
            html = "<h2>Сервер регистрации курса</h2><p>API: /api/reg, /api/check, /api/users</p><p>Зарегистрировано: %d/%d</p>" % (len(db["users"]), MAX_USERS)
            body = html.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

        else:
            return self._json({"ok":False,"reason":"notfound"}, 404)

def main():
    port = int(sys.argv[1]) if len(sys.argv)>1 else 8001
    Handler.db = load_db()
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    # глобально: DB_FILE относительно папки скрипта
    global DB_FILE
    DB_FILE = os.path.join(base, DB_FILE)
    with socketserver.ThreadingTCPServer(("", port), Handler) as httpd:
        print("Сервер регистрации запущен на http://localhost:%d" % port)
        print("База:", DB_FILE, "| лимит пользователей:", MAX_USERS)
        print("Пример: http://localhost:%d/api/reg?name=Иван&email=ivan@mail.ru" % port)
        print("Ctrl+C — остановка.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nСервер остановлен.")

if __name__ == "__main__":
    main()