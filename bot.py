# ── SETTINGS ─────────────────────────────────────────────────────
BOT_TOKEN          = "YOUR-BOT-TOKEN"
THRESHOLD          = 0.5
MONITORED_CHANNELS = []
TIMEOUT_MINUTES    = 10
LOG_CHANNEL_NAME   = "mod-logs"
# ─────────────────────────────────────────────────────────────────

if BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
    print("⛔ Paste your bot token into BOT_TOKEN first!")
    raise SystemExit()

!pip install discord.py nest_asyncio -q

import discord
from discord.ext import commands
from datetime import timedelta
import nest_asyncio
nest_asyncio.apply()   # ← this is the fix for Colab's event loop conflict

violations  = {}
log_channel = None

intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True
bot = commands.Bot(command_prefix="!", intents=intents)

WARNINGS = [
    "⚠️ **Warning #{count}:** Your message was removed for cyberbullying. Please be respectful 💛",
    "🛡️ **Warning #{count}:** Harmful content is not allowed here. Keep this a safe space!",
    "❌ **Warning #{count}:** Message flagged and removed. One more violation = timeout.",
]

async def send_log(guild, msg):
    global log_channel
    if not LOG_CHANNEL_NAME: return
    if log_channel is None:
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel:
        try: await log_channel.send(msg)
        except: pass

@bot.event
async def on_ready():
    print(f"✅ Bot online as: {bot.user}")
    print(f"📡 Servers: {[g.name for g in bot.guilds]}")
    print(f"🎯 Threshold: {THRESHOLD} | Timeout: {TIMEOUT_MINUTES}min after 3 violations")
    print(f"📺 Monitoring: {'ALL channels' if not MONITORED_CHANNELS else MONITORED_CHANNELS}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="for cyberbullying 🛡️")
    )

@bot.event
async def on_message(message):
    if message.author.bot: return
    if len(message.content.strip()) < 3:
        await bot.process_commands(message); return
    if MONITORED_CHANNELS and message.channel.name not in MONITORED_CHANNELS:
        await bot.process_commands(message); return

    result = predict(message.content, threshold=THRESHOLD)

    if result['is_cyberbullying']:
        uid   = message.author.id
        count = violations.get(uid, 0) + 1
        violations[uid] = count

        # Delete message
        try:
            await message.delete()
            print(f"🗑️  Deleted | {message.author} | violation #{count} | {result['cyberbullying_prob']}% | '{message.content[:60]}'")
        except discord.Forbidden:
            print(f"⚠️  No 'Manage Messages' permission in #{message.channel.name}")

        # Warning text
        warn = WARNINGS[(count-1) % len(WARNINGS)].replace("{count}", str(count))
        warn += f"\n*(Confidence: {result['cyberbullying_prob']}% | Violation {count}/3)*"

        # DM the user, fall back to channel
        try:
            await message.author.send(warn)
        except:
            try:
                await message.channel.send(f"{message.author.mention} {warn}", delete_after=15)
            except: pass

        # Log to mod-logs
        await send_log(message.guild,
            f"🚨 **Cyberbullying detected**\n"
            f"👤 {message.author} (`{uid}`)\n"
            f"📺 {message.channel.mention}\n"
            f"💬 ```{message.content[:300]}```\n"
            f"🎯 Confidence: {result['cyberbullying_prob']}% | Violation #{count}"
        )

        # Timeout after 3 violations
        if count >= 3:
            try:
                until = discord.utils.utcnow() + timedelta(minutes=TIMEOUT_MINUTES)
                await message.author.timeout(until, reason=f"Cyberbullying — {count} violations")
                await message.channel.send(
                    f"⏰ {message.author.mention} timed out for **{TIMEOUT_MINUTES} min** (3+ violations).",
                    delete_after=20
                )
                violations[uid] = 0
                print(f"⏰ Timed out {message.author} for {TIMEOUT_MINUTES} minutes")
                await send_log(message.guild, f"⏰ **Timeout** | {message.author} | {TIMEOUT_MINUTES} min")
            except discord.Forbidden:
                print(f"⚠️  No 'Moderate Members' permission to timeout {message.author}")

    await bot.process_commands(message)


