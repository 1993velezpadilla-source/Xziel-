#!/usr/bin/env python3
"""Fetch and rasterize the CC0 HUD icon set used by Xziel mobile.

Upstream: Nieobie/Game-Icon-Pack
License: CC0 1.0 Universal
Pinned revision: b1a5fec8b68c99e7b46484db707610ab2414ad4c
"""
from pathlib import Path
from urllib.request import Request, urlopen
import io
import re
import sys
import zipfile
import cairosvg

REV = "b1a5fec8b68c99e7b46484db707610ab2414ad4c"
BASE = f"https://raw.githubusercontent.com/Nieobie/Game-Icon-Pack/{REV}/svg/no-padding"
ICONS = {
    "fire": "6-buildings/target.svg",
    "ads": "6-buildings/target-02.svg",
    "reload": "8-ui/refresh.svg",
    "use": "6-buildings/open-the-door.svg",
    "jump": "8-ui/arrow-up.svg",
    "knife": "5-food/knife.svg",
    "grenade": "3-gear/bomb.svg",
    "pause": "9-media/pause.svg",
    "sprint": "3-gear/shoe.svg",
    "slide": "8-ui/arrow-down-02.svg",
    "pistol": "3-gear/pistol.svg",
    "weapon": "3-gear/bullet.svg",
    "weapon_wonder": "4-nature/lightning.svg",
    "weapon_launcher": "3-gear/missile.svg",
    "threat": "1-game/skull.svg",
}

def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Xziel-build/0.18"})
    with urlopen(req, timeout=30) as response:
        return response.read()


