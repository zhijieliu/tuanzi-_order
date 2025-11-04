import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import os
import io

# --- 1. 国际化 (i18n) 配置 ---
# 所有UI文本都集中在这里
TRANSLATIONS = {
    "app_title": {"zh": "🧾 团子订单生成器", "en": "🧾 Tuanzi Order Generator"},
    "app_intro": {"zh": "您可以直接在下面的表格中编辑商品信息，并通过下方的上传工具为指定商品添加图片。", "en": "You can edit product information directly in the table below and add images for specific products using the upload tool."},
    "edit_table_header": {"zh": "📝 编辑商品清单", "en": "📝 Edit Product List"},
    "upload_header": {"zh": "📷 上传图片", "en": "📷 Upload Image"},
    "no_products_warning": {"zh": "请先在上方表格中添加商品行。", "en": "Please add product rows in the table above first."},
    "product_selector_label": {"zh": "选择要上传图片的商品:", "en": "Select product to upload image for:"},
    "file_uploader_label": {"zh": "点击此处上传图片...", "en": "Click here to upload an image..."},
    "upload_success_message": {"zh": "图片已成功关联到: {product_name}", "en": "Image successfully associated with: {product_name}"},
    "billing_summary_header": {"zh": "💰 最终账单汇总", "en": "💰 Final Bill Summary"},
    "subtotal_label": {"zh": "商品总计", "en": "Subtotal"},
    "tax_label": {"zh": "税价 ({rate:.0%})", "en": "Tax ({rate:.0%})"},
    "shipping_label": {"zh": "运费", "en": "Shipping Fee"},
    "grand_total_label": {"zh": "最终总计", "en": "Grand Total"},
    "settings_header": {"zh": "⚙️ 设置与操作", "en": "⚙️ Settings & Actions"},
    "shipping_input_label": {"zh": "输入运费", "en": "Enter Shipping Fee"},
    "download_button_label": {"zh": "📥 生成并下载表格图片", "en": "📥 Generate and Download Table Image"},
    "font_warning": {"zh": "SimHei 字体文件 (simhei.ttf) 未找到，请确保它和 webapp.py 在同一目录下。中文可能显示为方框。", "en": "SimHei font file (simhei.ttf) not found. Please ensure it's in the same directory as webapp.py. Chinese characters may not display correctly."},
    "image_generation_error": {"zh": "生成图片时出错: {error}", "en": "Error generating image: {error}"},
    # 表格列名
    "sn_col": {"zh": "S.N.", "en": "S.N."},
    "image_col": {"zh": "图片", "en": "Image"},
    "desc_col": {"zh": "商品名称", "en": "Product Name"},
    "price_col": {"zh": "单价(RMB)", "en": "Unit Price (RMB)"},
    "qty_col": {"zh": "数量(套)", "en": "Qty. (Set)"},
    "total_col": {"zh": "总价", "en": "Total"},
    "new_product_default_name": {"zh": "新商品", "en": "New Product"},
}

# --- 2. 语言选择与状态管理 ---
st.set_page_config(page_title="Tuanzi Order Generator", page_icon="🧾", layout="wide")

# 将语言选择器放在侧边栏
st.sidebar.title("Language / 语言")
lang_choice = st.sidebar.radio("Choose your language:", ["English", "中文"])
lang_code = 'en' if lang_choice == 'English' else 'zh'

# 翻译辅助函数
def t(key, **kwargs):
    text = TRANSLATIONS.get(key, {}).get(lang_code, f"MISSING_KEY: {key}")
    return text.format(**kwargs)

# --- Matplotlib 字体配置 ---
import matplotlib.font_manager as fm
FONT_PATH = 'simhei.ttf'
if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    plt.rcParams['font.sans-serif'] = ['SimHei']
else:
    if lang_code == 'zh': st.warning(t("font_warning"))
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# --- 动态生成列配置 ---
def get_column_config():
    return {
        "sn":      {"text": t("sn_col"), "weight": 1, "anchor": "center"},
        "image":   {"text": t("image_col"), "weight": 2.5, "anchor": "center"},
        "desc":    {"text": t("desc_col"), "weight": 5, "anchor": "w"},
        "price":   {"text": t("price_col"), "weight": 2, "anchor": "center"},
        "qty":     {"text": t("qty_col"), "weight": 1.5, "anchor": "center"},
        "total":   {"text": t("total_col"), "weight": 2, "anchor": "center"},
    }

