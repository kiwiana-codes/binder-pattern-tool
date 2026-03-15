import streamlit as st
import math
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib import colors

# Configuration
VERSION = "22.1-SECURE"
ACCESS_CODE = st.secrets.get("access_code", None)

if not ACCESS_CODE:
    st.error("🚀 **App Configuration Required**")
    st.info("Administrators: Please set the `access_code` in your Streamlit Cloud 'Secrets' panel or local `.streamlit/secrets.toml` file.")
    st.stop()

st.set_page_config(page_title="MJ's Custom Binder Pattern", page_icon="🏳️‍⚧️", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; padding: 0.5rem; }
    .stDownloadButton>button { width: 100%; background: linear-gradient(135deg, #4f46e5, #4338ca); color: white; border: none; }
    .stDownloadButton>button:hover { background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; }
    .info-card { background: rgba(30, 41, 59, 0.7); padding: 1rem; border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.1); margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- PASSWORD ---
with st.sidebar:
    st.title("MJ's Custom Binder Pattern")
    code = st.text_input("Access Code", type="password", help="Enter the code from the instructions you received after purchasing.")
    
    if not code:
        st.info("Please enter the access code provided found in the instructions you received after purchasing to access this tool. Found this app without purchasing? You can buy the pattern at https://ko-fi.com/kiwiana/shop.")
        st.stop()
    elif code != ACCESS_CODE:
        st.error("Incorrect Access Code.")
        st.stop()

# --- UNIT SYSTEM CONFIG ---
with st.sidebar:
    st.divider()
    unit_mode = st.radio("Measurement System", ["Metric (cm)", "Imperial (inches)"])
    is_metric = unit_mode == "Metric (cm)"
    unit_label = "cm" if is_metric else "in"
    
    # Conversion Factors for pattern math
    if is_metric:
        # Values in cm
        C_INCH = 2.54
        C_HALF = 1.27
        C_1_5 = 3.8
        X_INNER = 7.5
        X_OUTER = 15.0
        Y_S_STIFF = 5.0
        X_I_STIFF = 8.5
        X_O_STIFF = 14.0
        STRIP_1 = 1.0
        STRIP_HEM = 1.3
        GAP = 1.0
        GAP_BOT = 2.5
        NECK_D_F = 14.0
        NECK_D_B = 4.0
    else:
        # Values in inches
        C_INCH = 1.0
        C_HALF = 0.5
        C_1_5 = 1.5
        X_INNER = 3.0
        X_OUTER = 6.0
        Y_S_STIFF = 2.0
        X_I_STIFF = 3.375 # 3 3/8"
        X_O_STIFF = 5.5
        STRIP_1 = 0.375 # 3/8"
        STRIP_HEM = 0.5 # 1/2"
        GAP = 0.375 # ~1cm
        GAP_BOT = 1.0
        NECK_D_F = 5.5
        NECK_D_B = 1.5

# --- DRAFTING LOGIC ---
def calculate_pattern(A_raw, B_raw, C_raw, D_raw, is_metric):
    A_final = (A_raw / 2) - C_INCH
    B_final = B_raw + C_1_5
    C_final = C_raw + C_INCH
    D_final = (D_raw / 2) - C_HALF

    armpit_y = B_final - C_final
    armpit_x = A_final / 2
    D_half = D_final / 2

    def get_piece(neck_depth, name, fabric, is_stiff=False):
        if not is_stiff:
            y_s, x_i, x_o = 0, X_INNER, X_OUTER
            y_nc = neck_depth
            x_a, y_a = armpit_x, armpit_y
            y_b, x_b = B_final, D_half
        else:
            y_s, x_i, x_o = Y_S_STIFF, X_I_STIFF, X_O_STIFF
            y_nc = neck_depth + GAP
            x_a, y_a = armpit_x - GAP, armpit_y + GAP
            y_b, x_b = B_final - GAP_BOT, D_half - GAP

        d = f"M 0 {y_b} L {x_b} {y_b} L {x_a} {y_a} Q {x_o} {y_a} {x_o} {y_s} L {x_i} {y_s} Q {x_i} {y_nc} 0 {y_nc} " \
            f"Q {-x_i} {y_nc} {-x_i} {y_s} L {-x_o} {y_s} Q {-x_o} {y_a} {-x_a} {y_a} L {-x_b} {y_b} Z"
            
        return {
            "d": d, "label": f"{name} - {fabric} (CUT 1)", "height": B_final, "labelY": B_final/2,
            "coords": (y_s, x_i, x_o, y_nc, x_a, y_a, y_b, x_b)
        }

    front = get_piece(NECK_D_F, "FRONT PIECE", "STRETCH FABRIC")
    back = get_piece(NECK_D_B, "BACK PIECE", "STRETCH FABRIC")
    stiff = get_piece(NECK_D_F, "STIFF INNER PANEL", "STIFF FABRIC", True)

    def normalize(vx, vy):
        mag = math.sqrt(vx*vx + vy*vy)
        return (vx/mag, vy/mag) if mag > 0 else (0, 0)

    def get_ribbon_d(p0, p1, p2, width, reverse=False):
        def get_normal(t):
            dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
            dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
            m = -1 if reverse else 1
            return normalize(-dy * m, dx * m)
        
        n0 = get_normal(0); n1 = get_normal(0.5); n2 = get_normal(1)
        o0 = (p0[0] + n0[0]*width, p0[1] + n0[1]*width)
        o1 = (p1[0] + n1[0]*width, p1[1] + n1[1]*width)
        o2 = (p2[0] + n2[0]*width, p2[1] + n2[1]*width)
        
        return f" M {p0[0]} {p0[1]} Q {p1[0]} {p1[1]} {p2[0]} {p2[1]} L {o2[0]} {o2[1]} Q {o1[0]} {o1[1]} {o0[0]} {o0[1]} Z "

    strips = []
    strap_w = front['coords'][2] - front['coords'][1]
    strips.append({"label": "SHOULDER STRIPS - INTERFACING (CUT 4)", "d": f"M 0 0 L {strap_w} 0 L {strap_w} {STRIP_1} L 0 {STRIP_1} Z", "color": "#4f46e5", "h": STRIP_1*5})

    b_c = back['coords']
    b_neck_d = get_ribbon_d((-b_c[1], b_c[0]), (-b_c[1], b_c[3]), (0, b_c[3]), STRIP_1) + \
               get_ribbon_d((0, b_c[3]), (b_c[1], b_c[3]), (b_c[1], b_c[0]), STRIP_1)
    strips.append({"label": "BACK NECKLINE - INTERFACING (CUT 1)", "d": b_neck_d, "color": "#4f46e5", "h": abs(b_c[3]-b_c[0])+STRIP_1*5})

    b_arm_d = get_ribbon_d((b_c[4], b_c[5]), (b_c[2], b_c[5]), (b_c[2], b_c[0]), STRIP_1, True)
    strips.append({"label": "BACK ARMHOLES - INTERFACING (CUT 2)", "d": b_arm_d, "color": "#4f46e5", "h": abs(b_c[5]-b_c[0])+STRIP_1*5})

    strips.append({"label": "BACK HEM - INTERFACING (CUT 1)", "d": f"M {-b_c[7]} 0 L {b_c[7]} 0 L {b_c[7]} {STRIP_HEM} L {-b_c[7]} {STRIP_HEM} Z", "color": "#4f46e5", "h": STRIP_HEM*8})

    s_c = stiff['coords']
    s_neck_d = get_ribbon_d((-s_c[1], s_c[0]), (-s_c[1], s_c[3]), (0, s_c[3]), STRIP_1) + \
               get_ribbon_d((0, s_c[3]), (s_c[1], s_c[3]), (s_c[1], s_c[0]), STRIP_1)
    strips.append({"label": "WEBBING NECKLINE - WEBBING (CUT 2)", "d": s_neck_d, "color": "#dc2626", "h": abs(s_c[3]-s_c[0])+STRIP_1*5})

    s_arm_d = get_ribbon_d((s_c[4], s_c[5]), (s_c[2], s_c[5]), (s_c[2], s_c[0]), STRIP_1, True)
    strips.append({"label": "WEBBING ARMPIT - WEBBING (CUT 4)", "d": s_arm_d, "color": "#dc2626", "h": abs(s_c[5]-s_c[0])+STRIP_1*5})

    view_mult = 1 if is_metric else 2.54
    return {
        "front": front, "back": back, "stiff": stiff, "strips": strips,
        "params": (A_final, B_final, C_final, D_final),
        "total_w": max(armpit_x * 2, 40/view_mult) + 10/view_mult,
        "total_h": (B_final * 3) + (len(strips) * (20/view_mult)) + (100/view_mult),
        "view_mult": view_mult
    }

# --- PDF GENERATOR ---
def generate_pdf(pattern, inputs, is_metric, page_size=A4):
    PT_PER_INCH = 72.0
    PT_PER_CM = 28.346; PT_PER_MM = 2.8346
    U_FACTOR = PT_PER_CM if is_metric else PT_PER_INCH
    
    P_W, P_H = page_size
    MARGIN = 10 * PT_PER_MM
    DRAW_W, DRAW_H = P_W - (MARGIN * 2), P_H - (MARGIN * 2)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page_size)
    
    pieces = []
    v_gap = (5 if is_metric else 2) * U_FACTOR; curr_y = 0
    pieces.append({"label": pattern['front']['label'], "d": pattern['front']['d'], "color": colors.HexColor("#4f46e5"), "y": curr_y, "h": pattern['front']['height']*U_FACTOR, "type": "main"})
    curr_y += pattern['front']['height']*U_FACTOR + v_gap
    pieces.append({"label": pattern['back']['label'], "d": pattern['back']['d'], "color": colors.HexColor("#4f46e5"), "y": curr_y, "h": pattern['back']['height']*U_FACTOR, "type": "main"})
    curr_y += pattern['back']['height']*U_FACTOR + v_gap
    pieces.append({"label": pattern['stiff']['label'], "d": pattern['stiff']['d'], "color": colors.HexColor("#dc2626"), "y": curr_y, "h": pattern['stiff']['height']*U_FACTOR, "type": "main"})
    curr_y += pattern['stiff']['height']*U_FACTOR + (10 if is_metric else 4) * U_FACTOR

    for s in pattern['strips']:
        pieces.append({"label": s['label'], "d": s['d'], "color": colors.HexColor(s['color']), "y": curr_y, "h": s['h']*U_FACTOR, "type": "strip"})
        curr_y += s['h']*U_FACTOR + v_gap

    total_w_pt = pattern['total_w'] * U_FACTOR
    min_x = (-pattern['total_w']/2) * U_FACTOR
    min_y = -5 * U_FACTOR

    rows = math.ceil((curr_y + 50) / DRAW_H)
    cols = math.ceil(total_w_pt / DRAW_W)

    def draw_q(path, p0, p1, p2):
        c1x = p0[0] + (2/3)*(p1[0]-p0[0]); c1y = p0[1] + (2/3)*(p1[1]-p0[1])
        c2x = p2[0] + (2/3)*(p1[0]-p2[0]); c2y = p2[1] + (2/3)*(p1[1]-p2[1])
        path.curveTo(c1x, c1y, c2x, c2y, p2[0], p2[1])

    def draw_d(d_str, p_y_pt, off_x, off_y):
        cmds = d_str.split(); i = 0; curX, curY = 0, 0; startX, startY = 0, 0
        path = c.beginPath()
        while i < len(cmds):
            cmd = cmds[i]
            if cmd == 'M':
                curX = float(cmds[i+1])*U_FACTOR - off_x + MARGIN; curY = float(cmds[i+2])*U_FACTOR + p_y_pt - off_y + MARGIN
                startX, startY = curX, curY; path.moveTo(curX, curY); i += 3
            elif cmd == 'L':
                curX = float(cmds[i+1])*U_FACTOR - off_x + MARGIN; curY = float(cmds[i+2])*U_FACTOR + p_y_pt - off_y + MARGIN
                path.lineTo(curX, curY); i += 3
            elif cmd == 'Q':
                x1 = float(cmds[i+1])*U_FACTOR - off_x + MARGIN; y1 = float(cmds[i+2])*U_FACTOR + p_y_pt - off_y + MARGIN
                x2 = float(cmds[i+3])*U_FACTOR - off_x + MARGIN; y2 = float(cmds[i+4])*U_FACTOR + p_y_pt - off_y + MARGIN
                draw_q(path, (curX, curY), (x1, y1), (x2, y2))
                curX, curY = x2, y2; i += 5
            elif cmd == 'Z': path.close(); i += 1
            else: i += 1
        c.drawPath(path, stroke=1, fill=0)

    for r in range(rows):
        for col in range(cols):
            if r > 0 or col > 0: c.showPage()
            off_x = min_x + col * DRAW_W; off_y = min_y + r * DRAW_H
            
            c.setStrokeColor(colors.Color(150/255, 150/255, 150/255)); c.setLineWidth(0.5); c.rect(MARGIN, MARGIN, DRAW_W, DRAW_H)
            c.setFont("Helvetica-Bold", 60); c.setFillColor(colors.Color(220/255, 220/255, 220/255))
            c.drawCentredString(P_W/2, P_H/2, f"{r+1}{chr(65+col)}")

            # Join Indicators
            c.setStrokeColor(colors.Color(200/255, 200/255, 200/255)); c.setLineWidth(0.5); c.setFont("Helvetica", 6); c.setFillColor(colors.grey)
            if r > 0: c.drawCentredString(P_W/2, MARGIN + 15, f"JOIN TO {r}{chr(65+col)}")
            if r < rows-1: c.drawCentredString(P_W/2, MARGIN + DRAW_H - 10, f"JOIN TO {r+2}{chr(65+col)}")
            if col > 0: c.drawString(MARGIN + 5, P_H/2, f"JOIN TO {r+1}{chr(64+col)}")
            if col < cols-1: c.drawRightString(MARGIN + DRAW_W - 5, P_H/2, f"JOIN TO {r+1}{chr(66+col)}")

            # --- SCALE BAR ---
            c.setStrokeColor(colors.black); c.setLineWidth(1); c.setFont("Helvetica", 8); c.setFillColor(colors.black)
            sY = MARGIN + DRAW_H - 35
            scale_len_pt = 5 * PT_PER_CM if is_metric else 2 * PT_PER_INCH
            scale_label = "5cm Scale Check" if is_metric else "2in Scale Check"
            c.line(P_W/2 - scale_len_pt/2, sY, P_W/2 + scale_len_pt/2, sY)
            c.line(P_W/2 - scale_len_pt/2, sY-5, P_W/2 - scale_len_pt/2, sY+5)
            c.line(P_W/2 + scale_len_pt/2, sY-5, P_W/2 + scale_len_pt/2, sY+5)
            c.drawCentredString(P_W/2, sY - 10, scale_label)

            for p in pieces:
                if p['y'] < off_y + DRAW_H + 50 and (p['y'] + p['h']) > off_y - 50:
                    c.setStrokeColor(p['color']); c.setLineWidth(0.8)
                    draw_d(p['d'], p['y'], off_x, off_y)
                    lY = (p['y'] + p['h']/2 - off_y) + MARGIN
                    if lY > MARGIN and lY < MARGIN + DRAW_H:
                        parts = p['label'].split(' - '); c.setFillColor(colors.black)
                        if p['type'] == 'main':
                            c.setFont("Helvetica-Bold", 10); c.drawCentredString(P_W/2, lY-5, parts[0])
                            c.setFont("Helvetica", 8); c.drawCentredString(P_W/2, lY+8, parts[1])
                        else:
                            c.setFont("Helvetica", 8); c.drawCentredString(P_W/2, lY, p['label'])
    c.save()
    buffer.seek(0)
    return buffer

# --- APP UI ---
with st.sidebar:
    st.divider()
    if is_metric:
        A = st.number_input("Chest (Below Armpits) cm", 50, 200, 90)
        B = st.number_input("Shoulder to Waist cm", 20, 100, 40)
        C = st.number_input("Armpit to Waist cm", 10, 80, 20)
        D = st.number_input("Waist Circumference cm", 40, 200, 80)
    else:
        A = st.number_input("Chest (Below Armpits) inches", 20.0, 80.0, 35.5)
        B = st.number_input("Shoulder to Waist inches", 8.0, 40.0, 15.75)
        C = st.number_input("Armpit to Waist inches", 4.0, 32.0, 8.0)
        D = st.number_input("Waist Circumference inches", 15.0, 80.0, 31.5)
    st.divider()
    st.markdown(f"**App Version:** {VERSION}")

pattern = calculate_pattern(A, B, C, D, is_metric)

col1, col2 = st.columns([1, 2])
with col1:
    st.title("Binder Pattern Creator")
    st.markdown(f"Draft custom compression binders in **{unit_mode.split(' ')[0]}**. Tiled PDF includes a precision scale check.")
    
    # Hidden Calculation logic
    # st.markdown(f"""
    # <div class="info-card">
    #     <b>📐 Pattern Drafting Requirements ({unit_label}):</b><br/>
    #     • Chest final: {pattern['params'][0]:.2f}{unit_label}<br/>
    #     • Waist final: {pattern['params'][3]:.2f}{unit_label}<br/>
    #     • Shoulder Length: {pattern['params'][1]:.2f}{unit_label}<br/>
    #     • Armpit to Waist: {pattern['params'][2]:.2f}{unit_label}
    # </div>
    # """, unsafe_allow_html=True)
    
    st.divider()
    
    # A4 Button
    pdf_a4 = generate_pdf(pattern, {"A":A, "B":B}, is_metric, A4)
    st.download_button(
        label=f"Download Tiled PDF (A4 - {unit_label})",
        data=pdf_a4,
        file_name=f"binder_pattern_{A}_{B}_A4_{unit_label}.pdf",
        mime="application/pdf"
    )
    
    # Letter Button
    pdf_letter = generate_pdf(pattern, {"A":A, "B":B}, is_metric, LETTER)
    st.download_button(
        label=f"Download Tiled PDF (US Letter - {unit_label})",
        data=pdf_letter,
        file_name=f"binder_pattern_{A}_{B}_Letter_{unit_label}.pdf",
        mime="application/pdf"
    )

    st.markdown(f"""
    <div class="info-card" style="border: 1px solid #4f46e5; background: rgba(79, 70, 229, 0.1); margin-top: 2rem;">
        <p style="font-size: 0.9rem; margin: 0;">
            <b>Support my journey!</b><br/>
            This pattern is for sale via my Ko-Fi store. If the access code for this app has been shared with you without purchasing, I'd really appreciate you making a donation at <a href="https://ko-fi.com/kiwiana" target="_blank" style="color: #6366f1;">ko-fi.com/kiwiana</a>&mdash;every little bit gets me closer to my top surgery!
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # SVG Preview
    svg_h = pattern['total_h']
    svg_w = pattern['total_w']
    viewbox = f"{-svg_w/2} -5 {svg_w} {svg_h}"
    
    scale_svg_len = 5 if is_metric else 5.08
    scale_svg_label = "5cm" if is_metric else "2in"
    
    svg_code = f'<svg viewBox="{viewbox}" xmlns="http://www.w3.org/2000/svg" style="background: white; border-radius: 8px;">'
    svg_code += f'<g transform="translate(0,-5)"><line x1="{-scale_svg_len/2}" x2="{scale_svg_len/2}" y1="0" y2="0" stroke="#000" stroke-width="0.2"/><line x1="{-scale_svg_len/2}" x2="{-scale_svg_len/2}" y1="-0.5" y2="0.5" stroke="#000" stroke-width="0.2"/><line x1="{scale_svg_len/2}" x2="{scale_svg_len/2}" y1="-0.5" y2="0.5" stroke="#000" stroke-width="0.2"/><text x="0" y="-1" text-anchor="middle" font-size="1.5">{scale_svg_label} Scale</text></g>'
    
    def add_p_svg(p, y_off, color):
        s_d = p['d']
        label_parts = p['label'].split(' - ')
        res = f'<g transform="translate(0, {y_off})">'
        res += f'<path d="{s_d}" fill="{color}22" stroke="{color}" stroke-width="0.5"/>'
        res += f'<text x="0" y="{p["labelY"]-3}" text-anchor="middle" font-size="2.5" font-weight="bold" fill="#312e81">{label_parts[0]}</text>'
        res += f'<text x="0" y="{p["labelY"]}" text-anchor="middle" font-size="1.2" fill="#4338ca">{label_parts[1]}</text>'
        res += '</g>'
        return res

    svg_code += add_p_svg(pattern['front'], 0, "#4f46e5")
    svg_code += add_p_svg(pattern['back'], pattern['front']['height']+2, "#4f46e5")
    svg_code += add_p_svg(pattern['stiff'], pattern['front']['height']+pattern['back']['height']+4, "#dc2626")
    
    curr_y = pattern['front']['height']+pattern['back']['height']+pattern['stiff']['height']+10
    svg_code += f'<text x="0" y="{curr_y-2}" text-anchor="middle" font-size="2" font-weight="bold" fill="#475569">STRIPS</text>'
    for s in pattern['strips']:
        svg_code += f'<g transform="translate(0, {curr_y})"><path d="{s["d"]}" fill="{s["color"]}22" stroke="{s["color"]}" stroke-width="0.3"/><text x="0" y="0.5" text-anchor="middle" font-size="1.0" fill="{s["color"]}">{s["label"]}</text></g>'
        curr_y += s['h'] + 2

    svg_code += '</svg>'
    st.components.v1.html(svg_code, height=800, scrolling=True)
