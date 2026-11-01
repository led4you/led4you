#!/usr/bin/env python3
# LED4YOU "a sua mensagem na matriz" — ponte entre a página dos visitantes e uma matriz LED4YOU / WLED em casa.
#
# A página pública (show/index.html) envia cada pedido para um canal do ntfy.sh. Este programa corre num
# computador da rede de casa (por exemplo o Raspberry Pi do FPP), ouve esse canal e mostra os pedidos na matriz,
# um de cada vez, através da interface JSON do WLED. A rede de casa nunca fica aberta para a internet.
#
# Tudo se controla numa página web própria, aberta no telemóvel ou no computador na rede de casa:
#     http://<ip-do-pi>:8099
# Lá liga e desliga a opção, procura as placas, escolhe a matriz e a zona, o tempo de cada pedido, o tema,
# aprova pedidos (se quiser) e copia o endereço do QR.
#
# Só usa a biblioteca normal do Python 3 (nada para instalar). Arranque:  python3 ponte_show.py
# As escolhas ficam em show_config.json, ao lado deste ficheiro.

import json, os, sys, time, threading, queue, unicodedata, re, socket, secrets, urllib.request, uuid, collections
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = 8099
RELAY = "https://ntfy.sh/"
PAGE = "https://led4you.github.io/led4you/show/"
GIF_SITE = "https://led4you.github.io/led4you/gifs/"
CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "show_config.json")
QUEUE_MAX = 20
RATE_MAX = 20         # no máximo 20 pedidos aceites por minuto, venham de onde vierem (a espera na página é só no telemóvel)
FACE_MAX = 128        # tamanho máximo de um lado (igual na página dos visitantes)

PAL = ["000000", "ffffff", "ff2a2a", "ff7a1a", "ffd23f", "39d353", "2bb7ff", "9b5cff", "ff4fd8"]   # igual à página
BAD = ["merda", "caralho", "foda", "fodase", "puta", "cabrao", "cona", "piroca", "pila", "paneleiro", "filhodaputa",
       "corno", "cu", "mamas", "boceta", "porra", "fuck", "shit", "bitch", "dick", "pussy", "cunt", "nigger", "nazi", "hitler"]
FX_TEXT, FX_IMAGE = 122, 53          # efeitos do WLED: texto a passar, imagem (GIF)
GIF_OK = re.compile(r"^(hw|xm|ev)-[a-z0-9]{2,20}\.gif$")

S = {   # definições (guardadas em show_config.json)
    "on": False, "topic": "l4yshow-3352b4beefd1", "board": "", "boardName": "",
    "faces": [],          # lados (zonas) onde aparecem os pedidos: [{"zone": id, "n": nome, "w": largura, "h": altura}]
    "seconds": {"text": 20, "gif": 12, "draw": 15, "fx": 180}, "theme": "hw", "approve": False,
    "wait": 0,            # segundos entre dois pedidos do mesmo telemóvel (0 = sem espera)
    "hold": False,        # True = o último pedido fica nas luzes até chegar outro (dá tempo para fotografias)
    "wait_turn": False,
    "fx_all": True,       # True = os visitantes também podem escolher qualquer efeito da placa (além das sugestões do tema)   # False = um pedido novo substitui logo o que está no lado; True = espera que o anterior acabe
    "free": True,         # True = escrever texto livre (com filtro de palavrões); False = só as mensagens prontas
}
# mensagens prontas (iguais às da página dos visitantes)
QUICK = {
    "hw": ["Feliz Halloween!", "Boo!", "Docura ou travessura!", "Ola!", "Uuuuh!", "Abobora!"],
    "xm": ["Feliz Natal!", "Boas Festas!", "Ho ho ho!", "Ola!", "Pai Natal!", "Neve!"],
    "ev": ["Parabens!", "Viva!", "Ola!", "Feliz Ano Novo!", "Boa Pascoa!", "Amo-te!"],
    "": ["Ola!", "Viva!", "Boo!", "Feliz Natal!", "Feliz Halloween!", "Parabens!"],
}
# efeitos que os visitantes podem escolher (v8): chave -> nome do efeito na placa (iguais aos da página dos visitantes)
FX_LIST = {
    "hw": [("haunted", "Haunted"), ("eyes", "Halloween Eyes"), ("fire", "Fire 2012"), ("lightning", "Lightning"),
           ("firenoise", "Firenoise"), ("blackhole", "Black Hole")],
    "xm": [("snowfall", "Snowfall"), ("candy", "Candy Cane"), ("retro", "Retro Tree"), ("twinkle", "Twinklefox"),
           ("fireworks", "Fireworks"), ("bursts", "Colored Bursts")],
    "ev": [("rainbow", "Rainbow"), ("fireworks", "Fireworks"), ("plasma", "Plasma Ball"), ("ripple", "Ripple"),
           ("matrix", "Matrix"), ("pacifica", "Pacifica")],
}
FX_NAMES = {k: n for v in FX_LIST.values() for k, n in v}
fx_cache = {}         # placa -> (hora, lista dos nomes dos efeitos): o número de cada efeito vem da própria placa


