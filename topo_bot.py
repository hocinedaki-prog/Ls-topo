#!/usr/bin/env python3
"""
بوت تلغرام للحسابات الهندسية والطبوغرافية
Telegram Bot for Engineering & Topography Calculations
"""

import math
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== States =====================
(
    MAIN_MENU, POLYGON_INPUT, AREA_SELECT, AREA_INPUT,
    COORDS_SELECT, COORDS_INPUT, SLOPE_INPUT,
    TRAVERSE_INPUT, COORD_CONVERT_INPUT
) = range(9)

# ===================== Keyboards =====================

def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📐 حساب المضلعات", callback_data="polygon")],
        [InlineKeyboardButton("📏 حساب المساحات", callback_data="areas")],
        [InlineKeyboardButton("📍 الإحداثيات والمسافات", callback_data="coords")],
        [InlineKeyboardButton("⛰️ حساب الميول", callback_data="slope")],
        [InlineKeyboardButton("🔄 تحويل الإحداثيات", callback_data="coord_convert")],
        [InlineKeyboardButton("📊 حساب الترافيرس", callback_data="traverse")],
    ]
    return InlineKeyboardMarkup(keyboard)

def area_keyboard():
    keyboard = [
        [InlineKeyboardButton("⬛ مربع", callback_data="area_square"),
         InlineKeyboardButton("▬ مستطيل", callback_data="area_rect")],
        [InlineKeyboardButton("🔺 مثلث", callback_data="area_triangle"),
         InlineKeyboardButton("⭕ دائرة", callback_data="area_circle")],
        [InlineKeyboardButton("🔷 شبه منحرف", callback_data="area_trap"),
         InlineKeyboardButton("◈ متوازي أضلاع", callback_data="area_para")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def coords_keyboard():
    keyboard = [
        [InlineKeyboardButton("📏 المسافة بين نقطتين", callback_data="coords_dist")],
        [InlineKeyboardButton("🧭 الزاوية الاتجاهية (Bearing)", callback_data="coords_bearing")],
        [InlineKeyboardButton("📍 نقطة من مسافة وزاوية", callback_data="coords_point")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard(back_target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=back_target)]])

# ===================== Helpers =====================

def dms_to_dd(d, m, s):
    """Degrees Minutes Seconds → Decimal Degrees"""
    return d + m/60 + s/3600

def dd_to_dms(dd):
    """Decimal Degrees → Degrees Minutes Seconds"""
    d = int(dd)
    m = int((dd - d) * 60)
    s = ((dd - d) * 60 - m) * 60
    return d, m, s

def bearing_to_azimuth(bearing_str):
    """N45E → 45, S45W → 225, etc."""
    bearing_str = bearing_str.upper().strip()
    if bearing_str[0] == 'N' and bearing_str[-1] == 'E':
        return float(bearing_str[1:-1])
    elif bearing_str[0] == 'N' and bearing_str[-1] == 'W':
        return 360 - float(bearing_str[1:-1])
    elif bearing_str[0] == 'S' and bearing_str[-1] == 'E':
        return 180 - float(bearing_str[1:-1])
    elif bearing_str[0] == 'S' and bearing_str[-1] == 'W':
        return 180 + float(bearing_str[1:-1])
    return float(bearing_str)

def polygon_area_centroid(points):
    """Shoelace formula for area and centroid"""
    n = len(points)
    area = 0
    cx = cy = 0
    for i in range(n):
        j = (i + 1) % n
        cross = points[i][0] * points[j][1] - points[j][0] * points[i][1]
        area += cross
        cx += (points[i][0] + points[j][0]) * cross
        cy += (points[i][1] + points[j][1]) * cross
    area = abs(area) / 2
    if area == 0:
        return area, 0, 0
    cx = cx / (6 * area)
    cy = cy / (6 * area)
    if area < 0:
        cx, cy = -cx, -cy
    return area, abs(cx), abs(cy)

def perimeter(points):
    n = len(points)
    p = 0
    for i in range(n):
        j = (i + 1) % n
        dx = points[j][0] - points[i][0]
        dy = points[j][1] - points[i][1]
        p += math.sqrt(dx**2 + dy**2)
    return p

# ===================== Handlers =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = (
        "🌍 *مرحباً بك في بوت الحسابات الهندسية والطبوغرافية*\n\n"
        "يمكنني مساعدتك في:\n"
        "• حساب مساحات ومحيطات المضلعات\n"
        "• حساب الأشكال الهندسية المختلفة\n"
        "• حساب المسافات والزوايا الاتجاهية\n"
        "• حساب الميول بأشكالها المختلفة\n"
        "• تحويل الإحداثيات (UTM ↔ جغرافية)\n"
        "• حساب الترافيرس المفتوح والمغلق\n\n"
        "اختر ما تريد حسابه:"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=main_keyboard())
    else:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_keyboard())
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *دليل الاستخدام*\n\n"
        "*المضلعات:*\n"
        "أدخل إحداثيات النقاط كل نقطة في سطر:\n`x1,y1`\n`x2,y2`\n`x3,y3`\n\n"
        "*المساحات:*\n"
        "اختر الشكل ثم أدخل الأبعاد المطلوبة.\n\n"
        "*الإحداثيات:*\n"
        "أدخل الإحداثيات بالتنسيق: `x1,y1,x2,y2`\n\n"
        "*الميول:*\n"
        "أدخل: `ارتفاع,مسافة_أفقية`\n\n"
        "*الترافيرس:*\n"
        "أدخل كل ضلع في سطر: `زاوية,مسافة`\n"
        "مع نقطة البداية في السطر الأول: `x0,y0`\n\n"
        "اكتب /start للعودة للقائمة الرئيسية."
    )
    await update.message.reply_text(text, parse_mode='Markdown')

