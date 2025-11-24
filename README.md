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

### Setup Database
1. Create PostgreSQL database on Render
2. Copy "Internal Database URL"

### Deploy App
1. Connect GitHub repo to Render
2. Choose Docker environment
3. Add environment variables:
   - `DATABASE_URL` = [your PostgreSQL URL]
   - `SECRET_KEY` = [random string]
4. Deploy

### Debug Database Issues
- Visit `/db-test` to check connection
- Visit `/db-init` to create tables manually