# --- 初始化会话状态 (现在是语言相关的) ---
if 'data' not in st.session_state or st.session_state.get('lang_code') != lang_code:
    st.session_state.lang_code = lang_code
    st.session_state.data = [
        {"S.N.": 1, t("desc_col"): "黑色钢琴玩偶(KAKA)", t("price_col"): 69.0, t("qty_col"): 5, "图片数据": None},
        {"S.N.": 2, t("desc_col"): "黄色钢琴玩偶(YUki)", t("price_col"): 59.0, t("qty_col"): 5, "图片数据": None},
        {"S.N.": 3, t("desc_col"): "大提琴地毯", t("price_col"): 89.0, t("qty_col"): 5, "图片数据": None},
    ]
if 'tax_rate' not in st.session_state: st.session_state.tax_rate = 0.01
if 'shipping_fee' not in st.session_state: st.session_state.shipping_fee = 0.0

# --- 核心函数 (现在使用翻译后的列名) ---
def update_totals():
    price_col, qty_col, total_col = t("price_col"), t("qty_col"), t("total_col")
    for item in st.session_state.data:
        try:
            item[total_col] = float(item.get(price_col, 0)) * int(item.get(qty_col, 0))
        except (ValueError, TypeError):
            item[total_col] = 0.0

def generate_table_image():
    update_totals()
    COLUMN_CONFIG = get_column_config()
    desc_col, price_col, qty_col, total_col = t("desc_col"), t("price_col"), t("qty_col"), t("total_col")
    
    headers = [cfg["text"] for cfg in COLUMN_CONFIG.values()]
    cell_data = []
    for item in st.session_state.data:
        cell_data.append([
            item["S.N."], "", item[desc_col], f'{item.get(price_col, 0.0):.2f}',
            item.get(qty_col, 0), f'{item.get(total_col, 0.0):.2f}'
        ])

    subtotal = sum(item.get(total_col, 0) for item in st.session_state.data)
    tax = subtotal * st.session_state.tax_rate
    grand_total = subtotal + tax + st.session_state.shipping_fee

    summary_rows = [
        {"label": t("tax_label", rate=st.session_state.tax_rate), "value": f"{tax:.2f}"},
        {"label": t("shipping_label"), "value": f'{st.session_state.shipping_fee:.2f}'},
        {"label": t("grand_total_label"), "value": f"{grand_total:,.2f}"}
    ]
    for row in summary_rows: cell_data.append(["", "", "", "", row["label"], row["value"]])

    fig_height_inches = (len(cell_data) + 1) * 0.6
    fig, ax = plt.subplots(figsize=(12, fig_height_inches), dpi=300)
    ax.axis('off')

    col_widths = [cfg["weight"] / sum(c["weight"] for c in COLUMN_CONFIG.values()) for cfg in COLUMN_CONFIG.values()]
    table = ax.table(cellText=cell_data, colLabels=headers, loc='center', cellLoc='center', colWidths=col_widths)
    table.auto_set_font_size(False); table.set_fontsize(10)
    
    align_map = {'w': 'left', 'e': 'right', 'center': 'center'}
    for (i, j), cell in table.get_celld().items():
        cell.set_edgecolor('#cccccc'); cell.set_height(0.6 / fig_height_inches)
        col_id = list(COLUMN_CONFIG.keys())[j]
        anchor = COLUMN_CONFIG.get(col_id, {}).get("anchor", "center")
        ha_align = align_map.get(anchor, 'left')
        if i == 0: cell.set_facecolor('#f0f0f0'); cell.set_text_props(weight='bold', ha=ha_align)
        elif i > len(st.session_state.data):
            cell.set_facecolor('#fafafa')
            if j < 4: cell.set_edgecolor('#fafafa'); cell.get_text().set_color('#fafafa')
            elif j == 4: cell.set_edgecolor('#fafafa'); cell.set_text_props(ha='right', va='center', weight='bold', color='#003366')
            else: cell.set_text_props(weight='bold', ha='center')
        else: cell.set_text_props(ha=ha_align, va='center')

    fig.canvas.draw()
    for i, item in enumerate(st.session_state.data):
        img_bytes = item.get("图片数据")
        if img_bytes:
            try:
                img = Image.open(io.BytesIO(img_bytes))
                img.thumbnail((50, 50), Image.LANCZOS)
                im_offset = OffsetImage(img, zoom=1)
                cell = table.get_celld()[(i + 1, 1)]
                bbox = cell.get_bbox()
                ab = AnnotationBbox(im_offset, (bbox.x0 + bbox.width / 2, bbox.y0 + bbox.height / 2),
                                    xycoords='axes fraction', box_alignment=(0.5, 0.5), frameon=False, pad=0)
                ax.add_artist(ab)
            except Exception as e:
                st.error(t("image_generation_error", error=e))

    buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight', dpi=300, pad_inches=0.1); plt.close(fig); buf.seek(0)
    return buf

