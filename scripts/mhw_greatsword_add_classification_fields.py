import pandas as pd
from pathlib import Path

INPUT_CSV = "mhw_greatsword_filtered.csv"
OUTPUT_CSV = "mhw_greatsword_classified.csv"


def contains_any(text: str, keywords: list[str]) -> bool:
    if text is None:
        return False
    text = str(text)
    return any(keyword in text for keyword in keywords)


def classify_weapon(row: pd.Series) -> dict:
    """
    给大剑 Final Upgrade 数据添加分类字段。

    设计口径：
    - 不物理删除特殊武器；
    - 常规素材 / 古龙 / 金银火进入 train_core；
    - 公会宫殿、活动武器作为 marked validation；
    - 绚辉 / 冥赤 / 煌黑 / 黑龙 / 激昂 / 猛爆作为 special validation；
    - 防卫队作为 progression catch-up，不进入 EFR 训练，但可单独讨论。
    """
    name = str(row.get("weapon_name", "") or "")
    url = str(row.get("weapon_url", "") or "")
    text = f"{name} {url}"

    # ---------- 1. 追赶机制 / 明确不参与训练 ----------
    defender_keywords = [
        "防卫队", "防衛隊", "fang-wei-dui", "defender",
    ]

    if contains_any(text, defender_keywords):
        return {
            "source_category_detailed": "defender",
            "model_role": "exclude_progression",
            "efr_train_inclusion": False,
            "validation_inclusion": True,
            "classification_note": "追赶机制武器；不参与常规预算拟合，可用于验证 progression catch-up 是否超出同稀有度曲线。",
        }

    # ---------- 2. 终局 / 系统外特殊武器 ----------
    fatalis_keywords = [
        "黑龙", "黑龍", "hei-long", "Fatalis", "fatalis",
    ]

    if contains_any(text, fatalis_keywords):
        return {
            "source_category_detailed": "fatalis",
            "model_role": "validation_special",
            "efr_train_inclusion": False,
            "validation_inclusion": True,
            "classification_note": "黑龙终局武器；用于验证最终版本 power ceiling / 终局奖励是否显著超出常规预算。",
        }

    alatreon_keywords = [
        "煌黑", "煌黒", "huang-hei", "Alatreon", "alatreon",
    ]

    if contains_any(text, alatreon_keywords):
        return {
            "source_category_detailed": "alatreon",
            "model_role": "validation_special",
            "efr_train_inclusion": False,
            "validation_inclusion": True,
            "classification_note": "煌黑龙武器；用于验证高属性 / 高斩味终局武器相对常规预算的偏离。",
        }

    safi_keywords = [
        "赤龙", "赤龍", "冥赤", "冥赤龙", "冥赤龍",
        "chi-long-duan-jue", "Safi", "safi",
    ]

    if contains_any(text, safi_keywords):
        return {
            "source_category_detailed": "siege_safi",
            "model_role": "validation_special",
            "efr_train_inclusion": False,
            "validation_inclusion": True,
            "classification_note": "冥赤龙 / 赤龙武器；基础表格不包含完整觉醒系统预算，用作系统外验证样本。",
        }

    kulve_keywords = [
        "绚辉", "絢輝", "绚辉龙", "絢輝龍",
        "铠罗", "鎧羅", "凯罗", "凱羅",
        "皇金", "金色的大剑", "金色的大劍",
        "kai-luo", "huang-jin", "jin-se-de-da-jian",
        "Kulve", "kulve", "Taroth", "taroth", "Kjarr", "kjarr",
    ]

    if contains_any(text, kulve_keywords):
        return {
            "source_category_detailed": "siege_kulve",
            "model_role": "validation_special",
            "efr_train_inclusion": False,
            "validation_inclusion": True,
            "classification_note": "绚辉龙 / 凯罗 / 皇金武器；攻城与鉴定系统武器，用于验证非普通素材树预算。",
        }

    variant_endgame_keywords = [
        # 激昂金狮子
        "激昂", "猿魔王", "gui-shen-jin-bang-yuan-mo-wang",
        # 猛爆碎龙 / Raging Brachydios
        "猛爆", "碎光", "sui-guang",
        # 注意：用户核验“罪罚粉碎者2”不是猛爆碎龙武器，因此不写入这里。
    ]

    if contains_any(text, variant_endgame_keywords):
        return {
            "source_category_detailed": "variant_endgame",
            "model_role": "validation_special",
            "efr_train_inclusion": False,
            "validation_inclusion": True,
            "classification_note": "MR 后期变体 / 特殊强怪武器；用于验证版本后期素材武器是否存在额外预算溢价。",
        }

    # ---------- 3. 保留但标记的非普通素材 ----------
    guild_palace_keywords = [
        "公会", "公會", "宫廷", "宮廷", "宫殿", "宮殿",
        "gong-hui", "gong-ting", "gong-dian", "jin-xing",
    ]

    if contains_any(text, guild_palace_keywords):
        return {
            "source_category_detailed": "guild_palace",
            "model_role": "validation_marked",
            "efr_train_inclusion": False,
            "validation_inclusion": True,
            "classification_note": "公会 / 宫殿系武器；保留但不参与常规素材预算拟合，用于验证其是否贴近常规曲线。",
        }

    event_special_keywords = [
        "爆热机关式", "爆熱機關式", "bao-re-ji-guan",
        "瞬间冷冻剑鱼", "瞬間冷凍劍魚", "shun-jian-leng-dong-jian-yu",
    ]

    if contains_any(text, event_special_keywords):
        return {
            "source_category_detailed": "event_special",
            "model_role": "validation_marked",
            "efr_train_inclusion": False,
            "validation_inclusion": True,
            "classification_note": "活动 / 特殊外观武器；保留为 marked validation，不参与常规预算拟合。",
        }

    # ---------- 4. 训练集：常规素材、古龙、稀有亚种 ----------
    rare_subspecies_keywords = [
        "金火", "银火", "銀火", "金火龙", "银火龙", "銀火龍",
        "辉剑火龙", "hui-jian-huo-long",
    ]

    if contains_any(text, rare_subspecies_keywords):
        return {
            "source_category_detailed": "rare_subspecies",
            "model_role": "train_core",
            "efr_train_inclusion": True,
            "validation_inclusion": False,
            "classification_note": "金火龙 / 银火龙等稀有亚种素材武器；纳入常规素材预算训练集。",
        }

    elder_dragon_keywords = [
        "灭鬼", "滅鬼", "灭尽", "滅盡", "歼世", "殲世",
        "钢龙", "鋼龍", "麒麟", "冥灯", "冥燈", "炎妃",
        "熔山", "尸套", "屍套", "封龙", "封龍",
        "怨憎", "冰翼灵羽", "冰翼靈羽", "无相法身", "無相法身",
        "mie-gui", "gang-long", "qi-lin", "ming-deng", "yan-fei",
        "rong-shan", "shi-tao", "feng-long", "yuan-zeng", "bing-yi-ling-yu", "wu-xiang",
    ]

    if contains_any(text, elder_dragon_keywords):
        return {
            "source_category_detailed": "elder_dragon",
            "model_role": "train_core",
            "efr_train_inclusion": True,
            "validation_inclusion": False,
            "classification_note": "古龙素材武器；纳入常规预算训练集。",
        }

    # ---------- 5. 默认：普通素材武器 ----------
    return {
        "source_category_detailed": "material_standard",
        "model_role": "train_core",
        "efr_train_inclusion": True,
        "validation_inclusion": False,
        "classification_note": "普通素材树 Final Upgrade；纳入常规预算训练集。",
    }


def main():
    input_path = Path(INPUT_CSV)

    if not input_path.exists():
        raise FileNotFoundError(f"找不到输入文件：{INPUT_CSV}")

    df = pd.read_csv(input_path)

    classifications = df.apply(classify_weapon, axis=1, result_type="expand")

    # 如果原 CSV 里已有旧 source_category / include_in_model，可保留原列，同时新增更明确的新列。
    df_out = pd.concat([df, classifications], axis=1)

    # 为了兼容旧字段，也同步生成 include_in_efr_train。
    df_out["include_in_efr_train"] = df_out["efr_train_inclusion"]
    df_out["include_in_validation"] = df_out["validation_inclusion"]

    df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"Input:  {INPUT_CSV}")
    print(f"Output: {OUTPUT_CSV}")
    print("")
    print("model_role counts:")
    print(df_out["model_role"].value_counts(dropna=False))
    print("")
    print("source_category_detailed counts:")
    print(df_out["source_category_detailed"].value_counts(dropna=False))


if __name__ == "__main__":
    main()