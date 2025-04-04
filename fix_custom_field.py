import os
import json

fixtures_path = os.path.join("pos_restaurant_itb", "fixtures")

def generate_name(entry, index):
    base = entry.get("doctype", "Unknown")
    field_id = entry.get("fieldname") or entry.get("label") or str(index)
    return f"{base}-{field_id}".replace(" ", "_")

def fix_fixture_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Gagal baca {filepath}: {e}")
            return

    if isinstance(data, list):
        changed = False
        for idx, entry in enumerate(data):
            if "name" not in entry or not entry["name"]:
                entry["name"] = generate_name(entry, idx)
                changed = True

        if changed:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[✔] Sudah diperbaiki: {filepath}")
        else:
            print(f"[=] Tidak ada yang perlu diperbaiki: {filepath}")
    else:
        print(f"[SKIP] Bukan list di: {filepath}")

def run():
    print("🔍 Memeriksa semua file JSON di fixtures...")
    for file in os.listdir(fixtures_path):
        if file.endswith(".json"):
            fix_fixture_file(os.path.join(fixtures_path, file))
    print("✅ Selesai!")

if __name__ == "__main__":
    run()