# --- 3. Streamlit UI (使用翻译函数 t() ) ---

st.title(t("app_title"))
st.markdown(t("app_intro"))

st.header(t("edit_table_header"))
df_for_editor = pd.DataFrame(st.session_state.data).drop(columns=['图片数据'], errors='ignore')
edited_df = st.data_editor(df_for_editor, use_container_width=True, num_rows="dynamic", key="data_editor")

if edited_df is not None:
    img_data_map = {item['S.N.']: item.get('图片数据') for item in st.session_state.data}
    st.session_state.data = edited_df.to_dict('records')
    for i, item in enumerate(st.session_state.data):
        item["S.N."] = i + 1
        item["图片数据"] = img_data_map.get(item["S.N."])

update_totals()

st.divider()

st.header(t("upload_header"))
if not st.session_state.data:
    st.warning(t("no_products_warning"))
else:
    product_options = [f'{item["S.N."]}. {item[t("desc_col")]}' for item in st.session_state.data]
    selected_product_str = st.selectbox(t("product_selector_label"), product_options, key="product_selector")
    uploaded_file = st.file_uploader(t("file_uploader_label"), type=["png", "jpg", "jpeg", "gif"], key="file_uploader")

    if uploaded_file is not None and selected_product_str:
        selected_index = product_options.index(selected_product_str)
        st.session_state.data[selected_index]["图片数据"] = uploaded_file.getvalue()
        st.success(t("upload_success_message", product_name=selected_product_str))
        st.image(uploaded_file, caption=f"Preview for {selected_product_str}", width=100)

st.divider()

col1, col2 = st.columns([3, 1])
with col1:
    st.header(t("billing_summary_header"))
    subtotal = sum(item.get(t("total_col"), 0) for item in st.session_state.data)
    tax = subtotal * st.session_state.tax_rate
    shipping_fee = st.session_state.get('shipping_fee', 0.0)
    grand_total = subtotal + tax + shipping_fee
    st.metric(t("subtotal_label"), f"¥ {subtotal:,.2f}")
    st.metric(t("tax_label", rate=st.session_state.tax_rate), f"¥ {tax:,.2f}")
    st.metric(t("shipping_label"), f"¥ {shipping_fee:,.2f}")
    st.metric(t("grand_total_label"), f"¥ {grand_total:,.2f}", delta="CNY")

with col2:
    st.header(t("settings_header"))
    st.session_state.shipping_fee = st.number_input(t("shipping_input_label"), value=st.session_state.shipping_fee, min_value=0.0, step=1.0)
    st.download_button(t("download_button_label"), generate_table_image(), "commodity_table.png", "image/png")
