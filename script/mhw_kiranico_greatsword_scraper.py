import re
import time
import csv
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://mhworld.kiranico.com"
LIST_URL = "https://mhworld.kiranico.com/zh/weapons?type=0"

COLORS = ["red", "orange", "yellow", "green", "blue", "white", "purple"]

SHARPNESS_RAW_MULTIPLIER = {
    "red": 0.50,
    "orange": 0.75,
    "yellow": 1.00,
    "green": 1.05,
    "blue": 1.20,
    "white": 1.32,
    "purple": 1.39,
    "none": 0.00,
}

SHARPNESS_ELEMENT_MULTIPLIER = {
    "red": 0.25,
    "orange": 0.50,
    "yellow": 0.75,
    "green": 1.00,
    "blue": 1.0625,
    "white": 1.125,
    "purple": 1.25,
    "none": 0.00,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

EXCLUDE_KEYWORDS = [
    "防卫队",
    "防衛隊",
    "激昂",
    "猛爆",
    "绚辉",
    "絢輝",
    "冥赤",
    "煌黑",
    "煌黒",
    "黑龙",
    "黑龍",
    "Fatalis",
    "Alatreon",
    "Safi",
    "Kulve",
]

INCLUDE_NOTES = [
    "公会 / 宫殿系保留",
    "古龙素材武器保留",
    "金火龙 / 银火龙保留",
    "普通怪物素材 Final Upgrade 保留",
]


def get_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def normalize_url(href: str) -> str:
    return urljoin(BASE_URL, href)


def extract_weapon_links_from_list_page(list_html: str) -> list[str]:
    """
    从 Kiranico 大剑列表页提取所有武器详情页链接。

    注意：
    如果你只想抓 Final Upgrade，建议在浏览器中打开 Kiranico 页面，
    手动切到 Final Upgrades 后，用浏览器 Console 导出当前显示链接。
    这个函数默认会抓页面 HTML 中出现的所有大剑链接。
    """
    soup = BeautifulSoup(list_html, "html.parser")

    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/zh/weapons/" not in href:
            continue

        full_url = normalize_url(href)

        if full_url not in seen:
            links.append(full_url)
            seen.add(full_url)

    return links


def extract_urls_from_text(text: str) -> list[str]:
    """
    从任意文本中提取 Kiranico 武器详情页 URL。

    兼容两种情况：
    1. 每个 URL 真实换行；
    2. 整个文件只有一行，但里面包含字面量 \\n。
    """
    text = text.replace("\\\\n", "\n")
    text = text.replace("\\n", "\n")

    pattern = r"https://mhworld\.kiranico\.com/zh/weapons/[A-Za-z0-9]+/[A-Za-z0-9_\-]+"
    urls = re.findall(pattern, text)

    deduped = []
    seen = set()

    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)

    return deduped


