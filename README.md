# School Management System (SMS)

Sisiteme yuzuye yo gufasha amashuri gucunga:
- Amanota
- Attendance
- Amafaranga y'ishuri
- Raporo z'abanyeshuri

## Ikibazo gikemurwa

Amashuri menshi aracyakoresha impapuro. Iyi system ibika amakuru muri database imwe, igatanga raporo zihuse kandi zigabanya amakosa.

## Features z'ingenzi

- **Amanota:** kwinjiza amanota ku isomo no kureba impuzandengo.
- **Attendance:** gufata present/late/absent buri munsi.
- **Amafaranga:** kwandika ubwishyu no kubara amafaranga yishyuwe yose.
- **Raporo:** raporo y'umunyeshuri irimo summary + detail zose.
- **Dashboard:** imibare y'ibanze (abanyeshuri, average grade, absences, total paid).

## Pricing (Business model)

- **50,000 FRW – 300,000 FRW** one-time setup fee kuri buri shuri
- Cyangwa **monthly subscription** (bitewe n'ingano y'ishuri)

---

## 1) Guhita uyitangiza kuri machine yawe (Local)

### Ibisabwa
- Python 3.10+

### Steps

```bash
# 1) clone repo (simbuza URL iyawe)
git clone <REPO_URL>

# 2) injira muri project
cd new-project

# 3) reba python version
python3 --version

# 4) tangiza app
python3 app.py
```

Hanyuma fungura: `http://localhost:8000`

> App ikoresha SQLite (`data/sms.db`) ihita yirema ubwayo igihe uyitangiye.

---

## 2) Uko uyikura hano ukayi-hostinga ikora neza

### Option A: VPS (Ubuntu) — uburyo bworoshye kandi bwizewe

```bash
# kuri server ya Ubuntu
sudo apt update
sudo apt install -y git python3

# kura code
git clone <REPO_URL>
cd new-project

# tangiza kuri port ushaka (urugero 8080)
SMS_HOST=0.0.0.0 SMS_PORT=8080 python3 app.py
```

Fungura firewall kuri 8080 niba bikenewe.

### Option B: Docker hosting (Render/Railway/Fly.io/VM)

Iyi project ifite `Dockerfile`, bityo ushobora kuyihostinga kuri provider wese wemera Docker.

```bash
# local docker test
docker build -t sms-app .
docker run -p 8000:8000 sms-app
```

Fungura: `http://localhost:8000`

### Option C: Render (Web Service)

1. Push code kuri GitHub.
2. Jya kuri Render → **New Web Service**.
3. Hitamo repo yawe.
4. Runtime: **Docker** (Render izasoma `Dockerfile`).
5. Deploy.

Render izatanga URL nka: `https://your-sms.onrender.com`

---

## 3) Igenamiterere ry'ingenzi (Environment variables)

- `SMS_HOST` (default: `0.0.0.0`)
- `SMS_PORT` (default: `8000`)

Urugero:

```bash
SMS_HOST=0.0.0.0 SMS_PORT=9000 python3 app.py
```

---

## 4) Troubleshooting

- **Port 8000 iri gukoreshwa:** hindura `SMS_PORT`.
- **Ntibifunguka hanze ya server:** reba firewall/security group.
- **Data ntibika:** emeza ko folder `data/` yandikwamo.

---

## API endpoints

- `GET /api/dashboard`
- `GET /api/students`
- `POST /api/students`
- `POST /api/grades`
- `POST /api/attendance`
- `POST /api/payments`
- `GET /api/reports/student/{id}`
