# Runbook: the PyCon US Maintainer Summit's instance

The instance runs on Heroku from this repository's image, under
`summit.flashlights.app`, with mail through Mailgun and uploads in an
S3-compatible bucket. The core's [deployment guide](https://docs.flashlights.app/0.1.0/developer/deployment/)
has the general case; this page is what is specific to the Maintainer Summit.

## First deployment

1. Create the Heroku app from this repository: the Deploy button, or
   `heroku create maintainer-summit --stack container` followed by
   `heroku addons:create heroku-postgresql:essential-0` and
   `heroku addons:create heroku-redis:mini`. `app.json` lists every
   variable with a description; `.env.example` is the same list with the
   Maintainer Summit's values.
2. Set the secrets the platform cannot generate: `FERNET_KEY`, `EMAIL_URL`
   (the Mailgun SMTP credentials for `mail.flashlights.app`), and the four
   bucket variables.
3. Push, or connect the GitHub repository and deploy `main`. The release
   step runs `createcachetable` and `migrate` before the dynos take traffic.
4. Add the custom domain: `heroku domains:add summit.flashlights.app`, then the
   DNS record it prints, then `heroku certs:auto:enable`.
5. On the instance: `heroku run python manage.py set_site_domain summit.flashlights.app`,
   then create the first organiser account and give it the Organizers team
   (the core's [getting started guide](https://docs.flashlights.app/0.1.0/user/get_started/)).

## Upgrading the core

1. Read the core's changelog from the running tag to the new one.
2. Merge the pull request that bumps the tag in `Dockerfile` (Dependabot
   opens it), once CI is green: the image builds, the preset loads into a
   fresh database, the tests pass.
3. Deploy. Watch `heroku logs --tail --dyno release` for the migrations,
   then `--dyno web` and `--dyno worker`.
4. If the help links are the core's (`DOCS_URL` unset), they follow the
   image on their own; the Maintainer Summit sets `DOCS_URL` to its own site,
   which links to the core docs at the pinned version, so move that link
   by hand.

## Rolling back

`heroku rollback` returns to the previous release, as long as no migration
in between is irreversible; the changelog marks those. Otherwise restore
the database from the add-on's backup first.

## Where things are

| | |
|---|---|
| Logs | `heroku logs --tail --dyno web` (or `worker`, `release`) |
| Database | the Postgres add-on; `heroku pg:backups:capture` before a risky migration |
| Uploads | the bucket named by `AWS_STORAGE_BUCKET_NAME` |
| Outgoing mail | the Mailgun logs for `mail.flashlights.app` |
| Errors | Sentry, when `SENTRY_DSN` is set (it sends no personal data unless `SENTRY_SEND_DEFAULT_PII` is on) |
