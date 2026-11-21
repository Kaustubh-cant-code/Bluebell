# Bluebell
# Private Server Moderation Bot

Discord slash command moderation bot built with `discord.py` 2.x.

## Commands

- `/warn member reason`
- `/timeout member minutes reason` (1–40,320 minutes)
- `/untimeout member reason`
- `/kick member reason`
- `/ban member reason delete_message_days` (0–7 days)
- `/purge amount` (1–100 messages in the current channel)
- `/slowmode seconds` (0 disables it)
- `/lock` and `/unlock` (manage @everyone's send permission in the current channel)
- `/setmodlog channel` (server managers can configure the log channel while the bot is running)

Each command checks the invoking user's Discord permission. Member actions also check role hierarchy. Configure a log channel with `/setmodlog`; setting `MOD_LOG_CHANNEL_ID` supplies a default on startup. The `/warn` command records and reports a warning but does not persist a warning history.

## Setup

1. Create an application and bot in the Discord Developer Portal. Invite it to your server with the `bot` and `applications.commands` scopes, granting only the moderation permissions you need: Moderate Members, Kick Members, Ban Members, Manage Messages, and Manage Channels.
2. Enable **Server Members Intent** in the bot's Developer Portal settings.
3. Install dependencies: `python3 -m pip install -r requirements.txt`
4. Set `DISCORD_TOKEN` in your shell. Optionally set `MOD_LOG_CHANNEL_ID` to a channel ID.
5. Start it with `python3 main_bot.py`.

Slash commands are registered globally by Discord after the bot starts; initial propagation can take a while. Keep the token private and out of source control.