# ---- Main Menu Callbacks ----

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        return await start(update, context)

    elif data == "polygon":
        await query.edit_message_text(
            "📐 *حساب المضلع*\n\n"
            "أدخل إحداثيات رؤوس المضلع، كل نقطة في سطر منفصل:\n"
            "`x,y`\n\n"
            "مثال:\n`0,0\n10,0\n10,10\n0,10`\n\n"
            "أرسل النقاط الآن:",
            parse_mode='Markdown', reply_markup=back_keyboard()
        )
        return POLYGON_INPUT

    elif data == "areas":
        await query.edit_message_text(
            "📏 *حساب مساحة شكل هندسي*\n\nاختر الشكل:",
            parse_mode='Markdown', reply_markup=area_keyboard()
        )
        return AREA_SELECT

    elif data == "coords":
        await query.edit_message_text(
            "📍 *الإحداثيات والمسافات*\n\nاختر العملية:",
            parse_mode='Markdown', reply_markup=coords_keyboard()
        )
        return COORDS_SELECT

    elif data == "slope":
        await query.edit_message_text(
            "⛰️ *حساب الميل*\n\n"
            "أدخل: `فرق_الارتفاع , المسافة_الأفقية`\n\n"
            "مثال: `5,100`",
            parse_mode='Markdown', reply_markup=back_keyboard()
        )
        context.user_data['mode'] = 'slope'
        return SLOPE_INPUT

    elif data == "coord_convert":
        await query.edit_message_text(
            "🔄 *تحويل الإحداثيات*\n\n"
            "أدخل إحداثيات UTM بالشكل:\n"
            "`easting,northing,zone`\n\n"
            "مثال: `500000,4000000,37`\n\n"
            "سيتم التحويل إلى إحداثيات جغرافية (خط طول، عرض).",
            parse_mode='Markdown', reply_markup=back_keyboard()
        )
        context.user_data['mode'] = 'coord_convert'
        return COORD_CONVERT_INPUT

    elif data == "traverse":
        await query.edit_message_text(
            "📊 *حساب الترافيرس*\n\n"
            "أدخل البيانات على الشكل التالي:\n"
            "السطر الأول: `x0,y0` (نقطة البداية)\n"
            "كل سطر تالٍ: `زاوية_اتجاهية,مسافة`\n\n"
            "مثال:\n"
            "`100,200\n45,150\n135,200\n225,150`",
            parse_mode='Markdown', reply_markup=back_keyboard()
        )
        context.user_data['mode'] = 'traverse'
        return TRAVERSE_INPUT

    return MAIN_MENU

