from flask import Flask, Response
import socket
import os

app = Flask(__name__)
# estimation approximative du temps de service moyen (s) — ajustez
AVG_SERVICE_TIME = float(os.environ.get("AVG_SERVICE_TIME", "1.5"))
HAPROXY_SOCKET = os.environ.get("HAPROXY_SOCKET", "/var/run/haproxy.sock")

def read_haproxy_stats():
    # envoie "show stat" au socket admin et récupère le CSV
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(HAPROXY_SOCKET)
        sock.sendall(b"show stat\n")
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        sock.close()
        return data.decode(errors="ignore")
    except Exception as e:
        return ""

def parse_queue_for_backend(csv, backend_name="servers"):
    # cherche la ligne pour le backend (pxname = backend_name, svname = BACKEND or one of servers)
    # le champ qcur (current queued requests) est à l'index connu dans CSV: on récupère le header pour trouver l'index
    if not csv:
        return 0
    lines = csv.splitlines()
    header = lines[0].lstrip('# ').split(',')
    try:
        qcur_idx = header.index('qcur')
        pxname_idx = header.index('pxname')
        svname_idx = header.index('svname')
    except ValueError:
        return 0
    total_q = 0
    for ln in lines[1:]:
        cols = ln.split(',')
        if len(cols) <= max(qcur_idx, pxname_idx):
            continue
        if cols[pxname_idx] == backend_name:
            try:
                total_q += int(cols[qcur_idx])
            except:
                pass
    return total_q

@app.route("/")
def waiting():
    csv = read_haproxy_stats()
    q = parse_queue_for_backend(csv, "servers")
    # estimation simple : position = q, eta = q * AVG_SERVICE_TIME
    eta = int(q * AVG_SERVICE_TIME)
    html = f"""
    <html><head><title>Liste d'attente</title></head>
    <body>
      <h1>Vous êtes en file d'attente</h1>
      <p>Position approximative : {q}</p>
      <p>Temps d'attente estimé : {eta} secondes</p>
      <p>La page se rafraîchira automatiquement.</p>
      <script>setTimeout(()=>location.reload(), 5000);</script>
    </body></html>
    """
    return Response(html, mimetype="text/html")
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)