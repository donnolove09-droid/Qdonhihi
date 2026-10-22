# QDONENLITE — Free Fire Telegram API Bot

A Telegram polling bot with an HTTP health endpoint for Render Web Service.

## Integrated API routes

The project uses the API base URL `https://flash-player-info-v1.vercel.app` and the credential path format `/{API_UID}/{API_PASSWORD}/{endpoint}`.

Implemented endpoints:
- `player-info`
- `bancheck`
- `stats-info`
- `STATS/CAREER/BR`
- `STATS/CAREER/CS`
- `STATS/RANKED/BR`
- `STATS/RANKED/CS`
- `STATS/NORMAL/BR`
- `STATS/NORMAL/CS`
- `level`
- `region`
- `wishlist`
- `workshop-info`
- `duo-info`

UID targets are sent as `?uid=...`; non-numeric targets are sent as `?name=...`.

## Telegram commands

- `/start`
- `/help`
- `/player <UID|name>`
- `/bancheck <UID|name>`
- `/stats <UID|name>`
- `/careerbr <UID|name>`
- `/careercs <UID|name>`
- `/rankedbr <UID|name>`
- `/rankedcs <UID|name>`
- `/normalbr <UID|name>`
- `/normalcs <UID|name>`
- `/level <UID|name>`
- `/region <UID|name>`
- `/wishlist <UID|name>`
- `/workshop <UID|name>`
- `/duo <UID|name>`

The bot registers the command menu with Telegram at startup. The Telegram bot's actual username must be set separately through `@BotFather`; this code sets its display text and command list, not its `@username`.

## Deploy to Render Web Service

1. Upload these files to a private GitHub repository.
2. In Render, create a Web Service connected to that repository (or use the included `render.yaml` as a Blueprint).
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. Health check path: `/health`
6. Add environment variables in Render:
   - `BOT_TOKEN` — token from BotFather
   - `API_UID` — API account UID supplied by your API provider
   - `API_PASSWORD` — API password supplied by your API provider
   - `API_BASE_URL` — default is already set in `render.yaml`
7. Deploy. Test the website root and `/health`, then test `/start` and `/player <UID>` in Telegram.
8. After confirming Render works, stop the Railway bot so two polling instances do not conflict.

## Security and limitations

- Credentials are intentionally not hardcoded in source files. Set them as Render environment variables.
- Do not publish the API UID/password or Telegram token in a public repository or screenshots.
- The routes and parameter format reflect the details supplied by the user. The live API may enforce a different response schema, parameter requirement, or endpoint casing; verify results in Render Logs and adjust if the provider's API differs.
- The bot currently formats returned JSON generically. It does not claim to verify or bypass any game ban.
- Keep one running instance for Telegram polling. Render's free Web Service can spin down; check current Render plan limits if continuous uptime is required.
