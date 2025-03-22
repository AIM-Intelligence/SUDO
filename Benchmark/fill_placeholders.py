import pandas as pd
import re

df = pd.read_csv('./benchmark/SUDO_dataset.csv')

def parse_extra_info(extra_info):
    if pd.isna(extra_info) or extra_info.strip().lower() == 'none':
        return None
    pairs = re.findall(r'(\w+):\s*<(\w+)>', extra_info)
    return {key: value for key, value in pairs}

def fill_placeholders_full(row):
    replacements = parse_extra_info(row['extra_info'])

    fields = ['task(publish)', 'default_url', 'topic', 'expected']
    filled_data = {}

    for field in fields:
        original_text = row.get(field, '')
        filled_text = original_text
        if replacements is not None:
            for key, value in replacements.items():
                placeholder_tag = f'<{key}>'
                filled_text = filled_text.replace(placeholder_tag, value)
        filled_data[field.replace('(publish)', '(fast)')] = filled_text

    return pd.Series(filled_data)

df_filled = df.apply(fill_placeholders_full, axis=1)

df_final = pd.concat([df, df_filled], axis=1)

df_final.to_csv('SUDO_dataset.csv', index=False)

print("SUDO dataset placeholders filled and saved to SUDO_dataset_filled.csv")