# ---- Area Select ----

async def area_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        return await start(update, context)

    prompts = {
        "area_square":   ("⬛ *مربع*\nأدخل طول الضلع:", "square"),
        "area_rect":     ("▬ *مستطيل*\nأدخل: `الطول,العرض`", "rect"),
        "area_triangle": ("🔺 *مثلث*\nأدخل: `القاعدة,الارتفاع`\nأو ثلاثة أضلاع: `a,b,c`", "triangle"),
        "area_circle":   ("⭕ *دائرة*\nأدخل نصف القطر:", "circle"),
        "area_trap":     ("🔷 *شبه منحرف*\nأدخل: `القاعدة_الكبرى,القاعدة_الصغرى,الارتفاع`", "trap"),
        "area_para":     ("◈ *متوازي أضلاع*\nأدخل: `القاعدة,الارتفاع`", "para"),
    }

    if data in prompts:
        prompt, mode = prompts[data]
        context.user_data['area_mode'] = mode
        await query.edit_message_text(prompt, parse_mode='Markdown', reply_markup=back_keyboard("back_areas"))
        return AREA_INPUT

    return AREA_SELECT

# ---- Coords Select ----

async def coords_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        return await start(update, context)

    prompts = {
        "coords_dist":    ("📏 *المسافة بين نقطتين*\nأدخل: `x1,y1,x2,y2`", "dist"),
        "coords_bearing": ("🧭 *الزاوية الاتجاهية*\nأدخل: `x1,y1,x2,y2`", "bearing"),
        "coords_point":   ("📍 *حساب نقطة جديدة*\nأدخل: `x,y,زاوية_اتجاهية,مسافة`", "point"),
    }

    if data in prompts:
        prompt, mode = prompts[data]
        context.user_data['coords_mode'] = mode
        await query.edit_message_text(prompt, parse_mode='Markdown', reply_markup=back_keyboard("back_coords"))
        return COORDS_INPUT

    return COORDS_SELECT

# ---- Input Handlers ----

async def polygon_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        lines = text.strip().split('\n')
        points = []
        for line in lines:
            x, y = map(float, line.strip().replace(' ', '').split(','))
            points.append((x, y))

        if len(points) < 3:
            await update.message.reply_text("❌ يجب إدخال 3 نقاط على الأقل.", reply_markup=back_keyboard())
            return POLYGON_INPUT

        area, cx, cy = polygon_area_centroid(points)
        peri = perimeter(points)

        result = (
            f"📐 *نتائج المضلع ({len(points)} رؤوس)*\n\n"
            f"📌 المساحة: `{area:,.4f}` وحدة²\n"
            f"📌 المحيط: `{peri:,.4f}` وحدة\n"
            f"📌 مركز الثقل: `({cx:.4f}, {cy:.4f})`\n\n"
            f"*الرؤوس المُدخلة:*\n"
        )
        for i, (x, y) in enumerate(points):
            result += f"  P{i+1}: ({x}, {y})\n"

        await update.message.reply_text(result, parse_mode='Markdown', reply_markup=main_keyboard())
        return MAIN_MENU
    except Exception:
        await update.message.reply_text(
            "❌ خطأ في التنسيق. تأكد من إدخال الإحداثيات بالشكل:\n`x,y`\nكل نقطة في سطر منفصل.",
            parse_mode='Markdown', reply_markup=back_keyboard()
        )
        return POLYGON_INPUT

