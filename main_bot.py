"""Small, configurable Discord moderation bot using discord.py 2.x.

Configure DISCORD_TOKEN in the environment (never commit your bot token).
Optional: MOD_LOG_CHANNEL_ID sets the default moderation log channel.
"""

from __future__ import annotations

import os
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # Enable Server Members Intent in the Developer Portal.
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)
log_channel_id = int(os.getenv("MOD_LOG_CHANNEL_ID", "0") or 0)


def bot_can(guild: discord.Guild, permission: str) -> bool:
    member = guild.me
    return bool(member and getattr(member.guild_permissions, permission, False))


async def post_log(guild: discord.Guild, text: str) -> None:
    if log_channel_id:
        channel = guild.get_channel(log_channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(text)
            except discord.Forbidden:
                pass


async def moderation_ready(interaction: discord.Interaction, permission: str) -> bool:
    if interaction.guild is None:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return False
    if not getattr(interaction.user.guild_permissions, permission, False):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return False
    if not bot_can(interaction.guild, permission):
        await interaction.response.send_message(f"I need the **{permission.replace('_', ' ')}** permission.", ephemeral=True)
        return False
    return True


def target_is_actionable(interaction: discord.Interaction, member: discord.Member) -> bool:
    guild = interaction.guild
    if guild is None or member.id == interaction.user.id or member.id == bot.user.id:
        return False
    actor = interaction.user
    if isinstance(actor, discord.Member) and actor.id != guild.owner_id:
        if member.top_role >= actor.top_role:
            return False
    bot_member = guild.me
    return bool(bot_member and member.top_role < bot_member.top_role)


async def validate_target(interaction: discord.Interaction, member: discord.Member) -> bool:
    if not target_is_actionable(interaction, member):
        await interaction.response.send_message(
            "That member is yourself, the bot, or has a role at or above your/bot's highest role.",
            ephemeral=True,
        )
        return False
    return True


@bot.event
async def on_ready() -> None:
    print(f"Ready as {bot.user} (ID: {bot.user.id})")


@bot.tree.command(name="setmodlog", description="Set the channel for moderation action logs")
@app_commands.checks.has_permissions(manage_guild=True)
async def set_modlog(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    global log_channel_id
    if not bot_can(interaction.guild, "manage_channels"):
        await interaction.response.send_message("I need Manage Channels to use that log channel.", ephemeral=True)
        return
    log_channel_id = channel.id
    await interaction.response.send_message(f"Moderation logs will be sent to {channel.mention}.", ephemeral=True)


@bot.tree.command(name="warn", description="Warn a member and record the reason")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
    if not await moderation_ready(interaction, "moderate_members") or not await validate_target(interaction, member):
        return
    await interaction.response.send_message(f"⚠️ {member.mention} was warned. Reason: {reason}")
    await post_log(interaction.guild, f"⚠️ **Warn** · {member.mention} · by {interaction.user.mention}\nReason: {reason}")


@bot.tree.command(name="timeout", description="Timeout a member for up to 28 days")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(minutes="Duration in minutes (1–40320)")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320], reason: str) -> None:
    if not await moderation_ready(interaction, "moderate_members") or not await validate_target(interaction, member):
        return
    try:
        await member.timeout(timedelta(minutes=minutes), reason=f"{interaction.user}: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("Discord denied the timeout. Check my role position and permissions.", ephemeral=True)
        return
    await interaction.response.send_message(f"⏳ {member.mention} timed out for {minutes} minute(s). Reason: {reason}")
    await post_log(interaction.guild, f"⏳ **Timeout ({minutes}m)** · {member.mention} · by {interaction.user.mention}\nReason: {reason}")


@bot.tree.command(name="untimeout", description="Remove a member's timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
    if not await moderation_ready(interaction, "moderate_members") or not await validate_target(interaction, member):
        return
    try:
        await member.timeout(None, reason=f"{interaction.user}: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("Discord denied the action. Check my role position and permissions.", ephemeral=True)
        return
    await interaction.response.send_message(f"✅ Timeout removed for {member.mention}.")
    await post_log(interaction.guild, f"✅ **Untimeout** · {member.mention} · by {interaction.user.mention}\nReason: {reason}")


@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
    if not await moderation_ready(interaction, "kick_members") or not await validate_target(interaction, member):
        return
    try:
        await member.kick(reason=f"{interaction.user}: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("Discord denied the kick. Check my role position and permissions.", ephemeral=True)
        return
    await interaction.response.send_message(f"👢 **{member}** was kicked. Reason: {reason}")
    await post_log(interaction.guild, f"👢 **Kick** · {member} · by {interaction.user.mention}\nReason: {reason}")


@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str, delete_message_days: app_commands.Range[int, 0, 7] = 0) -> None:
    if not await moderation_ready(interaction, "ban_members") or not await validate_target(interaction, member):
        return
    try:
        await member.ban(reason=f"{interaction.user}: {reason}", delete_message_seconds=delete_message_days * 86400)
    except discord.Forbidden:
        await interaction.response.send_message("Discord denied the ban. Check my role position and permissions.", ephemeral=True)
        return
    await interaction.response.send_message(f"🔨 **{member}** was banned. Reason: {reason}")
    await post_log(interaction.guild, f"🔨 **Ban** · {member} · by {interaction.user.mention}\nReason: {reason}")


@bot.tree.command(name="purge", description="Delete up to 100 recent messages in this channel")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
    if not await moderation_ready(interaction, "manage_messages"):
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use this command in a text channel.", ephemeral=True)
        return
    try:
        deleted = await interaction.channel.purge(limit=amount)
    except discord.Forbidden:
        await interaction.response.send_message("I need Manage Messages in this channel.", ephemeral=True)
        return
    await interaction.response.send_message(f"🧹 Deleted {len(deleted)} message(s).", ephemeral=True)
    await post_log(interaction.guild, f"🧹 **Purge** · {len(deleted)} message(s) in {interaction.channel.mention} · by {interaction.user.mention}")


@bot.tree.command(name="slowmode", description="Set this channel's slowmode (0 disables it)")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.describe(seconds="Seconds between messages (0–21600)")
async def slowmode(interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]) -> None:
    if not await moderation_ready(interaction, "manage_channels"):
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use this command in a text channel.", ephemeral=True)
        return
    try:
        await interaction.channel.edit(slowmode_delay=seconds, reason=f"Set by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("I need Manage Channels in this channel.", ephemeral=True)
        return
    await interaction.response.send_message(f"🐢 Slowmode set to {seconds} second(s).")
    await post_log(interaction.guild, f"🐢 **Slowmode** · {seconds}s in {interaction.channel.mention} · by {interaction.user.mention}")


@bot.tree.command(name="lock", description="Prevent @everyone from sending messages here")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction) -> None:
    if not await moderation_ready(interaction, "manage_channels"):
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use this command in a text channel.", ephemeral=True)
        return
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    try:
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Locked by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("I need Manage Channels in this channel.", ephemeral=True)
        return
    await interaction.response.send_message("🔒 Channel locked for @everyone.")
    await post_log(interaction.guild, f"🔒 **Lock** · {interaction.channel.mention} · by {interaction.user.mention}")


@bot.tree.command(name="unlock", description="Allow @everyone to send messages here again")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction) -> None:
    if not await moderation_ready(interaction, "manage_channels"):
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use this command in a text channel.", ephemeral=True)
        return
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    try:
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Unlocked by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("I need Manage Channels in this channel.", ephemeral=True)
        return
    await interaction.response.send_message("🔓 @everyone can send messages again.")
    await post_log(interaction.guild, f"🔓 **Unlock** · {interaction.channel.mention} · by {interaction.user.mention}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        message = "You don't have the server permission required for this command."
    else:
        message = "The command failed. Check the bot's permissions and role position."
        print(f"Slash command error: {error!r}")
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Set DISCORD_TOKEN in your environment before starting the bot.")
    bot.run(token)


if __name__ == "__main__":
    main()
