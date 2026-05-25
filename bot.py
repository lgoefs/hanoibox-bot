import os, logging
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from database import Database
from ai_handler import AIHandler
from gym_info import find_faq_answer, get_gym_context, SCHEDULE, PRICING, GYM_NAME

logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_CHAT_ID = os.getenv('OWNER_CHAT_ID', '')
db = Database()
ai = AIHandler()

def is_owner(update): return str(update.effective_chat.id) == OWNER_CHAT_ID

async def notify_owner(context, msg):
    if OWNER_CHAT_ID:
        await context.bot.send_message(chat_id=int(OWNER_CHAT_ID), text=msg)

async def cmd_start(update, context):
    await update.message.reply_text(
        "HanoiBox Admin Bot\n\n"
        "MEMBER COMMANDS\n"
        "check in [name] - check in a member\n"
        "new member - add a new member\n"
        "log payment - record a payment\n"
        "members - list active members\n"
        "expiring - expiry alerts\n"
        "summary - today's summary\n\n"
        "GYM INFO\n"
        "/info - gym info, schedule, pricing\n"
        "/schedule - class timetable\n"
        "/prices - membership pricing\n"
        "/faq - common questions\n\n"
        "Send a photo of a receipt or ID card and I will read it.\n"
        "Type /myid to get your Telegram chat ID.\n"
        "Type /test to run a full system check.")

async def cmd_myid(update, context):
    await update.message.reply_text(f"Your Chat ID: {update.effective_chat.id}")

async def cmd_info(update, context):
    from gym_info import GYM_ADDRESS, GYM_PHONE, GYM_FACEBOOK
    msg = (f"{GYM_NAME} - Gym Info\n\n"
           f"Address: {GYM_ADDRESS or 'Ask admin to update in gym_info.py'}\n"
           f"Phone: {GYM_PHONE or 'Ask admin to update'}\n"
           f"Facebook: {GYM_FACEBOOK or 'Ask admin to update'}\n\n"
           f"CLASS SCHEDULE\n{SCHEDULE.strip()}\n\n"
           f"PRICING\n{PRICING.strip()}\n\n"
           "Type /faq for more or ask me anything!")
    await update.message.reply_text(msg)

async def cmd_schedule(update, context):
    await update.message.reply_text("Class Schedule:\n" + SCHEDULE.strip())

async def cmd_prices(update, context):
    await update.message.reply_text("Membership Pricing:\n" + PRICING.strip())

async def cmd_faq(update, context):
    await update.message.reply_text(
        "Common Questions - just type:\n\n"
        "location / address / parking\n"
        "schedule / classes / timetable\n"
        "price / cost / membership / fee\n"
        "gear / equipment\n"
        "beginner / first time\n"
        "trial\n"
        "coach / trainer\n"
        "kids / women\n\n"
        "Or ask in plain English - e.g. 'how much does it cost?' or 'when are the morning classes?'")

async def cmd_test(update, context):
    from gym_info import GYM_NAME, GYM_ADDRESS, GYM_PHONE, GYM_EMAIL, GYM_FACEBOOK, find_faq_answer
    lines = ["\U0001f94a BOT TEST REPORT\n"]

    lines.append("── GYM INFO ──")
    lines.append(f"Name: {GYM_NAME or '❌ missing'}")
    lines.append(f"Address: {GYM_ADDRESS or '❌ missing'}")
    lines.append(f"Phone: {GYM_PHONE or '❌ missing'}")
    lines.append(f"Email: {GYM_EMAIL or '❌ missing'}")
    lines.append(f"Facebook: {GYM_FACEBOOK or '❌ missing'}")

    lines.append("\n── ADMIN ──")
    lines.append(f"Owner ID set: {'✅ ' + OWNER_CHAT_ID if OWNER_CHAT_ID else '❌ not set'}")
    lines.append(f"Your ID: {update.effective_chat.id}")
    lines.append(f"Is owner: {'✅ yes' if is_owner(update) else '❌ no'}")

    lines.append("\n── MEMBERS ──")
    try:
        members = db.get_active_members()
        att = db.get_today_attendance()
        exp = db.get_expiring_members(7)
        rev = db.get_monthly_revenue()
        lines.append(f"Active members: {len(members)}")
        lines.append(f"Check-ins today: {len(att)}")
        lines.append(f"Expiring in 7 days: {len(exp)}")
        lines.append(f"Monthly revenue: ${round((rev.get('total_usd') or 0), 2)}")
    except Exception as e:
        lines.append(f"DB error: {e}")

    lines.append("\n── FAQ ──")
    lines.append(f"Location FAQ: {'✅' if find_faq_answer('location') else '❌'}")
    lines.append(f"Price FAQ: {'✅' if find_faq_answer('price') else '❌'}")
    lines.append(f"Schedule FAQ: {'✅' if find_faq_answer('schedule') else '❌'}")

    lines.append("\n✅ Test complete")
    await update.message.reply_text("\n".join(lines))