FX_SKIP = {"RSVD", "Image", "Scrolling Text", "My LEDs", "Solid", "Blink", "Blink Rainbow", "Strobe", "Strobe Rainbow",
           "Strobe Mega", "Multi Strobe", "Lightning"}   # não fazem sentido como pedido (ou piscam demasiado para crianças)


def fx_names(ip):
    """os nomes dos efeitos da placa (a posição na lista é o número do efeito) e os dados de cada um"""
    t, names, data = fx_cache.get(ip, (0, None, None))
    if not names or time.time() - t > 600:
        names = http_json(ip, "/json/eff")
        try:
            data = http_json(ip, "/json/fxdata")
        except Exception:
            data = None
        fx_cache[ip] = (time.time(), names, data)
    return names if isinstance(names, list) else [], data if isinstance(data, list) else []


def fx_id(ip, name):
    names, _ = fx_names(ip)
    return names.index(name) if name in names else -1


def board_fx(ip):
    """os efeitos da placa que os visitantes podem escolher: sem os de som (precisam de microfone) e sem os da lista FX_SKIP"""
    names, data = fx_names(ip)
    out = []
    for i, n in enumerate(names):
        if not n or n in FX_SKIP or n.startswith("-") or n in out:
            continue
        d = data[i] if i < len(data) and isinstance(data[i], str) else ""
        flags = d.split(";")[3] if d.count(";") >= 3 else ""
        if "v" in flags or "f" in flags:
            continue
        out.append(n)
    return sorted(out, key=str.lower)


lock = threading.RLock()
jobs = queue.Queue(QUEUE_MAX)
pending = []          # pedidos à espera de aprovação: {id, kind, cmd, raw, at}
boards = []           # placas encontradas na rede: {ip, name, w, h}
logs = []
uploaded = {}        # (ip, nome do GIF) -> hora em que se confirmou que está na placa
recent = collections.deque()   # (hora, pedido) dos pedidos aceites no último minuto
now_showing = {"what": ""}


def log(*a):
    line = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    with lock:
        logs.append(line)
        del logs[:-60]


def load():
    sec = dict(S["seconds"])
    try:
        with open(CFG_FILE) as f:
            S.update(json.load(f))
    except Exception:
        pass
    S["seconds"] = dict(sec, **S["seconds"])   # tempos novos (por exemplo o do efeito) num ficheiro antigo
    if not S["topic"]:
        S["topic"] = "l4yshow-" + secrets.token_hex(6)   # código do show, criado uma vez
        save()


def save():
    with open(CFG_FILE, "w") as f:
        json.dump(S, f, indent=1)


def qr_url(tema=""):
    # um endereço por tema (Halloween / Natal); sem tema, a página usa o tema escolhido aqui
    return "%s?t=%s%s" % (PAGE, S["topic"], "&tema=" + tema if tema else "")


