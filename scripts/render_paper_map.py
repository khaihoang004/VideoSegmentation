"""Render the curated paper map without importing the training package.

Requires matplotlib. Run from any directory; source data stays in docs/paper_map.json.
"""

import argparse
import json
from pathlib import Path
import textwrap

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
except ImportError as error:
    raise SystemExit("Install figure dependency: python -m pip install matplotlib") from error


ROOT = Path(__file__).resolve().parents[1]
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none",
                     "svg.hashsalt": "videosegmentation-paper-map-v01"})
INK, MUTED = "#172338", "#526277"
STATUS = {"N": ("#d1fae5", "#065f46"), "R": ("#fef3c7", "#92400e"),
          "-": ("#f1f5f9", "#64748b")}


def load_data():
    data = json.loads((ROOT / "docs/paper_map.json").read_text())
    sources = {p["id"]: p for p in json.loads((ROOT / "papers/manifest.json").read_text())["papers"]}
    papers = {p["id"]: p for p in data["papers"]}
    components = {c["id"] for c in data["components"]}
    members = [p for g in data["groups"] for p in g["members"]]
    if len(papers) != len(data["papers"]) or set(papers) != set(sources):
        raise ValueError("Paper IDs must match the PDF manifest, without duplicates")
    if len(members) != len(set(members)) or set(members) != set(papers):
        raise ValueError("Each paper must have exactly one primary group")
    for paper in papers.values():
        if not set(paper["coverage"]) <= components or not set(paper["coverage"].values()) <= {"N", "R"}:
            raise ValueError(f"Bad component/status in {paper['id']}")
        if not (ROOT / "papers" / sources[paper["id"]]["filename"]).is_file():
            raise ValueError(f"Missing PDF for {paper['id']}")
    return data, papers, sources


def canvas(width, height):
    fig = plt.figure(figsize=(width / 100, height / 100), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, width), ylim=(height, 0))
    ax.axis("off")
    return fig, ax


def label(ax, x, y, text, size=11, color=INK, **kwargs):
    return ax.text(x, y, text, fontsize=size, color=color, va="center", **kwargs)


def box(ax, x, y, width, height, fill, edge, radius=12):
    patch = FancyBboxPatch((x, y), width, height,
                          boxstyle=f"round,pad=0,rounding_size={radius}",
                          facecolor=fill, edgecolor=edge, linewidth=1.2)
    ax.add_patch(patch)


def wrapped(ax, x, y, text, width=73, size=11, color=INK):
    for i, line in enumerate(textwrap.wrap(text, width=width)):
        label(ax, x, y + i * 21, line, size, color)


def save(fig, stem, preview_dir):
    assets = ROOT / "docs/figures"
    assets.mkdir(parents=True, exist_ok=True)
    path = assets / f"{stem}.svg"
    fig.savefig(path, metadata={"Date": None})
    # Matplotlib emits trailing spaces in multiline SVG paths; retain newline
    # separators while keeping generated assets clean under git diff --check.
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")
    if preview_dir:
        preview_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(preview_dir / f"{stem}.png", dpi=100)
    plt.close(fig)