async def cmd_summary(update, context):
    ctx = db.get_context(); att = db.get_today_attendance(); rev = db.get_monthly_revenue(); exp = db.get_expiring_members(7)
    summary = ai.generate_daily_summary({'date': date.today().isoformat(), 'active_members': ctx['active_members'],
        'today_checkins': len(att), 'monthly_revenue_usd': round((rev.get('total_usd') or 0), 2),
        'expiring_soon': [f"{m['name']} exp {m['expiry_date']}" for m in exp]})
    await update.message.reply_text(summary)

async def handle_checkin(update, context, text):
    name = text.lower().replace('check in','').replace('checkin','').replace('check-in','').strip()
    if not name:
        await update.message.reply_text("Who? e.g. check in james"); return
    members = db.find_member(name)
    if not members:
        await update.message.reply_text(f"No member matching {name}"); return
    if len(members) > 1:
        kb = [[InlineKeyboardButton(m['name'], callback_data=f"checkin_{m['id']}")] for m in members]
        await update.message.reply_text("Multiple matches:", reply_markup=InlineKeyboardMarkup(kb)); return
    m = members[0]; stype = 'private' if 'private' in (m.get('plan') or '') else 'group'
    db.log_attendance(m['id'], m['name'], stype)
    msg = f"Checked in: {m['name']} at {datetime.now().strftime('%I:%M %p')}"
    if m.get('expiry_date'):
        days = (date.fromisoformat(m['expiry_date']) - date.today()).days
        if days < 0: msg += f" - EXPIRED {abs(days)} days ago - needs renewal!"
        elif days <= 7: msg += f" - Expires in {days} days"
    await update.message.reply_text(msg)

async def handle_member_list(update, context):
    members = db.get_active_members()
    if not members: await update.message.reply_text("No active members."); return
    lines = [f"Active Members ({len(members)})\n"]
    for m in members:
        lines.append(f"- {m['name']} | {(m.get('plan') or '').replace('_',' ')} | exp: {m.get('expiry_date','?')}")
    await update.message.reply_text('\n'.join(lines))

async def handle_expiring(update, context):
    exp = db.get_expiring_members(7); expired = db.get_expired_members()
    if not exp and not expired: await update.message.reply_text("No expiry alerts."); return
    lines = ["Expiry Alerts\n"]
    if exp:
        lines.append("Expiring soon:")
        for m in exp:
            d = (date.fromisoformat(m['expiry_date']) - date.today()).days
            lines.append(f"- {m['name']} | {d} days ({m['expiry_date']})")
    if expired:
        lines.append("\nAlready expired:")
        for m in expired: lines.append(f"- {m['name']} | {m['expiry_date']}")
    await update.message.reply_text('\n'.join(lines))

