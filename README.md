# DS Credit Shield Analytics

Flask app untuk dashboard dan prediksi risiko kredit, siap dijalankan lokal, dalam Docker, dan di Railway.

## Jalankan Lokal

1. Buat virtualenv dan aktifkan.

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependensi.

```bash
pip install -r requirements.txt
```

3. Jalankan aplikasi.

```bash
python app.py
```

Buka http://127.0.0.1:5000/

## Build Docker

```bash
docker build -t ds-credishield-analytics .
docker run --rm -p 8080:8080 -e PORT=8080 ds-credishield-analytics
```

## Deploy ke Railway

1. Push repo ini ke GitHub.
2. Buat service baru di Railway dari GitHub repo tersebut.
3. Railway akan memakai [Dockerfile](Dockerfile) otomatis.
4. Set environment variable berikut di Railway:

```bash
PORT=8080
```

## Monitoring ke DagsHub

App ini akan mengirim prediksi ke MLflow kalau variabel berikut diset:

```bash
MLFLOW_TRACKING_URI=https://dagshub.com/<username>/<repo>.mlflow
MLFLOW_TRACKING_USERNAME=<username>
MLFLOW_TRACKING_PASSWORD=<dagshub_token>
MLFLOW_EXPERIMENT_NAME=ds-credishield-monitoring
```

Kalau belum diset, aplikasi tetap berjalan dan menyimpan log prediksi lokal ke folder `monitoring/`.

## Push ke GitHub dan DagsHub

```bash
git init
git add .
git commit -m "Prepare Docker deploy and monitoring"

git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main

git remote add dagshub https://dagshub.com/<username>/<repo>.git
git push dagshub main
```
