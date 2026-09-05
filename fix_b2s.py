import shutil

PUT = "/opt/voicebot/handlers/voice.py"

# --- Pravka 1: ubiraem trebovanie kartinki ---
ST1 = "            if _b2s_tok and _b2s_net and _max_img_url:"
NEW1 = "            if _b2s_tok and _b2s_net:"

# --- Pravka 2: mediaObjects tolko kogda kartinka est ---
ST2 = '''                _pl = _js.dumps({"service_token": _st, "access_token": _at,
                    "client_user_network_id": _cid,
                    "b2s_posts": [{"client_user_network_id": _cid,
                        "message": _b2s_txt, "postFormat": 1,
                        "mediaObjects": [{"type": "IMAGE", "url": _max_img_url}]}]}).encode()'''

NEW2 = '''                _b2s_post = {"client_user_network_id": _cid,
                        "message": _b2s_txt, "postFormat": 1}
                if _max_img_url:
                    _b2s_post["mediaObjects"] = [{"type": "IMAGE", "url": _max_img_url}]
                _pl = _js.dumps({"service_token": _st, "access_token": _at,
                    "client_user_network_id": _cid,
                    "b2s_posts": [_b2s_post]}).encode()'''

s = open(PUT, encoding="utf-8").read()

for nomer, staroe in ((1, ST1), (2, ST2)):
    n = s.count(staroe)
    if n != 1:
        raise SystemExit("STOP: pravka %d naydena %d raz, zhdali 1. NICHEGO NE MENYALI." % (nomer, n))
print("Oba mesta naydeny. Delaem bekap.")

shutil.copy(PUT, PUT + ".bak_05sep_b2s")

s = s.replace(ST1, NEW1).replace(ST2, NEW2)
open(PUT, "w", encoding="utf-8").write(s)

p = open(PUT, encoding="utf-8").read()
print("staroe uslovie:", p.count(ST1), "| novoe uslovie:", p.count(NEW1))
print("mediaObjects pod usloviem:", p.count('if _max_img_url:\n                    _b2s_post["mediaObjects"]'))
print("GOTOVO")