async def handle_new_member_prompt(update, context):
    context.user_data['flow'] = 'new_member'; context.user_data['new_member'] = {}
    kb = [[InlineKeyboardButton("Group 3-Month", callback_data="plan_group_3month")],
          [InlineKeyboardButton("Private 10-Pack", callback_data="plan_private_10pack")],
          [InlineKeyboardButton("Private Monthly", callback_data="plan_private_monthly")],
          [InlineKeyboardButton("Drop-in / Trial", callback_data="plan_dropin")]]
    await update.message.reply_text("New Member - Select plan:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_payment_prompt(update, context):
    context.user_data['flow'] = 'payment'
    await update.message.reply_text("Log Payment\nFormat: [Name] [Amount VND] [cash/transfer]\nExample: James 3600000 cash\n\nOr send a receipt photo.")

async def handle_payment_text(update, context, text):
    parts = text.strip().split(); amount = None; name_parts = []; method = 'cash'
    for i, p in enumerate(parts):
        try:
            amount = int(p.replace(',','').replace('.',''))
            name_parts = parts[:i]
            if i+1 < len(parts): method = parts[i+1].lower()
            break
        except ValueError: continue
    if not amount or not name_parts:
        await update.message.reply_text("Try: James 3600000 cash"); return
    name = ' '.join(name_parts).title(); usd = round(amount/25000, 2)
    pid = db.log_payment(name, amount, 'manual', method)
    await update.message.reply_text(f"Payment logged: {name} - {amount:,} VND (~${usd}) - pending confirmation")
    kb = [[InlineKeyboardButton("Confirm", callback_data=f"confirm_payment_{pid}"),
           InlineKeyboardButton("Reject", callback_data=f"reject_payment_{pid}")]]
    if OWNER_CHAT_ID:
        await context.bot.send_message(int(OWNER_CHAT_ID),
            f"Payment - Confirm?\n{name} - {amount:,} VND (~${usd}) - {method}",
            reply_markup=InlineKeyboardMarkup(kb))

async def handle_photo(update, context):
    await update.message.reply_text("Reading photo...")
    photo = update.message.photo[-1]; f = await context.bot.get_file(photo.file_id)
    img = bytes(await f.download_as_bytearray())
    flow = context.user_data.get('flow', '')
    if flow == 'new_member':
        info = ai.read_member_id(img)
        context.user_data['new_member'].update({'name': info.get('name',''), 'phone': info.get('phone','')})
        await update.message.reply_text(f"Read: {info.get('name','')} / {info.get('phone','')}\nType name to confirm or correct.")
    else:
        info = ai.read_payment_receipt(img)
        avnd = info.get('amount_vnd'); name = info.get('member_name','Unknown'); method = info.get('method','cash')
        msg = f"Receipt: {name} - {f'{avnd:,} VND' if avnd else 'amount unclear'} - {method}"
        if avnd and name != 'Unknown':
            pid = db.log_payment(name, avnd, 'manual', method, notes=info.get('notes',''))
            msg += f"\nLogged #{pid}, pending confirmation."
            kb = [[InlineKeyboardButton("Confirm", callback_data=f"confirm_payment_{pid}"),
                   InlineKeyboardButton("Reject", callback_data=f"reject_payment_{pid}")]]
            if OWNER_CHAT_ID:
                await context.bot.send_message(int(OWNER_CHAT_ID), msg, reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text(msg)

async def handle_callback(update, context):
    q = update.callback_query; await q.answer(); d = q.data
    if d.startswith('checkin_'):
        m = db.get_member(int(d.split('_')[1]))
        if m:
            stype = 'private' if 'private' in (m.get('plan') or '') else 'group'
            db.log_attendance(m['id'], m['name'], stype)
            await q.edit_message_text(f"Checked in: {m['name']} at {datetime.now().strftime('%I:%M %p')}")
    elif d.startswith('plan_'):
        plan = d.replace('plan_',''); context.user_data['new_member']['plan'] = plan
        context.user_data['flow'] = 'new_member_name'
        await q.edit_message_text("Plan selected. Now type the member's full name:")
    elif d.startswith('confirm_payment_'):
        db.confirm_payment(int(d.split('_')[-1])); await q.edit_message_text("Payment confirmed.")
    elif d.startswith('reject_payment_'):
        await q.edit_message_text("Payment rejected.")

async def handle_message(update, context):
    text = update.message.text or ''; lower = text.lower().strip()
    sender = update.effective_user.first_name or 'Admin'; flow = context.user_data.get('flow','')
    db.log_message(sender, text[:200])

    if flow == 'new_member_name':
        context.user_data['new_member']['name'] = text.strip().title()
        context.user_data['flow'] = 'new_member_phone'
        await update.message.reply_text(f"Name: {text.strip().title()}\nPhone? (or skip)"); return
    if flow == 'new_member_phone':
        phone = '' if lower=='skip' else text.strip()
        nm = context.user_data['new_member']; plan = nm.get('plan','group_3month')
        mid = db.add_member(nm['name'], phone, plan=plan)
        context.user_data['flow'] = ''
        plans = {'group_3month':'Group 3-Month','private_10pack':'Private 10-Pack','private_monthly':'Private Monthly','dropin':'Drop-in'}
        await update.message.reply_text(f"Added: {nm['name']} - {plans.get(plan,plan)} (ID #{mid})")
        await notify_owner(context, f"New member: {nm['name']} - {plans.get(plan,plan)} added by {sender}"); return
    if flow == 'payment':
        context.user_data['flow'] = ''; await handle_payment_text(update, context, text); return

    if any(x in lower for x in ['check in','checkin','check-in']): await handle_checkin(update, context, lower)
    elif any(x in lower for x in ['new member','add member']): await handle_new_member_prompt(update, context)
    elif any(x in lower for x in ['log payment','payment','paid']): await handle_payment_prompt(update, context)
    elif any(x in lower for x in ['members','member list']): await handle_member_list(update, context)
    elif any(x in lower for x in ['expiring','expire']): await handle_expiring(update, context)
    elif any(x in lower for x in ['summary','report','today']): await cmd_summary(update, context)
    else:
        faq_answer = find_faq_answer(lower)
        if faq_answer:
            await update.message.reply_text(faq_answer)
        else:
            gym_ctx = get_gym_context()
            db_ctx = db.get_context()
            combined = {**db_ctx, **gym_ctx}
            r = ai.interpret_message(text, combined)
            await update.message.reply_text(r)

async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand('start',    'Show help & all commands'),
        BotCommand('test',     'System check - test everything'),
        BotCommand('info',     'Gym info, address & schedule'),
        BotCommand('schedule', 'Class timetable'),
        BotCommand('prices',   'Membership pricing'),
        BotCommand('faq',      'Common questions'),
        BotCommand('summary',  "Today's report"),
        BotCommand('myid',     'Your Telegram chat ID'),
    ])

def build_app():
    from database import init_db; init_db()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('myid', cmd_myid))
    app.add_handler(CommandHandler('summary', cmd_summary))
    app.add_handler(CommandHandler('info', cmd_info))
    app.add_handler(CommandHandler('faq', cmd_faq))
    app.add_handler(CommandHandler('schedule', cmd_schedule))
    app.add_handler(CommandHandler('prices', cmd_prices))
    app.add_handler(CommandHandler('test', cmd_test))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    return app
