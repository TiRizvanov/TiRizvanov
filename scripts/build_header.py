"""Build assets/header.svg: name, headline and a rotating backbone of cryptochrome 1 (PDB 1U3D).

GitHub READMEs cannot run scripts, so the rotation is pre-computed: the smoothed C-alpha trace is
projected at FRAMES angles and SMIL interpolates each path's `d` between them.

Usage: python3 scripts/build_header.py [path/to/1u3d.pdb]   (downloads the file when no path is given)
"""
import math
import pathlib
import sys
import urllib.request

import numpy as np

PDB_URL = "https://files.rcsb.org/download/1U3D.pdb"
CHAIN = "A"
# Trp triad of Arabidopsis cryptochrome 1, ordered outward from the flavin.
TRIAD = (400, 377, 324)
FRAMES = 20
PERIOD_S = 26
CENTER = (1012, 152)
RADIUS = 122
TILT = math.radians(18)
# Short segments so each can fade with its own depth: far strands dim, near strands bright.
SEGMENTS = 40
BLUE, VIOLET = (0x70, 0xBE, 0xFA), (0xA7, 0x8B, 0xFA)
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "header.svg"


def read_structure(lines):
    """Return (C-alpha coords in chain order, {resseq: index}, FAD N5 coord)."""
    trace, index, flavin = [], {}, None
    for line in lines:
        record, atom, resname, chain = line[:6].strip(), line[12:16].strip(), line[17:20], line[21]
        if chain != CHAIN or record not in ("ATOM", "HETATM"):
            continue
        xyz = [float(line[30:38]), float(line[38:46]), float(line[46:54])]
        if record == "ATOM" and atom == "CA" and line[16] in " A":
            index[int(line[22:26])] = len(trace)
            trace.append(xyz)
        elif resname == "FAD" and atom == "N5":
            flavin = xyz
    for resseq in TRIAD:
        line_resname = next(l[17:20] for l in lines if l.startswith("ATOM") and l[21] == CHAIN
                            and int(l[22:26]) == resseq)
        if line_resname != "TRP":
            raise ValueError(f"residue {resseq} is {line_resname}, expected TRP")
    if flavin is None:
        raise ValueError("FAD N5 atom not found")
    return np.array(trace), index, np.array(flavin)


def smooth(trace):
    """Binomial smoothing turns helices into tubes, which reads as a ribbon at this size."""
    kernel = np.array([1, 4, 6, 4, 1]) / 16
    padded = np.vstack([trace[:1], trace[:1], trace, trace[-1:], trace[-1:]])
    return sum(w * padded[i:i + len(trace)] for i, w in enumerate(kernel))


def project(points, angle):
    """Rotate about the vertical axis and tilt toward the viewer; returns screen x, y and depth."""
    c, s = math.cos(angle), math.sin(angle)
    x = points[:, 0] * c + points[:, 2] * s
    z = -points[:, 0] * s + points[:, 2] * c
    y = points[:, 1] * math.cos(TILT) - z * math.sin(TILT)
    depth = points[:, 1] * math.sin(TILT) + z * math.cos(TILT)
    return np.column_stack([CENTER[0] + x, CENTER[1] - y, depth])


def polyline(xy):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in xy)


def rounded_path(xy):
    """Quadratic curves through the midpoints, with the vertices as control points."""
    mid = (xy[:-1] + xy[1:]) / 2
    curves = "".join(f" Q{cx:.1f},{cy:.1f} {mx:.1f},{my:.1f}"
                     for (cx, cy), (mx, my) in zip(xy[1:-1], mid[1:]))
    return f"M{mid[0][0]:.1f},{mid[0][1]:.1f}{curves}"


def animate(attribute, per_frame):
    values = ";".join(per_frame + per_frame[:1])
    return (f'<animate attributeName="{attribute}" dur="{PERIOD_S}s" repeatCount="indefinite" '
            f'values="{values}"/>')


def chain_colour(t):
    return "#" + "".join(f"{round(a + (b - a) * t):02x}" for a, b in zip(BLUE, VIOLET))


