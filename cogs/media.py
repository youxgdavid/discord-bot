import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import asyncio
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
import tempfile
import time

class Media(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="vidtogif", description="Convert a video to a GIF (auto-compressed to <8MB)")
    @app_commands.describe(video="The video file to convert", fps="Frame rate (default: 10)", scale="Resize factor (0.1 to 1.0, default: auto)", start_time="Trim start (seconds, default: 0)", duration="Trim duration (seconds, default: full)")
    async def vidtogif(self, interaction: discord.Interaction, video: discord.Attachment, fps: int = 10, scale: float = None, start_time: float = 0, duration: float = None):
        if not video.content_type or not video.content_type.startswith('video/'):
            return await interaction.response.send_message("❌ Please attach a valid video file.", ephemeral=True)

        MAX_SIZE = 8 * 1024 * 1024
        await interaction.response.defer(thinking=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, video.filename)
            output_path = os.path.join(tmpdir, "output.gif")

            try:
                await video.save(input_path)
                
                # Use subclip if duration is specified
                full_clip = VideoFileClip(input_path)
                end_time = start_time + duration if duration else full_clip.duration
                clip = full_clip.subclip(start_time, min(end_time, full_clip.duration))
                
                actual_duration = clip.duration
                if actual_duration > 60:
                    return await interaction.followup.send("❌ Video segment is too long (max 60s for GIF). Trim it using 'duration'.")

                # Heuristic: Target bit budget per second
                # 8MB = 64Mbits. 60s = ~1Mbit/s. 
                # GIF overhead is huge. We aim for ~0.8MB per 10s.
                if scale is None:
                    if actual_duration > 30: scale = 0.2
                    elif actual_duration > 15: scale = 0.4
                    elif actual_duration > 5: scale = 0.6
                    else: scale = 0.8

                final_clip = clip.resize(scale).set_fps(min(fps, 12))
                
                # Write to GIF using ffmpeg for best compression
                # 'opt' can be 'optimizeplus', 'nq' (neuquant)
                final_clip.write_gif(output_path, program='ffmpeg', opt='nq', fuzz=10)
                
                size = os.path.getsize(output_path)
                
                # If it's too big, we retry with much lower res/fps
                if size > MAX_SIZE:
                    print(f"GIF too large ({size/1024/1024:.2f}MB), retrying more aggressive compression...")
                    output_path = os.path.join(tmpdir, "output_tiny.gif")
                    final_clip.resize(0.5).set_fps(8).write_gif(output_path, program='ffmpeg', opt='nq', fuzz=20)
                    size = os.path.getsize(output_path)

                if size > MAX_SIZE:
                    return await interaction.followup.send(f"⚠️ GIF ({size/1024/1024:.2f}MB) still exceeds 8MB. Try a shorter segment or lower FPS.")

                with open(output_path, 'rb') as f:
                    file = discord.File(f, filename="converted.gif")
                    await interaction.followup.send(f"🎬 **Converted!**\n- Size: `{size/1024/1024:.2f}MB` / 8.0MB\n- Duration: `{actual_duration:.1f}s`", file=file)

                # Cleanup
                clip.close()
                full_clip.close()
                final_clip.close()

            except Exception as e:
                await interaction.followup.send(f"❌ Failed to convert video: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Media(bot))