async def area_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    mode = context.user_data.get('area_mode', '')
    try:
        vals = list(map(float, text.replace(' ', '').split(',')))

        if mode == 'square':
            a = vals[0]
            result = f"⬛ *مربع*\n\nالضلع: `{a}`\nالمساحة: `{a**2:,.4f}`\nالمحيط: `{4*a:,.4f}`"

        elif mode == 'rect':
            l, w = vals[0], vals[1]
            result = f"▬ *مستطيل*\n\nالطول: `{l}` | العرض: `{w}`\nالمساحة: `{l*w:,.4f}`\nالمحيط: `{2*(l+w):,.4f}`"

        elif mode == 'triangle':
            if len(vals) == 2:
                b, h = vals
                area = 0.5 * b * h
                result = f"🔺 *مثلث* (قاعدة × ارتفاع)\n\nالقاعدة: `{b}` | الارتفاع: `{h}`\nالمساحة: `{area:,.4f}`"
            else:
                a, b, c = vals[0], vals[1], vals[2]
                s = (a + b + c) / 2
                area = math.sqrt(s * (s-a) * (s-b) * (s-c))
                result = (
                    f"🔺 *مثلث* (هيرون)\n\n"
                    f"الأضلاع: `{a}, {b}, {c}`\n"
                    f"المساحة: `{area:,.4f}`\n"
                    f"المحيط: `{a+b+c:,.4f}`"
                )

        elif mode == 'circle':
            r = vals[0]
            result = (
                f"⭕ *دائرة*\n\nنصف القطر: `{r}`\n"
                f"المساحة: `{math.pi*r**2:,.4f}`\n"
                f"المحيط: `{2*math.pi*r:,.4f}`\n"
                f"القطر: `{2*r:,.4f}`"
            )

        elif mode == 'trap':
            a, b, h = vals[0], vals[1], vals[2]
            area = 0.5 * (a + b) * h
            result = (
                f"🔷 *شبه منحرف*\n\n"
                f"القاعدة الكبرى: `{a}` | الصغرى: `{b}` | الارتفاع: `{h}`\n"
                f"المساحة: `{area:,.4f}`"
            )

        elif mode == 'para':
            b, h = vals[0], vals[1]
            result = f"◈ *متوازي أضلاع*\n\nالقاعدة: `{b}` | الارتفاع: `{h}`\nالمساحة: `{b*h:,.4f}`"

        else:
            result = "❌ وضع غير معروف."

        await update.message.reply_text(result, parse_mode='Markdown', reply_markup=main_keyboard())
        return MAIN_MENU

    except Exception:
        await update.message.reply_text("❌ خطأ في البيانات. تحقق من التنسيق وأعد المحاولة.", reply_markup=back_keyboard("back_areas"))
        return AREA_INPUT

