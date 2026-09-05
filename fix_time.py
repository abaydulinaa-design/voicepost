import shutil

STAROE = "за 30 секунд"
NOVOE = "за 3 минуты"

FAJLY = {
    "/opt/voicebot/handlers/start.py": 10,
    "/opt/voicebot/handlers/channel.py": 2,
    "/opt/voicebot/handlers/style.py": 2,
    "/opt/voicebot/handlers/support.py": 1,
    "/opt/voicebot/max_bot.py": 3,
}

# 1) Сначала только считаем. Ничего не меняем, пока не сойдётся всё.
for put, zhdem in FAJLY.items():
    s = open(put, encoding="utf-8").read()
    n = s.count(STAROE)
    if n != zhdem:
        raise SystemExit("STOP: %s naydeno %d, zhdali %d. NICHEGO NE MENYALI." % (put, n, zhdem))
print("Schetchik soshelsya vezde. Delaem bekapy i pravim.")

# 2) Бэкап и замена
for put, zhdem in FAJLY.items():
    shutil.copy(put, put + ".bak_05sep_vremya")
    s = open(put, encoding="utf-8").read()
    s = s.replace(STAROE, NOVOE)
    open(put, "w", encoding="utf-8").write(s)
    print("OK", put)

# 3) Проверка: старого не осталось, новое на месте
print("--- PROVERKA ---")
for put, zhdem in FAJLY.items():
    s = open(put, encoding="utf-8").read()
    print(put, "| staroe:", s.count(STAROE), "| novoe:", s.count(NOVOE))
