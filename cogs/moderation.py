import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from typing import Optional

def make_mod_embed(title, color, *, user, moderator, reason=None, extra_fields=None):
    """Build a consistent moderation embed UI."""
    embed = discord.Embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
    try:
        embed.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass
    embed.add_field(name="Member", value=f"{getattr(user, 'mention', str(user))} (`{user.id}`)", inline=False)
    embed.add_field(name="Moderator", value=f"{getattr(moderator, 'mention', str(moderator))}", inline=True)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
    if extra_fields:
        for name, value, inline in extra_fields:
            embed.add_field(name=name, value=value, inline=inline)
    return embed

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to ban", reason="Reason for the ban", delete_days="Delete message history (0-7 days)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban_member(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None, delete_days: app_commands.Range[int, 0, 7] = 0):
        if member.id == interaction.user.id:
            return await interaction.response.send_message("❌ You cannot ban yourself.", ephemeral=True)
        if interaction.guild.owner_id == member.id:
            return await interaction.response.send_message("❌ You cannot ban the server owner.", ephemeral=True)
        if interaction.user != interaction.guild.owner and interaction.user.top_role <= member.top_role:
            return await interaction.response.send_message("❌ You cannot ban a member with an equal or higher role.", ephemeral=True)
        if interaction.guild.me.top_role <= member.top_role:
            return await interaction.response.send_message("❌ I cannot ban that member due to role hierarchy.", ephemeral=True)

        dm_embed = make_mod_embed(title=f"You have been banned from {interaction.guild.name}", color=discord.Color.red(), user=member, moderator=interaction.user, reason=reason)
        try: await member.send(embed=dm_embed)
        except: pass

        try:
            await member.ban(reason=reason or f"Banned by {interaction.user}", delete_message_seconds=int(delete_days) * 86400)
            await interaction.response.send_message(embed=make_mod_embed(title="🔨 Member Banned", color=discord.Color.red(), user=member, moderator=interaction.user, reason=reason, extra_fields=[("Deleted Messages", f"{delete_days} days", True)]))
        except Exception as e:
            await interaction.response.send_message(f"❌ Ban failed: {e}", ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to kick", reason="Reason for the kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick_member(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        if member.id == interaction.user.id:
            return await interaction.response.send_message("❌ You cannot kick yourself.", ephemeral=True)
        if interaction.guild.owner_id == member.id:
            return await interaction.response.send_message("❌ You cannot kick the server owner.", ephemeral=True)
        if interaction.user != interaction.guild.owner and interaction.user.top_role <= member.top_role:
            return await interaction.response.send_message("❌ You cannot kick a member with an equal or higher role.", ephemeral=True)
        if interaction.guild.me.top_role <= member.top_role:
            return await interaction.response.send_message("❌ I cannot kick that member due to role hierarchy.", ephemeral=True)

        dm_embed = make_mod_embed(title=f"You have been kicked from {interaction.guild.name}", color=discord.Color.orange(), user=member, moderator=interaction.user, reason=reason)
        try: await member.send(embed=dm_embed)
        except: pass

        try:
            await member.kick(reason=reason or f"Kicked by {interaction.user}")
            await interaction.response.send_message(embed=make_mod_embed(title="Member Kicked", color=discord.Color.orange(), user=member, moderator=interaction.user, reason=reason))
        except Exception as e:
            await interaction.response.send_message(f"❌ Kick failed: {e}", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member for a duration (1-40320 minutes)")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to timeout", minutes="Duration in minutes (1-40320)", reason="Reason for timeout")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout_member(self, interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320], reason: Optional[str] = None):
        if member.id == interaction.user.id:
            return await interaction.response.send_message("❌ You cannot timeout yourself.", ephemeral=True)
        if interaction.guild.owner_id == member.id:
            return await interaction.response.send_message("❌ You cannot timeout the server owner.", ephemeral=True)
        if interaction.user != interaction.guild.owner and interaction.user.top_role <= member.top_role:
            return await interaction.response.send_message("❌ You cannot timeout a member with an equal or higher role.", ephemeral=True)
        if interaction.guild.me.top_role <= member.top_role:
            return await interaction.response.send_message("❌ I cannot timeout that member due to role hierarchy.", ephemeral=True)

        until = datetime.now(timezone.utc) + timedelta(minutes=int(minutes))
        dm_embed = make_mod_embed(title=f"You have been timed out in {interaction.guild.name}", color=discord.Color.blurple(), user=member, moderator=interaction.user, reason=reason, extra_fields=[("Duration", f"{int(minutes)} minute(s)", True)])
        try: await member.send(embed=dm_embed)
        except: pass

        try:
            await member.timeout(until, reason=reason or f"Timed out by {interaction.user}")
            await interaction.response.send_message(embed=make_mod_embed(title="Member Timed Out", color=discord.Color.blurple(), user=member, moderator=interaction.user, reason=reason, extra_fields=[("Duration", f"{int(minutes)} minute(s)", True)]))
        except Exception as e:
            await interaction.response.send_message(f"❌ Timeout failed: {e}", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.guild_only()
    @app_commands.describe(member="Member to remove timeout", reason="Reason for removing timeout")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout_member(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        if interaction.user != interaction.guild.owner and interaction.user.top_role <= member.top_role:
            return await interaction.response.send_message("❌ You cannot modify a member with an equal or higher role.", ephemeral=True)
        if interaction.guild.me.top_role <= member.top_role:
            return await interaction.response.send_message("❌ I cannot modify that member due to role hierarchy.", ephemeral=True)

        dm_embed = make_mod_embed(title=f"Your timeout has been lifted in {interaction.guild.name}", color=discord.Color.green(), user=member, moderator=interaction.user, reason=reason)
        try: await member.send(embed=dm_embed)
        except: pass

        try:
            await member.timeout(None, reason=reason or f"Timeout cleared by {interaction.user}")
            await interaction.response.send_message(embed=make_mod_embed(title="Timeout Lifted", color=discord.Color.green(), user=member, moderator=interaction.user, reason=reason))
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

    @app_commands.command(name="purge", description="Delete a number of messages from this channel")
    @app_commands.guild_only()
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f"✅ Deleted **{len(deleted)}** messages.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Purge failed: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