def protein_markup(trace, index, flavin):
    centroid = trace.mean(axis=0)
    centred = smooth(trace) - centroid
    # Put the longest principal axis upright so the molecule spins like a top instead of tumbling.
    _, _, axes = np.linalg.svd(centred, full_matrices=False)
    to_frame = np.array([axes[1], axes[0], axes[2]])
    scale = RADIUS / np.linalg.norm(centred, axis=1).max()
    body = centred @ to_frame.T * scale
    marks = (np.vstack([flavin, trace[[index[r] for r in TRIAD]]]) - centroid) @ to_frame.T * scale

    angles = [2 * math.pi * k / FRAMES for k in range(FRAMES)]
    body_frames = [project(body[::2], a) for a in angles]
    mark_frames = [project(marks, a) for a in angles]

    parts = []
    edges = np.linspace(0, len(body_frames[0]) - 1, SEGMENTS + 1).round().astype(int)
    for i, (start, stop) in enumerate(zip(edges[:-1], edges[1:])):
        # One point of overlap on each side keeps neighbouring segments joined at their midpoints.
        chunks = [frame[max(start - 1, 0):stop + 2] for frame in body_frames]
        per_frame = [rounded_path(chunk[:, :2]) for chunk in chunks]
        opacity = [f"{0.3 + 0.7 * (chunk[:, 2].mean() + RADIUS) / (2 * RADIUS):.2f}" for chunk in chunks]
        parts.append(f'<path d="{per_frame[0]}" stroke="{chain_colour(i / (SEGMENTS - 1))}" '
                     f'stroke-opacity="{opacity[0]}">{animate("d", per_frame)}'
                     f'{animate("stroke-opacity", opacity)}</path>')
    backbone = ('<g fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
                + "".join(parts) + "</g>")

    relay_frames = [polyline(frame[:, :2]) for frame in mark_frames]
    relay = (f'<path d="{relay_frames[0]}" fill="none" stroke="#ffffff" stroke-opacity="0.9" '
             f'stroke-width="1.6" stroke-dasharray="3 5">{animate("d", relay_frames)}'
             '<animate attributeName="stroke-dashoffset" from="16" to="0" dur="1.2s" '
             'repeatCount="indefinite"/></path>')
    dots = []
    for j in range(len(marks)):
        radius, fill = (5.5, "#ffffff") if j == 0 else (3.6, "#dbeafe")
        xs = [f"{frame[j, 0]:.1f}" for frame in mark_frames]
        ys = [f"{frame[j, 1]:.1f}" for frame in mark_frames]
        dots.append(f'<circle r="{radius}" fill="{fill}" cx="{xs[0]}" cy="{ys[0]}">'
                    f'{animate("cx", xs)}{animate("cy", ys)}</circle>')
    return backbone + relay + "".join(dots)


def header_svg(protein):
    cx, cy = CENTER
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 320" width="1200" height="320" role="img" aria-label="Timur Rizvanov - Co-Founder and CTO at MacroGlide; computational chemistry, spatial biology, GPU and database-accelerated scientific software; Chemistry and CS at Boston University. Beside the text, a rotating backbone of cryptochrome 1 with its flavin and tryptophan triad marked.">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0a0a0a"/>
      <stop offset="1" stop-color="#0e1430"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#70befa"/>
      <stop offset="1" stop-color="#a78bfa"/>
    </linearGradient>
    <linearGradient id="name" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#b9dcfd"/>
    </linearGradient>
    <radialGradient id="glow">
      <stop offset="0" stop-color="#70befa" stop-opacity="0.22"/>
      <stop offset="1" stop-color="#70befa" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="frame"><rect width="1200" height="320" rx="18"/></clipPath>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="1200" height="320" fill="url(#bg)"/>
    <circle cx="{cx}" cy="{cy}" r="170" fill="url(#glow)"/>
    {protein}
    <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
      <text x="{cx}" y="304" font-size="12" text-anchor="middle" fill="#6e7681">Cryptochrome 1 (PDB 1U3D) - flavin and Trp triad</text>
      <text x="64" y="118" font-size="62" font-weight="700" letter-spacing="-1.5" fill="url(#name)">Timur Rizvanov</text>
      <rect x="66" y="142" width="250" height="4" rx="2" fill="url(#accent)"/>
      <text x="64" y="192" font-size="25" font-weight="600" fill="#b9dcfd">Co-Founder &amp; CTO @ MacroGlide</text>
      <text x="64" y="232" font-size="18" fill="#c9d1d9">Computational Chemistry • Spatial Biology • GPU &amp; Database-Accelerated Scientific Software</text>
      <text x="64" y="264" font-size="18" fill="#8b949e">Chemistry + CS @ Boston University</text>
    </g>
  </g>
</svg>
'''


def main():
    if len(sys.argv) > 1:
        lines = pathlib.Path(sys.argv[1]).read_text().splitlines()
    else:
        with urllib.request.urlopen(PDB_URL, timeout=60) as response:
            lines = response.read().decode().splitlines()
    trace, index, flavin = read_structure(lines)
    OUT.write_text(header_svg(protein_markup(trace, index, flavin)))
    print(f"{OUT.name}: {len(trace)} residues, {FRAMES} frames, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