def read_urls_from_txt(path: str) -> list[str]:
    """
    可选：如果你已经从浏览器 Console 导出了 Final Upgrade 链接，
    可以保存为 greatsword_final_urls.txt，然后用这个函数读取。

    注意：
    如果 txt 文件里不是实际换行，而是出现了字面量 \\n，
    这个函数也会自动拆分。
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    return extract_urls_from_text(text)


def parse_sharpness_bar(bar) -> tuple[dict, dict, str]:
    """
    解析单条锋利度条。

    Kiranico 中每个颜色段类似：
    <div style="width: 22.5px" class="sharpness-purple"></div>

    已验证：
    px × 4 = 游戏内斩味单位
    """
    px = {color: 0.0 for color in COLORS}

    for div in bar.find_all("div"):
        cls = div.get("class", [])
        style = div.get("style", "")

        color = None

        for c in COLORS:
            if f"sharpness-{c}" in cls:
                color = c
                break

        if color is None:
            continue

        match = re.search(r"width:\s*([\d.]+)px", style)

        if match:
            px[color] = float(match.group(1))

    units = {color: px[color] * 4 for color in COLORS}

    max_sharpness = "none"

    for color in reversed(COLORS):
        if units[color] > 0:
            max_sharpness = color
            break

    return px, units, max_sharpness


def extract_sharpness(soup: BeautifulSoup) -> dict:
    """
    解析基础斩味与匠 5 后斩味。

    已验证：
    height: 5px = 基础斩味 / 无匠
    height: 3px = 匠 5 后斩味
    """
    result = {}

    bars = soup.find_all("div", class_="d-flex")

    for bar in bars:
        style = bar.get("style", "")

        if "height: 5px" in style:
            px, units, max_s = parse_sharpness_bar(bar)

            result["base_px"] = px
            result["base_units"] = units
            result["base_max_sharpness"] = max_s
            result["base_total_units"] = sum(units.values())

        elif "height: 3px" in style:
            px, units, max_s = parse_sharpness_bar(bar)

            result["handicraft5_px"] = px
            result["handicraft5_units"] = units
            result["handicraft5_max_sharpness"] = max_s
            result["handicraft5_total_units"] = sum(units.values())

    if "base_total_units" in result and "handicraft5_total_units" in result:
        result["handicraft_gain_units"] = (
            result["handicraft5_total_units"] - result["base_total_units"]
        )
        result["can_extend_by_handicraft"] = result["handicraft_gain_units"] > 0
    else:
        result["handicraft_gain_units"] = None
        result["can_extend_by_handicraft"] = None

    return result


def classify_handicraft_value(row: dict) -> str:
    base_max = row.get("base_max_sharpness")
    handi_max = row.get("handicraft5_max_sharpness")

    base_white = row.get("base_white_units") or 0
    base_purple = row.get("base_purple_units") or 0

    handi_white = row.get("handicraft5_white_units") or 0
    handi_purple = row.get("handicraft5_purple_units") or 0

    gain = row.get("handicraft_gain_units")

    if gain is None:
        return "unknown"

    if gain <= 0:
        return "no_effect"

    if base_purple > 0 and handi_purple > base_purple:
        return "extends_purple"

    if base_purple <= 0 and handi_purple > 0:
        return "unlocks_purple"

    if base_white > 0 and handi_white > base_white and handi_purple <= 0:
        return "extends_white"

    if base_white <= 0 and handi_white > 0:
        return "unlocks_white"

    if base_max == handi_max:
        return "extends_same_tier"

    return "other"


def parse_slots_from_soup(soup: BeautifulSoup) -> tuple[int | None, int | None, int | None]:
    """
    解析 Kiranico 武器详情页的镶嵌槽。

    页面结构示例：
    <td>
        <strong>
            <img src=".../slot_size_2.png" width="16">
            <img src=".../slot_size_2.png" width="16">
        </strong>
        <div class="balance-label ...">镶嵌槽</div>
    </td>

    返回：
    - 有一个一级孔：slot_1=1, slot_2=None, slot_3=None
    - 有两个二级孔：slot_1=2, slot_2=2, slot_3=None
    - 无孔：slot_1=None, slot_2=None, slot_3=None
    """
    slot_sizes = []

    # 优先定位 label 为“镶嵌槽”的 td
    for label in soup.find_all("div", class_="balance-label"):
        label_text = label.get_text(strip=True)

        if label_text != "镶嵌槽":
            continue

        td = label.find_parent("td")

        if td is None:
            continue

        for img in td.find_all("img"):
            src = img.get("src", "")
            match = re.search(r"slot_size_([1-4])\.png", src)

            if match:
                slot_sizes.append(int(match.group(1)))

        break

    # 保底：如果结构变化，直接全页面搜索 slot_size 图标
    if not slot_sizes:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            match = re.search(r"slot_size_([1-4])\.png", src)

            if match:
                slot_sizes.append(int(match.group(1)))

    # Kiranico 页面通常按孔位顺序显示；这里保留原顺序，不排序。
    slot_sizes = slot_sizes[:3]

    while len(slot_sizes) < 3:
        slot_sizes.append(None)

    return slot_sizes[0], slot_sizes[1], slot_sizes[2]


def parse_weapon_detail(url: str) -> dict:
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    weapon_name = None

    # Kiranico 武器详情页的武器名通常在 project-title 中，而不是 h1。
    title_node = soup.select_one(".project-title h5 .align-self-center")
    if title_node:
        weapon_name = title_node.get_text(strip=True)

    # 备用：面包屑最后一项。
    if not weapon_name:
        breadcrumb_active = soup.select_one(".breadcrumb-item.active")
        if breadcrumb_active:
            weapon_name = breadcrumb_active.get_text(strip=True)

    # 备用：武器图标 alt。
    if not weapon_name:
        icon_img = soup.select_one(".project-title img[alt]")
        if icon_img:
            weapon_name = icon_img.get("alt", "").strip()

    # 最后备用：如果页面结构变化，再尝试 h1。
    if not weapon_name:
        h1 = soup.find("h1")
        weapon_name = h1.get_text(strip=True) if h1 else None

    # 武器类型：详情页通常会出现“大剑 - 描述”
    weapon_type = "大剑" if "大剑" in text else None

    rarity = None
    match = re.search(r"稀有度\s*([0-9]+)", text)
    if match:
        rarity = int(match.group(1))

    display_attack = None
    true_raw = None

    # 例：1344 | 280
    match = re.search(r"([0-9]{3,4})\s*\|\s*([0-9]{2,3})", text)
    if match:
        display_attack = int(match.group(1))
        true_raw = int(match.group(2))

    affinity = 0

    # 常见结构：0% 会心率 / -30% 会心率 / +10% 会心率
    match = re.search(r"([+-]?[0-9]+)%\s*会心率", text)
    if match:
        affinity = int(match.group(1))

    defense_bonus = 0

    # 常见结构：(+30) 防御力加成
    match = re.search(r"\(\+([0-9]+)\)\s*防御力加成", text)
    if match:
        defense_bonus = int(match.group(1))

    element_type = None
    element_value = None
    is_hidden_element = False

    # 例：龙 240 属性
    # 例：(水 480) 属性
    element_pattern = r"(\(?\s*(火|水|雷|冰|龙|毒|麻痹|睡眠|爆破)\s*([0-9]+)\s*\)?)\s*属性"
    match = re.search(element_pattern, text)

    if match:
        full_element_text = match.group(1)
        element_type = match.group(2)
        element_value = int(match.group(3))
        is_hidden_element = "(" in full_element_text and ")" in full_element_text

    elderseal = None
    match = re.search(r"(小|中|大)\s*龙封力", text)
    if match:
        elderseal = match.group(1)

    slot_1, slot_2, slot_3 = parse_slots_from_soup(soup)

    sharpness = extract_sharpness(soup)

    row = {
        "weapon_name": weapon_name,
        "weapon_url": url,
        "weapon_type": weapon_type,
        "rarity": rarity,
        "display_attack": display_attack,
        "true_raw": true_raw,
        "affinity": affinity,
        "element_type": element_type,
        "element_value": element_value,
        "is_hidden_element": is_hidden_element,
        "defense_bonus": defense_bonus,
        "elderseal": elderseal,
        "slot_1": slot_1,
        "slot_2": slot_2,
        "slot_3": slot_3,
    }

    base_px = sharpness.get("base_px", {})
    base_units = sharpness.get("base_units", {})

    handi_px = sharpness.get("handicraft5_px", {})
    handi_units = sharpness.get("handicraft5_units", {})

    for color in COLORS:
        row[f"base_{color}_px"] = base_px.get(color)
        row[f"base_{color}_units"] = base_units.get(color)

        row[f"handicraft5_{color}_px"] = handi_px.get(color)
        row[f"handicraft5_{color}_units"] = handi_units.get(color)

    row["base_total_units"] = sharpness.get("base_total_units")
    row["base_max_sharpness"] = sharpness.get("base_max_sharpness")
    row["base_raw_sharpness_multiplier"] = SHARPNESS_RAW_MULTIPLIER.get(
        row["base_max_sharpness"], None
    )
    row["base_element_sharpness_multiplier"] = SHARPNESS_ELEMENT_MULTIPLIER.get(
        row["base_max_sharpness"], None
    )

    row["handicraft5_total_units"] = sharpness.get("handicraft5_total_units")
    row["handicraft5_max_sharpness"] = sharpness.get("handicraft5_max_sharpness")
    row["handicraft5_raw_sharpness_multiplier"] = SHARPNESS_RAW_MULTIPLIER.get(
        row["handicraft5_max_sharpness"], None
    )
    row["handicraft5_element_sharpness_multiplier"] = SHARPNESS_ELEMENT_MULTIPLIER.get(
        row["handicraft5_max_sharpness"], None
    )

    row["handicraft_gain_units"] = sharpness.get("handicraft_gain_units")
    row["can_extend_by_handicraft"] = sharpness.get("can_extend_by_handicraft")

    row["handicraft_value_type"] = classify_handicraft_value(row)

    return row


def classify_source_category(row: dict) -> str:
    """
    给武器来源做人工规则标记。

    注意：
    - 公会 / 宫殿系保留，但标记为 guild_palace。
    - 罪罚粉碎者 II 当前按用户核验结果保留，不按猛爆碎龙删除。
    - 真正需要删除的特殊来源仍通过 EXCLUDE_KEYWORDS 或后续人工核验处理。
    """
    name = row.get("weapon_name") or ""
    url = row.get("weapon_url") or ""

    guild_palace_keywords = [
        "公会",
        "公會",
        "宫廷",
        "宮廷",
        "宫殿",
        "宮殿",
        "gong-hui",
        "gong-ting",
        "gong-dian",
        "jin-xing",
    ]

    if any(keyword in name or keyword in url for keyword in guild_palace_keywords):
        return "guild_palace"

    return "material_or_elder"


def apply_filter_rules(row: dict) -> dict:
    name = row.get("weapon_name") or ""
    url = row.get("weapon_url") or ""

    row["source_category"] = classify_source_category(row)
    row["include_in_model"] = True
    row["exclude_reason"] = ""

    # 用户核验：罪罚粉碎者 II 不是猛爆碎龙武器，保留。
    keep_keywords = [
        "罪罚粉碎者",
        "罪罰粉碎者",
        "zui-fa-fen-sui-zhe",
    ]

    if any(keyword in name or keyword in url for keyword in keep_keywords):
        return row

    for keyword in EXCLUDE_KEYWORDS:
        if keyword in name or keyword in url:
            row["include_in_model"] = False
            row["exclude_reason"] = keyword
            return row

    return row


def write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        print(f"No rows to write: {path}")
        return

    fieldnames = sorted(set().union(*(row.keys() for row in rows)))

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def scrape_from_list_page() -> list[str]:
    print(f"Loading list page: {LIST_URL}")
    html = get_html(LIST_URL)
    links = extract_weapon_links_from_list_page(html)
    print(f"Found {len(links)} weapon detail links")
    return links


def scrape_from_url_file(path: str) -> list[str]:
    links = read_urls_from_txt(path)
    print(f"Loaded {len(links)} URLs from {path}")
    return links


def main():
    """
    默认模式：
    直接从 Kiranico 大剑列表页抓所有出现的武器详情页。

    如果你想只抓 Final Upgrade：
    1. 在浏览器中打开 Kiranico 大剑页面
    2. 手动切到 Final Upgrades
    3. Console 执行：
       const links = [...document.querySelectorAll('a[href*="/zh/weapons/"]')]
         .map(a => a.href)
         .filter((v, i, arr) => arr.indexOf(v) === i);
       console.log(links.join("\\n"));
    4. 保存为 greatsword_final_urls.txt
    5. 把下面 use_url_file 改成 True
    """
    use_url_file = True
    url_file_path = "greatsword_final_urls.txt"

    if use_url_file:
        links = scrape_from_url_file(url_file_path)
    else:
        links = scrape_from_list_page()

    rows = []

    for index, url in enumerate(links, start=1):
        print(f"[{index}/{len(links)}] {url}")

        try:
            row = parse_weapon_detail(url)
            row = apply_filter_rules(row)
            rows.append(row)
            time.sleep(0.5)
        except Exception as error:
            print(f"Failed: {url}")
            print(error)

    raw_path = "mhw_greatsword_raw.csv"
    filtered_path = "mhw_greatsword_filtered.csv"

    write_csv(raw_path, rows)

    filtered_rows = [row for row in rows if row.get("include_in_model") is True]
    write_csv(filtered_path, filtered_rows)

    print("")
    print("Done.")
    print(f"Raw output: {raw_path}")
    print(f"Filtered output: {filtered_path}")
    print("")
    print("Filter notes:")
    for note in INCLUDE_NOTES:
        print(f"- {note}")


if __name__ == "__main__":
    main()