async def coords_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    mode = context.user_data.get('coords_mode', '')
    try:
        vals = list(map(float, text.replace(' ', '').split(',')))

        if mode == 'dist':
            x1, y1, x2, y2 = vals
            dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            result = (
                f"📏 *المسافة بين النقطتين*\n\n"
                f"P1: `({x1}, {y1})`\n"
                f"P2: `({x2}, {y2})`\n\n"
                f"المسافة: `{dist:,.4f}` وحدة"
            )

        elif mode == 'bearing':
            x1, y1, x2, y2 = vals
            dx = x2 - x1
            dy = y2 - y1
            angle = math.degrees(math.atan2(dx, dy))
            if angle < 0:
                angle += 360
            dist = math.sqrt(dx**2 + dy**2)
            d, m, s = dd_to_dms(angle)
            result = (
                f"🧭 *الزاوية الاتجاهية (Bearing)*\n\n"
                f"P1: `({x1}, {y1})`\nP2: `({x2}, {y2})`\n\n"
                f"الزاوية: `{angle:.4f}°`\n"
                f"بالدرجات: `{d}° {m}' {s:.2f}\"`\n"
                f"المسافة: `{dist:,.4f}` وحدة"
            )

        elif mode == 'point':
            x, y, az, dist = vals
            rad = math.radians(az)
            nx = x + dist * math.sin(rad)
            ny = y + dist * math.cos(rad)
            result = (
                f"📍 *النقطة الجديدة*\n\n"
                f"نقطة البداية: `({x}, {y})`\n"
                f"الزاوية الاتجاهية: `{az}°`\n"
                f"المسافة: `{dist}`\n\n"
                f"النقطة الناتجة: `({nx:.4f}, {ny:.4f})`"
            )
        else:
            result = "❌ وضع غير معروف."

        await update.message.reply_text(result, parse_mode='Markdown', reply_markup=main_keyboard())
        return MAIN_MENU

    except Exception:
        await update.message.reply_text("❌ خطأ في البيانات. تحقق من التنسيق وأعد المحاولة.", reply_markup=back_keyboard("back_coords"))
        return COORDS_INPUT

async def slope_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        vals = list(map(float, text.replace(' ', '').split(',')))
        h, d = vals[0], vals[1]
        if d == 0:
            await update.message.reply_text("❌ المسافة الأفقية لا يمكن أن تكون صفراً.")
            return SLOPE_INPUT

        pct = (h / d) * 100
        angle = math.degrees(math.atan(h / d))
        ratio = f"1:{d/h:.2f}" if h != 0 else "0"
        slope_dist = math.sqrt(h**2 + d**2)

        result = (
            f"⛰️ *نتائج الميل*\n\n"
            f"فرق الارتفاع (h): `{h}` م\n"
            f"المسافة الأفقية (d): `{d}` م\n\n"
            f"📌 الميل بالنسبة المئوية: `{pct:.2f}%`\n"
            f"📌 زاوية الميل: `{angle:.4f}°`\n"
            f"📌 نسبة الميل: `{ratio}`\n"
            f"📌 المسافة المائلة: `{slope_dist:.4f}` م"
        )
        await update.message.reply_text(result, parse_mode='Markdown', reply_markup=main_keyboard())
        return MAIN_MENU
    except Exception:
        await update.message.reply_text("❌ خطأ في البيانات. أدخل: `ارتفاع,مسافة_أفقية`", parse_mode='Markdown', reply_markup=back_keyboard())
        return SLOPE_INPUT

async def traverse_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        lines = text.strip().split('\n')
        start = list(map(float, lines[0].split(',')))
        x, y = start[0], start[1]

        points = [(x, y)]
        for line in lines[1:]:
            az, dist = map(float, line.strip().split(','))
            rad = math.radians(az)
            x += dist * math.sin(rad)
            y += dist * math.cos(rad)
            points.append((x, y))

        result = "📊 *نتائج الترافيرس*\n\n"
        for i, (px, py) in enumerate(points):
            result += f"P{i}: `({px:.3f}, {py:.3f})`\n"

        # Check if closed (last point ≈ first)
        dx = points[-1][0] - points[0][0]
        dy = points[-1][1] - points[0][1]
        closure = math.sqrt(dx**2 + dy**2)
        result += f"\n📌 خطأ الإغلاق: `{closure:.4f}` وحدة"

        await update.message.reply_text(result, parse_mode='Markdown', reply_markup=main_keyboard())
        return MAIN_MENU
    except Exception:
        await update.message.reply_text(
            "❌ خطأ في البيانات. تأكد من التنسيق:\n`x0,y0`\n`زاوية,مسافة`",
            parse_mode='Markdown', reply_markup=back_keyboard()
        )
        return TRAVERSE_INPUT