def taxonomy(data, papers, sources, preview_dir):
    fig, ax = canvas(1400, 1190)
    label(ax, 40, 43, "Bản đồ paper: 8 nhóm theo bài toán chính", 23, weight="bold")
    label(ax, 40, 81, "23 paper • một nhóm chính mỗi bài; kỹ thuật giao nhau xem ma trận thành phần", 12, MUTED)
    box(ax, 440, 120, 520, 72, "#eff6ff", "#2563eb")
    label(ax, 700, 147, "Định vị online toàn lượt công việc", 17, ha="center", weight="bold")
    label(ax, 700, 173, "Exocentric • nhiều lượt • pause/repair • completion", 11, ha="center")
    ax.plot([700, 700], [192, 987], color="#94a3b8", lw=1.3, zorder=0)
    for i, group in enumerate(data["groups"]):
        x, y = (40 if i % 2 == 0 else 750), 230 + (i // 2) * 220
        edge = x + 610 if i % 2 == 0 else x
        ax.add_patch(FancyArrowPatch((700, y + 97), (edge, y + 97), arrowstyle="-|>",
                                    mutation_scale=12, color="#94a3b8", lw=1.3, zorder=0))
        box(ax, x, y, 610, 195, "#fafcfe", group["color"])
        label(ax, x + 20, y + 27, f"{group['id']} · {group['name']}", 13.5,
              group["color"], weight="bold")
        lines = [""]
        for pid in group["members"]:
            name = f"{pid} {papers[pid]['name']}"
            candidate = lines[-1] + (" · " if lines[-1] else "") + name
            if len(candidate) > 65:
                lines.append(name)
            else:
                lines[-1] = candidate
        for line_index, line in enumerate(lines):
            label(ax, x + 20, y + 61 + line_index * 21, line, 11.2)
        wrapped(ax, x + 20, y + 115, "Xử lý: " + group["handles"], size=10.8)
        wrapped(ax, x + 20, y + 157, "Giới hạn: " + group["limit"], size=10.5, color=MUTED)
    label(ax, 40, 1134, "Cạnh = thuộc nhóm nghiên cứu; không phải quan hệ trích dẫn hoặc module đã ghép thành hệ thống.", 11, MUTED)
    label(ax, 40, 1160, f"Khảo sát v{data['version']} · {data['updated']} · phạm vi/nguồn: docs/paper_map.md", 10, MUTED)
    save(fig, "paper_taxonomy", preview_dir)


def coverage(data, papers, sources, preview_dir):
    fig, ax = canvas(1450, 1460)
    label(ax, 40, 43, "Paper × thành phần đã xử lý", 24, weight="bold")
    label(ax, 40, 81, "N = trực tiếp trong setting gốc     R = liên quan, cần thích nghi     – = chưa ghi nhận", 12, MUTED)
    label(ax, 40, 112, "Không cộng ô thành điểm, không xếp hạng model; N ở completion có thể chỉ là cấp bước/action.", 11, MUTED)
    left, cell, row_height, y = 390, 111, 40, 215
    for col, component in enumerate(data["components"]):
        center = left + col * cell + cell / 2
        label(ax, center, 161, component["id"], 13, ha="center", weight="bold")
        label(ax, center, 187, component["label"], 10.5, ha="center")
    for group in data["groups"]:
        start = y
        for pid in group["members"]:
            paper = papers[pid]
            label(ax, 49, y + 19, f"{pid}  {paper['name']}", 11,
                  url=sources[pid]["source_url"])
            label(ax, 350, y + 19, group["id"], 9, group["color"], ha="right")
            for col, component in enumerate(data["components"]):
                status = paper["coverage"].get(component["id"], "-")
                fill, ink = STATUS[status]
                ax.add_patch(Rectangle((left + col * cell, y), cell - 5, row_height - 4,
                                       facecolor=fill, edgecolor="white"))
                label(ax, left + col * cell + (cell - 5) / 2, y + 18,
                      "–" if status == "-" else status, 12, ink, ha="center", weight="bold")
            y += row_height
        ax.add_patch(Rectangle((34, start), 5, y - start - 4,
                               facecolor=group["color"], edgecolor="none"))
        y += 15
    label(ax, 40, 1307, "C Causal    I Interval    H Cấu trúc/tiến trình    G Goal achievement    M Bộ nhớ dài", 11, MUTED)
    label(ax, 40, 1336, "U Xác suất/prior/duration    V Unseen-view    L Giảm nhãn    E Protocol/metric/latency", 11, MUTED)
    label(ax, 40, 1379, "Chưa xác lập trong tập bài này: toàn lượt + ownership qua pause/repair + completion đúng + exo + emission online.", 11, INK)
    label(ax, 40, 1412, "N không chứng minh real-time end-to-end hoặc khả năng giải task đích; đọc setting và giới hạn ở bảng chi tiết.", 10.5, MUTED)
    label(ax, 40, 1440, f"Khảo sát v{data['version']} · {data['updated']} · dữ liệu: docs/paper_map.json", 10, MUTED)
    save(fig, "paper_coverage", preview_dir)


def update_tables(data, papers, sources):
    def paper_link(pid):
        return f"[{pid} {papers[pid]['name']}](../papers/{sources[pid]['filename']})"

    lines = ["| Paper | Nhóm | " + " | ".join(c["id"] for c in data["components"]) + " |",
             "| --- | --- | " + " | ".join(":---:" for _ in data["components"]) + " |"]
    evidence = ["| Paper / bằng chứng | Setting và phần xử lý trực tiếp | Giới hạn với bài toán đích |",
                "| --- | --- | --- |"]
    for group in data["groups"]:
        for pid in group["members"]:
            paper = papers[pid]
            values = " | ".join(paper["coverage"].get(c["id"], "–") for c in data["components"])
            lines.append(f"| {paper_link(pid)} | {group['id']} | {values} |")
            evidence.append(f"| {paper_link(pid)}; [nguồn]({sources[pid]['source_url']}). {paper['evidence']} "
                            f"| **{paper['setting']}** {paper['solves']} | {paper['gap']} |")
    path = ROOT / "docs/paper_map.md"
    content = path.read_text()
    for name, rows in [("COVERAGE", lines), ("EVIDENCE", evidence)]:
        opening, closing = f"<!-- BEGIN {name} -->", f"<!-- END {name} -->"
        if content.count(opening) != 1 or content.count(closing) != 1:
            raise ValueError(f"Missing/duplicate {name} markers")
        before, rest = content.split(opening)
        _, after = rest.split(closing)
        content = before + opening + "\n\n" + "\n".join(rows) + "\n\n" + closing + after
    path.write_text(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir", type=Path, help="Optionally also write PNG previews")
    args = parser.parse_args()
    data, papers, sources = load_data()
    taxonomy(data, papers, sources, args.preview_dir)
    coverage(data, papers, sources, args.preview_dir)
    update_tables(data, papers, sources)
    print(f"Rendered {len(papers)} papers / {len(data['groups'])} groups; updated SVGs and Markdown tables")


if __name__ == "__main__":
    main()
