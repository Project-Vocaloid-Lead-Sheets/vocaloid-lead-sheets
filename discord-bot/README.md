# Discord Bot
We have discovered there is a need for a Discord bot which allows project maintainers to trigger workloads and surveil server status without manually opening Google Drive. To facilitate this, we create a Discord bot which gives maintainers levers to flip around.

## Setup
This bot currently runs using `docker compose`. Please ensure that docker is installed by following these instructions:

[Docker Compose Installation Instructions](https://docs.docker.com/compose/install/)

Make sure your `DISCORD_TOKEN` environment variable is set. Please contact a site administrator for access to a Discord Token (or make one yourself if you already know how).

To run the server, run the following command:

```bash
docker compose up --build --detach
```

To view logs as the Discord bot server is running, use the following command:

```bash
docker compose logs -f discord-bot
```

To stop the bot's execution, use the following command:

```bash
docker compose down
```