async def coord_convert_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        vals = list(map(float, text.replace(' ', '').split(',')))
        easting, northing, zone = vals[0], vals[1], int(vals[2])

        # Simplified UTM to Geographic (WGS84) - approximate
        k0 = 0.9996
        a = 6378137.0
        e = 0.081819190842622
        e2 = e**2
        e4 = e**4
        e6 = e**6

        x = easting - 500000
        y = northing

        # Northern hemisphere assumed
        M = y / k0
        mu = M / (a * (1 - e2/4 - 3*e4/64 - 5*e6/256))

        e1 = (1 - math.sqrt(1-e2)) / (1 + math.sqrt(1-e2))
        phi1 = mu + (3*e1/2 - 27*e1**3/32)*math.sin(2*mu)
        phi1 += (21*e1**2/16 - 55*e1**4/32)*math.sin(4*mu)
        phi1 += (151*e1**3/96)*math.sin(6*mu)

        N1 = a / math.sqrt(1 - e2*math.sin(phi1)**2)
        T1 = math.tan(phi1)**2
        C1 = e2*math.cos(phi1)**2 / (1-e2)
        R1 = a*(1-e2) / (1-e2*math.sin(phi1)**2)**1.5
        D = x / (N1*k0)

        lat = phi1 - (N1*math.tan(phi1)/R1) * (
            D**2/2 - (5+3*T1+10*C1-4*C1**2-9*e2)*D**4/24
        )
        lat = math.degrees(lat)

        lon0 = (zone - 1)*6 - 180 + 3
        lon = lon0 + math.degrees(
            (D - (1+2*T1+C1)*D**3/6) / math.cos(phi1)
        )

        lat_d, lat_m, lat_s = dd_to_dms(abs(lat))
        lon_d, lon_m, lon_s = dd_to_dms(abs(lon))
        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"

        result = (
            f"🔄 *تحويل الإحداثيات*\n\n"
            f"*UTM (مُدخل):*\n"
            f"Easting: `{easting:,.2f}`\n"
            f"Northing: `{northing:,.2f}`\n"
            f"Zone: `{zone}`\n\n"
            f"*إحداثيات جغرافية (WGS84):*\n"
            f"خط العرض: `{lat:.6f}°` ({lat_d}° {lat_m}' {lat_s:.2f}\" {lat_dir})\n"
            f"خط الطول: `{lon:.6f}°` ({lon_d}° {lon_m}' {lon_s:.2f}\" {lon_dir})"
        )
        await update.message.reply_text(result, parse_mode='Markdown', reply_markup=main_keyboard())
        return MAIN_MENU
    except Exception:
        await update.message.reply_text(
            "❌ خطأ في البيانات. أدخل: `easting,northing,zone`",
            parse_mode='Markdown', reply_markup=back_keyboard()
        )
        return COORD_CONVERT_INPUT

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 اكتب /start للعودة للقائمة الرئيسية.",
        reply_markup=main_keyboard()
    )
    return MAIN_MENU

# ===================== Main =====================

def main():
    TOKEN = os.environ.get("TOKEN")  # يُقرأ من متغيرات البيئة
    if not TOKEN:
        raise ValueError("❌ لم يتم تعيين TOKEN في متغيرات البيئة!")

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(menu_callback),
            ],
            POLYGON_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, polygon_input),
                CallbackQueryHandler(menu_callback),
            ],
            AREA_SELECT: [
                CallbackQueryHandler(area_select_callback),
            ],
            AREA_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, area_input),
                CallbackQueryHandler(menu_callback),
            ],
            COORDS_SELECT: [
                CallbackQueryHandler(coords_select_callback),
            ],
            COORDS_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, coords_input),
                CallbackQueryHandler(menu_callback),
            ],
            SLOPE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, slope_input),
                CallbackQueryHandler(menu_callback),
            ],
            TRAVERSE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, traverse_input),
                CallbackQueryHandler(menu_callback),
            ],
            COORD_CONVERT_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, coord_convert_input),
                CallbackQueryHandler(menu_callback),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("help", help_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, fallback),
        ],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    print("🤖 البوت يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