@bot.command(name="check")
async def cmd_check(ctx, *, text: str):
    """!check <text> — test if a message is cyberbullying"""
    r  = predict(text, threshold=THRESHOLD)
    em = discord.Embed(
        title="🛡️ Cyberbullying Check",
        color=discord.Color.red() if r['is_cyberbullying'] else discord.Color.green()
    )
    em.add_field(name="Message",     value=f"```{text[:400]}```",            inline=False)
    em.add_field(name="Result",      value="🔴 CYBERBULLYING" if r['is_cyberbullying'] else "🟢 CLEAN", inline=True)
    em.add_field(name="Bully Score", value=f"{r['cyberbullying_prob']}%",    inline=True)
    em.add_field(name="Clean Score", value=f"{r['clean_prob']}%",            inline=True)
    await ctx.send(embed=em)


@bot.command(name="violations")
@commands.has_permissions(manage_messages=True)
async def cmd_violations(ctx):
    """!violations — show violators (mods only)"""
    active = {uid: c for uid, c in violations.items() if c > 0}
    if not active:
        await ctx.send("📊 No violations yet — great community! 🎉"); return
    em = discord.Embed(title="📊 Violations", color=discord.Color.orange())
    for uid, c in sorted(active.items(), key=lambda x: -x[1])[:10]:
        user = bot.get_user(uid)
        em.add_field(name=str(user) if user else f"ID:{uid}", value=f"{'🟥'*min(c,5)} {c} violation(s)", inline=False)
    await ctx.send(embed=em)


@bot.command(name="reset")
@commands.has_permissions(manage_messages=True)
async def cmd_reset(ctx, member: discord.Member):
    """!reset @user — reset violation count (mods only)"""
    old = violations.get(member.id, 0)
    violations[member.id] = 0
    await ctx.send(f"✅ Reset {member.mention}'s violations: {old} → 0")


@bot.command(name="sensitivity")
@commands.has_permissions(manage_guild=True)
async def cmd_sensitivity(ctx, value: float):
    """!sensitivity 0.6 — change threshold (admins only)"""
    global THRESHOLD
    if not 0.1 <= value <= 1.0:
        await ctx.send("❌ Use a value between 0.1 and 1.0"); return
    THRESHOLD = value
    label = "very sensitive" if value < 0.4 else "balanced ✅" if value < 0.7 else "strict"
    await ctx.send(f"✅ Threshold set to **{value}** ({label})")


@bot.command(name="botstatus")
async def cmd_status(ctx):
    """!botstatus — show bot settings"""
    em = discord.Embed(title="🤖 Bot Status", color=discord.Color.blue())
    em.add_field(name="Threshold",    value=f"{THRESHOLD} ({THRESHOLD*100:.0f}%)", inline=True)
    em.add_field(name="Monitoring",   value="All" if not MONITORED_CHANNELS else str(MONITORED_CHANNELS), inline=True)
    em.add_field(name="Timeout",      value=f"{TIMEOUT_MINUTES} min",              inline=True)
    em.add_field(name="Total flags",  value=str(sum(violations.values())),         inline=True)
    em.add_field(name="Latency",      value=f"{round(bot.latency*1000)}ms",        inline=True)
    await ctx.send(embed=em)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission for this command.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument. Try: `!{ctx.command.name} {ctx.command.signature}`", delete_after=8)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found. Mention them with @name.", delete_after=5)


# ── Run (Colab-compatible) ────────────────────────────────────────
print("🚀 Starting bot...")
import asyncio
asyncio.get_event_loop().run_until_complete(bot.start(BOT_TOKEN))
