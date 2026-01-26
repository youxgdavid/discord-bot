import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from typing import Optional
import json
import aiohttp
import os

AI_MOD_CONFIG_FILE = "ai_mod_config.json"
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
HF_MOD_MODEL = "unitary/toxic-bert"

def load_ai_mod_configs():
    if not os.path.exists(AI_MOD_CONFIG_FILE):
        return {}
    try:
        with open(AI_MOD_CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_ai_mod_configs(configs):
    with open(AI_MOD_CONFIG_FILE, 'w') as f:
        json.dump(configs, f, indent=2)

async def check_moderation(text: str) -> Optional[dict]:
    """Check text against Hugging Face Toxicity API (Free alternative to OpenAI)."""
    if not HUGGINGFACE_TOKEN:
        print("DEBUG: Moderation check failed - Missing HUGGINGFACE_TOKEN", flush=True)
        return None
    
    url = f"https://router.huggingface.co/hf-inference/models/{HF_MOD_MODEL}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
    payload = {"inputs": text}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    # HF returns a list of lists of dicts: [[{"label": "toxic", "score": 0.9}, ...]]
                    if not results or not isinstance(results, list):
                        return None
                    
                    scores = results[0] if isinstance(results[0], list) else results
                    flagged = False
                    categories = {}
                    
                    # Mapping HF labels to a similar structure as OpenAI for compatibility
                    for entry in scores:
                        label = entry["label"].lower()
                        score = entry["score"]
                        # Threshold for flagging (usually > 0.7 for high confidence)
                        is_flagged = score > 0.7
                        categories[label] = is_flagged
                        if is_flagged:
                            flagged = True
                    
                    return {"flagged": flagged, "categories": categories}
                elif resp.status == 503:
                    print(f"DEBUG: HF Model is loading (503). Moderation skipped.", flush=True)
                    return None
                else:
                    error_text = await resp.text()
                    print(f"DEBUG: Hugging Face API Error ({resp.status}): {error_text}", flush=True)
                    return None
    except Exception as e:
        print(f"DEBUG: Exception during HF moderation check: {e}", flush=True)
        return None

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

    ai_mod = app_commands.Group(name="ai_mod", description="AI-powered moderation settings")

    @ai_mod.command(name="toggle", description="Toggle AI moderation for this server")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ai_mod_toggle(self, interaction: discord.Interaction, enabled: bool):
        await interaction.response.defer(ephemeral=True)
        configs = load_ai_mod_configs()
        configs[str(interaction.guild.id)] = enabled
        save_ai_mod_configs(configs)
        status = "enabled" if enabled else "disabled"
        await interaction.followup.send(f"✅ AI Moderation has been **{status}** for this server.")

    @ai_mod.command(name="status", description="Check AI moderation status")
    @app_commands.guild_only()
    async def ai_mod_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        configs = load_ai_mod_configs()
        is_enabled = configs.get(str(interaction.guild.id), False)
        status = "enabled" if is_enabled else "disabled"
        
        embed = discord.Embed(title="🤖 AI Moderation Status (Free HF Mode)", color=discord.Color.blue() if is_enabled else discord.Color.greyple())
        embed.add_field(name="Status", value=f"Currently **{status}**")
        embed.add_field(name="HF Configured", value="✅ Yes" if HUGGINGFACE_TOKEN else "❌ No (Missing HF Token)")
        await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Early debug to see if listener is active and seeing content
        print(f"DEBUG: Message from {message.author} (Length: {len(message.content)})", flush=True)

        if message.author.bot or not message.guild:
            return
        
        configs = load_ai_mod_configs()
        guild_id_str = str(message.guild.id)
        if not configs.get(guild_id_str, False):
            # print(f"DEBUG: AI Mod not enabled for guild {guild_id_str}", flush=True)
            return

        # Skip moderation for users with manage_messages permission
        if message.author.guild_permissions.manage_messages:
            return

        print(f"DEBUG: AI SCANNING message from {message.author}: {message.content[:50]}", flush=True)
        result = await check_moderation(message.content)
        if result:
            print(f"DEBUG: Flagged status: {result.get('flagged')}", flush=True)
        else:
            print("DEBUG: AI Moderation check returned None (API issue?)", flush=True)

        if result and result.get("flagged"):
            categories = [cat for cat, val in result.get("categories", {}).items() if val]
            reason = f"AI Moderation Flagged: {', '.join(categories)}"
            
            try:
                if not message.channel.permissions_for(message.guild.me).manage_messages:
                    print(f"DEBUG: Cannot delete message - Missing 'Manage Messages' permission in {message.channel.name}")
                    return

                await message.delete()
                
                # Notify in channel
                embed = discord.Embed(
                    title="🛡️ AI Moderation Action",
                    description=f"Message from {message.author.mention} was removed.",
                    color=discord.Color.red(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Reason", value=reason)
                await message.channel.send(embed=embed, delete_after=10)
                
                # Log to DM (optional)
                try:
                    await message.author.send(f"⚠️ Your message in **{message.guild.name}** was removed because it triggered our AI moderation filters.\n**Reason:** {reason}")
                except:
                    pass
            except Exception as e:
                print(f"Error in AI moderation: {e}")

async def setup(bot: commands.Bot):
    print("DEBUG: Loading Moderation Cog", flush=True)
    await bot.add_cog(Moderation(bot))
