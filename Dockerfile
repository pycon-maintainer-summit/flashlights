# The PyCon US Maintainer Summit's instance: the core image at a pinned version, plus this
# repository's app. Upgrading the core is a change to the tag on the first
# line. The second collectstatic adds the app's static files to the image,
# with the placeholder values the core's own build uses.
FROM ghcr.io/mariatta/flashlights:0.2.0
COPY . /community
RUN pip install --no-cache-dir /community
ENV EXTRA_APPS=flashlights_summit
RUN BOOT_CHECK=0 SECRET_KEY=build-only DJANGO_ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgres://localhost:5432/db \
    python manage.py collectstatic --noinput --clear