# ---------------------------------------------------------------------------------------- matriz ----
def plain(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()


def is_bad(s):
    n = plain(s).lower().translate(str.maketrans("0@1!345$", "ooiieass"))
    words = re.split(r"[^a-z]+", n)
    joined = re.sub(r"[^a-z]", "", n)
    return any(b in words or (len(b) >= 5 and b in joined) for b in BAD)


def http_json(ip, path, body=None, timeout=5):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request("http://%s%s" % (ip, path), data=data, headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def gif_on_board(ip, name):
    """o GIF ainda está na placa? (pode ter sido apagado na app, por exemplo com "Apagar todos os GIF")"""
    try:
        with urllib.request.urlopen("http://%s/%s" % (ip, name), timeout=4) as r:
            return r.status == 200 and r.read(6)[:3] == b"GIF"
    except Exception:
        return False


def upload_gif(ip, name):
    # confirmado há menos de 10 minutos: não perguntar outra vez; senão ver se ainda lá está antes de o enviar de novo
    if time.time() - uploaded.get((ip, name), 0) < 600:
        return True
    if gif_on_board(ip, name):
        uploaded[(ip, name)] = time.time()
        return True
    try:
        with urllib.request.urlopen(GIF_SITE + name, timeout=10) as r:
            gif = r.read()
        b = uuid.uuid4().hex
        body = (("--%s\r\nContent-Disposition: form-data; name=\"data\"; filename=\"/%s\"\r\nContent-Type: image/gif\r\n\r\n" % (b, name)).encode()
                + gif + ("\r\n--%s--\r\n" % b).encode())
        req = urllib.request.Request("http://%s/upload" % ip, data=body, headers={"Content-Type": "multipart/form-data; boundary=" + b})
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
        uploaded[(ip, name)] = time.time()
        return True
    except Exception as e:
        log("imagem", name, "não foi para a placa:", e)
        return False


def check(msg, allow_free=False):
    """valida um pedido vindo da internet; devolve (tipo, comando, resumo) ou None"""
    try:
        m = json.loads(msg)
    except Exception:
        return None
    if not isinstance(m, dict) or not S["faces"]:
        return None
    k, z = m.get("k"), m.get("z", -1)
    if not isinstance(z, int) or z < -1 or z >= len(S["faces"]):
        return None
    faces = S["faces"] if z == -1 else [S["faces"][z]]
    where = "todos os lados" if z == -1 or len(S["faces"]) == 1 else (S["faces"][z].get("n") or "lado %d" % (z + 1))
    segs = lambda part: {"on": True, "seg": [dict(part, id=f["zone"]) for f in faces]}
    if k in ("text", "quick"):
        if k == "quick":
            t = str(m.get("q", ""))
            if not any(t in v for v in QUICK.values()):
                return None
        else:
            if not (S["free"] or allow_free):
                return None
            t = str(m.get("t", ""))[:40].strip()
            if not t or is_bad(t):
                return None
            t = re.sub(r"[^ -~]", "", plain(t)).strip()
            if not t:
                return None
        c = m.get("c", 3)
        c = PAL[c] if isinstance(c, int) and 1 <= c < len(PAL) else PAL[3]
        rgb = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
        return "text", segs({"fx": FX_TEXT, "n": t, "col": [rgb, [0, 0, 0], rgb], "sx": 140, "ix": 128, "c1": 0, "c2": 128, "c3": 16,
                             "o1": False, "o2": False, "o3": False, "tp": False, "frz": False}), {"t": t, "c": c, "where": where}
    if k == "gif":
        f = str(m.get("f", ""))
        if not GIF_OK.match(f):
            return None
        return "gif", segs({"fx": FX_IMAGE, "n": f, "sx": 128, "ix": 0, "c3": 0, "frz": False}), {"f": f, "where": where}
    if k == "fx":
        e = str(m.get("e", ""))
        if e in FX_NAMES:
            n = FX_NAMES[e]
        else:   # v12: um efeito qualquer da placa (se a opção estiver ligada)
            n = str(m.get("n", ""))[:40]
            try:
                if not S.get("fx_all", True) or not S["board"] or n not in board_fx(S["board"]):
                    return None
            except Exception:
                return None
        return "fx", segs({"fx": 0, "fxdef": True, "frz": False}), {"e": e, "n": n, "where": where}
    if k == "draw":
        p = str(m.get("p", ""))
        w, h = m.get("w"), m.get("h")
        if any(f["w"] != w or f["h"] != h for f in faces) or not isinstance(w, int) or len(p) != w * h or not re.fullmatch(r"[0-8]+", p):
            return None
        pix = [0, w * h, "000000"]
        for i, ch in enumerate(p):
            if ch != "0":
                pix += [i, PAL[int(ch)]]
        return "draw", segs({"frz": True, "i": pix}), {"w": w, "h": h, "p": p, "where": where}
    return None


def add(msg):
    if not S["on"] or not S["board"] or not S["faces"]:
        log("pedido ignorado: a opção está desligada")
        return
    job = check(msg)
    if not job:
        log("pedido recusado:", msg[:80])
        return
    now = time.time()
    with lock:
        while recent and now - recent[0][0] > 60:
            recent.popleft()
        if any(m == msg and now - t < 3 for t, m in recent):   # o mesmo pedido duas vezes em 3 s (toque duplo)
            log("pedido repetido ignorado")
            return
        if len(recent) >= RATE_MAX:
            log("demasiados pedidos neste minuto, ignorado")
            return
        recent.append((now, msg))
    kind, cmd, info = job
    if S["approve"]:
        with lock:
            if len(pending) >= QUEUE_MAX:
                log("demasiados pedidos por aprovar, ignorado")
                return
            pending.append({"id": secrets.token_hex(4), "kind": kind, "cmd": cmd, "info": info, "at": time.strftime("%H:%M:%S")})
        log("pedido à espera de aprovação:", kind)
        return
    enqueue(kind, cmd, info)


def enqueue(kind, cmd, info):
    try:
        jobs.put_nowait((kind, cmd, info))
        log("pedido em fila:", kind, "(%d à espera)" % jobs.qsize())
    except queue.Full:
        log("fila cheia, pedido ignorado")


waiting = []          # pedidos já tirados da fila, à espera que o lado (ou lados) deles fique livre


def show_loop():
    """v10: cada lado é independente: um pedido para um lado aparece logo, mesmo que outro lado esteja a mostrar
    um texto ou um efeito (antes era um pedido de cada vez para o cubo todo, e um texto longo num lado parava os outros).
    Pedidos para o mesmo lado esperam pela vez, por ordem de chegada."""
    saved = None          # (placa, estado da placa antes dos pedidos): cada lado volta ao que estava
    busy = {}             # zona -> até quando está a mostrar um pedido
    shown = {}            # zona -> o que está a mostrar (para a página de controlo)
    while True:
        try:
            while True:
                waiting.append(jobs.get_nowait())
        except queue.Empty:
            pass
        now = time.time()
        ip = S["board"]
        if not S["on"] or not ip:
            waiting.clear(); busy.clear(); shown.clear(); saved = None; now_showing["what"] = ""
            time.sleep(0.5)
            continue
        # v11: de origem, um pedido novo substitui logo o que está nesse lado (os mais antigos para o mesmo lado, que
        # ainda não apareceram, são postos de lado). Com "esperar pela vez": o primeiro pedido da fila para cada lado livre.
        started = False
        taken = set()
        if not S.get("wait_turn"):
            newest = {}
            for i, (_, c, _) in enumerate(waiting):
                for sg in c["seg"]:
                    newest[sg["id"]] = i
            waiting[:] = [j for i, j in enumerate(waiting) if any(newest[sg["id"]] == i for sg in j[1]["seg"])]
            for j in waiting:
                for sg in j[1]["seg"]:
                    busy.pop(sg["id"], None)
        for job in list(waiting):
            kind, cmd, info = job
            zones = [sg["id"] for sg in cmd["seg"]]
            if any(busy.get(z, 0) > now or z in taken for z in zones):
                taken.update(zones)       # quem chegou primeiro a estes lados tem a vez
                continue
            waiting.remove(job)
            taken.update(zones)
            try:
                if saved is None or saved[0] != ip:
                    saved = (ip, http_json(ip, "/json/state"))
                if kind == "gif" and not upload_gif(ip, cmd["seg"][0]["n"]):
                    continue
                if kind == "fx":   # o número do efeito é o desta placa (os efeitos do LED4YOU podem ter outro número noutra)
                    fid = fx_id(ip, info["n"])
                    if fid < 0:
                        log("esta placa não tem o efeito", info["n"])
                        continue
                    for sg in cmd["seg"]:
                        sg["fx"] = fid
                http_json(ip, "/json/state", cmd)
                what = kind + ": " + (info.get("t") or info.get("f") or info.get("n") or "desenho") + " (" + info.get("where", "") + ")"
                log("a mostrar", what)
                until = time.time() + max(3, int(S["seconds"].get(kind, 15)))
                for z in zones:
                    busy[z] = until
                    shown[z] = what
                started = True
            except Exception as e:
                log("a placa não respondeu:", e)
                waiting.insert(0, job)
                time.sleep(3)
                break
        # lados cujo tempo acabou e sem mais pedidos: voltam ao que estavam (a não ser "deixar o último pedido")
        now = time.time()
        for z in [z for z, t in busy.items() if t <= now]:
            if any(z in [sg["id"] for sg in c["seg"]] for _, c, _ in waiting):
                continue
            del busy[z]
            shown.pop(z, None)
            if S["hold"] or saved is None:
                continue
            try:
                old = [dict(sg, frz=False) for sg in saved[1].get("seg", []) if sg.get("id") == z]
                if old:
                    http_json(saved[0], "/json/state", {"seg": old})
                    log("o lado voltou ao que estava (zona %d)" % z)
            except Exception as e:
                log("não voltei ao estado anterior:", e)
        if not busy and not waiting and not S["hold"]:
            saved = None
        now_showing["what"] = " · ".join(shown[z] for z in sorted(shown))
        if not started:
            time.sleep(0.3)


# ------------------------------------------------------------------------------ canal na internet ----
def publish_status():
    """a página dos visitantes lê isto para saber se a opção está ligada"""
    try:
        body = json.dumps({"on": bool(S["on"] and S["board"] and S["faces"]), "faces": [{"n": f.get("n", ""), "w": f["w"], "h": f["h"]} for f in S["faces"]],
                           "theme": S["theme"], "free": S["free"], "wait": S["wait"], "at": int(time.time())}).encode()
        urllib.request.urlopen(urllib.request.Request(RELAY + S["topic"] + "-estado", data=body, headers={"Cache": "yes"}), timeout=10).read()
    except Exception as e:
        log("não consegui avisar a página do estado:", e)
    publish_fx()


def publish_fx():
    """v12: a lista dos efeitos da placa para a página dos visitantes (num canal à parte: cabe nos 4 KB de uma mensagem)"""
    try:
        names = board_fx(S["board"]) if S.get("fx_all", True) and S["board"] else []
    except Exception as e:
        log("não consegui ler os efeitos da placa:", e)
        return
    try:
        body = json.dumps({"fx": names, "at": int(time.time())}, ensure_ascii=False, separators=(",", ":")).encode()
        if len(body) > 4000:   # mensagens maiores viram anexo no ntfy: corta a lista
            while len(body) > 4000 and names:
                names = names[:-5]
                body = json.dumps({"fx": names, "at": int(time.time())}, ensure_ascii=False, separators=(",", ":")).encode()
        urllib.request.urlopen(urllib.request.Request(RELAY + S["topic"] + "-fx", data=body, headers={"Cache": "yes"}), timeout=10).read()
        log("lista de %d efeitos enviada para a página dos visitantes" % len(names))
    except Exception as e:
        log("não consegui enviar a lista de efeitos:", e)


def status_loop():
    while True:
        publish_status()
        time.sleep(1800)


def listen():
    since = None
    while True:
        topic = S["topic"]
        try:
            url = "%s%s/json" % (RELAY, topic) + ("?since=%s" % since if since else "")
            with urllib.request.urlopen(url, timeout=90) as r:
                log("ligado ao canal do show")
                for line in r:
                    ev = json.loads(line)
                    if ev.get("event") != "message":
                        continue
                    since = ev.get("id", since)
                    add(ev.get("message", ""))
        except Exception as e:
            log("canal desligado (%s); volto a ligar daqui a 5 s" % e)
            time.sleep(5)


# ---------------------------------------------------------------------------------- placas na rede ----
def my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "192.168.1.2"
    finally:
        s.close()


def probe(ip):
    try:
        i = http_json(ip, "/json/info", timeout=0.8)
        if not isinstance(i, dict) or "ver" not in i:
            return None
        mx = (i.get("leds") or {}).get("matrix") or {}
        return {"ip": ip, "name": i.get("name", ip), "w": mx.get("w", 0), "h": mx.get("h", 0)}
    except Exception:
        return None


def scan():
    base = my_ip().rsplit(".", 1)[0]
    with ThreadPoolExecutor(64) as ex:
        found = [b for b in ex.map(probe, ["%s.%d" % (base, n) for n in range(1, 255)]) if b]
    with lock:
        boards[:] = found
    log("procura na rede: %d placa(s) encontrada(s)" % len(found))
    return found


def zones(ip):
    st = http_json(ip, "/json/state")
    out = []
    for s in st.get("seg", []):
        if s.get("stop", 0) <= s.get("start", 0):
            continue
        w = s["stop"] - s["start"]
        h = max(1, s.get("stopY", 1) - s.get("startY", 0))
        out.append({"id": s.get("id", 0), "w": w, "h": h, "name": s.get("n") or ""})
    return out


# ------------------------------------------------------------------------------------ página web ----
ADMIN = r"""<!doctype html><html lang="pt-PT"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mensagens dos visitantes</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
:root{--bg:#120b1f;--card:#1d1430;--raise:#281c40;--line:#3a2d52;--fg:#fff;--muted:#c9bddc;--hot:#ff7a1a;--ok:#39d353}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,sans-serif}
main{max-width:620px;margin:0 auto;padding:20px 16px 40px;display:flex;flex-direction:column;gap:14px}
h1{margin:0;font-size:24px}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:10px}
.ct{font-weight:700;font-size:17px}.note{font-size:14px;color:var(--muted)}label{font-size:14px;color:var(--muted)}
select,input[type=number],input[type=text]{width:100%;min-height:44px;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--raise);color:var(--fg);font:inherit}
.btn{min-height:44px;padding:8px 16px;border-radius:10px;border:1px solid var(--line);background:var(--raise);color:var(--fg);font:inherit;font-weight:600;cursor:pointer}
.btn.primary{background:var(--hot);border-color:var(--hot);color:#120b1f}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.three{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.big{display:flex;align-items:center;gap:12px;font-size:18px;font-weight:700}
.big input{width:26px;height:26px}.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:700}
.on{background:var(--ok);color:#06240f}.off{background:#5a4d6b}.url{word-break:break-all;font-size:14px;background:#000;padding:10px;border-radius:10px}
.qr{background:#fff;padding:10px;border-radius:12px;align-self:center}.qrs{display:flex;flex-wrap:wrap;gap:14px;justify-content:center}.qrb{display:flex;flex-direction:column;gap:8px;align-items:center;text-align:center;max-width:240px}.item{display:flex;gap:10px;align-items:center;border:1px solid var(--line);border-radius:12px;padding:8px}
.item .what{flex:1;min-width:0;word-break:break-word}.zrow{display:flex;gap:10px;align-items:center}.zrow input[type=checkbox]{width:24px;height:24px;flex:none}.zrow span{flex:none;min-width:120px}canvas{image-rendering:pixelated;background:#000;border-radius:6px}
pre{white-space:pre-wrap;font-size:12px;color:var(--muted);margin:0;max-height:220px;overflow:auto}
[hidden]{display:none!important}
</style></head><body><main>
<h1>Mensagens dos visitantes</h1>
<div class="card">
  <label class="big"><input type="checkbox" id="on"> Mostrar os pedidos dos visitantes</label>
  <div class="note" id="state"></div>
</div>
<div class="card">
  <div class="ct">Matriz</div>
  <div class="row"><button class="btn" id="scan" type="button">Procurar placas na rede</button><span class="note" id="scanMsg"></span></div>
  <label for="board">Placa</label><select id="board"></select>
  <div class="note">Lados (zonas) onde aparecem os pedidos — marque um ou mais e dê-lhes um nome (por exemplo Frente, Topo):</div>
  <div id="zones" style="display:flex;flex-direction:column;gap:8px"></div>
</div>
<div class="card">
  <div class="ct">Como aparecem</div>
  <label for="theme">Tema de quem abre a página sem tema no endereço</label>
  <select id="theme"><option value="hw">Halloween</option><option value="xm">Natal</option><option value="ev">Outras festas</option><option value="">Todas</option></select>
  <div class="three">
    <div><label for="sText">Texto (s)</label><input type="number" id="sText" min="3" max="300"></div>
    <div><label for="sGif">Imagem (s)</label><input type="number" id="sGif" min="3" max="300"></div>
    <div><label for="sDraw">Desenho (s)</label><input type="number" id="sDraw" min="3" max="300"></div>
    <div><label for="sFx">Efeito (s)</label><input type="number" id="sFx" min="3" max="300"></div>
  </div>
  <label for="wait">Espera entre pedidos do mesmo telemóvel (segundos, 0 = sem espera)</label>
  <input type="number" id="wait" min="0" max="600">
  <label class="big" style="font-size:16px"><input type="checkbox" id="hold"> Deixar o último pedido nas luzes até chegar outro</label>
  <div class="note">Dá tempo para tirar fotografias. Desligado: depois do tempo, as luzes voltam ao que mostravam antes.</div>
  <label class="big" style="font-size:16px"><input type="checkbox" id="fxAll"> Mostrar aos visitantes todos os efeitos da placa</label>
  <div class="note">Além das sugestões do tema. Ficam de fora os efeitos de som e os que piscam muito.</div>
  <label class="big" style="font-size:16px"><input type="checkbox" id="waitTurn"> Cada pedido espera que o anterior acabe</label>
  <div class="note">Desligado: um pedido novo substitui logo o que está nesse lado.</div>
  <label class="big" style="font-size:16px"><input type="checkbox" id="free"> Deixar escrever texto livre</label>
  <div class="note">Desligado (recomendado para crianças): só as mensagens prontas, as imagens e os desenhos.</div>
  <label class="big" style="font-size:16px"><input type="checkbox" id="approve"> Aprovar cada pedido antes de aparecer</label>
  <div class="row"><button class="btn primary" id="save" type="button">Guardar</button><span class="note" id="saveMsg"></span></div>
</div>
<div class="card" id="pendCard" hidden>
  <div class="ct">Por aprovar</div><div id="pend" style="display:flex;flex-direction:column;gap:8px"></div>
</div>
<div class="card">
  <div class="ct">Códigos QR para os cartazes</div>
  <div class="note">Um para o Halloween e outro para o Natal: cada um abre a página com as cores, mensagens e imagens desse tema.</div>
  <div class="qrs">
   <div class="qrb"><b>Halloween</b><div class="qr" id="qr_hw"></div><div class="url" id="url_hw"></div><button class="btn" type="button" data-copy="hw">Copiar endereço</button></div>
   <div class="qrb"><b>Natal</b><div class="qr" id="qr_xm"></div><div class="url" id="url_xm"></div><button class="btn" type="button" data-copy="xm">Copiar endereço</button></div>
  </div>
  <div class="row"><input type="text" id="testTxt" placeholder="Texto de teste" style="flex:1;min-width:140px"><button class="btn" id="test" type="button">Testar</button></div>
</div>
<div class="card"><div class="ct">Registo</div><div class="note" id="now"></div><pre id="log"></pre></div>
</main><script>
const $=id=>document.getElementById(id);let st=null,editing=false,qrFor='',zonesFor=null;
const api=(p,b)=>fetch('/api/'+p,b===undefined?{}:{method:'POST',headers:{'X-L4Y':'1'},body:JSON.stringify(b)}).then(r=>r.json());
function opt(sel,list,val){sel.replaceChildren(...list.map(([v,t])=>{const o=document.createElement('option');o.value=v;o.textContent=t;return o;}));sel.value=val;}
let zl=[];
async function loadZones(ip,faces){zl=[];if(ip){try{zl=await api('zones?ip='+encodeURIComponent(ip));}catch(e){}}
 $('zones').replaceChildren(...(zl.length?zl.map(q=>{const f=(faces||[]).find(x=>x.zone===q.id);const r=document.createElement('label');r.className='zrow';
  const c=document.createElement('input');c.type='checkbox';c.checked=!!f;c.dataset.id=q.id;const t=document.createElement('span');t.textContent='Zona '+(q.id+1)+' ('+q.w+'×'+q.h+')';
  const n=document.createElement('input');n.type='text';n.placeholder='Nome (opcional)';n.value=f?f.n:'';n.dataset.id=q.id;n.onfocus=()=>editing=true;c.onchange=()=>editing=true;r.append(c,t,n);return r;}):[Object.assign(document.createElement('div'),{className:'note',textContent:ip?'A placa não respondeu.':'Escolha primeiro uma placa.'})]));}
function facesNow(){return zl.filter(q=>$('zones').querySelector('input[type=checkbox][data-id="'+q.id+'"]').checked).map(q=>({zone:q.id,w:q.w,h:q.h,n:$('zones').querySelector('input[type=text][data-id="'+q.id+'"]').value.trim()}));}
function render(){
 $('on').checked=st.on;$('state').innerHTML=st.on&&st.board?'<span class="pill on">LIGADO</span> Os pedidos aparecem em '+(st.boardName||st.board)+'.':'<span class="pill off">DESLIGADO</span> Os pedidos dos visitantes não aparecem.';
 if(!editing){opt($('board'),[['','Escolha uma placa']].concat(st.boards.map(b=>[b.ip,b.name+' ('+b.ip+')'])).concat(st.board&&!st.boards.some(b=>b.ip===st.board)?[[st.board,(st.boardName||st.board)+' ('+st.board+')']]:[]),st.board);
  if(zonesFor!==st.board){zonesFor=st.board;loadZones(st.board,st.faces);}
  $('free').checked=st.free;
  $('theme').value=st.theme;$('sText').value=st.seconds.text;$('sGif').value=st.seconds.gif;$('sDraw').value=st.seconds.draw;$('sFx').value=st.seconds.fx||180;$('wait').value=st.wait||0;$('hold').checked=!!st.hold;$('waitTurn').checked=!!st.wait_turn;$('fxAll').checked=st.fx_all!==false;$('approve').checked=st.approve;}
 const qk=st.urls.hw+st.urls.xm;$('url_hw').textContent=st.urls.hw;$('url_xm').textContent=st.urls.xm;
 if(qrFor!==qk&&window.QRCode){for(const t of ['hw','xm']){$('qr_'+t).replaceChildren();new QRCode($('qr_'+t),{text:st.urls[t],width:200,height:200,correctLevel:QRCode.CorrectLevel.M});}qrFor=qk;}
 $('pendCard').hidden=!st.pending.length;
 $('pend').replaceChildren(...st.pending.map(p=>{const d=document.createElement('div');d.className='item';const w=document.createElement('div');w.className='what';
  if(p.kind==='draw'){const c=document.createElement('canvas');c.width=p.info.w;c.height=p.info.h;c.style.width=(p.info.w*5)+'px';const g=c.getContext('2d');[...p.info.p].forEach((v,i)=>{if(v!=='0'){g.fillStyle='#'+['000000','ffffff','ff2a2a','ff7a1a','ffd23f','39d353','2bb7ff','9b5cff','ff4fd8'][+v];g.fillRect(i%p.info.w,Math.floor(i/p.info.w),1,1);}});w.append(c);}
  else w.textContent=(p.kind==='text'?'Texto: '+p.info.t:p.kind==='fx'?'Efeito: '+p.info.n:'Imagem: '+p.info.f);if(p.info.where){const s=document.createElement('div');s.className='note';s.textContent=p.info.where;w.append(s);}
  const ok=document.createElement('button');ok.className='btn primary';ok.textContent='Mostrar';ok.onclick=()=>api('approve',{id:p.id}).then(refresh);
  const no=document.createElement('button');no.className='btn';no.textContent='Recusar';no.onclick=()=>api('reject',{id:p.id}).then(refresh);
  d.append(w,ok,no);return d;}));
 $('now').textContent=st.now?'Agora na matriz: '+st.now+' · '+st.queue+' em fila':st.queue+' em fila';$('log').textContent=st.log.slice().reverse().join('\n');}
async function refresh(){st=await api('state');render();}
$('on').onchange=()=>api('settings',{on:$('on').checked}).then(refresh);
$('board').onfocus=()=>editing=true;
['sText','sGif','sDraw','sFx','wait','theme','approve','free','hold','waitTurn','fxAll'].forEach(id=>{const e=$(id);e.addEventListener('focus',()=>editing=true);e.addEventListener('input',()=>editing=true);e.addEventListener('change',()=>editing=true);});   // v9: the 3 s refresh no longer puts back the old times while typing
$('board').onchange=()=>{editing=true;loadZones($('board').value,[]);};$('free').onchange=()=>editing=true;$('hold').onchange=()=>editing=true;$('wait').oninput=()=>editing=true;
$('scan').onclick=async()=>{$('scanMsg').textContent='A procurar… (até 10 s)';const r=await api('scan',{});$('scanMsg').textContent=r.length+' placa(s) encontrada(s)';editing=false;await refresh();};
$('save').onclick=async()=>{const b=st.boards.find(x=>x.ip===$('board').value);const faces=facesNow();
 if(!faces.length){$('saveMsg').textContent='Marque pelo menos um lado.';return;}
 await api('settings',{board:$('board').value,boardName:b?b.name:(st.board===$('board').value?st.boardName:''),faces,theme:$('theme').value,approve:$('approve').checked,free:$('free').checked,hold:$('hold').checked,wait_turn:$('waitTurn').checked,fx_all:$('fxAll').checked,wait:Math.max(0,Math.min(600,+$('wait').value|0)),seconds:{text:+$('sText').value,gif:+$('sGif').value,draw:+$('sDraw').value,fx:+$('sFx').value}});
 editing=false;$('saveMsg').textContent='Guardado.';setTimeout(()=>$('saveMsg').textContent='',2500);refresh();};
document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=()=>navigator.clipboard&&navigator.clipboard.writeText(st.urls[b.dataset.copy]).then(()=>{b.textContent='Copiado';setTimeout(()=>b.textContent='Copiar endereço',2000);}));
$('test').onclick=()=>api('test',{t:$('testTxt').value||'Ola!'}).then(refresh);
refresh();setInterval(()=>{if(!editing)refresh();},3000);
</script></body></html>"""


class Admin(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else (json.dumps(body) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            return self.send(200, ADMIN, "text/html")
        if p == "/api/state":
            with lock:
                return self.send(200, dict(S, boards=boards, url=qr_url(), urls={"hw": qr_url("hw"), "xm": qr_url("xm")}, log=logs[-40:], now=now_showing["what"], queue=jobs.qsize() + len(waiting),
                                         pending=[{k: v for k, v in x.items() if k != "cmd"} for x in pending]))
        if p == "/api/zones":
            ip = self.path.split("ip=", 1)[-1] if "ip=" in self.path else ""
            ip = urllib.request.unquote(ip)
            if not re.fullmatch(r"[0-9.]{7,15}", ip):
                return self.send(400, [])
            try:
                return self.send(200, zones(ip))
            except Exception:
                return self.send(200, [])
        self.send(404, {"error": "?"})

    def do_POST(self):
        # só a página de controlo envia este cabeçalho: um site qualquer aberto num telemóvel da rede de casa não o
        # consegue juntar (o navegador pediria autorização, que a ponte nunca dá), por isso não consegue mudar nada
        if self.headers.get("X-L4Y") != "1":
            return self.send(403, {"error": "forbidden"})
        p, b = self.path, self.body()
        if p == "/api/settings":
            changed_on = "on" in b and bool(b["on"]) != S["on"]
            with lock:
                for k in ("on", "approve", "free", "hold", "wait_turn", "fx_all"):
                    if k in b:
                        S[k] = bool(b[k])
                if "board" in b and (b["board"] == "" or re.fullmatch(r"[0-9.]{7,15}", str(b["board"]))):
                    S["board"] = b["board"]; S["boardName"] = str(b.get("boardName", ""))[:40]
                if isinstance(b.get("faces"), list):
                    fs = []
                    for f in b["faces"][:8]:
                        if isinstance(f, dict) and isinstance(f.get("zone"), int) and 0 <= f["zone"] < 32 and all(isinstance(f.get(k), int) and 1 <= f[k] <= FACE_MAX for k in ("w", "h")):
                            fs.append({"zone": f["zone"], "w": f["w"], "h": f["h"], "n": str(f.get("n", ""))[:20]})
                    S["faces"] = fs
                if b.get("theme") in ("hw", "xm", "ev", ""):
                    S["theme"] = b["theme"]
                if isinstance(b.get("wait"), int) and 0 <= b["wait"] <= 600:
                    S["wait"] = b["wait"]
                if isinstance(b.get("seconds"), dict):
                    for k in ("text", "gif", "draw", "fx"):
                        v = b["seconds"].get(k)
                        if isinstance(v, int) and 3 <= v <= 300:
                            S["seconds"][k] = v
                save()
            log("definições guardadas" + (" (ligado)" if S["on"] else " (desligado)"))
            if not S["on"]:
                with lock:
                    pending.clear()
                while not jobs.empty():
                    jobs.get_nowait()
                waiting.clear()
            threading.Thread(target=publish_status, daemon=True).start()
            return self.send(200, {"ok": True})
        if p == "/api/scan":
            return self.send(200, scan())
        if p in ("/api/approve", "/api/reject"):
            with lock:
                item = next((x for x in pending if x["id"] == b.get("id")), None)
                if item:
                    pending.remove(item)
            if item and p == "/api/approve":
                enqueue(item["kind"], item["cmd"], item["info"])
            return self.send(200, {"ok": bool(item)})
        if p == "/api/test":
            job = check(json.dumps({"k": "text", "t": str(b.get("t", "Ola!"))[:40], "c": 3, "z": -1}), allow_free=True)   # o teste pode ter texto escrito
            if job and S["board"]:
                enqueue(*job)
            return self.send(200, {"ok": bool(job)})
        self.send(404, {"error": "?"})


if __name__ == "__main__":
    load()
    log("página de controlo: http://%s:%d" % (my_ip(), PORT))
    threading.Thread(target=show_loop, daemon=True).start()
    threading.Thread(target=listen, daemon=True).start()
    threading.Thread(target=status_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Admin).serve_forever()