def _render_svg(out: Path, name: str, body: str, size: int = 512) -> None:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    {body}
    </svg>'''
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(out / f"{name}.png"),
        output_width=size,
        output_height=size,
    )

def build_xziel_modern_surfaces(out: Path) -> None:
    # Original Xziel HUD surfaces. These are generated locally rather than
    # copied from another game's UI, so the mobile HUD can be modern without
    # inheriting proprietary art.
    idle = '''
      <circle cx="256" cy="256" r="220" fill="#05080B" fill-opacity=".38"/>
      <circle cx="256" cy="256" r="220" fill="none" stroke="#F2F6FA" stroke-opacity=".58" stroke-width="14"/>
      <circle cx="256" cy="256" r="190" fill="none" stroke="#F2F6FA" stroke-opacity=".10" stroke-width="4"/>
      <path d="M256 22v28M256 462v28M22 256h28M462 256h28" stroke="#F2F6FA" stroke-opacity=".78" stroke-width="10" stroke-linecap="round"/>
    '''
    pressed = '''
      <circle cx="256" cy="256" r="224" fill="#15130B" fill-opacity=".78"/>
      <circle cx="256" cy="256" r="220" fill="none" stroke="#F4C83D" stroke-opacity=".96" stroke-width="18"/>
      <circle cx="256" cy="256" r="184" fill="none" stroke="#F4C83D" stroke-opacity=".24" stroke-width="7"/>
      <path d="M256 18v34M256 460v34M18 256h34M460 256h34" stroke="#FFF7D7" stroke-width="11" stroke-linecap="round"/>
    '''
    editor = '''
      <circle cx="256" cy="256" r="220" fill="#071018" fill-opacity=".52"/>
      <circle cx="256" cy="256" r="220" fill="none" stroke="#EAF8FF" stroke-opacity=".82" stroke-width="14"/>
      <circle cx="256" cy="256" r="188" fill="none" stroke="#EAF8FF" stroke-opacity=".16" stroke-width="5"/>
      <path d="M256 18v34M256 460v34M18 256h34M460 256h34" stroke="#EAF8FF" stroke-opacity=".92" stroke-width="10" stroke-linecap="round"/>
    '''
    joy_ring = '''
      <circle cx="256" cy="256" r="220" fill="#020609" fill-opacity=".22"/>
      <circle cx="256" cy="256" r="216" fill="none" stroke="#F1F6FA" stroke-opacity=".28" stroke-width="12"/>
      <circle cx="256" cy="256" r="150" fill="none" stroke="#F1F6FA" stroke-opacity=".09" stroke-width="5"/>
      <path d="M256 20v50M256 442v50M20 256h50M442 256h50" stroke="#F1F6FA" stroke-opacity=".58" stroke-width="12" stroke-linecap="round"/>
      <path d="M222 72l34-36 34 36" fill="none" stroke="#F4C83D" stroke-opacity=".74" stroke-width="11" stroke-linejoin="round"/>
    '''
    joy_knob = '''
      <circle cx="256" cy="256" r="190" fill="#10161B" fill-opacity=".78"/>
      <circle cx="256" cy="256" r="188" fill="none" stroke="#F1F6FA" stroke-opacity=".62" stroke-width="16"/>
      <circle cx="256" cy="256" r="86" fill="#F1F6FA" fill-opacity=".13"/>
    '''
    joy_knob_active = '''
      <circle cx="256" cy="256" r="194" fill="#16150E" fill-opacity=".90"/>
      <circle cx="256" cy="256" r="190" fill="none" stroke="#F4C83D" stroke-opacity=".98" stroke-width="18"/>
      <circle cx="256" cy="256" r="88" fill="#FFF7D7" fill-opacity=".19"/>
    '''
    for name, body in {
        "touch_idle": idle,
        "touch_pressed": pressed,
        "touch_editor": editor,
        "joystick_ring": joy_ring,
        "joystick_knob": joy_knob,
        "joystick_knob_active": joy_knob_active,
    }.items():
        _render_svg(out, name, body)

    # Recognisable, original silhouette set matched to NZ:P's actual weapon
    # families. PaP variants map back to the same physical silhouette.
    silhouettes = {
      "weapon_colt": '''
        <path d="M95 205h242v62H215l-22 145h-72l28-145H95z"/>
        <path d="M326 211h96v25h-96z"/><rect x="145" y="176" width="94" height="30" rx="8"/>
      ''',
      "weapon_revolver": '''
        <rect x="95" y="214" width="230" height="54" rx="10"/><circle cx="235" cy="241" r="55"/>
        <path d="M181 264h72l-22 145h-68z"/><rect x="322" y="224" width="110" height="20"/>
      ''',
      "weapon_kar": '''
        <path d="M42 252l82-52h210l67 26 70 6v24l-137 8H126l-84 45z"/>
        <rect x="248" y="247" width="20" height="92"/><rect x="371" y="218" width="105" height="14"/>
      ''',
      "weapon_kar_scope": '''
        <path d="M34 260l90-52h214l62 28 76 5v24l-140 8H126l-92 44z"/>
        <rect x="244" y="255" width="20" height="88"/>
        <rect x="206" y="176" width="150" height="26" rx="12"/><circle cx="210" cy="189" r="24"/><circle cx="350" cy="189" r="24"/>
      ''',
      "weapon_thompson": '''
        <path d="M42 252l82-58h78v33h155v58H191l-68 44-81-17z"/>
        <rect x="354" y="241" width="116" height="19"/><rect x="200" y="282" width="28" height="106"/>
        <circle cx="278" cy="307" r="52"/>
      ''',
      "weapon_bar": '''
        <path d="M35 258l94-58h182l68 36h99v25h-164l-69 22H130l-95 46z"/>
        <path d="M247 278h43l-9 106h-46z"/><rect x="370" y="228" width="108" height="12"/>
      ''',
      "weapon_ballistic": '''
        <path d="M72 263l260-68 91 20-83 35-268 55z"/><path d="M321 203l90-90 29 17-55 101z"/>
      ''',
      "weapon_browning": '''
        <path d="M28 250l81-47h237l50 29h92v30h-142l-54 35H111l-83 35z"/>
        <rect x="225" y="286" width="44" height="115"/><rect x="351" y="221" width="137" height="13"/>
        <path d="M388 262l-36 120h12l48-120z"/>
      ''',
      "weapon_doublebarrel": '''
        <path d="M28 270l96-60h151v61H126l-98 45z"/>
        <rect x="270" y="217" width="210" height="17"/><rect x="270" y="246" width="210" height="17"/>
      ''',
      "weapon_sawnoff": '''
        <path d="M72 273l76-48h139v58H146l-74 35z"/>
        <rect x="280" y="232" width="128" height="15"/><rect x="280" y="256" width="128" height="15"/>
      ''',
      "weapon_fg42": '''
        <path d="M35 258l82-49h204l51 31h103v24H320l-58 31H120l-85 38z"/>
        <path d="M205 287h42l23 95h-45z"/><rect x="333" y="225" width="141" height="12"/>
      ''',
      "weapon_gewehr": '''
        <path d="M32 260l92-55h198l70 31h88v24l-153 12-62 28H125l-93 39z"/>
        <path d="M242 286h38l18 91h-42z"/>
      ''',
      "weapon_m1": '''
        <path d="M30 260l98-58h205l54 33h91v25l-146 10-69 27H126l-96 42z"/>
        <rect x="241" y="280" width="22" height="72"/>
      ''',
      "weapon_m1a1": '''
        <path d="M55 258l74-45h176l60 31h107v24H306l-58 28H130l-75 38z"/>
        <path d="M238 287h35l12 88h-40z"/>
      ''',
      "weapon_flamer": '''
        <path d="M52 255l68-40h192l55 30h111v25H302l-49 30H122l-70 33z"/>
        <rect x="194" y="289" width="34" height="100"/><circle cx="274" cy="337" r="41"/>
        <rect x="346" y="228" width="132" height="13"/>
      ''',
      "weapon_mp40": '''
        <path d="M63 250l67-38h180l50 31h108v28H306l-55 25H130l-67 32z"/>
        <path d="M222 289h34l4 114h-39z"/><path d="M93 250L38 190l9-8 72 54z" fill="none" stroke="#fff" stroke-width="13"/>
      ''',
      "weapon_mg42": '''
        <path d="M24 250l88-46h222l58 30h95v29H333l-61 34H113l-89 35z"/>
        <rect x="356" y="220" width="132" height="14"/>
        <path d="M384 266l-51 118h12l61-118zM420 266l53 118h-12l-63-118z"/>
      ''',
      "weapon_panzer": '''
        <rect x="52" y="222" width="384" height="86" rx="38"/><rect x="20" y="240" width="66" height="50" rx="18"/>
        <path d="M195 305h62l-8 93h-55z"/><rect x="427" y="238" width="65" height="54" rx="15"/>
      ''',
      "weapon_ppsh": '''
        <path d="M45 254l78-46h186l62 31h107v28H308l-58 28H125l-80 38z"/>
        <circle cx="278" cy="319" r="55"/><rect x="351" y="226" width="127" height="13"/>
      ''',
      "weapon_ptrs": '''
        <path d="M18 260l101-59h221l70 32h84v26l-154 12-78 29H120l-102 43z"/>
        <rect x="210" y="175" width="156" height="22" rx="10"/>
        <path d="M367 270l-48 115h12l58-115z"/>
      ''',
      "weapon_ray": '''
        <path d="M105 217h190l91 58-52 56H210l-18 103h-73l28-115-42-32z"/>
        <circle cx="292" cy="274" r="62"/><rect x="321" y="191" width="99" height="38" rx="18"/>
      ''',
      "weapon_raymk2": '''
        <path d="M56 245l78-47h224l76 45-43 58H227l-15 105h-63l18-105H82z"/>
        <circle cx="332" cy="253" r="42"/><rect x="355" y="198" width="115" height="23" rx="10"/>
      ''',
      "weapon_stg": '''
        <path d="M36 258l86-52h198l66 34h91v26H319l-61 30H123l-87 39z"/>
        <path d="M242 288h46l-11 105h-50z"/><rect x="365" y="228" width="112" height="12"/>
      ''',
      "weapon_trench": '''
        <path d="M32 263l92-55h197l57 32h101v26H320l-58 27H125l-93 41z"/>
        <rect x="323" y="225" width="157" height="14"/><rect x="309" y="273" width="93" height="18" rx="8"/>
      ''',
      "weapon_type100": '''
        <path d="M55 255l72-42h183l57 31h103v27H306l-55 25H128l-73 35z"/>
        <path d="M226 288h34l-8 105h-39z"/><rect x="347" y="228" width="124" height="12"/>
      ''',
      "weapon_mp5": '''
        <path d="M75 247l51-31h191l50 29h100v31H315l-53 26H128l-53 28z"/>
        <path d="M228 294h35l11 103h-39z"/><path d="M105 250L51 201" fill="none" stroke="#fff" stroke-width="12"/>
      ''',
      "weapon_tesla": '''
        <path d="M72 250l64-40h176l52 34h95v28H309l-54 30H134l-62 35z"/>
        <path d="M215 291h40l-4 101h-44z"/>
        <circle cx="345" cy="236" r="28" fill="none" stroke="#fff" stroke-width="12"/>
        <circle cx="402" cy="236" r="28" fill="none" stroke="#fff" stroke-width="12"/>
        <path d="M353 236h41" stroke="#fff" stroke-width="14"/>
      ''',
      "weapon_springfield": '''
        <path d="M28 260l97-56h204l62 31h88v25l-151 11-67 28H126l-98 40z"/>
        <rect x="242" y="281" width="21" height="70"/><rect x="365" y="226" width="114" height="12"/>
      ''',
    }
    for name, body in silhouettes.items():
        _render_svg(out, name, f'<g fill="#FFFFFF">{body}</g>', 512)


def build_xziel_fps_controls(out: Path) -> None:
    """Render Xziel's original mobile-FPS control language.

    The layout is informed by common mobile-FPS conventions (large primary
    fire, separate ADS, compact reload/jump/crouch utility controls), but all
    vector artwork below is original and generated at build time.
    """
    controls = {
        # Primary fire: the requested bullet over a segmented aiming reticle.
        "fire": '''
          <g fill="none" stroke="#FFFFFF" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="256" cy="256" r="132" stroke-width="18" stroke-opacity=".86"
                    stroke-dasharray="92 34"/>
            <path d="M256 80v54M256 378v54M80 256h54M378 256h54"
                  stroke-width="18" stroke-opacity=".94"/>
          </g>
          <g transform="rotate(-38 256 256)" fill="#FFFFFF">
            <path d="M225 118h62l18 44v196l-49 52-49-52V162z"/>
            <path d="M225 164h80v24h-80z" fill="#111820" fill-opacity=".30"/>
            <path d="M237 118l19-36 19 36z"/>
          </g>
        ''',
        # ADS is deliberately a clean reticle instead of another bullet.
        "ads": '''
          <g fill="none" stroke="#FFFFFF" stroke-linecap="round">
            <circle cx="256" cy="256" r="118" stroke-width="18" stroke-opacity=".94"/>
            <circle cx="256" cy="256" r="24" stroke-width="14"/>
            <path d="M256 76v102M256 334v102M76 256h102M334 256h102"
                  stroke-width="18"/>
          </g>
        ''',
        "reload": '''
          <g fill="none" stroke="#FFFFFF" stroke-width="22" stroke-linecap="round" stroke-linejoin="round">
            <path d="M135 196a142 142 0 0 1 232-40"/>
            <path d="M366 123l18 71-72-13"/>
            <path d="M377 316a142 142 0 0 1-232 40"/>
            <path d="M146 389l-18-71 72 13"/>
          </g>
          <path d="M220 183h74v151l-37 34-37-34z" fill="#FFFFFF"/>
          <path d="M229 202h56v23h-56z" fill="#111820" fill-opacity=".42"/>
        ''',
        "use": '''
          <g fill="#FFFFFF">
            <rect x="221" y="104" width="34" height="164" rx="16"/>
            <rect x="263" y="121" width="34" height="147" rx="16"/>
            <rect x="305" y="153" width="34" height="128" rx="16"/>
            <path d="M174 235c17-25 43-14 62 8l18 21v-28h85v102c0 55-42 91-98 91h-8c-49 0-83-29-101-67l-35-77c-11-25 24-42 39-20z"/>
          </g>
        ''',
        "jump": '''
          <g fill="#FFFFFF">
            <circle cx="266" cy="108" r="30"/>
            <path d="M227 148l70 14 45 58-30 22-34-42-17 78 52 56-27 25-73-66-27-5-55 67-31-24 69-92 25-74z"/>
          </g>
          <path d="M98 405h316" stroke="#FFFFFF" stroke-width="18" stroke-linecap="round" stroke-opacity=".72"/>
        ''',
        "slide": '''
          <g fill="#FFFFFF">
            <circle cx="328" cy="139" r="27"/>
            <path d="M278 168l60 22 46 58-29 22-38-43-73 51 77 27-10 37-110-32-58 55-30-27 78-83z"/>
            <path d="M104 378h297v18H104z" opacity=".76"/>
          </g>
        ''',
        "sprint": '''
          <g fill="#FFFFFF">
            <circle cx="300" cy="112" r="28"/>
            <path d="M252 148l70 18 40 55-30 22-31-36-31 68 67 54-24 31-85-61-44 87-37-18 54-116-54 21-13-35z"/>
          </g>
        ''',
        "knife": '''
          <g fill="#FFFFFF">
            <path d="M100 344l211-211 78-22-22 78-211 211z"/>
            <path d="M123 365l38 38-29 29-38-38z"/>
            <path d="M161 339l53 53-18 18-53-53z"/>
          </g>
        ''',
        "grenade": '''
          <g fill="#FFFFFF">
            <path d="M180 194h151l42 57v126l-52 55H190l-52-55V251z"/>
            <rect x="213" y="135" width="86" height="60" rx="14"/>
            <path d="M292 134l38-40 57 27-16 33-50-13-19 21z"/>
            <circle cx="393" cy="112" r="22" fill="none" stroke="#FFFFFF" stroke-width="15"/>
          </g>
          <path d="M177 268h157M177 320h157" stroke="#111820" stroke-opacity=".28" stroke-width="15"/>
        ''',
        "pause": '''
          <rect x="154" y="112" width="70" height="288" rx="20" fill="#FFFFFF"/>
          <rect x="288" y="112" width="70" height="288" rx="20" fill="#FFFFFF"/>
        ''',
    }
    for name, body in controls.items():
        _render_svg(out, name, body, 512)

    # Thin translucent mobile-FPS surfaces: visible enough to target, without
    # the old oversized compass-like rings around every action.
    touch_idle = '''
      <circle cx="256" cy="256" r="220" fill="#05080B" fill-opacity=".34"/>
      <circle cx="256" cy="256" r="216" fill="none" stroke="#FFFFFF"
              stroke-opacity=".34" stroke-width="10"/>
    '''
    touch_pressed = '''
      <circle cx="256" cy="256" r="222" fill="#0B0E12" fill-opacity=".66"/>
      <circle cx="256" cy="256" r="216" fill="none" stroke="#F4C83D"
              stroke-opacity=".96" stroke-width="16"/>
      <circle cx="256" cy="256" r="186" fill="none" stroke="#F4C83D"
              stroke-opacity=".18" stroke-width="7"/>
    '''
    touch_editor = '''
      <circle cx="256" cy="256" r="222" fill="#071018" fill-opacity=".42"/>
      <circle cx="256" cy="256" r="216" fill="none" stroke="#F2F7FA"
              stroke-opacity=".88" stroke-width="13" stroke-dasharray="36 18"/>
    '''
    for name, body in {
        "touch_idle": touch_idle,
        "touch_pressed": touch_pressed,
        "touch_editor": touch_editor,
    }.items():
        _render_svg(out, name, body, 512)


def build_xziel_v024_assets(out: Path) -> None:
    """Final v0.24 HUD art approved from the visual mockup.

    Keep every action readable at phone size and keep every physical weapon
    family on its own silhouette. PaP aliases are mapped in runtime to the
    silhouette of the same physical gun, never to a generic category icon.
    """
    controls = {
        "jump": '''
          <g fill="#FFFFFF">
            <circle cx="232" cy="112" r="27"/>
            <path d="M205 149l58 16 38 47-27 22-31-34-15 60 47 42-25 29-63-51-31 6-45 59-31-24 58-82 22-77z"/>
            <path d="M307 326l31-43 31 43h-20v82h-23v-82z"/>
          </g>
          <path d="M82 416h292" stroke="#FFFFFF" stroke-width="18" stroke-linecap="round" stroke-opacity=".72"/>
        ''',
        "slide": '''
          <g fill="#FFFFFF">
            <circle cx="307" cy="160" r="25"/>
            <path d="M265 187l60 17 43 38-24 27-40-29-48 41 73 20-9 35-103-24-74 51-25-29 86-72 31-61z"/>
            <path d="M159 320l-68 10 4 18 74-3zM188 352l-93 19 5 18 102-13z" opacity=".82"/>
          </g>
          <path d="M102 414h309" stroke="#FFFFFF" stroke-width="18" stroke-linecap="round" stroke-opacity=".72"/>
        ''',
        "sprint": '''
          <g fill="#FFFFFF">
            <circle cx="301" cy="112" r="27"/>
            <path d="M255 148l67 19 43 51-29 23-32-35-25 61 62 55-26 31-81-63-39 91-38-18 48-116-55 23-15-34 86-45z"/>
            <path d="M107 178h74v16h-74zM83 225h92v16H83zM100 272h64v16h-64z" opacity=".78"/>
          </g>
        ''',
        "reload": '''
          <g fill="none" stroke="#FFFFFF" stroke-width="20" stroke-linecap="round" stroke-linejoin="round">
            <path d="M136 191a146 146 0 0 1 237-37"/>
            <path d="M370 120l17 76-76-15"/>
            <path d="M380 322a146 146 0 0 1-237 37"/>
            <path d="M145 394l-17-76 76 15"/>
          </g>
          <g fill="#FFFFFF">
            <path d="M222 170h72v178l-36 39-36-39z"/>
            <rect x="232" y="194" width="52" height="21" rx="5" fill="#111820" fill-opacity=".35"/>
          </g>
        ''',
        "use": '''
          <g fill="#FFFFFF">
            <rect x="216" y="101" width="31" height="163" rx="15"/>
            <rect x="255" y="116" width="31" height="148" rx="15"/>
            <rect x="294" y="145" width="31" height="130" rx="15"/>
            <rect x="333" y="177" width="31" height="116" rx="15"/>
            <path d="M174 235c18-28 47-15 68 10l19 23v-26h103v97c0 58-45 95-105 95h-12c-53 0-89-31-108-72l-34-76c-12-27 25-45 42-21z"/>
          </g>
        ''',
        "knife": '''
          <g fill="#FFFFFF">
            <path d="M98 352l223-223 83-20-22 82-223 223z"/>
            <path d="M123 367l39 39-31 31-39-39z"/>
            <path d="M156 337l60 60-20 20-60-60z"/>
          </g>
        ''',
        "grenade": '''
          <g fill="#FFFFFF">
            <path d="M175 205h160l43 57v119l-53 54H186l-52-54V262z"/>
            <rect x="213" y="147" width="90" height="58" rx="12"/>
            <path d="M296 146l37-45 59 28-17 35-51-14-20 22z"/>
          </g>
          <circle cx="394" cy="116" r="23" fill="none" stroke="#FFFFFF" stroke-width="14"/>
          <path d="M178 281h157M178 332h157" stroke="#111820" stroke-opacity=".25" stroke-width="14"/>
        ''',
    }
    for name, body in controls.items():
        _render_svg(out, name, body, 512)

    # Premium card surfaces from the approved mockup. The weapon, slot number,
    # name and ammo remain live overlays; this is only the translucent frame.
    card_active = '''
      <defs>
        <linearGradient id="bg" x1="0" x2="1">
          <stop offset="0" stop-color="#050607" stop-opacity=".90"/>
          <stop offset=".60" stop-color="#111418" stop-opacity=".82"/>
          <stop offset="1" stop-color="#080A0D" stop-opacity=".92"/>
        </linearGradient>
      </defs>
      <path d="M18 18H830L998 154v320H18z" fill="url(#bg)"/>
      <path d="M18 18H830L998 154" fill="none" stroke="#D7DDE2" stroke-opacity=".34" stroke-width="7"/>
      <path d="M18 472h980" stroke="#F4C72E" stroke-width="18"/>
      <path d="M18 441h500" stroke="#F4C72E" stroke-width="5" stroke-opacity=".55"/>
      <path d="M210 18l150 0-120 118H90z" fill="#F4C72E" fill-opacity=".07"/>
      <path d="M650 18h120L620 166H500z" fill="#F4C72E" fill-opacity=".05"/>
    '''
    card_inactive = '''
      <path d="M18 18H842L998 145v329H18z" fill="#07090B" fill-opacity=".72"/>
      <path d="M18 18H842L998 145" fill="none" stroke="#C9D0D5" stroke-opacity=".20" stroke-width="6"/>
      <path d="M18 472h980" stroke="#899096" stroke-width="10" stroke-opacity=".52"/>
    '''
    _render_svg(out, "weapon_card_active", card_active, 1024)
    _render_svg(out, "weapon_card_inactive", card_inactive, 1024)

    # Refined, original side-profile silhouettes. These are drawn from public
    # reference research but are original vector geometry. They replace the
    # rough blocky silhouettes from v0.22.
    silhouettes = {
      "weapon_colt": '''
        <path d="M70 197h314l39 13v31l-50 8-52 26-15 129h-75l-55-146H96l-26-17z"/>
        <path d="M148 173h170l35 24H143z"/>
        <path d="M206 258h99l-11 38h-68z" fill="#000000" fill-opacity=".38"/>
        <path d="M394 196l28-24 17 10-15 31z"/>
      ''',
      "weapon_revolver": '''
        <path d="M71 213h246l44 25-25 48H213l-18 126h-68l25-126H91z"/>
        <circle cx="249" cy="259" r="61"/>
        <rect x="311" y="227" width="144" height="26" rx="8"/>
        <path d="M317 213l27-40 24 12-17 43z"/>
      ''',
      "weapon_thompson": '''
        <path d="M35 246l92-57h87v39h152v61H208l-82 51-91-16z"/>
        <rect x="361" y="240" width="120" height="20" rx="5"/>
        <path d="M201 286h39l-8 112h-44z"/>
        <circle cx="286" cy="318" r="58"/>
        <path d="M78 247l-56-61 24-19 84 62z"/>
      ''',
      "weapon_doublebarrel": '''
        <path d="M23 270l104-62h155v62H129L23 320z"/>
        <rect x="276" y="215" width="218" height="17" rx="7"/>
        <rect x="276" y="244" width="218" height="17" rx="7"/>
        <path d="M164 268l37 12-21 99h-43z"/>
      ''',
      "weapon_sawnoff": '''
        <path d="M61 272l88-53h145v61H149l-88 41z"/>
        <rect x="288" y="227" width="139" height="16" rx="7"/>
        <rect x="288" y="253" width="139" height="16" rx="7"/>
        <path d="M178 278h49l-27 92h-45z"/>
      ''',
      "weapon_mp40": '''
        <path d="M54 247l75-37h185l55 31h111v31H310l-54 28H128l-74 31z"/>
        <rect x="220" y="292" width="38" height="121" rx="5"/>
        <path d="M117 247L44 180l12-13 86 61z" fill="none" stroke="#FFFFFF" stroke-width="14"/>
        <path d="M57 181L27 158" fill="none" stroke="#FFFFFF" stroke-width="14"/>
      ''',
      "weapon_ppsh": '''
        <path d="M42 252l83-46h190l61 31h111v29H311l-61 30H125l-83 39z"/>
        <circle cx="281" cy="321" r="60"/>
        <rect x="357" y="224" width="130" height="14"/>
        <path d="M91 249l-50-40 13-15 63 38z"/>
      ''',
      "weapon_mg42": '''
        <path d="M20 247l93-45h226l61 30h97v29H334l-63 35H113l-93 37z"/>
        <rect x="360" y="217" width="138" height="14"/>
        <path d="M390 262l-55 124h14l66-124zM424 262l58 124h-14l-68-124z"/>
        <path d="M88 246l-53-37 12-16 66 37z"/>
      ''',
      "weapon_stg": '''
        <path d="M34 255l89-50h201l67 33h96v28H321l-61 31H123l-89 41z"/>
        <path d="M239 289h49l-14 111h-52z"/>
        <rect x="372" y="225" width="116" height="13"/>
        <path d="M100 254L38 210l12-15 75 39z"/>
      ''',
      "weapon_mp5": '''
        <path d="M66 246l61-32h194l52 29h103v31H317l-55 29H127l-61 30z"/>
        <path d="M226 295h39l12 109h-43z"/>
        <path d="M108 246L49 196l12-14 71 45z" fill="none" stroke="#FFFFFF" stroke-width="13"/>
        <rect x="374" y="235" width="103" height="13"/>
      ''',
      "weapon_trench": '''
        <path d="M29 261l98-54h201l58 31h103v27H323l-61 28H127l-98 43z"/>
        <rect x="329" y="224" width="160" height="14"/>
        <rect x="314" y="270" width="100" height="20" rx="9"/>
        <path d="M83 258l-54-35 14-16 64 33z"/>
      ''',
      "weapon_browning": '''
        <path d="M23 248l90-45h239l52 28h97v30H350l-59 36H112l-89 36z"/>
        <rect x="226" y="286" width="44" height="116"/>
        <rect x="361" y="218" width="140" height="14"/>
        <path d="M393 262l-40 121h14l51-121zM430 262l50 121h-14l-60-121z"/>
      ''',
      "weapon_panzer": '''
        <rect x="47" y="220" width="399" height="89" rx="40"/>
        <rect x="16" y="239" width="70" height="52" rx="17"/>
        <path d="M197 306h64l-10 98h-57z"/>
        <rect x="436" y="237" width="66" height="57" rx="15"/>
        <path d="M122 220l-20-54h25l27 54z"/>
      ''',
      "weapon_ray": '''
        <path d="M92 213h204l103 62-60 62H215l-19 105h-78l30-119-56-34z"/>
        <circle cx="294" cy="276" r="62"/>
        <rect x="321" y="186" width="106" height="42" rx="18"/>
        <path d="M408 206l56-28 16 18-47 39z"/>
      ''',
      "weapon_raymk2": '''
        <path d="M48 242l84-47h231l80 48-47 61H228l-15 110h-67l19-110H77z"/>
        <circle cx="338" cy="255" r="43"/>
        <rect x="362" y="195" width="121" height="25" rx="10"/>
        <path d="M84 243l-49-48 14-15 63 43z"/>
      ''',
    }
    for name, body in silhouettes.items():
        _render_svg(out, name, f'<g fill="#FFFFFF">{body}</g>', 512)


def build_xziel_v025_assets(out: Path) -> None:
    """Phone-readability cleanup for the approved HUD."""
    controls = {
        "jump": '''
          <g fill="#FFFFFF">
            <circle cx="214" cy="122" r="28"/>
            <path d="M184 154l60 13 47 47-27 25-35-31-13 60 53 44-27 31-69-55-34 4-48 61-31-24 62-86 20-75z"/>
            <path d="M321 300l39-51 39 51h-24v100h-29V300z"/>
          </g>
          <path d="M78 416h265" stroke="#FFFFFF" stroke-width="18" stroke-linecap="round" stroke-opacity=".76"/>
        ''',
        "slide": '''
          <g fill="#FFFFFF">
            <circle cx="315" cy="164" r="27"/>
            <path d="M270 193l62 17 48 40-27 29-43-29-48 42 84 24-11 38-116-28-73 49-26-31 88-73 30-62z"/>
            <path d="M155 316H78v18h68zM180 350H65v18h105zM207 384H95v18h102z" opacity=".86"/>
          </g>
          <path d="M103 422h317" stroke="#FFFFFF" stroke-width="18" stroke-linecap="round" stroke-opacity=".76"/>
        ''',
        "sprint": '''
          <g fill="#FFFFFF">
            <circle cx="296" cy="115" r="28"/>
            <path d="M249 151l69 18 46 53-30 24-34-37-25 64 65 57-27 32-84-66-42 94-39-19 52-119-59 23-15-36 91-45z"/>
            <path d="M112 177H52v17h60zM130 225H48v17h82zM115 274H66v17h49z" opacity=".84"/>
          </g>
        ''',
    }
    for name, body in controls.items():
        _render_svg(out, name, body, 512)

    # M1911: unmistakable long slide, trigger guard and rear angled grip.
    # Muzzle points right, matching the in-hand presentation.
    colt = '''
      <g fill="#FFFFFF">
        <rect x="74" y="184" width="332" height="58" rx="7"/>
        <rect x="394" y="197" width="61" height="30" rx="4"/>
        <rect x="111" y="166" width="80" height="18" rx="4"/>
        <rect x="326" y="167" width="15" height="17"/>
        <path d="M132 241h218l-17 47h-49l-18 125h-78l33-125h-62z"/>
        <path d="M289 284l73 2-21 131h-82z"/>
        <path d="M341 184l30-28 22 12-20 28z"/>
      </g>
      <path d="M200 247h91c29 0 48 14 48 36s-19 37-48 37h-58"
            fill="none" stroke="#FFFFFF" stroke-width="24" stroke-linecap="round"/>
      <path d="M228 270h58c13 0 20 5 20 13s-7 14-20 14h-49"
            fill="none" stroke="#050607" stroke-width="12" stroke-linecap="round"/>
    '''
    _render_svg(out, "weapon_colt", colt, 512)

    # Keep the most visually recognizable families strongly distinct.
    revolver = '''
      <g fill="#FFFFFF">
        <rect x="74" y="210" width="244" height="48" rx="8"/>
        <rect x="314" y="218" width="146" height="22" rx="7"/>
        <circle cx="248" cy="252" r="58"/>
        <path d="M185 282h79l-30 132h-72z"/>
        <path d="M315 209l26-39 24 12-16 39z"/>
      </g>
    '''
    _render_svg(out, "weapon_revolver", revolver, 512)

    thompson = '''
      <g fill="#FFFFFF">
        <path d="M36 245l91-61h73v38h169v58H203l-76 54-91-15z"/>
        <rect x="366" y="235" width="122" height="22" rx="5"/>
        <path d="M198 278h42l-11 116h-42z"/>
        <circle cx="288" cy="314" r="58"/>
        <path d="M118 242L42 174l-27 25 92 70z"/>
      </g>
    '''
    _render_svg(out, "weapon_thompson", thompson, 512)

    mp40 = '''
      <g fill="#FFFFFF">
        <path d="M57 244l73-38h189l54 29h111v31H315l-58 29H129l-72 32z"/>
        <rect x="222" y="286" width="39" height="126" rx="5"/>
      </g>
      <path d="M127 244L48 177l-22-16M48 177l-20 28"
            fill="none" stroke="#FFFFFF" stroke-width="14" stroke-linecap="round"/>
    '''
    _render_svg(out, "weapon_mp40", mp40, 512)

    ppsh = '''
      <g fill="#FFFFFF">
        <path d="M40 250l84-47h194l60 30h111v30H313l-62 31H125l-85 40z"/>
        <circle cx="283" cy="318" r="62"/>
        <rect x="359" y="220" width="131" height="15"/>
        <path d="M115 248L53 197l-18 21 67 48z"/>
      </g>
    '''
    _render_svg(out, "weapon_ppsh", ppsh, 512)

    stg = '''
      <g fill="#FFFFFF">
        <path d="M34 253l90-52h205l66 32h96v29H324l-63 32H124l-90 42z"/>
        <path d="M237 286h52l-16 116h-54z"/>
        <rect x="373" y="221" width="118" height="14"/>
        <path d="M119 252L47 203l-19 22 73 47z"/>
      </g>
    '''
    _render_svg(out, "weapon_stg", stg, 512)

    mg42 = '''
      <g fill="#FFFFFF">
        <path d="M19 245l94-47h230l60 29h98v30H338l-65 36H113l-94 38z"/>
        <rect x="364" y="213" width="138" height="15"/>
        <path d="M118 244L51 201l-20 23 70 39z"/>
      </g>
      <path d="M391 258l-58 129M425 258l61 129"
            fill="none" stroke="#FFFFFF" stroke-width="14" stroke-linecap="round"/>
    '''
    _render_svg(out, "weapon_mg42", mg42, 512)

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_xziel_icons.py <output-dir>")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    build_xziel_modern_surfaces(out)
    for name, rel in ICONS.items():
        svg = fetch(f"{BASE}/{rel}").replace(b"currentColor", b"#FFFFFF")
        cairosvg.svg2png(
            bytestring=svg,
            write_to=str(out / f"{name}.png"),
            output_width=256,
            output_height=256,
        )
    # Overwrite generic source-pack glyphs with Xziel's original mobile-FPS controls.
    build_xziel_fps_controls(out)
    build_xziel_v024_assets(out)
    build_xziel_v025_assets(out)

    # Weapon cards use actual CC0 gun artwork rather than a hand-drawn glyph.
    # Kay Lousberg's pack is CC0, transparent PNG, and explicitly includes
    # pistol/revolver/shotgun/sniper/SMG/assault-rifle artwork.
    # OpenGameArt canonical page:
    # https://opengameart.org/content/2d-guns
    try:
        weapon_zip = fetch("https://opengameart.org/sites/default/files/guns_gameassets.zip")
        with zipfile.ZipFile(io.BytesIO(weapon_zip)) as archive:
            names = [
                n for n in archive.namelist()
                if n.lower().endswith(".png")
                and "__macosx" not in n.lower()
                and "spritesheet" not in n.lower()
            ]

            def pick(keyword: str) -> str | None:
                choices = []
                for name in names:
                    base = Path(name).stem.lower()
                    if keyword not in base:
                        continue
                    if any(bad in base for bad in ("magazine", "bullet", "ammo", "box")):
                        continue
                    score = 0
                    if "@2x" in base or "2x" in base:
                        score += 5
                    if "separate" in name.lower() or "individual" in name.lower():
                        score += 3
                    if "alternate" not in name.lower() and "alt" not in base:
                        score += 1
                    choices.append((score, len(name), name))
                if not choices:
                    return None
                choices.sort(key=lambda x: (-x[0], x[1], x[2]))
                return choices[0][2]

            categories = {
                "weapon_pistol.png": "pistol",
                "weapon_revolver.png": "revolver",
                "weapon_shotgun.png": "shotgun",
                "weapon_sniper.png": "sniper",
                "weapon_smg.png": "smg",
                "weapon_assault.png": "assault",
            }
            picked = {}
            for filename, keyword in categories.items():
                selected = pick(keyword)
                if selected:
                    payload = archive.read(selected)
                    (out / filename).write_bytes(payload)
                    picked[keyword] = filename

            # Preserve legacy names used by older checkpoints.
            if "pistol" in picked:
                (out / "pistol.png").write_bytes((out / picked["pistol"]).read_bytes())
            if "assault" in picked:
                (out / "weapon.png").write_bytes((out / picked["assault"]).read_bytes())
    except Exception as exc:
        # The Nieobie CC0 pistol/bullet icons remain a deterministic fallback
        # if OpenGameArt is temporarily unavailable during CI.
        print(f"warning: Kay Lousberg weapon art unavailable: {exc}", file=sys.stderr)

    # CI must always produce every HUD path even when OpenGameArt is down or
    # the upstream archive changes a filename. The fallback images are also
    # CC0 from the already-pinned Nieobie pack.
    fallback_map = {
        "weapon_pistol.png": "pistol.png",
        "weapon_revolver.png": "pistol.png",
        "weapon_shotgun.png": "weapon.png",
        "weapon_sniper.png": "weapon.png",
        "weapon_smg.png": "weapon.png",
        "weapon_assault.png": "weapon.png",
    }
    for dst, src in fallback_map.items():
        target = out / dst
        if not target.exists():
            target.write_bytes((out / src).read_bytes())

    (out / "LICENSE-CC0.txt").write_text(
        "Xziel mobile HUD assets are CC0/public-domain or original Xziel vector art.\n"
        "Touch/action icons: Nieobie/Game-Icon-Pack, CC0 1.0 Universal.\n"
        f"Source revision: {REV}\nhttps://github.com/Nieobie/Game-Icon-Pack\n"
        "Weapon card art: Kay Lousberg, 2D Guns, CC0.\n"
        "https://opengameart.org/content/2d-guns\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
