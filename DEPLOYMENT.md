# Deployment Checklist

Use Python 3.12 or 3.13 in production. Python 3.14 may work locally, but most hosting stacks are still safer on 3.12/3.13.

## Environment

1. Copy `.env.example` to `.env` on the server.
2. Set a real `SECRET_KEY`.
3. Set `DEBUG=False`.
4. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for the live domain.
5. Configure PostgreSQL or MySQL credentials.
6. Configure SMTP credentials if password reset or email sending is needed.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

## WeasyPrint

PDF downloads use WeasyPrint only. Install the OS libraries required by WeasyPrint on the server before testing invoice/refund PDFs.

## Server

Serve static files from `STATIC_ROOT` and media files from `MEDIA_ROOT` through the web server. Do not rely on Django to serve media when `DEBUG=False`.

## Final Smoke Tests

- Login page opens and login works.
- Dashboard and payment dashboard load.
- Invoice create/edit/detail works.
- Invoice PDF downloads as a PDF.
- Refund list/add/statement PDF works.
- Product detail pages open without encoding errors.
