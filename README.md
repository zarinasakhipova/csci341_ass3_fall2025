# Caregivers Platform

Flask app for managing caregivers database.

## Local run
```bash
pip install -r requirements.txt
python app.py
```

## Docker run
```bash
docker-compose up --build
```

## Deploy to Render
1. Connect GitHub repo to Render
2. Choose Docker environment
3. Set DATABASE_URL env var (PostgreSQL URL)
4. Set SECRET_KEY env var
5. Set FLASK_DEBUG=False
6. Deploy
